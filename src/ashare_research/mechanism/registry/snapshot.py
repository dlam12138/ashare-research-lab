"""Deterministic, bounded in-memory hypothesis registry snapshots."""

from __future__ import annotations

import json
from dataclasses import dataclass

from ashare_research.mechanism.model_digest import canonical_digest

from .records import (
    DIGEST_ALGORITHM_ID,
    HypothesisRecordV1,
    RegistryError,
    hypothesis_record_to_canonical_dict,
    validate_hypothesis_record,
)

SNAPSHOT_SCHEMA_VERSION = "M4_HYPOTHESIS_REGISTRY_SNAPSHOT_V1"
REGISTRY_VERSION = "M4_THEORY_HYPOTHESIS_REGISTRY_V1"
MAX_REAL_DEMO_CANDIDATES = 3
MAX_RECORDS_PER_SNAPSHOT = 3
INTERPRETATION_BOUNDARY = (
    "REGISTRY_METADATA_ONLY: design-stage hypothesis provenance metadata. Not evidence, "
    "not a research finding, not a significance, effectiveness, estimability or tradability "
    "claim, not an A-share mechanism result, and not an authorization to implement the "
    "registry, to create a real candidate dataset, to acquire literature, to execute on real "
    "data, to access holdout, or to enter M4-A/M4-B execution."
)


@dataclass(frozen=True)
class HypothesisRegistrySnapshotV1:
    registry_schema_version: str
    registry_version: str
    digest_algorithm: str
    interpretation_boundary: str
    records: tuple[HypothesisRecordV1, ...]
    real_demo_candidate_count: int
    registry_digest: str


def count_real_demo_candidates(snapshot: HypothesisRegistrySnapshotV1) -> int:
    return sum(
        record.a_share_data_feasibility in {"FEASIBLE_FREE", "FEASIBLE_PAID"}
        for record in snapshot.records
    )


def _payload(snapshot: HypothesisRegistrySnapshotV1) -> dict[str, object]:
    return {
        "registry_schema_version": snapshot.registry_schema_version,
        "registry_version": snapshot.registry_version,
        "digest_algorithm": snapshot.digest_algorithm,
        "interpretation_boundary": snapshot.interpretation_boundary,
        "records": [hypothesis_record_to_canonical_dict(record) for record in snapshot.records],
        "real_demo_candidate_count": snapshot.real_demo_candidate_count,
    }


def validate_hypothesis_registry_snapshot(snapshot: HypothesisRegistrySnapshotV1) -> None:
    if not isinstance(snapshot, HypothesisRegistrySnapshotV1) or not isinstance(
        snapshot.records, tuple
    ):
        raise RegistryError("INVALID_RECORD_STRUCTURE")
    if (
        snapshot.registry_schema_version != SNAPSHOT_SCHEMA_VERSION
        or snapshot.registry_version != REGISTRY_VERSION
        or snapshot.digest_algorithm != DIGEST_ALGORITHM_ID
        or snapshot.interpretation_boundary != INTERPRETATION_BOUNDARY
    ):
        raise RegistryError("INVALID_ENUM_VALUE")
    for record in snapshot.records:
        validate_hypothesis_record(record)
    keys: dict[tuple[str, int], str] = {}
    for record in snapshot.records:
        key = (record.hypothesis_id, record.hypothesis_version)
        if key in keys:
            code = (
                "DUPLICATE_HYPOTHESIS_ID"
                if keys[key] == record.identity_digest
                else "PROVENANCE_REWRITE"
            )
            raise RegistryError(code)
        keys[key] = record.identity_digest
    if (
        tuple(
            sorted(snapshot.records, key=lambda item: (item.hypothesis_id, item.hypothesis_version))
        )
        != snapshot.records
    ):
        raise RegistryError("INVALID_RECORD_STRUCTURE")
    count = count_real_demo_candidates(snapshot)
    if len(snapshot.records) > MAX_RECORDS_PER_SNAPSHOT or count > MAX_REAL_DEMO_CANDIDATES:
        raise RegistryError("SCALE_LIMIT_EXCEEDED")
    if (
        type(snapshot.real_demo_candidate_count) is not int
        or snapshot.real_demo_candidate_count != count
    ):
        raise RegistryError("INVALID_FIELD_TYPE")
    if snapshot.registry_digest != canonical_digest(_payload(snapshot)):
        raise RegistryError("RECORD_DIGEST_MISMATCH")


def build_hypothesis_registry_snapshot(
    records: tuple[HypothesisRecordV1, ...],
) -> HypothesisRegistrySnapshotV1:
    if not isinstance(records, tuple):
        raise RegistryError("INVALID_RECORD_STRUCTURE")
    for record in records:
        validate_hypothesis_record(record)
    ordered = tuple(sorted(records, key=lambda item: (item.hypothesis_id, item.hypothesis_version)))
    draft = HypothesisRegistrySnapshotV1(
        registry_schema_version=SNAPSHOT_SCHEMA_VERSION,
        registry_version=REGISTRY_VERSION,
        digest_algorithm=DIGEST_ALGORITHM_ID,
        interpretation_boundary=INTERPRETATION_BOUNDARY,
        records=ordered,
        real_demo_candidate_count=sum(
            item.a_share_data_feasibility in {"FEASIBLE_FREE", "FEASIBLE_PAID"} for item in ordered
        ),
        registry_digest="",
    )
    digest = canonical_digest(_payload(draft))
    snapshot = HypothesisRegistrySnapshotV1(**{**draft.__dict__, "registry_digest": digest})
    validate_hypothesis_registry_snapshot(snapshot)
    return snapshot


def registry_snapshot_to_canonical_dict(
    snapshot: HypothesisRegistrySnapshotV1,
) -> dict[str, object]:
    validate_hypothesis_registry_snapshot(snapshot)
    return {**_payload(snapshot), "registry_digest": snapshot.registry_digest}


def serialize_hypothesis_registry_snapshot(snapshot: HypothesisRegistrySnapshotV1) -> bytes:
    return (
        json.dumps(
            registry_snapshot_to_canonical_dict(snapshot),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
