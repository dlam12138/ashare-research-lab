"""Offline K1 source-proof kernel. No provider, filesystem, or research execution.

The only accepted raw format is an invented canonical JSON test fixture. Calendar
dates are caller-frozen but unverified; a successful proof is NOT real-data ready.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

KERNEL_VERSION = "M4_REAL_DAILY_OFFLINE_PROOF_KERNEL_K1"
BUNDLE_SCHEMA = "M4_REAL_SOURCE_OFFLINE_BUNDLE_K1"
PROOF_SCHEMA = "M4_REAL_SOURCE_OFFLINE_PROOF_K1"
REJECTION_SCHEMA = "M4_REAL_SOURCE_OFFLINE_REJECTION_K1"
RAW_FORMAT = "M4_K1_CANONICAL_JSON_DAILY_ROWS"
MAX_RAW_BYTES = 16_000_000
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_LOCATOR = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\Z")
_ROW_KEYS = frozenset(
    {
        "role",
        "trade_date",
        "value",
        "observation_at",
        "published_at",
        "available_at",
        "available_at_basis",
        "ingested_at",
        "source_record_id",
    }
)
_RUN_KEYS = frozenset(
    {
        "role",
        "run_id",
        "provider_id",
        "endpoint_id",
        "revision_id",
        "vintage_id",
        "raw_locator",
        "raw_sha256",
        "raw_bytes_length",
        "normalization_rule_id",
    }
)
_CONTRACT_KEYS = frozenset(
    {
        "study_id",
        "development_start",
        "development_end",
        "holdout_start",
        "roles",
        "source_versions",
        "code_digest",
        "signal_cutoff_local",
        "timezone_offset",
        "coverage_gate",
        "min_joint_dates",
        "contract_digest",
    }
)
_DOMAIN_KEYS = frozenset({"expected_dates", "calendar_dates", "calendar_basis"})
_LOCK_KEYS = frozenset(
    {"contract_digest", "domain_digest", "sealed_before_outcome", "source_versions", "code_digest"}
)
_BUNDLE_KEYS = frozenset(
    {
        "schema_version",
        "study_id",
        "contract_digest",
        "roles",
        "source_runs",
        "observations",
        "input_digest",
    }
)


class RealSourceError(ValueError):
    """Stable fail-closed error with stage and host-independent locator."""

    def __init__(self, code: str, stage: int, locator: str):
        self.code, self.stage, self.locator = code, stage, locator
        super().__init__(f"{code} at stage {stage}: {locator}")


def _fail(code: str, stage: int, locator: str) -> None:
    raise RealSourceError(code, stage, locator)


def _object(value: Any, keys: frozenset[str], locator: str, stage: int = 0) -> dict:
    if type(value) is not dict or set(value) != keys:
        _fail("REAL_INVALID_INPUT_STRUCTURE", stage, locator)
    return value


def _str(value: Any, locator: str, *, identifier: bool = False, sha: bool = False) -> str:
    if (
        type(value) is not str
        or (identifier and not _ID.fullmatch(value))
        or (sha and not _HEX.fullmatch(value))
    ):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, locator)
    return value


def _date(value: Any, locator: str) -> str:
    _str(value, locator)
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, locator)
    return value


def _timestamp(value: Any, locator: str, *, missing_code: str) -> datetime:
    if value is None or value == "":
        _fail(missing_code, 5, locator)
    _str(value, locator)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 5, locator)
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or parsed.isoformat(timespec="seconds") != value
    ):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 5, locator)
    return parsed


def _decimal(value: Any, locator: str) -> None:
    if type(value) is not str or not re.fullmatch(
        r"-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,18})?", value
    ):
        _fail("REAL_INVALID_VALUE", 6, locator)
    try:
        number = Decimal(value)
    except InvalidOperation:
        _fail("REAL_INVALID_VALUE", 6, locator)
    if not number.is_finite() or ("." in value and value.endswith(".")):
        _fail("REAL_INVALID_VALUE", 6, locator)


def _canonical(value: Any) -> bytes:
    """Canonical bytes for already shape-checked, float-free values."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def contract_digest(contract: dict) -> str:
    """Compute the K1 contract identity; not a lock or authorization."""
    return _digest(
        {
            "kernel": KERNEL_VERSION,
            "contract": {k: v for k, v in contract.items() if k != "contract_digest"},
        }
    )


