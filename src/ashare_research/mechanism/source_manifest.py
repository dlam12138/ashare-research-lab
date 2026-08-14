"""Immutable raw-cache verification and canonical logical identity."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from ashare_research.mechanism.contracts import (
    Stage3BContractError,
    assert_no_restricted_research_outputs,
    sha256_file,
)


def canonical_frame_digest(frame: pd.DataFrame) -> str:
    """Hash a frame after stable ordering, ISO timestamp, and null canonicalization."""
    canonical = frame.copy()
    canonical = canonical.reindex(sorted(canonical.columns), axis=1)
    for column in canonical.columns:
        if pd.api.types.is_datetime64_any_dtype(canonical[column]):
            canonical[column] = canonical[column].dt.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    canonical = canonical.astype(object).where(pd.notna(canonical), None)
    records = canonical.to_dict(orient="records")
    records.sort(key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str))
    encoded = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_raw_manifest(entries: list[dict[str, Any]], raw_root: str | Path) -> None:
    """Verify every raw path remains under its explicit root and matches the locked SHA."""
    root = Path(raw_root).resolve()
    for entry in entries:
        relative = Path(str(entry.get("raw_file_path", "")))
        if relative.is_absolute() or not relative.parts:
            raise Stage3BContractError("raw manifest path must be relative")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise Stage3BContractError("raw manifest path escapes raw root") from exc
        expected = str(entry.get("raw_sha256", "")).lower()
        if not candidate.is_file() or sha256_file(candidate) != expected:
            raise Stage3BContractError(f"raw SHA mismatch: {relative.as_posix()}")


def build_coverage_metadata(
    frame: pd.DataFrame,
    *,
    dataset_id: str,
    expected_dates: pd.Series | None = None,
) -> dict[str, Any]:
    """Build data-quality-only metadata with no mechanism-result statistics."""
    if "trade_date" not in frame.columns:
        raise Stage3BContractError("coverage input missing trade_date")
    dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    if dates.isna().any():
        raise Stage3BContractError("coverage input has invalid trade_date")
    unique_dates = sorted(value.date().isoformat() for value in dates.drop_duplicates())
    expected: set[str] = set()
    if expected_dates is not None:
        expected = {
            value.date().isoformat()
            for value in pd.to_datetime(expected_dates, errors="raise").drop_duplicates()
        }
    observed = set(unique_dates)
    payload: dict[str, Any] = {
        "dataset_id": dataset_id,
        "rows": int(len(frame)),
        "date_start": unique_dates[0] if unique_dates else None,
        "date_end": unique_dates[-1] if unique_dates else None,
        "missing_dates": sorted(expected - observed),
        "duplicate_keys": int(frame.duplicated().sum()),
        "coverage_ratio": (len(observed & expected) / len(expected)) if expected else None,
        "schema": sorted(frame.columns),
        "logical_sha256": canonical_frame_digest(frame),
        "normalization_status": "NORMALIZED",
    }
    assert_no_restricted_research_outputs(payload)
    return payload


def atomic_write_json(path: str | Path, payload: dict[str, Any]) -> None:
    """Write canonical JSON atomically after applying the Stage 3B output-key gate."""
    assert_no_restricted_research_outputs(payload)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    data = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    try:
        temporary.write_text(data, encoding="utf-8", newline="\n")
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
