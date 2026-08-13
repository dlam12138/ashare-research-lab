"""Canonical SHA-256 identity for metric results."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from ashare_research.metrics.models import MetricResult


class MetricIdentityError(ValueError):
    """A metric result does not carry its canonical identity."""


def metric_identity_payload(result: MetricResult | dict[str, Any]) -> dict[str, Any]:
    data = asdict(result) if isinstance(result, MetricResult) else result
    return {
        "available_at": str(data.get("available_at", "")).strip(),
        "formula": str(data.get("formula", "")).strip(),
        "fiscal_year": int(data.get("fiscal_year", 0)),
        "input_fact_ids": [
            str(value)
            for value in data.get("input_fact_ids", ())
        ],
        "metric_definition_version": str(
            data.get("metric_definition_version", "1")
        ).strip(),
        "metric_id": str(data.get("metric_id", "")).strip(),
        "result_version": int(data.get("result_version", 1)),
        "status": str(data.get("status", "")).strip(),
        "supersedes_metric_result_id": str(
            data.get("supersedes_metric_result_id", "")
        ).strip(),
        "symbol": str(data.get("symbol", "")).strip(),
    }


def build_metric_result_id(result: MetricResult | dict[str, Any]) -> str:
    payload = json.dumps(
        metric_identity_payload(result),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_canonical_metric_result_id(result: MetricResult) -> None:
    expected = build_metric_result_id(result)
    if result.metric_result_id != expected:
        raise MetricIdentityError(
            "metric_result_id is not canonical: "
            f"actual={result.metric_result_id!r}, expected={expected}"
        )
