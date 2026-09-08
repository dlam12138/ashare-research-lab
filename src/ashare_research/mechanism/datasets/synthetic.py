"""Pure, bounded adapter for the M4 synthetic role dataset.

This module intentionally has no provider, filesystem, database, or statistics
dependencies.  It validates the frozen A.1 contract and A.2 plan before building
an immutable, canonical preparation envelope.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from types import UnionType
from typing import Any, get_args, get_origin, get_type_hints

from ashare_research.mechanism.model_digest import canonical_digest
from ashare_research.mechanism.planning import (
    build_analysis_plan,
    plan_to_canonical_dict,
    serialize_analysis_plan,
    validate_analysis_plan,
)

SCHEMA = "M4_BOUND_SYNTHETIC_DATASET_V1"
OUTPUT_SCHEMA = "M4_DATASET_PREPARATION_V1"
ADAPTER_VERSION = "M4_SYNTHETIC_ROLE_ADAPTER_V1"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ROLES = ("TARGET_OUTCOME", "FACTOR")


class AdapterError(ValueError):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def _fail(code: str, message: str | None = None) -> None:
    raise AdapterError(code, message)


def _shape(value: Any, expected: Any) -> None:
    """Reject mutable or forged runtime representations before any conversion."""
    origin = get_origin(expected)
    if origin is UnionType:
        for kind in get_args(expected):
            if type(value) is kind:
                _shape(value, kind)
                return
        _fail("INVALID_INPUT_STRUCTURE")
    elif origin is tuple:
        if type(value) is not tuple:
            _fail("INVALID_INPUT_STRUCTURE")
        kinds = get_args(expected)
        if len(kinds) == 2 and kinds[1] is Ellipsis:
            for item in value:
                _shape(item, kinds[0])
        else:
            if len(value) != len(kinds):
                _fail("INVALID_INPUT_STRUCTURE")
            for item, kind in zip(value, kinds, strict=True):
                _shape(item, kind)
    else:
        if type(value) is not expected:
            _fail("INVALID_INPUT_STRUCTURE")
        if is_dataclass(expected):
            for name, kind in get_type_hints(expected).items():
                _shape(getattr(value, name), kind)


class _Checked:
    def __post_init__(self) -> None:
        _shape(self, type(self))


def _identifier(value: Any) -> None:
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value) is None:
        _fail("INVALID_INPUT_STRUCTURE")


def _hash(value: Any) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _fail("INVALID_INPUT_STRUCTURE")


def _sequence(value: Any) -> Any:
    if type(value) not in (list, tuple):
        _fail("INVALID_INPUT_STRUCTURE")
    return value


def _date(value: Any) -> str:
    if type(value) is not str or not DATE_RE.fullmatch(value):
        _fail("INVALID_DATE")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail("INVALID_DATE")
    if parsed.isoformat() != value:
        _fail("INVALID_DATE")
    return value


def _dec(value: Any, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str:
        _fail("INVALID_VALUE")
    try:
        d = Decimal(value)
    except (InvalidOperation, ValueError):
        _fail("INVALID_VALUE")
    if not d.is_finite():
        _fail("INVALID_VALUE")
    # canonical_decimal is intentionally not used to accept or repair input.
    canonical = "0" if d == 0 else format(d, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    if canonical != value:
        _fail("INVALID_VALUE")
    return value


def _keys(obj: Any, expected: set[str]) -> None:
    if type(obj) is not dict or set(obj) != expected:
        _fail("INVALID_INPUT_STRUCTURE")


def _copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_copy(v) for v in value]
    return value


@dataclass(frozen=True)
class _CalendarEvidence(_Checked):
    evidence_kind: str
    domain_id: str
    development_start: str
    development_end: str
    expected_dates: tuple[str, ...]
    evidence_digest: str

    def as_dict(self) -> dict:
        return {
            "evidence_kind": self.evidence_kind,
            "domain_id": self.domain_id,
            "development_start": self.development_start,
            "development_end": self.development_end,
            "expected_dates": list(self.expected_dates),
            "evidence_digest": self.evidence_digest,
        }


@dataclass(frozen=True)
class _MembershipEvidence(_Checked):
    evidence_kind: str
    universe_id: str
    target_series_id: str
    expected_dates: tuple[str, ...]
    evidence_digest: str

    def as_dict(self) -> dict:
        return {
            "evidence_kind": self.evidence_kind,
            "universe_id": self.universe_id,
            "target_series_id": self.target_series_id,
            "expected_dates": list(self.expected_dates),
            "evidence_digest": self.evidence_digest,
        }


def _parse_evidence(value: dict, evidence_type: type) -> Any:
    _keys(value, {f.name for f in fields(evidence_type)})
    payload = dict(value)
    payload["expected_dates"] = tuple(_sequence(payload["expected_dates"]))
    return evidence_type(**payload)


@dataclass(frozen=True)
class ExpectedDomainV1(_Checked):
    domain_id: str
    universe_id: str
    membership_policy: str
    pit_policy: str
    target_series_id: str
    identity_policy: str
    development_start: str
    development_end: str
    expected_dates: tuple[str, ...]
    calendar_evidence: _CalendarEvidence
    membership_evidence: _MembershipEvidence

    def __post_init__(self) -> None:
        _shape(self, ExpectedDomainV1)
        if type(self.expected_dates) is not tuple or not self.expected_dates:
            _fail("EMPTY_EXPECTED_DOMAIN")
        dates = tuple(_date(x) for x in self.expected_dates)
        if dates != tuple(sorted(set(dates))):
            _fail("INVALID_DATE")
        for name in ("domain_id", "universe_id", "target_series_id"):
            _identifier(getattr(self, name))
        _date(self.development_start)
        _date(self.development_end)
        self.validate()

    @classmethod
    def from_dict(cls, value: dict) -> ExpectedDomainV1:
        _keys(value, set(cls.__dataclass_fields__))
        dates = tuple(_date(x) for x in _sequence(value["expected_dates"]))
        if not dates or dates != tuple(sorted(set(dates))):
            _fail("EMPTY_EXPECTED_DOMAIN")
        obj = cls(
            value["domain_id"],
            value["universe_id"],
            value["membership_policy"],
            value["pit_policy"],
            value["target_series_id"],
            value["identity_policy"],
            _date(value["development_start"]),
            _date(value["development_end"]),
            dates,
            _parse_evidence(value["calendar_evidence"], _CalendarEvidence),
            _parse_evidence(value["membership_evidence"], _MembershipEvidence),
        )
        obj.validate()
        return obj

    def validate(self) -> None:
        if self.development_start > self.development_end or any(
            not (self.development_start <= x <= self.development_end) for x in self.expected_dates
        ):
            _fail("INVALID_DATE")
        cal = {
            "evidence_kind": "SYNTHETIC_CALENDAR_V1",
            "domain_id": self.domain_id,
            "development_start": self.development_start,
            "development_end": self.development_end,
            "expected_dates": list(self.expected_dates),
        }
        mem = {
            "evidence_kind": "SYNTHETIC_FIXED_MEMBERSHIP_V1",
            "universe_id": self.universe_id,
            "target_series_id": self.target_series_id,
            "expected_dates": list(self.expected_dates),
        }
        c = self.calendar_evidence.as_dict()
        m = self.membership_evidence.as_dict()
        if c.get("evidence_digest") != canonical_digest(cal):
            _fail("EVIDENCE_DIGEST_MISMATCH")
        if m.get("evidence_digest") != canonical_digest(mem):
            _fail("EVIDENCE_DIGEST_MISMATCH")
        if {k: v for k, v in c.items() if k != "evidence_digest"} != cal:
            _fail("EVIDENCE_DIGEST_MISMATCH")
        if {k: v for k, v in m.items() if k != "evidence_digest"} != mem:
            _fail("EVIDENCE_DIGEST_MISMATCH")


@dataclass(frozen=True)
class RoleBindingV1(_Checked):
    role: str
    series_id: str
    value_semantics: str
    unit: str
    adjustment_policy: str
    outcome_id: str | None
    horizon: str
    observation_timing: str

    def __post_init__(self) -> None:
        _shape(self, RoleBindingV1)
        _identifier(self.role)
        _identifier(self.series_id)
        if self.outcome_id is not None:
            _identifier(self.outcome_id)

    @classmethod
    def from_dict(cls, value: dict) -> RoleBindingV1:
        _keys(value, set(cls.__dataclass_fields__))
        return cls(**_copy(value))


@dataclass(frozen=True)
class ObservationV1(_Checked):
    role: str
    trade_date: str
    value: str | None
    available_on: str | None
    source_record_id: str
    evidence_digest: str

    def __post_init__(self) -> None:
        _date(self.trade_date)
        _dec(self.value, True)
        if self.available_on is not None:
            _date(self.available_on)
        _shape(self, ObservationV1)
        _identifier(self.role)
        _identifier(self.source_record_id)
        _hash(self.evidence_digest)

    @classmethod
    def from_dict(cls, value: dict) -> ObservationV1:
        _keys(value, set(cls.__dataclass_fields__))
        obj = cls(
            value["role"],
            _date(value["trade_date"]),
            _dec(value["value"], True),
            None if value["available_on"] is None else _date(value["available_on"]),
            value["source_record_id"],
            value["evidence_digest"],
        )
        return obj


@dataclass(frozen=True)
class BoundDatasetInputsV1(_Checked):
    schema_version: str
    mode: str
    source_contract_digest: str
    plan_digest: str
    domain: ExpectedDomainV1
    bindings: tuple[RoleBindingV1, ...]
    observations: tuple[ObservationV1, ...]
    input_digest: str

    def __post_init__(self) -> None:
        _shape(self, BoundDatasetInputsV1)

    @classmethod
    def from_dict(cls, value: dict) -> BoundDatasetInputsV1:
        _keys(value, set(cls.__dataclass_fields__))
        return cls(
            value["schema_version"],
            value["mode"],
            value["source_contract_digest"],
            value["plan_digest"],
            ExpectedDomainV1.from_dict(value["domain"]),
            tuple(RoleBindingV1.from_dict(x) for x in _sequence(value["bindings"])),
            tuple(ObservationV1.from_dict(x) for x in _sequence(value["observations"])),
            value["input_digest"],
        )


@dataclass(frozen=True)
class AuditCellV1(_Checked):
    role: str
    value: str | None
    available_on: str | None
    source_record_id: str | None
    evidence_digest: str | None
    valid: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AuditRowV1(_Checked):
    trade_date: str
    cells: tuple[AuditCellV1, ...]


@dataclass(frozen=True)
class QualityReportV1(_Checked):
    coverage_numerator: int
    coverage_denominator: int
    coverage_gate: str
    missingness_policy: str
    failure_disposition: str
    reason_counts: tuple[tuple[str, int], ...]
    rejected_dates: tuple[str, ...]


@dataclass(frozen=True)
class DatasetPreparationV1(_Checked):
    schema_version: str
    adapter_version: str
    source_contract_digest: str
    plan_digest: str
    input_digest: str
    domain_digest: str
    role_order: tuple[str, ...]
    status: str
    execution_authorized: bool
    quality: QualityReportV1
    audit_rows: tuple[AuditRowV1, ...]
    complete_rows: tuple[tuple[str, tuple[str, ...], int], ...]
    dataset_digest: str


def _binding_dict(b: RoleBindingV1) -> dict:
    return {f.name: getattr(b, f.name) for f in fields(b)}


def _obs_dict(o: ObservationV1) -> dict:
    return {f.name: getattr(o, f.name) for f in fields(o)}


def _domain_dict(d: ExpectedDomainV1) -> dict:
    return {
        "domain_id": d.domain_id,
        "universe_id": d.universe_id,
        "membership_policy": d.membership_policy,
        "pit_policy": d.pit_policy,
        "target_series_id": d.target_series_id,
        "identity_policy": d.identity_policy,
        "development_start": d.development_start,
        "development_end": d.development_end,
        "expected_dates": list(d.expected_dates),
        "calendar_evidence": d.calendar_evidence.as_dict(),
        "membership_evidence": d.membership_evidence.as_dict(),
    }


def _input_payload(x: BoundDatasetInputsV1) -> dict:
    order = {b.role: i for i, b in enumerate(x.bindings)}
    return {
        "schema_version": x.schema_version,
        "mode": x.mode,
        "source_contract_digest": x.source_contract_digest,
        "plan_digest": x.plan_digest,
        "domain": _domain_dict(x.domain),
        "bindings": [_binding_dict(b) for b in x.bindings],
        "observations": [
            _obs_dict(o)
            for o in sorted(x.observations, key=lambda o: (o.trade_date, order.get(o.role, 10**9)))
        ],
    }


def _extract_plan(plan: Any) -> dict:
    return plan_to_canonical_dict(plan)


def _validate_inputs(contract: Any, plan: Any, x: BoundDatasetInputsV1) -> tuple[dict, list[str]]:
    _shape(x, BoundDatasetInputsV1)
    if contract is None or plan is None or x is None:
        _fail("INVALID_INPUT_STRUCTURE")
    if x.schema_version != SCHEMA:
        _fail("INVALID_INPUT_STRUCTURE")
    if x.mode != "SYNTHETIC":
        _fail("UNSUPPORTED_MODE")
    try:
        rebuilt = build_analysis_plan(contract)
    except (ValueError, TypeError) as exc:
        _fail("CONTRACT_PLAN_MISMATCH", str(exc))
    try:
        validate_analysis_plan(plan)
        plan_bytes = serialize_analysis_plan(plan)
        rebuilt_bytes = serialize_analysis_plan(rebuilt)
    except (ValueError, TypeError) as exc:
        _fail("CONTRACT_PLAN_MISMATCH", str(exc))
    if rebuilt_bytes != plan_bytes:
        _fail("CONTRACT_PLAN_MISMATCH")
    if x.source_contract_digest != contract.contract_digest or x.plan_digest != plan.plan_digest:
        _fail("CONTRACT_PLAN_MISMATCH")
    x.domain.__post_init__()
    if (
        x.domain.universe_id != contract.universe.universe_id
        or x.domain.membership_policy != contract.universe.membership_policy
        or x.domain.pit_policy != contract.universe.pit_policy
        or x.domain.target_series_id != contract.target.series_id
        or x.domain.identity_policy != contract.target.identity_policy
        or x.domain.development_start != contract.development.start
        or x.domain.development_end != contract.development.end
    ):
        _fail("ROLE_BINDING_MISMATCH")
    p = _extract_plan(plan)
    expected = [(z["role"], z["series_id"]) for z in p["dataset_requirements"]["requirements"]]
    if (
        contract.factor.transform_semantics != "RETURN"
        or contract.factor.factor_kind != "SYNTHETIC_REGISTERED"
        or contract.target.identity_policy != "SYNTHETIC_FIXED_IDENTITY"
        or contract.universe.membership_policy != "SYNTHETIC_FIXED_UNIVERSE"
        or contract.universe.pit_policy != "EXPLICIT_PIT"
    ):
        _fail("UNSUPPORTED_BINDING_POLICY")
    if contract.outcome.horizon != "1D" or contract.outcome.observation_timing != "CLOSE_TO_CLOSE":
        _fail("UNSUPPORTED_OUTCOME")
    if (
        tuple(b.role for b in x.bindings) != tuple(a for a, _ in expected)
        or [(b.role, b.series_id) for b in x.bindings] != expected
    ):
        _fail("ROLE_BINDING_MISMATCH")
    for b, (role, sid) in zip(x.bindings, expected, strict=True):
        b.__post_init__()
        if (
            b.unit != "DECIMAL_RETURN"
            or b.adjustment_policy != "SYNTHETIC_DECLARED_RETURN"
            or b.value_semantics != "DAILY_RETURN"
            or b.horizon != "1D"
            or b.observation_timing != "CLOSE_TO_CLOSE"
            or b.series_id != sid
            or (
                b.outcome_id != contract.outcome.outcome_id
                if role == "TARGET_OUTCOME"
                else b.outcome_id is not None
            )
        ):
            _fail("ROLE_BINDING_MISMATCH")
    known = set(a for a, _ in expected)
    role_order = {role: i for i, (role, _) in enumerate(expected)}
    binding_by_role = {b.role: b for b in x.bindings}
    domain_dates = set(x.domain.expected_dates)
    if any(o.role not in known for o in x.observations):
        _fail("ROLE_BINDING_MISMATCH")
    observations = sorted(x.observations, key=lambda o: (o.trade_date, role_order[o.role]))
    seen = set()
    bykey = {}
    for o in observations:
        o.__post_init__()
        key = (o.role, o.trade_date)
        if key in seen:
            _fail("DUPLICATE_OBSERVATION")
        seen.add(key)
        if o.trade_date not in domain_dates:
            _fail("OUT_OF_DOMAIN")
        b = binding_by_role[o.role]
        ev = {
            "role": o.role,
            "trade_date": o.trade_date,
            "value": o.value,
            "available_on": o.available_on,
            "source_record_id": o.source_record_id,
            "binding": _binding_dict(b),
        }
        if o.evidence_digest != canonical_digest(ev):
            _fail("EVIDENCE_DIGEST_MISMATCH")
        bykey[key] = o
    source_rows: dict[str, tuple[str, str, str | None, str | None]] = {}
    for o in observations:
        identity = (binding_by_role[o.role].series_id, o.trade_date, o.value, o.available_on)
        prior = source_rows.get(o.source_record_id)
        if prior is not None and prior != identity:
            _fail("IDENTITY_CONFLICT")
        source_rows[o.source_record_id] = identity
    series_rows: dict[tuple[str, str], ObservationV1] = {}
    for o in observations:
        binding = binding_by_role[o.role]
        key = (binding.series_id, o.trade_date)
        prior = series_rows.get(key)
        if prior is not None and (
            prior.value,
            prior.available_on,
            prior.source_record_id,
        ) != (o.value, o.available_on, o.source_record_id):
            _fail("IDENTITY_CONFLICT")
        series_rows[key] = o
    if x.input_digest != canonical_digest(_input_payload(x)):
        _fail("INPUT_DIGEST_MISMATCH")
    return bykey, [a for a, _ in expected]


def _coverage_ge(n: int, d: int, gate: str) -> bool:
    g = Decimal(gate)
    p, q = g.as_integer_ratio()
    return n * q >= d * p


def materialize_analysis_dataset(
    contract: Any, plan: Any, bound_inputs: BoundDatasetInputsV1 | dict
) -> DatasetPreparationV1:
    x = (
        BoundDatasetInputsV1.from_dict(bound_inputs)
        if isinstance(bound_inputs, dict)
        else bound_inputs
    )
    bykey, roles = _validate_inputs(contract, plan, x)
    reasons: dict[str, int] = {}
    audits = []
    complete = []
    for td in x.domain.expected_dates:
        cells = []
        validrow = True
        vals = []
        for role in roles:
            o = bykey.get((role, td))
            rs = []
            if o is None:
                rs = ["MISSING_OBSERVATION"]
            else:
                if o.value is None:
                    rs.append("MISSING_VALUE")
                if o.available_on is None:
                    rs.append("PIT_UNPROVEN")
                elif o.available_on > td:
                    rs.append("PIT_NOT_AVAILABLE")
            for r in rs:
                reasons[r] = reasons.get(r, 0) + 1
            valid = not rs
            validrow &= valid
            if valid:
                vals.append(o.value)
            cells.append(
                AuditCellV1(
                    role,
                    None if o is None else o.value,
                    None if o is None else o.available_on,
                    None if o is None else o.source_record_id,
                    None if o is None else o.evidence_digest,
                    valid,
                    tuple(sorted(rs)),
                )
            )
        audits.append(AuditRowV1(td, tuple(cells)))
        if validrow:
            f = Decimal(vals[1])
            t = Decimal(contract.condition.threshold)
            op = contract.condition.operator
            indicator = int({"LT": f < t, "LTE": f <= t, "GT": f > t, "GTE": f >= t}[op])
            complete.append((td, tuple(vals), indicator))
    n = len(complete)
    d = len(x.domain.expected_dates)
    gate = contract.data_quality_gates.coverage_gate
    rejected = tuple(a.trade_date for a in audits if not all(c.valid for c in a.cells))
    fail_closed = contract.data_quality_gates.missingness_policy == "FAIL_CLOSED"
    status = (
        "READY_SYNTHETIC"
        if n and _coverage_ge(n, d, gate) and (not rejected or not fail_closed)
        else "REJECTED_QUALITY"
    )
    quality = QualityReportV1(
        n,
        d,
        gate,
        contract.data_quality_gates.missingness_policy,
        contract.evidence_rule.data_quality_failure_disposition,
        tuple(sorted(reasons.items())),
        rejected,
    )
    out = DatasetPreparationV1(
        OUTPUT_SCHEMA,
        ADAPTER_VERSION,
        contract.contract_digest,
        plan.plan_digest,
        x.input_digest,
        canonical_digest(_domain_dict(x.domain)),
        tuple(roles),
        status,
        False,
        quality,
        tuple(audits),
        tuple(complete if status == "READY_SYNTHETIC" else ()),
        "",
    )
    return _with_digest(out)


def _cell_dict(c: AuditCellV1) -> dict:
    return {
        f.name: (
            list(getattr(c, f.name))
            if isinstance(getattr(c, f.name), tuple)
            else getattr(c, f.name)
        )
        for f in fields(c)
    }


def _audit_dict(a: AuditRowV1) -> dict:
    return {"trade_date": a.trade_date, "cells": [_cell_dict(c) for c in a.cells]}


def _quality_dict(q: QualityReportV1) -> dict:
    return {
        "coverage_numerator": q.coverage_numerator,
        "coverage_denominator": q.coverage_denominator,
        "coverage_gate": q.coverage_gate,
        "missingness_policy": q.missingness_policy,
        "failure_disposition": q.failure_disposition,
        "reason_counts": {k: v for k, v in q.reason_counts},
        "rejected_dates": list(q.rejected_dates),
    }


def dataset_to_canonical_dict(p: DatasetPreparationV1) -> dict:
    _shape(p, DatasetPreparationV1)
    return {
        "schema_version": p.schema_version,
        "adapter_version": p.adapter_version,
        "source_contract_digest": p.source_contract_digest,
        "plan_digest": p.plan_digest,
        "input_digest": p.input_digest,
        "domain_digest": p.domain_digest,
        "role_order": list(p.role_order),
        "status": p.status,
        "execution_authorized": p.execution_authorized,
        "quality": _quality_dict(p.quality),
        "audit_rows": [_audit_dict(a) for a in p.audit_rows],
        "complete_rows": [
            {"trade_date": d, "values": list(v), "condition_indicator": i}
            for d, v, i in p.complete_rows
        ],
        "dataset_digest": p.dataset_digest,
    }


def _with_digest(p: DatasetPreparationV1) -> DatasetPreparationV1:
    d = dataset_to_canonical_dict(p)
    d.pop("dataset_digest")
    return replace(p, dataset_digest=canonical_digest(d))


def serialize_dataset(p: DatasetPreparationV1) -> bytes:
    _shape(p, DatasetPreparationV1)
    if p.schema_version != OUTPUT_SCHEMA or p.adapter_version != ADAPTER_VERSION:
        _fail("INVALID_INPUT_STRUCTURE")
    roles = (*ROLES, *(f"CONTROL_{i:04d}" for i in range(1, len(p.role_order) - 1)))
    if p.execution_authorized is not False or p.role_order != roles:
        _fail("INVALID_INPUT_STRUCTURE")
    for name in (
        "source_contract_digest",
        "plan_digest",
        "input_digest",
        "domain_digest",
        "dataset_digest",
    ):
        _hash(getattr(p, name))
    dates = tuple(_date(row.trade_date) for row in p.audit_rows)
    if not dates or dates != tuple(sorted(set(dates))):
        _fail("INVALID_INPUT_STRUCTURE")
    q = p.quality
    _dec(q.coverage_gate)
    if (
        q.coverage_denominator != len(dates)
        or not 0 <= q.coverage_numerator <= q.coverage_denominator
        or not Decimal(0) <= Decimal(q.coverage_gate) <= Decimal(1)
        or q.missingness_policy not in ("FAIL_CLOSED", "RETAIN_IN_DENOMINATOR")
        or q.failure_disposition not in ("FAIL", "INCONCLUSIVE")
    ):
        _fail("INVALID_INPUT_STRUCTURE")
    observed_reasons: dict[str, int] = {}
    valid_rows = []
    rejected_dates = []
    for row in p.audit_rows:
        if tuple(c.role for c in row.cells) != p.role_order:
            _fail("INVALID_INPUT_STRUCTURE")
        for cell in row.cells:
            reasons = []
            if cell.source_record_id is None:
                if any(
                    v is not None for v in (cell.value, cell.available_on, cell.evidence_digest)
                ):
                    _fail("INVALID_INPUT_STRUCTURE")
                reasons.append("MISSING_OBSERVATION")
            else:
                _identifier(cell.source_record_id)
                _hash(cell.evidence_digest)
                _dec(cell.value, nullable=True)
                if cell.value is None:
                    reasons.append("MISSING_VALUE")
                if cell.available_on is None:
                    reasons.append("PIT_UNPROVEN")
                elif _date(cell.available_on) > row.trade_date:
                    reasons.append("PIT_NOT_AVAILABLE")
            if cell.reasons != tuple(sorted(reasons)) or cell.valid is not (not reasons):
                _fail("INVALID_INPUT_STRUCTURE")
            for reason in cell.reasons:
                observed_reasons[reason] = observed_reasons.get(reason, 0) + 1
        if all(cell.valid for cell in row.cells):
            valid_rows.append((row.trade_date, tuple(cell.value for cell in row.cells)))
        else:
            rejected_dates.append(row.trade_date)
    if q.reason_counts != tuple(sorted(observed_reasons.items())):
        _fail("INVALID_INPUT_STRUCTURE")
    if q.rejected_dates != tuple(rejected_dates) or q.coverage_numerator != len(valid_rows):
        _fail("INVALID_INPUT_STRUCTURE")
    ready = (
        bool(valid_rows)
        and _coverage_ge(len(valid_rows), len(dates), q.coverage_gate)
        and (q.missingness_policy == "RETAIN_IN_DENOMINATOR" or not rejected_dates)
    )
    if p.status != ("READY_SYNTHETIC" if ready else "REJECTED_QUALITY"):
        _fail("INVALID_INPUT_STRUCTURE")
    expected_rows = tuple(valid_rows) if ready else ()
    if tuple((td, values) for td, values, _ in p.complete_rows) != expected_rows:
        _fail("INVALID_INPUT_STRUCTURE")
    for _, _, indicator in p.complete_rows:
        if indicator not in (0, 1):
            _fail("INVALID_INPUT_STRUCTURE")
    d = dataset_to_canonical_dict(p)
    if p.dataset_digest != canonical_digest({k: v for k, v in d.items() if k != "dataset_digest"}):
        _fail("INPUT_DIGEST_MISMATCH")
    return (
        json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def validate_dataset(
    preparation: DatasetPreparationV1,
    contract: Any,
    plan: Any,
    bound_inputs: BoundDatasetInputsV1 | dict,
) -> None:
    expected = materialize_analysis_dataset(contract, plan, bound_inputs)
    if serialize_dataset(preparation) != serialize_dataset(expected):
        _fail("IDENTITY_CONFLICT")