def domain_digest(domain: dict) -> str:
    """Bind frozen calendar/date sets without depending on caller list order."""
    payload = dict(domain)
    payload["expected_dates"] = sorted(domain["expected_dates"])
    payload["calendar_dates"] = sorted(domain["calendar_dates"])
    return _digest(payload)


def input_digest(bundle: dict) -> str:
    """Compute the K1 bundle identity after the caller canonically orders inputs."""
    payload = {k: v for k, v in bundle.items() if k != "input_digest"}
    payload["source_runs"] = sorted(payload["source_runs"], key=lambda x: (x["role"], x["run_id"]))
    payload["observations"] = sorted(
        payload["observations"], key=lambda x: (x["role"], x["trade_date"], x["source_record_id"])
    )
    return _digest({"kernel": KERNEL_VERSION, "bundle": payload})


def _no_float(value: Any) -> None:
    if type(value) is float:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "float")
    if type(value) is dict:
        for k, v in value.items():
            if type(k) is not str:
                _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "key")
            _no_float(v)
    elif type(value) in (list, tuple):
        for v in value:
            _no_float(v)


def _shape(
    bundle: Any, contract: Any, domain: Any, lock: Any, trusted_lock_digest: Any
) -> tuple[dict, dict, dict, dict]:
    b = _object(bundle, _BUNDLE_KEYS, "bundle")
    c = _object(contract, _CONTRACT_KEYS, "contract")
    d = _object(domain, _DOMAIN_KEYS, "domain")
    sealed_lock = _object(lock, _LOCK_KEYS, "lock")
    for obj in (b, c, d, sealed_lock):
        _no_float(obj)
    _str(trusted_lock_digest, "trusted_lock_digest", sha=True)
    if b["schema_version"] != BUNDLE_SCHEMA:
        _fail("REAL_UNSUPPORTED_SCHEMA_VERSION", 0, "bundle.schema_version")
    for key in ("study_id", "contract_digest"):
        _str(b[key], f"bundle.{key}", identifier=key == "study_id", sha=key.endswith("digest"))
    for key in ("study_id", "code_digest", "contract_digest"):
        _str(c[key], f"contract.{key}", identifier=key == "study_id", sha=key.endswith("digest"))
    if type(b["roles"]) is not list or type(c["roles"]) is not list or not c["roles"]:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "roles")
    for role in c["roles"] + b["roles"]:
        _str(role, "roles", identifier=True)
    if len(set(c["roles"])) != len(c["roles"]) or c["roles"][0] != "TARGET_OUTCOME":
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "contract.roles")
    for key in ("development_start", "development_end", "holdout_start"):
        _date(c[key], f"contract.{key}")
    if type(c["min_joint_dates"]) is not int or c["min_joint_dates"] < 1:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "contract.min_joint_dates")
    if type(c["coverage_gate"]) is not str or not re.fullmatch(
        r"(?:0|[1-9][0-9]{0,17})/[1-9][0-9]{0,17}", c["coverage_gate"]
    ):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "contract.coverage_gate")
    n, den = map(int, c["coverage_gate"].split("/"))
    if n > den:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "contract.coverage_gate")
    if type(c["source_versions"]) is not list or type(sealed_lock["source_versions"]) is not list:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "source_versions")
    for versions in (c["source_versions"], sealed_lock["source_versions"]):
        for version in versions:
            if type(version) is not list or len(version) != 8:
                _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "source_versions")
            for index, item in enumerate(version):
                _str(item, "source_versions", sha=index == 6, identifier=index != 6)
    for key in ("contract_digest", "domain_digest", "code_digest"):
        _str(sealed_lock[key], f"lock.{key}", sha=True)
    if type(sealed_lock["sealed_before_outcome"]) is not bool:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "lock.sealed_before_outcome")
    if type(c["timezone_offset"]) is not str or not re.fullmatch(
        r"[+-][0-9]{2}:[0-9]{2}", c["timezone_offset"]
    ):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "contract.timezone_offset")
    offset_hours, offset_minutes = int(c["timezone_offset"][1:3]), int(c["timezone_offset"][4:6])
    if offset_hours > 14 or offset_minutes > 59 or (offset_hours == 14 and offset_minutes != 0):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "contract.timezone_offset")
    if type(c["signal_cutoff_local"]) is not str or not re.fullmatch(
        r"[0-9]{2}:[0-9]{2}", c["signal_cutoff_local"]
    ):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "contract.signal_cutoff_local")
    try:
        time(*map(int, c["signal_cutoff_local"].split(":")))
    except ValueError:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "contract.signal_cutoff_local")
    for key in ("expected_dates", "calendar_dates"):
        if type(d[key]) is not list or not (1 <= len(d[key]) <= 10_000):
            _fail("REAL_INVALID_INPUT_STRUCTURE", 0, f"domain.{key}")
        for item in d[key]:
            _date(item, f"domain.{key}")
        if len(set(d[key])) != len(d[key]):
            _fail("REAL_INVALID_INPUT_STRUCTURE", 0, f"domain.{key}")
    if d["calendar_basis"] != "CALLER_FROZEN_UNVERIFIED":
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "domain.calendar_basis")
    if type(b["source_runs"]) is not list or type(b["observations"]) is not list:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "bundle.rows")
    for run in b["source_runs"]:
        _object(run, _RUN_KEYS, "source_run")
        for key in _RUN_KEYS - {"raw_bytes_length"}:
            _str(
                run[key],
                f"source_run.{key}",
                identifier=key not in {"raw_locator", "raw_sha256", "revision_id", "vintage_id"},
            )
        _str(run["raw_sha256"], "source_run.raw_sha256", sha=True)
        if type(run["raw_bytes_length"]) is not int or not (
            0 <= run["raw_bytes_length"] <= MAX_RAW_BYTES
        ):
            _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "source_run.raw_bytes_length")
        locator = run["raw_locator"]
        if not _LOCATOR.fullmatch(locator) or any(
            part in (".", "..") for part in locator.split("/")
        ):
            _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "source_run.raw_locator")
    for row in b["observations"]:
        _object(row, _ROW_KEYS, "observation")
        for key in _ROW_KEYS - {"value", "published_at", "available_at"}:
            _str(row[key], f"observation.{key}", identifier=key in {"role", "source_record_id"})
        if row["value"] is not None:
            _str(row["value"], "observation.value")
        _date(row["trade_date"], "observation.trade_date")
    _str(b["input_digest"], "bundle.input_digest", sha=True)
    return b, c, d, sealed_lock


