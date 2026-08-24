"""Focused M3 Stage 3B-R3 bounded Tier-1 acquisition unblock tests.

Covers the EIA Open Data API v2 bounded transport (secret redaction, route discovery, response
validation), the Shenwan official-source-resolution ladder, frozen Stage 3B-R2/R3 artifact hashes,
and the prohibition of any real mechanism result or holdout read. All EIA network behavior is
mocked; no real API key and no 2023+ date is ever used.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ashare_research.exceptions import DuplicateKeyError
from ashare_research.mechanism.acquisition_eia import (
    BOUNDED_START,
    DEVELOPMENT_END,
    ENDPOINT_TEMPLATE_REDACTED,
    STATUS_ACQUIRED,
    STATUS_BOUNDED_RESPONSE_VIOLATION,
    STATUS_DUPLICATE_DATE,
    STATUS_KEY_REQUIRED,
    STATUS_MALFORMED_NUMERIC,
    STATUS_REQUEST_UNBOUNDED,
    STATUS_WRONG_SERIES,
    STATUS_WRONG_UNIT,
    acquire_oil_bounded,
    discover_eia_route,
    parse_eia_data_payload,
    redact,
    validate_request_bounds,
    validate_series_metadata,
)
from ashare_research.mechanism.acquisition_shenwan import (
    REGIME_1_SYMBOL,
    REGIME_2_SYMBOL,
    STATUS_CAPSULE_HAS_HOLDOUT,
    STATUS_CAPSULE_REQUIRED,
    STATUS_UNVERIFIED_MIRROR_REJECTED,
    materialize_official_capsule,
    resolve_industry_source,
    validate_official_capsule,
)
from ashare_research.mechanism.acquisition_shenwan import (
    STATUS_ACQUIRED as INDUSTRY_ACQUIRED,
)
from ashare_research.mechanism.contracts import (
    Stage3BContractError,
    assert_no_restricted_research_outputs,
    verify_stage3br2_frozen,
    verify_stage3br3_frozen,
)
from ashare_research.mechanism.industry import build_industry_returns
from ashare_research.mechanism.source_manifest import canonical_frame_digest

ROOT = Path(__file__).resolve().parents[1]

# A marker used only inside this test file as the "known test secret"; it must never appear in the
# committed mechanism source or tool modules (Section 26 scan).
TEST_SECRET = "test-eia-key-0123456789"


# --------------------------------------------------------------------------- mocks


def _mock_eia(
    *,
    series_id: str = "PET.RBRTE.D",
    name: str = "Europe Brent Spot Price FOB, Daily",
    units: str = "Dollars per Barrel",
    data_rows: list[dict[str, str]] | None = None,
    fail_data: Exception | None = None,
) -> object:
    def http_get(url: str, params: dict | None = None) -> dict:
        path = url.rstrip("/")
        if path.endswith("/v2"):
            return {"response": {"categories": [{"id": "petroleum"}]}}
        if path.endswith("/v2/petroleum"):
            return {"response": {"categories": [{"id": "pri"}]}}
        if path.endswith("/v2/petroleum/pri"):
            return {"response": {"categories": [{"id": "spt"}]}}
        if path.endswith("/v2/petroleum/pri/spt"):
            return {
                "response": {
                    "series": [
                        {"series_id": series_id, "name": name, "units": units, "frequency": "daily"}
                    ]
                }
            }
        if path.endswith("/v2/petroleum/pri/spt/data"):
            if fail_data is not None:
                raise fail_data
            return {"response": {"data": data_rows or []}}
        raise AssertionError(f"unexpected URL {url}")

    return http_get


def _eia_rows() -> list[dict[str, str]]:
    return [
        {"period": "2015-01-02", "value": "50.0"},
        {"period": "2015-01-05", "value": "55.0"},
    ]


# --------------------------------------------------------------------------- frozen hashes


def test_frozen_stage3br2_artifacts_unchanged() -> None:
    assert len(verify_stage3br2_frozen(ROOT / "reports")) == 6


def test_frozen_stage3br3_artifacts_unchanged() -> None:
    assert len(verify_stage3br3_frozen(ROOT / "reports")) == 6


def test_r3_reports_contain_no_restricted_research_outputs() -> None:
    for name in (
        "m3_stage3br3_source_resolution_v1.json",
        "m3_stage3br3_oil_development_manifest_v1.json",
        "m3_stage3br3_industry_development_manifest_v1.json",
        "m3_stage3br3_data_coverage_v1.json",
        "m3_stage3br3_tier1_readiness_v2.json",
        "m3_stage3br3_joint_input_manifest_v1.json",
    ):
        payload = json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))
        assert_no_restricted_research_outputs(payload)


def test_r3_reports_declare_holdout_sealed_and_inputs_not_trusted() -> None:
    readiness = json.loads(
        (ROOT / "reports/m3_stage3br3_tier1_readiness_v2.json").read_text(encoding="utf-8")
    )
    assert readiness["holdout_status"] == "SEALED"
    assert readiness["holdout_read_performed"] is False
    assert readiness["market_ex_target"] == "TRUSTED"
    assert readiness["oil"] == "NOT_ACQUIRED"
    assert readiness["petrochemical_industry"] == "NOT_ACQUIRED"
    assert readiness["joint_tier1_dates"] == "NOT_READY"
    assert readiness["stage3c_status"] == "M3_STAGE3C_NOT_ALLOWED"


def test_r3_reports_contain_no_2023_plus_dates() -> None:
    # Every report is scanned; the ``fetched_at`` metadata timestamp records when the report was
    # generated (today, 2026) and is not a data date, so it is excluded. All data-bearing date
    # strings must be <= 2022-12-31.
    holdout = pd.Timestamp("2023-01-01")

    def walk(value, *, key: str | None = None) -> None:
        if key == "fetched_at":
            return
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, key=k)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, str):
            stripped = value.strip()
            if len(stripped) == 10 and stripped[4] == "-" and stripped[7] == "-":
                assert pd.to_datetime(stripped, errors="coerce") < holdout, (
                    f"data date {stripped} is on/after holdout"
                )

    for name in (
        "m3_stage3br3_source_resolution_v1.json",
        "m3_stage3br3_oil_development_manifest_v1.json",
        "m3_stage3br3_industry_development_manifest_v1.json",
        "m3_stage3br3_data_coverage_v1.json",
        "m3_stage3br3_tier1_readiness_v2.json",
        "m3_stage3br3_joint_input_manifest_v1.json",
    ):
        payload = json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))
        walk(payload)


# --------------------------------------------------------------------------- secret redaction


def test_redact_replaces_secret() -> None:
    assert redact("boom test-eia-key-0123456789 end", TEST_SECRET) == "boom <REDACTED> end"


def test_api_key_absent_fails_closed(tmp_path: Path) -> None:
    result = acquire_oil_bounded(tmp_path, http_get=_mock_eia(), key_provider=lambda: None)
    assert result["status"] == STATUS_KEY_REQUIRED
    assert result["codes"] == [STATUS_KEY_REQUIRED]
    assert result["holdout_read_performed"] is False
    assert not (tmp_path / "raw" / "oil_brent_observations.csv").exists()


def test_key_never_leaks_into_transport_exception(tmp_path: Path) -> None:
    def boom(url: str, params: dict | None = None) -> dict:
        raise RuntimeError(f"network exploded with key {TEST_SECRET} inside")

    result = acquire_oil_bounded(
        tmp_path, http_get=boom, key_provider=lambda: TEST_SECRET
    )
    blob = json.dumps(result, ensure_ascii=False)
    assert TEST_SECRET not in blob
    assert "REDACTED" in json.dumps(result["codes"])


def test_key_never_leaks_from_http_get_exception(tmp_path: Path) -> None:
    # A transport error emitted by the data endpoint must be redacted before it reaches the result.
    result = acquire_oil_bounded(
        tmp_path,
        http_get=_mock_eia(fail_data=RuntimeError(f"boom {TEST_SECRET}")),
        key_provider=lambda: TEST_SECRET,
    )
    blob = json.dumps(result, ensure_ascii=False)
    assert TEST_SECRET not in blob


def test_redacted_endpoint_template_is_stable() -> None:
    assert TEST_SECRET not in ENDPOINT_TEMPLATE_REDACTED
    assert "<REDACTED>" in ENDPOINT_TEMPLATE_REDACTED
    assert "api_key=" in ENDPOINT_TEMPLATE_REDACTED


def test_committed_source_contains_no_test_secret_literal() -> None:
    # The known test-secret literal must never appear in committed non-test mechanism source.
    for rel in (
        "src/ashare_research/mechanism/acquisition_eia.py",
        "src/ashare_research/mechanism/acquisition_shenwan.py",
        "src/ashare_research/tools/m3_stage3br3_data.py",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert TEST_SECRET not in text, f"{rel} contains the test-secret literal"


# ------------------------------------------- route discovery / bounds


def test_route_discovery_locates_rbrte() -> None:
    route = discover_eia_route(_mock_eia(), TEST_SECRET)
    assert route["data_route"] == "petroleum/pri/spt/data"
    assert "RBRTE" in route["series_id"]


def test_route_discovery_rejects_missing_series(tmp_path: Path) -> None:
    mock = _mock_eia(series_id="PET.WTI.D", name="WTI Crude Oil")
    with pytest.raises(Stage3BContractError):
        discover_eia_route(mock, TEST_SECRET)


def test_validate_request_requires_explicit_bounded_end() -> None:
    validate_request_bounds(BOUNDED_START, DEVELOPMENT_END)  # must not raise
    with pytest.raises(Stage3BContractError, match=STATUS_REQUEST_UNBOUNDED):
        validate_request_bounds(BOUNDED_START, "")
    with pytest.raises(Stage3BContractError, match=STATUS_REQUEST_UNBOUNDED):
        validate_request_bounds(BOUNDED_START, "2023-01-01")
    with pytest.raises(Stage3BContractError, match=STATUS_REQUEST_UNBOUNDED):
        validate_request_bounds(BOUNDED_START, "2023-06-01")


def test_wrong_series_identity_rejected() -> None:
    with pytest.raises(Stage3BContractError, match=STATUS_WRONG_SERIES):
        validate_series_metadata(
            {
                "series_id": "PET.WTI.D",
                "series_name": "WTI",
                "units": "Dollars per Barrel",
                "frequency": "daily",
            }
        )


def test_wrong_units_rejected() -> None:
    with pytest.raises(Stage3BContractError, match=STATUS_WRONG_UNIT):
        validate_series_metadata(
            {
                "series_id": "PET.RBRTE.D",
                "series_name": "Europe Brent Spot Price FOB, Daily",
                "units": "Kilopascal",
                "frequency": "daily",
            }
        )


def test_duplicate_date_rejected() -> None:
    rows = _eia_rows() + [{"period": "2015-01-02", "value": "51.0"}]
    with pytest.raises(DuplicateKeyError, match=STATUS_DUPLICATE_DATE):
        parse_eia_data_payload({"response": {"data": rows}})


def test_malformed_numeric_rejected() -> None:
    rows = [{"period": "2015-01-02", "value": "not-a-number"}]
    with pytest.raises(Stage3BContractError, match=STATUS_MALFORMED_NUMERIC):
        parse_eia_data_payload({"response": {"data": rows}})


def test_response_claiming_2023_fails_closed() -> None:
    rows = [{"period": "2023-01-02", "value": "50.0"}]
    with pytest.raises(Stage3BContractError, match=STATUS_BOUNDED_RESPONSE_VIOLATION):
        parse_eia_data_payload({"response": {"data": rows}})


def test_response_claiming_past_development_end_fails_closed() -> None:
    rows = [{"period": "2022-12-31", "value": "50.0"}]
    frame = parse_eia_data_payload({"response": {"data": rows}})
    assert int(len(frame)) == 1
    rows_bad = [{"period": "2023-01-01", "value": "50.0"}]
    with pytest.raises(Stage3BContractError, match=STATUS_BOUNDED_RESPONSE_VIOLATION):
        parse_eia_data_payload({"response": {"data": rows_bad}})


def test_acquire_oil_bounded_success_writes_immutable_raw(tmp_path: Path) -> None:
    result = acquire_oil_bounded(
        tmp_path, http_get=_mock_eia(data_rows=_eia_rows()), key_provider=lambda: TEST_SECRET
    )
    assert result["status"] == STATUS_ACQUIRED
    assert result["rows"] == 2
    assert result["first_observation"] == "2015-01-02"
    assert result["last_observation"] == "2015-01-05"
    raw = tmp_path / "raw" / "oil_brent_observations.csv"
    assert raw.is_file()
    assert result["raw_sha256"] is not None
    # The result and raw file must not contain the secret.
    assert TEST_SECRET not in raw.read_text(encoding="utf-8")
    assert TEST_SECRET not in json.dumps(result)


def test_acquire_oil_bounded_offline_ab_identity(tmp_path: Path) -> None:
    from ashare_research.tools.m3_stage3br2_data import normalize_oil

    acquire_oil_bounded(
        tmp_path, http_get=_mock_eia(data_rows=_eia_rows()), key_provider=lambda: TEST_SECRET
    )
    a = normalize_oil(tmp_path, "a")
    b = normalize_oil(tmp_path, "b")
    assert a["status"] == "NORMALIZED" and b["status"] == "NORMALIZED"
    fa = pd.read_csv(tmp_path / "normalized_a/oil_brent_observations.csv", dtype=str)
    fb = pd.read_csv(tmp_path / "normalized_b/oil_brent_observations.csv", dtype=str)
    assert canonical_frame_digest(fa) == canonical_frame_digest(fb)


# --------------------------------------------------------------------------- industry ladder


def _make_capsule(root: Path, *, with_holdout: bool = False) -> Path:
    capsule = root / "capsule"
    capsule.mkdir(parents=True, exist_ok=True)
    dev = [
        ("2021-12-09", 100.0),
        ("2021-12-10", 101.0),
    ]
    sw2021 = [
        ("2021-12-13", 110.0),
        ("2021-12-14", 111.0),
    ]
    if with_holdout:
        sw2021.append(("2023-01-03", 120.0))
    pd.DataFrame(dev, columns=["trade_date", "close"]).to_csv(
        capsule / "industry_801016.csv", index=False
    )
    pd.DataFrame(sw2021, columns=["trade_date", "close"]).to_csv(
        capsule / "industry_801960.csv", index=False
    )
    return capsule


def test_industry_no_source_reports_capsule_required(tmp_path: Path) -> None:
    result = resolve_industry_source(tmp_path)
    assert result["status"] == STATUS_CAPSULE_REQUIRED
    assert "AKSHARE_SW_UNBOUNDED_TRANSPORT_REJECTED" in result["codes"]
    assert "INDUSTRY_BOUNDED_ACQUISITION_NOT_PROVEN" in result["codes"]
    assert STATUS_UNVERIFIED_MIRROR_REJECTED in result["codes"]


def test_industry_known_unbounded_endpoint_family_rejected(tmp_path: Path) -> None:
    # The investigated official endpoint families must all be recorded as unbounded.
    result = resolve_industry_source(tmp_path)
    for fam in result["endpoint_families_investigated"]:
        assert fam["date_bounds_accepted"] is False


def test_industry_official_capsule_accepted(tmp_path: Path) -> None:
    capsule = _make_capsule(tmp_path)
    result = resolve_industry_source(tmp_path, user_capsule=capsule)
    assert result["status"] == INDUSTRY_ACQUIRED
    assert result["route"] == "C_USER_PROVIDED_OFFICIAL_CAPSULE"
    assert result["capsule"]["files"]["industry_801016.csv"]["rows"] == 2
    assert result["capsule"]["files"]["industry_801960.csv"]["rows"] == 2


def test_industry_capsule_with_holdout_rejected(tmp_path: Path) -> None:
    capsule = _make_capsule(tmp_path, with_holdout=True)
    with pytest.raises(Stage3BContractError, match=STATUS_CAPSULE_HAS_HOLDOUT):
        validate_official_capsule(capsule)


def test_industry_capsule_sha_mismatch_rejected(tmp_path: Path) -> None:
    capsule = _make_capsule(tmp_path)
    bad = {"industry_801016.csv": "0" * 64, "industry_801960.csv": "0" * 64}
    with pytest.raises(Stage3BContractError):
        validate_official_capsule(capsule, expected_sha256=bad)


def test_industry_capsule_materialize_and_ab(tmp_path: Path) -> None:
    capsule = _make_capsule(tmp_path)
    resolved = resolve_industry_source(tmp_path, user_capsule=capsule)
    entries = materialize_official_capsule(tmp_path, resolved["capsule"])
    assert set(entries) == {"industry_801016.csv", "industry_801960.csv"}
    from ashare_research.tools.m3_stage3br2_data import normalize_industry

    a = normalize_industry(tmp_path, "a")
    b = normalize_industry(tmp_path, "b")
    assert a["status"] == "NORMALIZED" and b["status"] == "NORMALIZED"
    fa = pd.read_csv(tmp_path / "normalized_a/industry_series.csv", dtype=str)
    fb = pd.read_csv(tmp_path / "normalized_b/industry_series.csv", dtype=str)
    assert canonical_frame_digest(fa) == canonical_frame_digest(fb)


def test_cross_taxonomy_return_rejected() -> None:
    cal = pd.Series(["2021-12-10", "2021-12-13"])
    closes = pd.DataFrame(
        [
            {"trade_date": "2021-12-10", "symbol": REGIME_1_SYMBOL, "close": 100.0},
            {"trade_date": "2021-12-13", "symbol": REGIME_2_SYMBOL, "close": 110.0},
        ]
    )
    ind = build_industry_returns(closes, cal)
    lex = {r["trade_date"]: r for _, r in ind.iterrows()}
    assert lex["2021-12-13"]["alignment_status"] == "INDUSTRY_TAXONOMY_TRANSITION_GAP"
    assert pd.isna(lex["2021-12-13"]["industry_return"])
