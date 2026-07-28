"""M2 fact identity and semantic comparison.

FactIdentity provides a canonical, hashable identity for every fact,
independent of how it was sourced or represented.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ashare_research.exceptions import FactIdentityError


@dataclass(frozen=True)
class FactIdentity:
    """Canonical identity for a financial fact.

    These fields together uniquely identify a fact across sources,
    time, and restatements.  Fields absent in the source fact default
    to empty strings (or 0 / 1 for version fields).
    """

    symbol: str = ""
    concept_id: str = ""
    concept_version: str = "1"
    context_id: str = ""
    source_id: str = ""
    fact_version: int = 1
    restatement_version: str = "original"
    derivation_definition_id: str = ""
    derivation_version: str = ""

    def canonical_payload(self) -> dict[str, Any]:
        """Return identity fields as a dict with sorted keys."""
        d = {
            "concept_id": self.concept_id,
            "concept_version": self.concept_version,
            "context_id": self.context_id,
            "derivation_definition_id": self.derivation_definition_id,
            "derivation_version": self.derivation_version,
            "fact_version": self.fact_version,
            "restatement_version": self.restatement_version,
            "source_id": self.source_id,
            "symbol": self.symbol,
        }
        return dict(sorted(d.items()))

    def canonical_key(self) -> str:
        """Return identity as a compact, sorted JSON string."""
        return json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
        )

    def fact_id(self) -> str:
        """Return the SHA-256 hex digest of the canonical key."""
        return hashlib.sha256(self.canonical_key().encode()).hexdigest()


# ──  helpers  ──────────────────────────────────────────────────────


def normalize_identity_text(value: Any) -> str:
    """Normalize a text field used in fact identity.

    ``None`` becomes the empty string; surrounding whitespace is
    stripped.  Identity text fields that are empty after stripping are
    treated as the canonical empty form so that ``""`` and ``None`` do
    not produce different fact_ids.
    """
    if value is None:
        return ""
    return str(value).strip()


def _identity_from_fact(fact: Any) -> FactIdentity:
    """Extract identity fields from a dict or an object with attributes."""

    def _get(k: str, default: Any = None) -> Any:
        if isinstance(fact, dict):
            return fact.get(k, default)
        return getattr(fact, k, default)

    def _int(v: Any, default: int = 1) -> int:
        if v is None:
            return default
        try:
            return int(v)
        except (ValueError, TypeError):
            return default

    def _str(v: Any, default: str) -> str:
        if v is None:
            return default
        s = str(v).strip()
        return s if s else default

    return FactIdentity(
        symbol=_str(_get("symbol", ""), ""),
        concept_id=_str(_get("concept_id", ""), ""),
        concept_version=_str(_get("concept_version", ""), "1"),
        context_id=_str(_get("context_id", ""), ""),
        source_id=_str(_get("source_id", ""), ""),
        fact_version=_int(_get("fact_version", 1), 1),
        restatement_version=_str(
            _get("restatement_version", ""), "original",
        ),
        derivation_definition_id=_str(
            _get("derivation_definition_id", ""), "",
        ),
        derivation_version=_str(_get("derivation_version", ""), ""),
    )


def build_fact_id(fact: dict[str, Any]) -> str:
    """Build a fact_id from a fact dict (or dataclass) using FactIdentity."""
    return _identity_from_fact(fact).fact_id()


def build_fact_identity_key(identity: FactIdentity) -> str:
    """Return the canonical JSON key for a FactIdentity.

    This is the exact string that ``build_fact_id`` hashes, exposed so
    callers can inspect or log the identity without recomputing it.
    """
    return identity.canonical_key()


def fact_identity_from_fact(fact: Any) -> FactIdentity:
    """Extract a FactIdentity from a fact dict or dataclass.

    Canonical name; ``fact_identity_from_dict`` is kept as a
    backward-compatible alias.
    """
    return _identity_from_fact(fact)


def fact_identity_from_dict(d: dict[str, Any]) -> FactIdentity:
    """Extract identity fields from a fact dict into a FactIdentity.

    Backward-compatible alias for :func:`fact_identity_from_fact`.
    """
    return _identity_from_fact(d)


def validate_canonical_fact_ids(facts: Sequence[Any]) -> None:
    """Ensure every fact carries a canonical ``fact_id``.

    Raises :class:`FactIdentityError` on the first fact whose
    ``fact_id`` is missing or does not match the canonical identity
    derived from its fields.  Called at the Service boundary (right
    after the Provider returns) and again at the Repository boundary so
    the identity contract is enforced by the persistence layer too.
    """
    for fact in facts:
        expected_id = build_fact_id(fact)
        actual_id = (
            fact.get("fact_id") if isinstance(fact, dict)
            else getattr(fact, "fact_id", "")
        )
        if not actual_id:
            raise FactIdentityError(
                "Fact is missing canonical fact_id "
                f"(symbol={_safe_get(fact, 'symbol')}, "
                f"concept_id={_safe_get(fact, 'concept_id')})"
            )
        if actual_id != expected_id:
            raise FactIdentityError(
                "Fact ID does not match canonical identity: "
                f"actual={actual_id}, expected={expected_id}, "
                f"symbol={_safe_get(fact, 'symbol')}, "
                f"concept_id={_safe_get(fact, 'concept_id')}"
            )


def _safe_get(fact: Any, key: str) -> Any:
    if isinstance(fact, dict):
        return fact.get(key, "")
    return getattr(fact, key, "")


# ──  semantic payload  ─────────────────────────────────────────────

# Persistent business fields that constitute the semantic content of a
# fact.  fact_id, created_at, and other metadata-only timestamps are
# excluded.  This list is kept in sync with FactRepository._FACT_COLS
# and the Fact dataclass (see test_fact_identity.py
# test_semantic_payload_matches_fact_columns).
_SEMANTIC_PAYLOAD_FIELDS: list[str] = [
    "symbol",
    "concept_id",
    "concept_version",
    "context_id",
    "fact_version",
    "restatement_version",
    "supersedes_fact_id",
    "value",
    "unit",
    "source_id",
    "source_provider",
    "source_tier",
    "source_document",
    "source_url",
    "source_hash",
    "source_page",
    "source_table",
    "source_label",
    "raw_value",
    "raw_unit",
    "normalized_value",
    "normalization_rule",
    "period_end",
    "announcement_date",
    "filing_date",
    "available_at",
    "verification_status",
    "verification_note",
    "eligible_for_metrics",
    "is_derived",
    "derivation_definition_id",
    "derivation_version",
    "input_fact_ids",
    "derived_from",
]

_SEMANTIC_EXCLUDE: frozenset[str] = frozenset(
    {
        "fact_id",
        "created_at",
        "run_id",
        "validation_run_id",
        "updated_at",
        "ingested_at",
        # Context/convenience fields not stored in financial_facts
        "fiscal_year",
        "report_type",
        "context_id",  # identity field, not semantic content
    }
)


def fact_semantic_payload(fact: dict[str, Any]) -> dict[str, Any]:
    """Return all persistent business fields, excluding fact_id and
    metadata timestamps (created_at, run_id, …).

    The returned dict follows the order of the canonical field list.
    """
    payload: dict[str, Any] = {}
    for key in _SEMANTIC_PAYLOAD_FIELDS:
        if key in fact:
            payload[key] = fact[key]
    # Catch any future fields not yet in the canonical list.
    for key, val in fact.items():
        if key not in payload and key not in _SEMANTIC_EXCLUDE:
            payload[key] = val
    return payload


# ──  comparison helpers  ───────────────────────────────────────────


def _normalize_list_field(v: Any) -> Any:
    """Normalise a value that may represent a list of IDs
    (e.g. ``input_fact_ids``).

    Accepts a Python list, a JSON-encoded list, or a comma-separated
    string (as stored in DuckDB).  Returns a canonical sorted JSON
    string so that ``"a,b,c"`` and ``"c,b,a"`` compare equal.
    """
    if v is None:
        return None
    if isinstance(v, list):
        return json.dumps(sorted(set(str(x) for x in v)))
    if isinstance(v, str):
        stripped = v.strip()
        if not stripped:
            return None
        # JSON-encoded list first
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return json.dumps(sorted(set(str(x) for x in parsed)))
        except (json.JSONDecodeError, TypeError):
            pass
        # Comma-separated string (the DuckDB storage form)
        parts = [p.strip() for p in stripped.split(",") if p.strip()]
        if parts:
            return json.dumps(sorted(set(parts)))
        return None
    return str(v)


def _values_equal(a: Any, b: Any) -> bool:
    """Compare two payload values, treating NaN as equal to None/empty.

    DuckDB reads DOUBLE NULL back as NaN in pandas; an incoming fact
    carries None for the same field, so a naive ``!=`` would wrongly
    flag a conflict.
    """
    def _is_missing(v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, float) and v != v:  # NaN
            return True
        return isinstance(v, str) and v == ""

    if _is_missing(a) and _is_missing(b):
        return True
    if isinstance(a, bool) or isinstance(b, bool):
        # avoid True == 1 surprises
        return bool(a) is bool(b)
    return a == b


def _normalize_for_comparison(payload: dict[str, Any]) -> str:
    """Convert a semantic payload to a canonical JSON string for
    comparison.  ``input_fact_ids`` is list-normalised.
    None and empty string are treated as equivalent.
    Booleans are stringified consistently across DB reads and dict inputs.
    NaN floats (read back from DuckDB DOUBLE NULLs) are treated as None
    so a stored NULL compares equal to an incoming None/missing value.
    """
    def _normalize_value(v: Any) -> Any:
        if v is None:
            return ""
        # pandas/DuckDB read DOUBLE NULL as NaN; treat as missing
        if isinstance(v, float) and v != v:  # NaN check
            return ""
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            return v
        # Numeric normalization: an integral number compares as int
        # regardless of whether it arrived as a Python int or was read
        # back from a DOUBLE column as a float.  Without this, an
        # incoming int 235000000 and a DOUBLE-read-back 235000000.0
        # serialize to different JSON ("235000000" vs "235000000.0")
        # and are wrongly flagged as a semantic conflict (with an empty
        # changed_fields list).  Non-integral floats keep their float
        # form so genuine fractional differences are still detected.
        if isinstance(v, float):
            iv = int(v)
            if iv == v:
                return iv
            return v
        if isinstance(v, int):
            return v
        return v

    normalized: dict[str, Any] = {}
    for k, v in payload.items():
        val = _normalize_value(v)
        if k == "input_fact_ids":
            normalized[k] = _normalize_list_field(val)
        else:
            normalized[k] = val
    return json.dumps(normalized, sort_keys=True, default=str)


def facts_semantically_equal(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> bool:
    """Return True if two fact dicts have the same business content."""
    return _normalize_for_comparison(
        fact_semantic_payload(existing),
    ) == _normalize_for_comparison(
        fact_semantic_payload(incoming),
    )


def diff_fact_semantic_payloads(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return a dict of changed fields between two fact dicts.

    Each entry maps ``field_name`` ->
    ``{"existing": old_val, "incoming": new_val}``.
    An empty dict means the two facts are semantically identical.
    """
    ex_payload = fact_semantic_payload(existing)
    in_payload = fact_semantic_payload(incoming)

    diffs: dict[str, dict[str, Any]] = {}
    all_keys = set(ex_payload.keys()) | set(in_payload.keys())

    for key in sorted(all_keys):
        ex_val = ex_payload.get(key)
        in_val = in_payload.get(key)
        if key == "input_fact_ids":
            if _normalize_list_field(
                ex_val,
            ) != _normalize_list_field(in_val):
                diffs[key] = {"existing": ex_val, "incoming": in_val}
        elif not _values_equal(ex_val, in_val):
            diffs[key] = {"existing": ex_val, "incoming": in_val}

    return diffs