def _pre_read(b: dict, c: dict, d: dict, sealed_lock: dict, trusted_lock_digest: str) -> None:
    if (
        not sealed_lock["sealed_before_outcome"]
        or type(sealed_lock["sealed_before_outcome"]) is not bool
        or _digest(sealed_lock) != trusted_lock_digest
    ):
        _fail("REAL_POST_OUTCOME_MUTATION", 1, "lock")
    if (
        contract_digest(c) != c["contract_digest"]
        or sealed_lock["contract_digest"] != c["contract_digest"]
    ):
        _fail("REAL_POST_OUTCOME_MUTATION", 1, "contract")
    if b["contract_digest"] != c["contract_digest"] or b["study_id"] != c["study_id"]:
        _fail("REAL_CONTRACT_PLAN_MISMATCH", 1, "bundle.contract_digest")
    if b["roles"] != c["roles"]:
        _fail("REAL_ROLE_BINDING_MISMATCH", 1, "bundle.roles")
    if (
        sealed_lock["code_digest"] != c["code_digest"]
        or sealed_lock["source_versions"] != c["source_versions"]
        or sealed_lock["domain_digest"] != domain_digest(d)
    ):
        _fail("REAL_POST_OUTCOME_MUTATION", 1, "lock.source_versions")
    if c["development_start"] > c["development_end"] or c["development_end"] >= c["holdout_start"]:
        _fail("REAL_HOLDOUT_INJECTION", 1, "contract.window")
    if any(
        x >= c["holdout_start"] or x < c["development_start"] or x > c["development_end"]
        for x in d["expected_dates"]
    ):
        _fail("REAL_HOLDOUT_INJECTION", 1, "domain.expected_dates")
    if any(x >= c["holdout_start"] for x in d["calendar_dates"]):
        _fail("REAL_HOLDOUT_INJECTION", 1, "domain.calendar_dates")
    if any(row["trade_date"] >= c["holdout_start"] for row in b["observations"]):
        _fail("REAL_HOLDOUT_INJECTION", 1, "bundle.observations")
    runs = b["source_runs"]
    if {r["role"] for r in runs} != set(c["roles"]) or len(runs) != len(c["roles"]):
        _fail("REAL_SOURCE_ROLE_MISSING", 1, "bundle.source_runs")
    if any(not r["revision_id"] or not r["vintage_id"] for r in runs):
        _fail("REAL_SOURCE_VERSION_MISSING", 1, "bundle.source_runs")
    versions = sorted(
        [
            [
                r[k]
                for k in (
                    "role",
                    "run_id",
                    "provider_id",
                    "endpoint_id",
                    "revision_id",
                    "vintage_id",
                    "raw_sha256",
                    "normalization_rule_id",
                )
            ]
            for r in runs
        ]
    )
    if versions != sorted(c["source_versions"]):
        _fail("REAL_POST_OUTCOME_MUTATION", 1, "contract.source_versions")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value


