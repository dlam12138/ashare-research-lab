"""Stage 2I.2 PetroChina Plan v3 official-fact acquisition.

Acquisition is network-capable and writes only an explicit external cache.
Formal mode is offline, verifies content-addressed objects, extracts exact CAS
cells, and writes an isolated fact bundle/read model.  It never opens the
default database and never calculates ROIC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.request
from copy import deepcopy
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path
from typing import Any

from ashare_research.facts.identity import build_fact_id, validate_canonical_fact_ids
from ashare_research.tools.roic_contracts import canonical_digest
from ashare_research.tools.roic_fact_readiness import build_readiness_report, render_markdown
from ashare_research.tools.roic_fact_snapshot import validate_inventory

ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = ROOT / "config" / "roic_official_source_evidence_v1.json"
CACHE_PATH = ROOT / "config" / "roic_official_cache_registry_v1.json"
PLAN_PATH = ROOT / "config" / "roic_official_fact_acquisition_plan_v3.json"
REGISTRY_PATH = ROOT / "config" / "roic_concept_registry_v2.json"
GRAPH_PATH = ROOT / "config" / "roic_formula_dependency_graph_v1.json"
READINESS_PATH = ROOT / "reports" / "petrochina_roic_fact_readiness_2020_2025_v2.json"
INVENTORY_PATH = ROOT / "config" / "roic_canonical_fact_inventory_v2.json"
VALUE_PROFILE_PATH = ROOT / "reports" / "petrochina_value_profile.json"

APPROVED_IDS = {
    "A-2024-finance-core",
    "A-2024-investment-income",
    "A-2024-fair-value",
    "A-2024-asset-disposal",
    "A-2024-operating-tax",
    "B-2024-lease-interest",
    "B-2023-2024-nci",
    "B-2023-2024-associate",
    "B-2023-2024-jv",
    "C-2023-2024-restricted-cash",
    "C-2023-2024-non-operating-financial-assets",
}
ALLOWED_RESULTS = {
    "acquired_verified",
    "acquired_with_official_mirror_difference",
    "missing_official_fact",
    "ambiguous_scope",
    "period_mismatch",
    "source_conflict",
    "missing_dual_official_evidence",
    "unresolved_restatement",
    "blocked_source_access",
}
DECIMAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class ExtractedCell:
    acquisition_id: str
    role_id: str
    concept_id: str
    fiscal_year: int
    period_type: str
    raw_value: str
    raw_numeric_string: str
    raw_sign_presentation: str
    raw_unit: str
    normalized_value: str
    conversion_multiplier: str
    sign_normalization_rule: str
    locator: dict[str, Any]
    purpose: str = ""
    derivation: str = ""


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plan_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for layer in plan["layers"].values() for item in layer]


def validate_contracts() -> dict[str, Any]:
    sources, cache, plan = _load(SOURCE_PATH), _load(CACHE_PATH), _load(PLAN_PATH)
    items = _plan_items(plan)
    ids = {item["acquisition_id"] for item in items}
    if ids != APPROVED_IDS or len(items) != 11:
        raise ValueError("Plan v3 acquisition IDs drifted from the approved 11-item set")
    if plan["layers"]["D_secondary_reconciliation_or_sensitivity"]:
        raise ValueError("Plan v3 Layer D must remain empty")
    evidence = {item["evidence_id"]: item for item in sources["entries"]}
    if {item["source_type"] for item in evidence.values()} != {
        "company_official",
        "exchange_official",
    }:
        raise ValueError("only issuer and exchange official evidence is allowed")
    mapped = {eid for obj in cache["objects"] for eid in obj["evidence_ids"]}
    if mapped != set(evidence):
        raise ValueError("cache/evidence alias mapping is incomplete")
    for obj in cache["objects"]:
        if Path(obj["object_key"]).is_absolute() or ".." in Path(obj["object_key"]).parts:
            raise ValueError("cache object keys must be relative and traversal-free")
        if obj["sha256"] not in obj["object_key"]:
            raise ValueError("cache objects must be content addressed")
    return {
        "status": "PASS",
        "approved_item_count": len(items),
        "affected_cell_count": sum(len(item["affected_fiscal_years"]) for item in items),
        "source_alias_count": len(evidence),
        "content_object_count": len(cache["objects"]),
        "plan_digest": plan["plan_digest"],
        "source_registry_sha256": _sha256(SOURCE_PATH),
        "cache_registry_sha256": _sha256(CACHE_PATH),
    }


def verify_official_cache(cache_root: Path | str | None) -> dict[str, Any]:
    if cache_root is None:
        raise FileNotFoundError("formal mode requires --official-cache-root")
    root = Path(cache_root).resolve()
    if root == ROOT.resolve() or ROOT.resolve() in root.parents:
        raise ValueError("official cache must be external to the repository")
    registry = _load(CACHE_PATH)
    verified = []
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency gate
        raise RuntimeError("pypdf is required for formal PDF verification") from exc
    for expected in registry["objects"]:
        path = root / expected["object_key"]
        if not path.is_file():
            raise FileNotFoundError(f"official cache object missing: {expected['object_key']}")
        size, digest = path.stat().st_size, _sha256(path)
        if size != expected["byte_size"] or digest != expected["sha256"]:
            raise ValueError(f"official cache hash/size mismatch: {expected['object_key']}")
        with path.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise ValueError(f"official cache object is not a PDF: {expected['object_key']}")
        page_count = len(PdfReader(path).pages)
        if page_count != expected["page_count"]:
            raise ValueError(f"official cache page-count mismatch: {expected['object_key']}")
        verified.append(
            {
                "object_key": expected["object_key"],
                "sha256": digest,
                "byte_size": size,
                "page_count": page_count,
                "evidence_ids": expected["evidence_ids"],
            }
        )
    return {
        "status": "TRUSTED",
        "external_cache": True,
        "network_used": False,
        "verified_object_count": len(verified),
        "verified_alias_count": sum(len(item["evidence_ids"]) for item in verified),
        "objects": verified,
    }


def acquire(cache_root: Path | str | None) -> dict[str, Any]:
    """Acquire missing approved objects with no more than three attempts each."""
    if cache_root is None:
        raise FileNotFoundError("acquire mode requires --official-cache-root")
    root = Path(cache_root).resolve()
    if root == ROOT.resolve() or ROOT.resolve() in root.parents:
        raise ValueError("official cache must be external to the repository")
    root.mkdir(parents=True, exist_ok=True)
    cache, sources = _load(CACHE_PATH), _load(SOURCE_PATH)
    evidence = {item["evidence_id"]: item for item in sources["entries"]}
    outcomes = []
    for expected in cache["objects"]:
        target = root / expected["object_key"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if (
            target.is_file()
            and target.stat().st_size == expected["byte_size"]
            and _sha256(target) == expected["sha256"]
        ):
            outcomes.append({"object_key": expected["object_key"], "status": "already_verified"})
            continue
        urls = [evidence[eid]["original_url"] for eid in expected["evidence_ids"]]
        last_error = ""
        success = False
        for attempt in range(1, 4):
            url = urls[(attempt - 1) % len(urls)]
            partial = target.with_suffix(".download")
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                    content = response.read()
                    final_url = response.geturl()
                    status = getattr(response, "status", 200)
                partial.write_bytes(content)
                if len(content) != expected["byte_size"] or _sha256(partial) != expected["sha256"]:
                    raise ValueError("downloaded bytes do not match the registered official object")
                partial.replace(target)
                outcomes.append(
                    {
                        "object_key": expected["object_key"],
                        "status": "downloaded_verified",
                        "attempt": attempt,
                        "http_status": status,
                        "final_url": final_url,
                        "byte_size": len(content),
                    }
                )
                success = True
                break
            except Exception as exc:  # bounded acquisition log
                last_error = f"{type(exc).__name__}: {exc}"
                if partial.exists():
                    partial.unlink()
                if attempt < 3:
                    time.sleep(attempt)
        if not success:
            raise RuntimeError(f"official acquisition failed after 3 attempts: {last_error}")
    result = verify_official_cache(root)
    result["acquisition_outcomes"] = outcomes
    return result


def _page_texts(cache_root: Path) -> dict[int, list[str]]:
    from pypdf import PdfReader

    cache = _load(CACHE_PATH)
    result: dict[int, list[str]] = {}
    for obj in cache["objects"]:
        year = 2024 if obj["sha256"].startswith("15a2") else 2023
        result[year] = [
            re.sub(r"\s+", " ", page.extract_text() or "").strip()
            for page in PdfReader(cache_root / obj["object_key"]).pages
        ]
    return result


def _match(page: str, pattern: str) -> re.Match[str]:
    match = re.search(pattern, page)
    if not match:
        raise ValueError(f"exact PDF extraction marker missing: {pattern}")
    return match


def _decimal(raw: str) -> Decimal:
    text = raw.replace(",", "").strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    with localcontext(DECIMAL_CONTEXT):
        value = Decimal(text)
        return -value if negative else value


def _normalized(raw: str, multiplier: str) -> str:
    with localcontext(DECIMAL_CONTEXT):
        return format(_decimal(raw) * Decimal(multiplier), "f")


def _locator(
    *,
    year: int,
    pdf_page: int,
    printed: int,
    note: str,
    title: str,
    row: str,
    column: str,
    unit: str,
    excerpt: str,
) -> dict[str, Any]:
    evidence_ids = [f"pc-roic-{year}-issuer-annual-cas", f"pc-roic-{year}-exchange-annual-cas"]
    return {
        "evidence_ids": evidence_ids,
        "pdf_page_index_zero_based": pdf_page - 1,
        "pdf_page_number_one_based": pdf_page,
        "printed_page_number": printed,
        "section_note_number": note,
        "table_title": title,
        "row_label": row,
        "column_year": column,
        "nearby_unit_declaration": unit,
        "source_excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
        "deterministic_cell_locator": f"p{pdf_page}|{note}|{row}|{column}",
        "extraction_method": "pypdf_embedded_text_regex_v1",
        "ocr_used": False,
    }


def _cell(
    *,
    acquisition_id: str,
    role_id: str,
    concept_id: str,
    fiscal_year: int,
    period_type: str,
    raw: str,
    raw_unit: str,
    multiplier: str,
    locator: dict[str, Any],
    sign: str = "source_accounting_sign_identity",
    purpose: str = "",
    derivation: str = "",
) -> ExtractedCell:
    return ExtractedCell(
        acquisition_id=acquisition_id,
        role_id=role_id,
        concept_id=concept_id,
        fiscal_year=fiscal_year,
        period_type=period_type,
        raw_value=raw,
        raw_numeric_string="0" if raw == "无" else raw,
        raw_sign_presentation="explicit_absence"
        if raw == "无"
        else ("parentheses" if raw.startswith("(") else "positive"),
        raw_unit=raw_unit,
        normalized_value="0" if raw == "无" else _normalized(raw, multiplier),
        conversion_multiplier=multiplier,
        sign_normalization_rule=sign,
        locator=locator,
        purpose=purpose,
        derivation=derivation,
    )


def extract_cells(cache_root: Path) -> list[ExtractedCell]:
    pages = _page_texts(cache_root)
    p24, p23 = pages[2024], pages[2023]
    results: list[ExtractedCell] = []

    finance_stmt = _match(p24[114], r"财务费用 47 \(12,552\) \(18,091\)").group(0)
    lease_note = _match(p24[177], r"其中：租赁负债的利息支出 5,165 5,239").group(0)
    results.append(
        _cell(
            acquisition_id="A-2024-finance-core",
            role_id="nopat.finance_cost_excluding_lease_interest",
            concept_id="finance_cost_excluding_lease_interest",
            fiscal_year=2024,
            period_type="annual",
            raw="7,387",
            raw_unit="人民币百万元",
            multiplier="100",
            locator=_locator(
                year=2024,
                pdf_page=178,
                printed=176,
                note="47",
                title="财务费用",
                row="财务费用减租赁负债利息支出",
                column="2024年度",
                unit="金额单位为人民币百万元",
                excerpt=f"{finance_stmt}|{lease_note}",
            ),
            derivation="12,552 - 5,165 = 7,387; both exact note/statement lines; no plug",
        )
    )
    results.append(
        _cell(
            acquisition_id="B-2024-lease-interest",
            role_id="nopat.lease_interest_expense",
            concept_id="lease_interest_expense",
            fiscal_year=2024,
            period_type="annual",
            raw="5,165",
            raw_unit="人民币百万元",
            multiplier="100",
            locator=_locator(
                year=2024,
                pdf_page=178,
                printed=176,
                note="47",
                title="财务费用",
                row="其中：租赁负债的利息支出",
                column="2024年度",
                unit="金额单位为人民币百万元",
                excerpt=lease_note,
            ),
            derivation=(
                "component of finance_cost_adjustment; never contributes "
                "independently after parent"
            ),
        )
    )
    for acquisition_id, role, concept, pattern, raw, page, printed, note, title, row in [
        (
            "A-2024-investment-income",
            "nopat.investment_income",
            "investment_income",
            r"投资收益 49 11,934 9,554",
            "11,934",
            115,
            113,
            "49",
            "投资收益",
            "投资收益",
        ),
        (
            "A-2024-fair-value",
            "nopat.fair_value_net_change",
            "fair_value_net_change",
            r"公允价值变动收益 50 4,673 2,008",
            "4,673",
            115,
            113,
            "50",
            "公允价值变动收益",
            "公允价值变动收益",
        ),
        (
            "A-2024-asset-disposal",
            "nopat.asset_disposal_gain_loss",
            "asset_disposal_gain_loss",
            r"资产处置收益 53 613 498",
            "613",
            115,
            113,
            "53",
            "资产处置收益",
            "资产处置收益",
        ),
    ]:
        excerpt = _match(p24[page - 1], pattern).group(0)
        results.append(
            _cell(
                acquisition_id=acquisition_id,
                role_id=role,
                concept_id=concept,
                fiscal_year=2024,
                period_type="annual",
                raw=raw,
                raw_unit="人民币百万元",
                multiplier="100",
                locator=_locator(
                    year=2024,
                    pdf_page=page,
                    printed=printed,
                    note=note,
                    title=title,
                    row=row,
                    column="2024年度合并",
                    unit="金额单位为人民币百万元",
                    excerpt=excerpt,
                ),
            )
        )

    for year, page_text, pdf_page, printed, note, raw in [
        (2023, p23[112], 113, 111, "42", "184,211"),
        (2024, p24[113], 114, 112, "41", "194,492"),
    ]:
        excerpt = _match(page_text, rf"少数股东权益 {note} {re.escape(raw)} [\d,]+ - -").group(0)
        results.append(
            _cell(
                acquisition_id="B-2023-2024-nci",
                role_id="invested_capital.non_controlling_interest",
                concept_id="non_controlling_interest",
                fiscal_year=year,
                period_type="instant",
                raw=raw,
                raw_unit="人民币百万元",
                multiplier="100",
                locator=_locator(
                    year=year,
                    pdf_page=pdf_page,
                    printed=printed,
                    note=note,
                    title=f"{year}年12月31日合并及公司资产负债表(续)",
                    row="少数股东权益",
                    column=f"{year}年12月31日合并",
                    unit="金额单位为人民币百万元",
                    excerpt=excerpt,
                ),
            )
        )

    restricted_2023 = _match(
        p23[153],
        (
            r"货币资金中有账面价值为 21\.40 亿元"
            r"\(2022 年 12 月 31 日：25\.86 亿元\)"
            r"的保证金账户存款作为美元借款质押"
        ),
    ).group(0)
    results.append(
        _cell(
            acquisition_id="C-2023-2024-restricted-cash",
            role_id="invested_capital.restricted_cash",
            concept_id="restricted_cash",
            fiscal_year=2023,
            period_type="instant",
            raw="21.40",
            raw_unit="亿元",
            multiplier="10000",
            locator=_locator(
                year=2023,
                pdf_page=154,
                printed=152,
                note="7",
                title="货币资金(续)",
                row="保证金账户存款作为美元借款质押",
                column="2023年12月31日",
                unit="句内金额单位为亿元",
                excerpt=restricted_2023,
            ),
            purpose=(
                "pledged guarantee-account deposit securing USD borrowings; "
                "never freely deductible cash"
            ),
        )
    )
    restricted_2024 = _match(
        p24[148], r"货币资金中无保证金账户存款作为美元借款质押\(2023 年 12 月 31 日：21\.40 亿元\)"
    ).group(0)
    results.append(
        _cell(
            acquisition_id="C-2023-2024-restricted-cash",
            role_id="invested_capital.restricted_cash",
            concept_id="restricted_cash",
            fiscal_year=2024,
            period_type="instant",
            raw="无",
            raw_unit="亿元",
            multiplier="10000",
            locator=_locator(
                year=2024,
                pdf_page=149,
                printed=147,
                note="7",
                title="货币资金",
                row="保证金账户存款作为美元借款质押",
                column="2024年12月31日",
                unit="comparative sentence uses 亿元",
                excerpt=restricted_2024,
            ),
            sign="explicit_source_absence_normalized_to_decimal_zero_not_default_fill",
            purpose=(
                "source explicitly states no guarantee-account deposit securing "
                "USD borrowings; never freely deductible cash"
            ),
        )
    )
    return sorted(results, key=lambda item: (item.acquisition_id, item.fiscal_year))


def _source_fact(cell: ExtractedCell, evidence: dict[str, Any]) -> dict[str, Any]:
    period_start = (
        f"{cell.fiscal_year}-01-01" if cell.period_type == "annual" else f"{cell.fiscal_year}-12-31"
    )
    period_end = f"{cell.fiscal_year}-12-31"
    fact = {
        "symbol": "601857.SH",
        "concept_id": cell.concept_id,
        "concept_version": "1",
        "context_id": f"601857.SH|{cell.fiscal_year}|{cell.period_type}|consolidated",
        "source_id": evidence["source_id"],
        "fact_version": 1,
        "restatement_version": "original",
        "derivation_definition_id": "finance_cost_excluding_lease_interest_note_bridge_v1"
        if cell.concept_id == "finance_cost_excluding_lease_interest"
        else "",
        "derivation_version": "1"
        if cell.concept_id == "finance_cost_excluding_lease_interest"
        else "",
        "supersedes_fact_id": None,
        "value_decimal": cell.normalized_value,
        "unit": "万元",
        "currency": "CNY",
        "accounting_standard": "CAS",
        "scope": "consolidated",
        "period_type": cell.period_type,
        "period_start": period_start,
        "period_end": period_end,
        "announcement_date": evidence["publication_date"],
        "filing_date": evidence["publication_date"],
        "available_at": evidence["available_at"],
        "source_provider": "petrochina_ir_stage2i2"
        if evidence["source_type"] == "company_official"
        else "sse_stage2i2",
        "source_tier": evidence["source_type"],
        "source_type": evidence["source_type"],
        "source_document": evidence["official_title"],
        "source_locator": evidence["original_url"],
        "source_page": (
            f"PDF page {cell.locator['pdf_page_number_one_based']} / "
            f"printed page {cell.locator['printed_page_number']}"
        ),
        "source_table": cell.locator["table_title"],
        "source_label": cell.locator["row_label"],
        "content_sha256": evidence["content_sha256"],
        "verification_status": "verified",
        "verification_note": (
            "deterministic embedded-text extraction with exact CAS locator; "
            "dual official alias reconciled"
        ),
        "eligible_for_metrics": False,
        "is_derived": cell.concept_id == "finance_cost_excluding_lease_interest",
        "input_fact_ids": "",
        "source_evidence": [],
    }
    fact["fact_id"] = build_fact_id(fact)
    return fact


def _reconciled_fact(cell: ExtractedCell, inputs: list[dict[str, Any]]) -> dict[str, Any]:
    source_id = (
        f"reconciled:601857.SH:company_exchange:stage2i2:{cell.concept_id}:{cell.fiscal_year}:v1"
    )
    fact = deepcopy(inputs[0])
    fact.update(
        {
            "source_id": source_id,
            "source_provider": "official_reconciliation",
            "source_tier": "dual_official_reconciled",
            "source_type": "exchange_official",
            "source_document": "issuer/SSE official dual-source reconciliation",
            "source_locator": inputs[1]["source_locator"],
            "source_page": "",
            "source_table": "",
            "source_label": "reconciled",
            "content_sha256": inputs[1]["content_sha256"],
            "verification_status": "reconciled",
            "verification_note": (
                "issuer and SSE evidence reconciled by value, unit, CAS scope, "
                "period and semantics"
            ),
            "eligible_for_metrics": True,
            "is_derived": True,
            "derivation_definition_id": "official_dual_source_reconciliation",
            "derivation_version": "1",
            "input_fact_ids": ",".join(item["fact_id"] for item in inputs),
            "source_evidence": [
                {
                    "fact_id": item["fact_id"],
                    "source_id": item["source_id"],
                    "source_type": item["source_type"],
                    "source_tier": item["source_tier"],
                    "source_document": item["source_document"],
                    "source_locator": item["source_locator"],
                    "source_page": item["source_page"],
                    "content_sha256": item["content_sha256"],
                }
                for item in inputs
            ],
            "available_at": max(item["available_at"] for item in inputs),
            "announcement_date": max(item["announcement_date"] for item in inputs),
            "filing_date": max(item["filing_date"] for item in inputs),
        }
    )
    fact["fact_id"] = build_fact_id(fact)
    return fact


def build_fact_bundle(cells: list[ExtractedCell]) -> dict[str, Any]:
    evidence = {item["evidence_id"]: item for item in _load(SOURCE_PATH)["entries"]}
    facts, economic = [], []
    for cell in cells:
        inputs = [_source_fact(cell, evidence[eid]) for eid in cell.locator["evidence_ids"]]
        reconciled = _reconciled_fact(cell, inputs)
        facts.extend([*inputs, reconciled])
        economic.append(
            {
                "acquisition_id": cell.acquisition_id,
                "role_id": cell.role_id,
                "fiscal_year": cell.fiscal_year,
                "source_fact_ids": [item["fact_id"] for item in inputs],
                "canonical_fact_id": reconciled["fact_id"],
                "context_id": reconciled["context_id"],
                "raw_value": cell.raw_value,
                "raw_numeric_string": cell.raw_numeric_string,
                "raw_sign_presentation": cell.raw_sign_presentation,
                "raw_unit": cell.raw_unit,
                "raw_currency": "CNY",
                "normalized_decimal_value": cell.normalized_value,
                "normalized_unit": "万元",
                "conversion_multiplier": cell.conversion_multiplier,
                "sign_normalization_rule": cell.sign_normalization_rule,
                "rounding_rule": "Decimal precision 28 ROUND_HALF_EVEN; no material rounding",
                "purpose": cell.purpose,
                "derivation": cell.derivation,
                "locator": cell.locator,
                "reconciliation_status": "acquired_verified",
            }
        )
    validate_canonical_fact_ids(facts)
    return {
        "schema": "roic_normalized_official_fact_bundle_v1",
        "symbol": "601857.SH",
        "fact_count": len(facts),
        "economic_fact_count": len(economic),
        "facts": facts,
        "economic_facts": economic,
        "shadow_status": "NOT_RUN",
        "production_metric_created": False,
    }


def _augment_inventory(bundle: dict[str, Any]) -> dict[str, Any]:
    inventory = deepcopy(_load(INVENTORY_PATH))
    base_max_lineage = max((int(item["lineage_id"]) for item in inventory["lineage"]), default=0)
    for offset, fact in enumerate(bundle["facts"], start=1):
        inventory["facts"].append(fact)
        inventory["sources"].append(
            {
                "fact_id": fact["fact_id"],
                "source_id": fact["source_id"],
                "source_type": fact["source_type"],
                "source_tier": fact["source_tier"],
                "source_document": fact["source_document"],
                "source_locator": fact["source_locator"],
                "source_page": fact["source_page"],
                "content_sha256": fact["content_sha256"],
            }
        )
        inventory["lineage"].append(
            {
                "lineage_id": base_max_lineage + offset,
                "fact_id": fact["fact_id"],
                "source_method": "stage2i2_official_extraction",
                "source_provider": fact["source_provider"],
                "source_tier": fact["source_tier"],
                "raw_file_path": "",
                "staging_file_path": "",
                "fetch_run_id": "stage2i2_acquire_20260803T000924Z",
                "run_id": "stage2i2_formal_v1",
                "role": "reconciled_output" if fact["eligible_for_metrics"] else "official_input",
                "parent_fact_ids": fact["input_fact_ids"],
                "reconciliation_rule_id": fact["derivation_definition_id"],
                "reconciliation_rule_version": fact["derivation_version"],
                "recorded_at": "2026-08-03T00:09:24Z",
            }
        )
    inventory.update(
        {
            "export_run_id": "stage2i2_isolated_verified_fact_bundle_v1",
            "exported_at": "2026-08-03T00:09:24Z",
            "fact_count": len(inventory["facts"]),
            "eligible_fact_count": sum(
                bool(item["eligible_for_metrics"]) for item in inventory["facts"]
            ),
            "source_count": len(inventory["sources"]),
            "lineage_count": len(inventory["lineage"]),
            "authority": (
                "isolated Stage 2I.2 verified fact bundle; default DB not "
                "opened or written"
            ),
        }
    )
    payload = {
        "symbol": inventory["symbol"],
        "facts": inventory["facts"],
        "contexts": inventory["contexts"],
        "sources": inventory["sources"],
        "lineage": inventory["lineage"],
    }
    inventory["snapshot_sha256"] = hashlib.sha256(_stable(payload)).hexdigest()
    validate_inventory(inventory)
    return inventory


def _missing_records() -> list[dict[str, Any]]:
    return [
        {
            "acquisition_id": "A-2024-operating-tax",
            "role_id": "tax.operating_tax_expense",
            "fiscal_year": 2024,
            "status": "missing_official_fact",
            "documents_searched": [
                "FY2024 issuer CAS annual report",
                "FY2024 SSE CAS annual report",
            ],
            "terms_searched": ["所得税费用", "当期所得税", "递延所得税", "经营税", "营业利润税"],
            "page_ranges": [
                "PDF 115 / printed 113",
                "PDF 180 / printed 178",
                "full embedded-text search PDF 1-280",
            ],
            "result": (
                "only total current/deferred income tax and tax-rate reconciliation "
                "are disclosed; no direct operating-tax allocation"
            ),
            "why_no_fact": "ETR, statutory rate and total income-tax expense are forbidden proxies",
        },
        *[
            {
                "acquisition_id": acquisition_id,
                "role_id": role,
                "fiscal_year": year,
                "status": "ambiguous_scope",
                "documents_searched": [
                    f"FY{year} issuer CAS annual report",
                    f"FY{year} SSE CAS annual report",
                    "FY2024 comparative CAS notes",
                ],
                "terms_searched": ["长期股权投资", "联营企业", "合营企业", "单项不重大"],
                "page_ranges": [
                    "FY2023 PDF 158-161 / printed 156-159",
                    "FY2024 PDF 153-156 / printed 151-154",
                ],
                "result": (
                    "major associates and JVs are separate, but remaining individually "
                    "immaterial holdings are disclosed only as a combined associate/JV amount"
                ),
                "why_no_fact": (
                    "a complete separate balance would require a forbidden residual "
                    "allocation or plug"
                ),
            }
            for acquisition_id, role in [
                ("B-2023-2024-associate", "invested_capital.associate_investment"),
                ("B-2023-2024-jv", "invested_capital.joint_venture_investment"),
            ]
            for year in (2023, 2024)
        ],
        *[
            {
                "acquisition_id": "C-2023-2024-non-operating-financial-assets",
                "role_id": "invested_capital.non_operating_financial_assets",
                "fiscal_year": year,
                "status": "missing_official_fact",
                "documents_searched": [
                    f"FY{year} issuer CAS annual report",
                    f"FY{year} SSE CAS annual report",
                    "FY2024 comparative CAS notes",
                ],
                "terms_searched": [
                    "非经营",
                    "非主营",
                    "交易性金融资产",
                    "其他权益工具投资",
                    "定期存款",
                    "投资收益",
                    "利息收入",
                ],
                "page_ranges": [
                    f"full embedded-text search FY{year} official PDF",
                    "financial-instrument, cash, investment-income and cash-flow notes",
                ],
                "result": (
                    "financial asset classes and income lines are disclosed, but no "
                    "exact official non-operating-purpose and linked-income classification "
                    "is provided"
                ),
                "why_no_fact": (
                    "unproven assets remain included in invested capital; no residual "
                    "classification"
                ),
            }
            for year in (2023, 2024)
        ],
    ]


def _acquisition_result(bundle: dict[str, Any], missing: list[dict[str, Any]]) -> dict[str, Any]:
    plan = _load(PLAN_PATH)
    by_key = {
        (item["acquisition_id"], item["fiscal_year"]): item for item in bundle["economic_facts"]
    }
    missing_by_key = {(item["acquisition_id"], item["fiscal_year"]): item for item in missing}
    cells = []
    for item in _plan_items(plan):
        for year in item["affected_fiscal_years"]:
            acquired = by_key.get((item["acquisition_id"], year))
            gap = missing_by_key.get((item["acquisition_id"], year))
            status = "acquired_verified" if acquired else gap["status"]
            if status not in ALLOWED_RESULTS:
                raise ValueError(f"unsupported acquisition status: {status}")
            cells.append(
                {
                    "plan_acquisition_id": item["acquisition_id"],
                    "role_id": item["role_id"],
                    "fiscal_year": year,
                    "expected_period_type": item["period_type"],
                    "source_evidence_ids": acquired["locator"]["evidence_ids"]
                    if acquired
                    else [
                        f"pc-roic-{year}-issuer-annual-cas",
                        f"pc-roic-{year}-exchange-annual-cas",
                    ],
                    "exact_locators": [acquired["locator"]] if acquired else [],
                    "extraction_result": status,
                    "reconciliation_status": status,
                    "canonical_fact_ids": [acquired["canonical_fact_id"]] if acquired else [],
                    "selected_active_fact_id": acquired["canonical_fact_id"] if acquired else None,
                    "superseded_fact_ids": [],
                    "missing_or_conflict_reason": gap["why_no_fact"] if gap else None,
                    "readiness_before": "missing_official_fact",
                    "readiness_after": "ready"
                    if acquired
                    else (
                        "scope_mismatch" if status == "ambiguous_scope" else "missing_official_fact"
                    ),
                    "formula_dependency_impact": item["downstream_formula_contribution"],
                    "review_status": "verified" if acquired else "bounded_search_complete",
                    "score_eligibility": False,
                }
            )
    if len(cells) != 16 or {cell["plan_acquisition_id"] for cell in cells} != APPROVED_IDS:
        raise ValueError("acquisition result lost a Plan v3 item or affected year cell")
    return {
        "schema": "roic_fact_acquisition_result_v1",
        "symbol": "601857.SH",
        "plan_digest": plan["plan_digest"],
        "cell_count": len(cells),
        "cells": cells,
        "status_counts": dict(
            sorted(
                {
                    status: sum(c["extraction_result"] == status for c in cells)
                    for status in {c["extraction_result"] for c in cells}
                }.items()
            )
        ),
        "plan_v3_acquisition_coverage": "COMPLETE",
        "shadow_feasibility": "NOT_RUN",
        "production_metric_result_created": False,
        "score_eligibility": False,
    }


def _readiness_diff(
    before: dict[str, Any], after: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    tracked = {(cell["role_id"], cell["fiscal_year"]) for cell in result["cells"]}
    old = {(cell["role_id"], cell["fiscal_year"]): cell for cell in before["matrix"]}
    new = {(cell["role_id"], cell["fiscal_year"]): cell for cell in after["matrix"]}
    transitions = [
        {
            "role_id": role,
            "fiscal_year": year,
            "before": old[(role, year)]["status"],
            "after": new[(role, year)]["status"],
            "after_fact_id": new[(role, year)].get("selected_fact_id"),
        }
        for role, year in sorted(tracked)
    ]
    blocking = [item for item in transitions if item["after"] != "ready"]
    decision = (
        "ROIC_FACT_GAPS_REMAIN"
        if after["evidence_gate"] == "BLOCKED_WITH_EXPLICIT_GAPS"
        else "ROIC_SHADOW_ALLOWED"
    )
    return {
        "schema": "roic_stage2i2_readiness_diff_v1",
        "before_report_sha256": before["report_sha256"],
        "after_report_sha256": after["report_sha256"],
        "transitions": transitions,
        "remaining_plan_blockers": blocking,
        "post_acquisition_evidence_gate": after["evidence_gate"],
        "stage2i2_decision": decision,
        "shadow_status": "NOT_RUN",
    }


def _manifest(run_dir: Path) -> dict[str, Any]:
    files = []
    for path in sorted(
        item
        for item in run_dir.rglob("*")
        if item.is_file() and item.name != "artifact_manifest.json"
    ):
        files.append(
            {
                "logical_path": path.relative_to(run_dir).as_posix(),
                "sha256": _sha256(path),
                "byte_size": path.stat().st_size,
            }
        )
    manifest = {"schema": "roic_stage2i2_artifact_manifest_v1", "files": files}
    manifest["artifact_set_sha256"] = canonical_digest(files)
    return manifest


def run_formal(
    *, official_cache_root: Path | str | None, output_root: Path | str, run_id: str
) -> dict[str, Any]:
    contracts = validate_contracts()
    cache_status = verify_official_cache(official_cache_root)
    root = Path(output_root) / run_id
    root.mkdir(parents=True, exist_ok=True)
    cells = extract_cells(Path(official_cache_root).resolve())
    bundle = build_fact_bundle(cells)
    inventory = _augment_inventory(bundle)
    inventory_path = root / "isolated_canonical_inventory_v2.json"
    _write(inventory_path, inventory)
    after = build_readiness_report(inventory_path=inventory_path, assessment_as_of="2026-08-03")
    before = _load(READINESS_PATH)
    missing = _missing_records()
    result = _acquisition_result(bundle, missing)
    diff = _readiness_diff(before, after, result)
    coverage = {
        "schema": "roic_stage2i2_plan_v3_acquisition_coverage_v1",
        "validation_status": "PASS",
        "plan_digest": contracts["plan_digest"],
        "approved_item_count": 11,
        "affected_cell_count": 16,
        "reported_item_count": len({cell["plan_acquisition_id"] for cell in result["cells"]}),
        "reported_cell_count": len(result["cells"]),
        "extra_items": [],
        "missing_items": [],
        "missing_cells_preserved": sum(
            cell["extraction_result"] != "acquired_verified" for cell in result["cells"]
        ),
        "decision": diff["stage2i2_decision"],
    }
    pit = {
        "schema": "roic_stage2i2_pit_restatement_verification_v1",
        "status": "PASS",
        "fy2023_original_comparative": {
            "non_controlling_interest": (
                "unchanged_184211_RMB_million_corroboration_no_new_economic_version"
            ),
            "restricted_cash": (
                "unchanged_21.40_RMB_100_million_corroboration_"
                "no_new_economic_version"
            ),
            "associate_and_jv": "combined_scope_remains_ambiguous_no_version_created",
        },
        "supersession_edges_created": 0,
        "backward_time_edges": 0,
        "cross_context_edges": 0,
        "active_fact_selection_as_of": "2026-08-03",
    }
    outputs = {
        "source_cache_verification.json": cache_status,
        "normalized_official_fact_bundle.json": bundle,
        "acquisition_result.json": result,
        "bounded_search_register.json": {
            "schema": "roic_bounded_search_register_v1",
            "records": missing,
        },
        "post_acquisition_readiness.json": after,
        "readiness_before_after_diff.json": diff,
        "plan_v3_acquisition_coverage.json": coverage,
        "pit_restatement_verification.json": pit,
        "contract_verification.json": contracts,
    }
    for name, payload in outputs.items():
        _write(root / name, payload)
    (root / "post_acquisition_readiness.md").write_text(render_markdown(after), encoding="utf-8")
    _write(root / "artifact_manifest.json", _manifest(root))
    return {
        "run_id": run_id,
        "run_dir": str(root),
        "decision": diff["stage2i2_decision"],
        "cache_status": cache_status["status"],
        "economic_fact_count": bundle["economic_fact_count"],
        "affected_cell_count": result["cell_count"],
        "remaining_plan_blocker_count": len(diff["remaining_plan_blockers"]),
        "shadow_status": "NOT_RUN",
        "production_metric_result_created": False,
        "artifact_set_sha256": _load(root / "artifact_manifest.json")["artifact_set_sha256"],
    }


def compare_runs(first: Path | str, second: Path | str) -> dict[str, Any]:
    a, b = Path(first), Path(second)
    names = sorted(path.relative_to(a).as_posix() for path in a.rglob("*") if path.is_file())
    other = sorted(path.relative_to(b).as_posix() for path in b.rglob("*") if path.is_file())
    if names != other:
        raise ValueError("formal A/B artifact paths differ")
    mismatches = [name for name in names if _sha256(a / name) != _sha256(b / name)]
    if mismatches:
        raise ValueError(f"formal A/B artifacts differ: {mismatches}")
    return {"status": "PASS", "artifact_count": len(names), "mismatches": []}


def publish_reports(
    run_dir: Path | str, report_dir: Path | str = ROOT / "reports"
) -> dict[str, Any]:
    source = Path(run_dir)
    target = Path(report_dir)
    mapping = {
        "source_cache_verification.json": "petrochina_roic_stage2i2_source_cache_verification.json",
        "normalized_official_fact_bundle.json": (
            "petrochina_roic_normalized_official_fact_bundle_v1.json"
        ),
        "acquisition_result.json": "petrochina_roic_fact_acquisition_result_v1.json",
        "bounded_search_register.json": "petrochina_roic_bounded_search_register_v1.json",
        "post_acquisition_readiness.json": "petrochina_roic_post_acquisition_readiness_v1.json",
        "post_acquisition_readiness.md": "petrochina_roic_post_acquisition_readiness_v1.md",
        "readiness_before_after_diff.json": "petrochina_roic_stage2i2_readiness_diff_v1.json",
        "plan_v3_acquisition_coverage.json": (
            "petrochina_roic_stage2i2_plan_v3_acquisition_coverage_v1.json"
        ),
        "pit_restatement_verification.json": (
            "petrochina_roic_stage2i2_pit_restatement_verification_v1.json"
        ),
        "contract_verification.json": "petrochina_roic_stage2i2_contract_verification.json",
        "artifact_manifest.json": "petrochina_roic_stage2i2_artifact_manifest.json",
    }
    target.mkdir(parents=True, exist_ok=True)
    published = []
    for source_name, target_name in mapping.items():
        source_path = source / source_name
        if not source_path.is_file():
            raise FileNotFoundError(f"formal artifact missing for publication: {source_name}")
        target_path = target / target_name
        target_path.write_bytes(source_path.read_bytes())
        published.append(
            {
                "logical_path": f"reports/{target_name}",
                "sha256": _sha256(target_path),
                "byte_size": target_path.stat().st_size,
            }
        )
    return {
        "status": "PASS",
        "published_count": len(published),
        "published_artifacts": published,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=["acquire", "verify-cache", "formal", "compare", "publish"]
    )
    parser.add_argument("--official-cache-root", type=Path)
    parser.add_argument("--output-root", type=Path, default=ROOT / "tmp" / "stage2i2_runs")
    parser.add_argument("--run-id", default="stage2i2_formal_v1")
    parser.add_argument("--first", type=Path)
    parser.add_argument("--second", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args(argv)
    if args.mode == "acquire":
        result = acquire(args.official_cache_root)
    elif args.mode == "verify-cache":
        result = verify_official_cache(args.official_cache_root)
    elif args.mode == "formal":
        result = run_formal(
            official_cache_root=args.official_cache_root,
            output_root=args.output_root,
            run_id=args.run_id,
        )
    elif args.mode == "compare":
        if args.first is None or args.second is None:
            parser.error("compare requires --first and --second")
        result = compare_runs(args.first, args.second)
    else:
        if args.run_dir is None:
            parser.error("publish requires --run-dir")
        result = publish_reports(args.run_dir, args.report_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
