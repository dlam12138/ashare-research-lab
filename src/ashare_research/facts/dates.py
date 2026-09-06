"""Canonical date gate for PIT queries backed by VARCHAR dates."""

from __future__ import annotations

import re
from datetime import date

from ashare_research.exceptions import PointInTimeError


def validate_pit_date(value: str, parameter: str) -> None:
    """Require YYYY-MM-DD exactly so lexical ordering equals calendar ordering."""
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise PointInTimeError(f"{parameter} must be a valid YYYY-MM-DD date, got: {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise PointInTimeError(
            f"{parameter} must be a valid YYYY-MM-DD date, got: {value!r}"
        ) from exc
