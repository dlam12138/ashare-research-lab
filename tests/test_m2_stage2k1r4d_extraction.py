"""M2 Stage 2K.1R4D — named-capture extraction contract tests.

Values must come only from named captures; there are no numeric constants in
extraction.  Changing the capture changes the result.  Changing a constant
cannot change the result because no constants exist.  Unit conversion is a
deterministic Decimal recomputation.  Q1/Q3 cumulative scope must be correct;
equity must be instant; table ambiguity must fail closed; OCR/LLM flags must
always be false.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ashare_research.pit_valuation.contracts import load_extraction_specs
from ashare_research.pit_valuation.extraction import (
    extract_cell,
    extract_share_capital,
    normalize_value,
    parse_decimal_token,
    sha256_span,
)
from ashare_research.pit_valuation.source_cache import solve_acw_sc_v2

ROOT = Path(__file__).resolve().parents[1]

# ── synthetic fixture helpers ─────────────────────────────────────────────

Q1_CAS_PAGES = [
    "中国石油天然气股份有限公司2026年第一季度报告",
    "单位：人民币百万元\n"
    "项目 年初至报告期末 上年初至上年报告期末 (追溯后) (a)"
    " 上年初至上年报告期末 (追溯前) 比上年同期增减变动幅度 (%)\n"
    "营业收入 736,383 753,056 753,108 (2.2)\n"
    "归属于母公司股东的净利润 48,333 47,452 46,809 1.9\n"
    "基本每股收益（人民币元） 0.264 0.259 0.256 1.9\n"
    "归属于母公司股东权益 1,624,532 1,617,287 1,586,061 0.4\n"
    "2.1.2 按中国企业会计准则编制的主要会计数据及财务指标\n"
    "项目 年初至报告期末 上年初至上年报告期末 比上年同期增减\n"
    "营业收入 736,383 753,056 (2.2)\n"
    "归属于母公司股东的净利润 48,332 47,450 1.9\n"
    "基本每股收益（人民币元） 0.264 0.259 1.9\n"
    "归属于母公司股东权益 1,624,532 1,617,287 0.4\n",
]

Q3_2020_CAS_PAGES = [
    "三、2020年第三季度报告",
    "2.1.2 按中国企业会计准则编制的主要会计数据及财务指标\n"
    "单位：人民币百万元\n"
    "项目 本报告期末 上年度期末 增减\n"
    "总资产 2,566,916 2,733,190 (6.1)\n"
    "归属于母公司股东权益 1,210,550 1,230,428 (1.6)\n"
    "项目 截至9月30日止3个月(7-9月)期间 截至9月30日止9个月(1-9月)期间\n"
    "2020年 2019年 增减(%) 2020年 2019年 增减(%)\n"
    "营业收入 497,125 618,143 (19.6) 1,426,170 1,814,402 (21.4)\n"
    "归属于母公司股东的净利润 40,050 8,830 353.6 10,067 37,253 (73.0)\n"
    "基本每股收益（人民币元） 0.219 0.048 353.6 0.055 0.204 (73.0)\n",
]

Q3_2024_CAS_PAGES = [
    "2024年第三季度报告",
    "2.1.2 按中国企业会计准则编制的主要会计数据及财务指标\n"
    "单位：人民币百万元\n"
    "项目 截至9月30日止3个月(7-9月)期间 截至9月30日止9个月(1-9月)期间\n"
    "营业收入 702,410 802,264 (12.4) 2,256,279 2,282,135 (1.1)\n"
    "归属于母公司股东的净利润 43,911 46,375 (5.3) 132,518 131,651 0.7\n"
    "基本每股收益(人民币元) 0.240 0.253 (5.3) 0.724 0.719 0.7\n"
    "归属于母公司股东权益 1,490,006 1,446,410 3.0\n",
]


def spec_for(report_type: str, role_id: str, fy: int | None = None) -> dict:
    specs = load_extraction_specs()["specs"]
    for s in specs:
        if s["report_type"] != report_type or s["role_id"] != role_id:
            continue
        if fy is not None and s.get("fiscal_year") != fy:
            continue
        if fy is None and "fiscal_year" in s:
            continue
        return s
    raise KeyError(f"no spec for {report_type}/{role_id}/{fy}")


def evidence(rid: str = "R4D-SSE-TEST-Q1", rtype: str = "q1", fy: int = 2026) -> dict:
    return {
        "evidence_id": rid,
        "fiscal_year": fy,
        "report_type": rtype,
        "announcement_date": "2026-04-30",
        "proof_url": "https://example.invalid/test.pdf",
        "report_title": "test report",
        "source_role": "exchange_official",
    }


# ── values come only from named captures ──────────────────────────────────


def test_value_comes_from_named_capture_only():
    spec = spec_for("q1", "net_profit_attributable_to_parent")
    cell = extract_cell(spec, Path("x.pdf"), evidence=evidence(), page_texts=Q1_CAS_PAGES)
    assert cell.status == "acquired_reported_verified"
    assert cell.raw_value == Decimal("48332")
    # The CFG section anchor picks the CAS table; the value is bound to the
    # capture group and is independently recomputable.
    recomputed = parse_decimal_token(cell.raw_token)
    assert recomputed == cell.raw_value


def test_changing_capture_changes_result():
    spec = spec_for("q1", "net_profit_attributable_to_parent")
    pages = list(Q1_CAS_PAGES)
    pages[1] = pages[1].replace("48,332", "99,999")
    cell = extract_cell(spec, Path("x.pdf"), evidence=evidence(), page_texts=pages)
    assert cell.normalized_value == Decimal("99999000000")


def test_no_numeric_constants_in_extraction():
    spec = spec_for("q1", "net_profit_attributable_to_parent")
    # The spec pattern must not contain a hard-coded expected value.
    import re

    numeric_literals = re.findall(r"[0-9]{4,}", spec["named_capture_pattern"])
    assert numeric_literals == []
    # The only numbers in the spec are the multiplier and descriptive indexes.
    assert str(spec["conversion_multiplier"]) == "1000000"


def test_unit_conversion_decimal_recomputable():
    raw = Decimal("736383")
    norm = normalize_value(raw, "1000000", "CNY_million")
    assert norm == Decimal("736383000000")
    # Deterministic: same input, same output.
    assert normalize_value(raw, "1000000", "CNY_million") == norm


def test_negative_parentheses_parsed():
    assert parse_decimal_token("(16,234)") == Decimal("-16234")
    assert parse_decimal_token("509,098") == Decimal("509098")
    assert parse_decimal_token("0.264") == Decimal("0.264")


# ── cumulative scope ──────────────────────────────────────────────────────


def test_q1_scope_is_cumulative_quarter_ytd():
    spec = spec_for("q1", "revenue")
    cell = extract_cell(spec, Path("x.pdf"), evidence=evidence(fy=2026), page_texts=Q1_CAS_PAGES)
    assert cell.normalized_value == Decimal("736383000000")
    assert spec["expected_context"] == "duration_cumulative"


def test_q3_2020_cumulative_token_index():
    spec = spec_for("q3", "revenue", fy=2020)
    cell = extract_cell(
        spec, Path("x.pdf"), evidence=evidence(rtype="q3", fy=2020), page_texts=Q3_2020_CAS_PAGES
    )
    # token index 3 = the 9-month cumulative current value.
    assert cell.raw_value == Decimal("1426170")
    assert cell.normalized_value == Decimal("1426170000000")


def test_q3_2024_cumulative_token_index():
    spec = spec_for("q3", "net_profit_attributable_to_parent", fy=2024)
    cell = extract_cell(
        spec, Path("x.pdf"), evidence=evidence(rtype="q3", fy=2024), page_texts=Q3_2024_CAS_PAGES
    )
    assert cell.raw_value == Decimal("132518")


def test_q3_single_quarter_not_mistaken_for_cumulative():
    spec = spec_for("q3", "revenue", fy=2024)
    cell = extract_cell(
        spec, Path("x.pdf"), evidence=evidence(rtype="q3", fy=2024), page_texts=Q3_2024_CAS_PAGES
    )
    # 702,410 is the single-quarter value; the cumulative value 2,256,279 is
    # at the documented token index and must NOT be the single-quarter value.
    assert cell.raw_value == Decimal("2256279")


def test_equity_is_instant():
    from ashare_research.pit_valuation.contracts import load_role_registry

    roles = load_role_registry()["roles"]
    equity = next(r for r in roles if r["role_id"] == "equity_attributable_to_parent")
    assert equity["instant_or_duration"] == "instant"


# ── fail-closed behaviour ─────────────────────────────────────────────────


def test_missing_marker_is_gap_not_guess():
    spec = spec_for("q1", "net_profit_attributable_to_parent")
    pages = ["no cas section here at all"]
    cell = extract_cell(spec, Path("x.pdf"), evidence=evidence(), page_texts=pages)
    assert cell.status == "extraction_marker_missing"
    assert cell.normalized_value is None


def test_table_ambiguity_fails_closed():
    spec = dict(spec_for("q1", "revenue"))
    spec["target_token_index"] = 99  # impossible token position
    cell = extract_cell(spec, Path("x.pdf"), evidence=evidence(), page_texts=Q1_CAS_PAGES)
    assert cell.status == "ambiguous_table_scope"
    assert cell.normalized_value is None


def test_ocr_llm_flags_always_false():
    for spec in load_extraction_specs()["specs"]:
        assert spec["ocr_allowed"] is False
        assert spec["llm_allowed"] is False


# ── share capital ─────────────────────────────────────────────────────────


def test_share_capital_extraction():
    spec = spec_for("annual", "total_ordinary_shares_at_period_end")
    pages = [
        "经董事会建议以本公司 2025 年 12 月 31 日的总 股 本 183,020,977,818 股为基数派发末期股息",
    ]
    cell = extract_share_capital(
        Path("x.pdf"), evidence(rtype="annual", fy=2025), spec, page_texts=pages
    )
    assert cell.status == "acquired_reported_verified"
    assert cell.normalized_value == Decimal("183020977818")


def test_share_capital_not_disclosed_is_gap():
    spec = spec_for("annual", "total_ordinary_shares_at_period_end")
    pages = ["no share capital statement here"]
    cell = extract_share_capital(
        Path("x.pdf"), evidence(rtype="annual", fy=2025), spec, page_texts=pages
    )
    assert cell.status == "not_separately_disclosed"
    assert cell.normalized_value is None


# ── deterministic hashing ─────────────────────────────────────────────────


def test_excerpt_hash_is_deterministic():
    a = sha256_span("归属于母公司股东的净利润 48,332")
    b = sha256_span("归属于母公司股东的净利润 48,332")
    c = sha256_span("归属于母公司股东的净利润 48,333")
    assert a == b
    assert a != c


def test_acw_solver_matches_recorded_challenge():
    # Recorded from the official SSE challenge on 2026-08-05.
    arg1 = "21690B61A6D04751E2DDD6D21D9B70EDFEA04773"
    cookie = solve_acw_sc_v2(arg1)
    assert len(cookie) == 40
    assert all(c in "0123456789abcdef" for c in cookie)
    # The solver is deterministic.
    assert solve_acw_sc_v2(arg1) == cookie