def _parse_raw(raw: bytes, role: str, run_id: str, locator: str) -> list[dict]:
    try:
        text = raw.decode("utf-8", "strict")
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=lambda _: (_ for _ in ()).throw(ValueError("float")),
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")),
        )
    except (UnicodeError, ValueError, TypeError):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 2, locator)
    if (
        type(value) is not dict
        or set(value) != {"format", "records"}
        or value["format"] != RAW_FORMAT
        or type(value["records"]) is not list
    ):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 2, locator)
    if _canonical(value) != raw:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 2, locator)
    seen = set()
    for row in value["records"]:
        _object(row, _ROW_KEYS, locator, 2)
        if row["role"] != role:
            _fail("REAL_ROLE_BINDING_MISMATCH", 2, locator)
        if row["source_record_id"] in seen:
            _fail("REAL_DUPLICATE_OBSERVATION", 2, locator)
        seen.add(row["source_record_id"])
    return value["records"]


@dataclass(frozen=True)
class RealSourceAuditProofK1:
    schema_version: str
    kernel_version: str
    contract_digest: str
    domain_digest: str
    input_digest: str
    coverage_numerator: int
    coverage_denominator: int
    joint_complete_dates: int
    gaps: tuple[tuple[str, str, str], ...]
    proof_digest: str
    calendar_evidence_verified: bool = False
    real_source_validated: bool = False
    outcome_bytes_examined: bool = True
    execution_authorized: bool = False
    statistics_computed: bool = False
    research_outcome_consumed: bool = False
    holdout_accessed: bool = False
    matrix: None = None


@dataclass(frozen=True)
class RealSourceRejectionK1:
    schema_version: str
    code: str
    coverage_numerator: int
    coverage_denominator: int
    joint_complete_dates: int
    gaps: tuple[tuple[str, str, str], ...]
    outcome_bytes_examined: bool
    accepted_roles: tuple = ()
    execution_authorized: bool = False
    statistics_computed: bool = False
    research_outcome_consumed: bool = False
    holdout_accessed: bool = False
    matrix: None = None


def proof_to_canonical_dict(proof: RealSourceAuditProofK1) -> dict:
    if type(proof) is not RealSourceAuditProofK1:
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "proof")
    result = dict(vars(proof))
    result["gaps"] = [list(gap) for gap in proof.gaps]
    return result


