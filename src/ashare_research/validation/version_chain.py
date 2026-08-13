"""M2 Stage 1B.4 - Repository-aware version chain validator.

``FACT_VERSION_001`` (in :mod:`validator`) only checks pure field rules:
version 1 must not supersede, version > 1 must reference a non-empty
``supersedes_fact_id`` that differs from its own id.  It cannot verify
that the *referenced* fact actually exists, that the version increments,
that the stable identity is consistent, or that dates do not move
backwards -- those require access to already-persisted facts.

``VersionChainValidator`` closes that gap.  It is given a
``FactRepository`` and the active connection so it can look up
superseded facts both in the incoming batch and in the database,
without opening a second connection (see spec 7.2).

Checks for every fact with ``fact_version > 1``:

  A. the superseded fact must exist (batch first, then repository);
  B. ``new.fact_version == old.fact_version + 1`` (strict +1);
  C. the stable identity fields must match between old and new;
  D. ``new.available_at >= old.available_at`` (and announcement_date);
  E. the supersedes chain must not form a cycle.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from ashare_research.exceptions import VersionChainCycleError
from ashare_research.facts.repository import FactRepository
from ashare_research.validation.results import FactValidationResult

logger = logging.getLogger(__name__)

RULE_ID = "FACT_VERSIONCHAIN_001"
RULE_VERSION = "1"

# Identity fields that must be identical across versions of the same
# logical fact.  Everything else (value, source_document, dates,
# fact_version, restatement_version, supersedes_fact_id, fact_id) is
# allowed to change between versions.
_STABLE_IDENTITY_FIELDS = (
    "symbol",
    "concept_id",
    "concept_version",
    "context_id",
    "source_id",
    "derivation_definition_id",
    "derivation_version",
)

# Safety bound for cycle traversal.  The visited-set already detects
# cycles; this guards against a pathological long chain.
_MAX_CHAIN_DEPTH = 1000


def _parse_date(value: Any) -> date | None:
    """Parse a YYYY-MM-DD string; return None if empty/invalid."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None


class VersionChainValidator:
    """Validate fact version chains against repository state."""

    def __init__(self, repository: FactRepository) -> None:
        self.repository = repository

    def validate(
        self,
        facts: list[dict[str, Any]],
        *,
        conn=None,
        now: str = "",
    ) -> list[FactValidationResult]:
        """Validate version chains for a batch of facts.

        Uses *conn* (or the repository's singleton connection when
        ``conn`` is None) to look up already-persisted superseded
        facts.  Does not open a second connection.

        Raises :class:`VersionChainCycleError` if a supersedes chain
        forms a cycle; otherwise returns a result list (one result per
        checked fact, pass or fail).
        """
        if conn is None:
            conn = self.repository.store.connect()

        if not now:
            from datetime import datetime
            now = datetime.now().isoformat()

        # Index the incoming batch by fact_id for in-batch lookups.
        batch_by_id: dict[str, dict[str, Any]] = {}
        for fact in facts:
            fid = fact.get("fact_id", "")
            if fid:
                batch_by_id[fid] = fact

        results: list[FactValidationResult] = []

        for fact in facts:
            fid = fact.get("fact_id", "")
            fv = fact.get("fact_version", 1)
            if not (isinstance(fv, int) and fv > 1):
                continue

            results.append(
                self._validate_versioned_fact(
                    fact, batch_by_id, conn, now,
                )
            )

        return results

    def _load_fact(
        self,
        fact_id: str,
        batch_by_id: dict[str, dict[str, Any]],
        conn,
    ) -> dict[str, Any] | None:
        """Find a fact by id, checking the batch first then the repo."""
        if fact_id in batch_by_id:
            return batch_by_id[fact_id]
        return self.repository._get_fact_by_id(fact_id, conn)

    def _validate_versioned_fact(
        self,
        fact: dict[str, Any],
        batch_by_id: dict[str, dict[str, Any]],
        conn,
        now: str,
    ) -> FactValidationResult:
        fid = fact.get("fact_id", "")
        fv = fact.get("fact_version", 1)
        sfid = fact.get("supersedes_fact_id", "")

        # E (early): a fact must not supersede itself.
        if sfid and sfid == fid:
            raise VersionChainCycleError(
                f"Version chain cycle detected: fact {fid} supersedes itself"
            )
        # E (early): detect longer cycles before field checks so a
        # malformed chain (e.g. A->B->A) is rejected as a cycle rather
        # than a confusing version-increment error.
        self._assert_no_cycle(fact, batch_by_id, conn)

        # A. Superseded fact must exist.
        old = self._load_fact(sfid, batch_by_id, conn) if sfid else None
        if old is None:
            return FactValidationResult(
                rule_id=RULE_ID, rule_version=RULE_VERSION,
                target_id=fid, severity="error", passed=False,
                expected=f"supersedes_fact_id {sfid!r} references an "
                         f"existing fact",
                actual="superseded fact not found in batch or repository",
                message=f"Version {fv} fact {fid} supersedes non-existent "
                        f"fact {sfid!r}",
                checked_at=now,
            )

        # B. Version must increment by exactly 1.
        old_fv = old.get("fact_version", 1)
        if not (isinstance(old_fv, int) and fv == old_fv + 1):
            return FactValidationResult(
                rule_id=RULE_ID, rule_version=RULE_VERSION,
                target_id=fid, severity="error", passed=False,
                expected=f"fact_version == old.fact_version + 1 "
                         f"(old={old_fv})",
                actual=f"fact_version={fv}",
                message=f"Version must increment by 1: new={fv}, old={old_fv}",
                checked_at=now,
            )

        # C. Stable identity must match.
        mismatched = [
            field for field in _STABLE_IDENTITY_FIELDS
            if str(fact.get(field, "")) != str(old.get(field, ""))
        ]
        if mismatched:
            return FactValidationResult(
                rule_id=RULE_ID, rule_version=RULE_VERSION,
                target_id=fid, severity="error", passed=False,
                expected=f"Stable identity fields match superseded fact: "
                         f"{_STABLE_IDENTITY_FIELDS}",
                actual=f"mismatched fields: {mismatched}",
                message=f"Version {fv} fact {fid} changes stable identity "
                        f"fields {mismatched} relative to superseded fact",
                checked_at=now,
            )

        # D. available_at (and announcement_date) must not move backwards.
        new_aa = _parse_date(fact.get("available_at", ""))
        old_aa = _parse_date(old.get("available_at", ""))
        if new_aa is not None and old_aa is not None and new_aa < old_aa:
            return FactValidationResult(
                rule_id=RULE_ID, rule_version=RULE_VERSION,
                target_id=fid, severity="error", passed=False,
                expected=f"available_at >= old.available_at "
                         f"({old.get('available_at', '')})",
                actual=f"available_at={fact.get('available_at', '')}",
                message=f"available_at moved backwards: "
                        f"new={fact.get('available_at', '')} < "
                        f"old={old.get('available_at', '')}",
                checked_at=now,
            )
        new_ad = _parse_date(fact.get("announcement_date", ""))
        old_ad = _parse_date(old.get("announcement_date", ""))
        if new_ad is not None and old_ad is not None and new_ad < old_ad:
            return FactValidationResult(
                rule_id=RULE_ID, rule_version=RULE_VERSION,
                target_id=fid, severity="error", passed=False,
                expected=f"announcement_date >= old.announcement_date "
                         f"({old.get('announcement_date', '')})",
                actual=f"announcement_date={fact.get('announcement_date', '')}",
                message=f"announcement_date moved backwards: "
                        f"new={fact.get('announcement_date', '')} < "
                        f"old={old.get('announcement_date', '')}",
                checked_at=now,
            )

        # E. Cycle detection: walk the supersedes chain from this fact.
        self._assert_no_cycle(fact, batch_by_id, conn)

        return FactValidationResult(
            rule_id=RULE_ID, rule_version=RULE_VERSION,
            target_id=fid, severity="error", passed=True,
            message=f"Version {fv} fact {fid} has a valid version chain",
            checked_at=now,
        )

    def _assert_no_cycle(
        self,
        new_fact: dict[str, Any],
        batch_by_id: dict[str, dict[str, Any]],
        conn,
    ) -> None:
        """Walk the supersedes chain upwards; raise on a cycle.

        A cycle exists if the chain revisits a fact id or returns to
        the starting fact id (A -> B -> A).  Raises
        :class:`VersionChainCycleError` with the offending chain.
        """
        start_id = new_fact.get("fact_id", "")
        visited: list[str] = []
        seen: set[str] = set()
        current_id = new_fact.get("supersedes_fact_id", "")

        while current_id:
            if current_id == start_id or current_id in seen:
                chain = " -> ".join(visited + [current_id])
                raise VersionChainCycleError(
                    f"Version chain cycle detected starting at {start_id}: "
                    f"{chain}"
                )
            seen.add(current_id)
            visited.append(current_id)
            if len(visited) > _MAX_CHAIN_DEPTH:
                raise VersionChainCycleError(
                    f"Version chain exceeds max depth {_MAX_CHAIN_DEPTH} "
                    f"starting at {start_id}"
                )
            current = self._load_fact(current_id, batch_by_id, conn)
            if current is None:
                break
            current_id = current.get("supersedes_fact_id", "")