def serialize_proof(proof: RealSourceAuditProofK1) -> bytes:
    payload = proof_to_canonical_dict(proof)
    digest = payload.pop("proof_digest")
    if (
        digest != _digest(payload)
        or payload["execution_authorized"]
        or payload["statistics_computed"]
        or payload["research_outcome_consumed"]
        or payload["holdout_accessed"]
        or payload["matrix"] is not None
        or payload["real_source_validated"]
        or payload["calendar_evidence_verified"]
        or payload["schema_version"] != PROOF_SCHEMA
        or payload["kernel_version"] != KERNEL_VERSION
        or payload["outcome_bytes_examined"] is not True
    ):
        _fail("REAL_DIGEST_MISMATCH", 6, "proof")
    payload["proof_digest"] = digest
    return _canonical(payload) + b"\n"


def verify_real_daily_source_proof_k1(
    bundle: dict,
    contract: dict,
    domain: dict,
    lock: dict,
    trusted_lock_digest: str,
    raw_bytes_by_locator: Mapping[str, bytes],
) -> RealSourceAuditProofK1 | RealSourceRejectionK1:
    """Validate invented offline evidence only; never grants real-data readiness."""
    b, c, d, sealed_lock = _shape(bundle, contract, domain, lock, trusted_lock_digest)
    b, c, d, sealed_lock = (copy.deepcopy(item) for item in (b, c, d, sealed_lock))
    _pre_read(b, c, d, sealed_lock, trusted_lock_digest)
    if not isinstance(raw_bytes_by_locator, Mapping):
        _fail("REAL_INVALID_INPUT_STRUCTURE", 0, "raw_bytes_by_locator")
    raw_rows = []
    for run in sorted(b["source_runs"], key=lambda r: r["role"]):
        locator = run["raw_locator"]
        if locator not in raw_bytes_by_locator:
            _fail("REAL_SOURCE_IDENTITY_MISMATCH", 2, locator)
        raw = raw_bytes_by_locator[locator]
        if type(raw) is not bytes:
            _fail("REAL_INVALID_INPUT_STRUCTURE", 2, locator)
        if (
            len(raw) != run["raw_bytes_length"]
            or hashlib.sha256(raw).hexdigest() != run["raw_sha256"]
        ):
            _fail("REAL_RAW_HASH_MISMATCH", 2, locator)
        if run["normalization_rule_id"] != RAW_FORMAT:
            _fail("REAL_UNSUPPORTED_SCHEMA_VERSION", 2, locator)
        raw_rows.extend(_parse_raw(raw, run["role"], run["run_id"], locator))

    def key(row: dict) -> tuple[str, str, str]:
        return row["role"], row["trade_date"], row["source_record_id"]

    if sorted(raw_rows, key=key) != sorted(b["observations"], key=key):
        _fail("REAL_SOURCE_IDENTITY_MISMATCH", 2, "bundle.observations")
    seen_cells = set()
    for row in raw_rows:
        cell = (row["role"], row["trade_date"])
        if cell in seen_cells:
            _fail("REAL_DUPLICATE_OBSERVATION", 6, "bundle.observations")
        seen_cells.add(cell)
        if (
            row["trade_date"] not in d["calendar_dates"]
            or row["trade_date"] not in d["expected_dates"]
        ):
            _fail("REAL_NON_TRADING_DATE", 3, row["trade_date"])
    if not set(d["expected_dates"]).issubset(set(d["calendar_dates"])):
        _fail("REAL_CALENDAR_CONFLICT", 3, "domain.expected_dates")
    if any(row["role"] not in c["roles"] for row in raw_rows):
        _fail("REAL_ROLE_BINDING_MISMATCH", 6, "bundle.observations")
    offset = c["timezone_offset"]
    hours, minutes = int(offset[1:3]), int(offset[4:6])
    tz = timezone((1 if offset[0] == "+" else -1) * timedelta(hours=hours, minutes=minutes))
    hh, mm = map(int, c["signal_cutoff_local"].split(":"))
    cutoff_time = time(hh, mm)
    valid_cells: set[tuple[str, str]] = set()
    reasons: dict[tuple[str, str], str] = {}
    for row in raw_rows:
        cell = (row["role"], row["trade_date"])
        observed = _timestamp(
            row["observation_at"],
            "observation.observation_at",
            missing_code="REAL_INVALID_INPUT_STRUCTURE",
        )
        published = _timestamp(
            row["published_at"],
            "observation.published_at",
            missing_code="REAL_PUBLISHED_AT_MISSING",
        )
        available = _timestamp(
            row["available_at"],
            "observation.available_at",
            missing_code="REAL_AVAILABLE_AT_MISSING",
        )
        ingested = _timestamp(
            row["ingested_at"],
            "observation.ingested_at",
            missing_code="REAL_INVALID_INPUT_STRUCTURE",
        )
        if row["available_at_basis"] != "SOURCE_PUBLICATION_VERIFIED":
            _fail("REAL_INGESTED_AT_AS_PIT", 5, "observation.available_at_basis")
        if not (observed <= published <= available <= ingested):
            _fail("REAL_INVALID_INPUT_STRUCTURE", 5, "observation.available_at")
        if row["value"] is not None:
            _decimal(row["value"], "observation.value")
        cutoff = datetime.combine(date.fromisoformat(row["trade_date"]), cutoff_time, tz)
        if available > cutoff:
            reasons[cell] = "PIT_UNPROVEN"
        elif row["value"] is None:
            reasons[cell] = "MISSING_OBSERVATION"
        else:
            valid_cells.add(cell)
    if b["input_digest"] != input_digest(b):
        _fail("REAL_DIGEST_MISMATCH", 6, "bundle.input_digest")
    gaps = tuple(
        (day, role, reasons.get((role, day), "MISSING_OBSERVATION"))
        for day in sorted(d["expected_dates"])
        for role in c["roles"]
        if (role, day) not in valid_cells
    )
    denominator = len(d["expected_dates"]) * len(c["roles"])
    numerator = len(valid_cells)
    joint = sum(
        all((role, day) in valid_cells for role in c["roles"]) for day in d["expected_dates"]
    )
    gate_n, gate_d = map(int, c["coverage_gate"].split("/"))
    code = (
        "REAL_COVERAGE_BELOW_GATE"
        if numerator * gate_d < gate_n * denominator
        else "REAL_JOINT_DATES_BELOW_MIN"
        if joint < c["min_joint_dates"]
        else None
    )
    if code:
        return RealSourceRejectionK1(
            REJECTION_SCHEMA, code, numerator, denominator, joint, gaps, True
        )
    payload = {
        "schema_version": PROOF_SCHEMA,
        "kernel_version": KERNEL_VERSION,
        "contract_digest": c["contract_digest"],
        "domain_digest": domain_digest(d),
        "input_digest": b["input_digest"],
        "coverage_numerator": numerator,
        "coverage_denominator": denominator,
        "joint_complete_dates": joint,
        "gaps": [list(g) for g in gaps],
        "calendar_evidence_verified": False,
        "real_source_validated": False,
        "outcome_bytes_examined": True,
        "execution_authorized": False,
        "statistics_computed": False,
        "research_outcome_consumed": False,
        "holdout_accessed": False,
        "matrix": None,
    }
    return RealSourceAuditProofK1(
        PROOF_SCHEMA,
        KERNEL_VERSION,
        c["contract_digest"],
        domain_digest(d),
        b["input_digest"],
        numerator,
        denominator,
        joint,
        gaps,
        _digest(payload),
    )


def validate_real_source_proof_k1(
    proof: RealSourceAuditProofK1,
    bundle: dict,
    contract: dict,
    domain: dict,
    lock: dict,
    trusted_lock_digest: str,
    raw_bytes_by_locator: Mapping[str, bytes],
) -> None:
    expected = verify_real_daily_source_proof_k1(
        bundle, contract, domain, lock, trusted_lock_digest, raw_bytes_by_locator
    )
    if type(expected) is not RealSourceAuditProofK1 or serialize_proof(proof) != serialize_proof(
        expected
    ):
        _fail("REAL_DIGEST_MISMATCH", 6, "proof")
