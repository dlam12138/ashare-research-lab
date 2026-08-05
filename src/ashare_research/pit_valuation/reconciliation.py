"""M2 Stage 2K.1R4D — dual-source reconciliation, restatement and share derivation.

Handles:

- dual official source consistency (issuer/SSE byte-identical objects collapse
  to one economic fact with two evidence aliases; distinct objects with equal
  values produce reconciled_derived facts);
- restatement / supersession chains (later comparative columns corroborate the
  original; an explicitly restated comparative creates a new fact version that
  becomes visible only from its own available_at);
- weighted-average-share derivation (report-direct disclosure first; otherwise
  parent net profit / basic EPS with full Decimal operands; an EPS rounding
  interval that cannot uniquely determine the share count is recorded as
  ``weighted_average_share_ambiguous_due_to_eps_rounding``).

Never produces TTM / MRQ / single-quarter / valuation facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class WeightedSharesDerivation:
    """Outcome of the weighted-average-share derivation for one period."""

    fiscal_year: int
    report_type: str
    status: str = "not_applicable"
    direct_disclosure: bool = False
    derived_value: Decimal | None = None
    profit_yuan: Decimal | None = None
    eps_rounded: Decimal | None = None
    eps_rounding_unit: Decimal | None = None
    implied_low: Decimal | None = None
    implied_high: Decimal | None = None
    known_total_shares: Decimal | None = None
    notes: str = ""


@dataclass
class VersionChain:
    """One concept/context version lineage."""

    concept_id: str = ""
    context_id: str = ""
    original_fact_id: str = ""
    original_value: float | None = None
    original_available_at: str = ""
    later_evidence: list[str] = field(default_factory=list)
    restatement_fact_ids: list[str] = field(default_factory=list)
    restated_values: list[float] = field(default_factory=list)
    supersession: str = ""
    conflict_status: str = "consistent"
    pit_selected_intervals: list[dict[str, str]] = field(default_factory=list)


EPS_ROUNDING_STATUS = "ambiguous_due_to_eps_rounding"
KNOWN_TOTAL_SHARES = Decimal("183020977818")


def tenths_place(eps: Decimal) -> Decimal:
    """Return the rounding unit (0.01 for 2 decimals, 0.001 for 3...)."""
    exp = eps.as_tuple().exponent
    if exp >= 0:
        return Decimal("1")
    return Decimal("1").scaleb(exp)


def derive_weighted_average_shares(
    *,
    profit_yuan: Decimal,
    eps: Decimal,
    direct_disclosure: bool = False,
    direct_value: Decimal | None = None,
) -> WeightedSharesDerivation:
    """Derive weighted-average shares from profit and rounded EPS.

    Priority 1: a directly disclosed weighted-average share count.
    Priority 2: exact derivation S = P / EPS when the rounding interval is
    consistent with a unique share count.
    Priority 3: otherwise record
    ``weighted_average_share_ambiguous_due_to_eps_rounding``.
    """
    der = WeightedSharesDerivation(fiscal_year=0, report_type="")
    if not isinstance(eps, Decimal):
        eps = Decimal(str(eps))
    if not isinstance(profit_yuan, Decimal):
        profit_yuan = Decimal(str(profit_yuan))
    if direct_disclosure:
        der.status = "directly_disclosed"
        der.direct_disclosure = True
        der.derived_value = direct_value
        return der
    rounding_unit = tenths_place(eps)
    eps_lo = eps - rounding_unit / 2
    eps_hi = eps + rounding_unit / 2
    # The implied interval is normalized to [low, high] so that a negative
    # profit/EPS pair (a loss period) does not invert the bounds.
    implied_a = profit_yuan / eps_hi
    implied_b = profit_yuan / eps_lo
    implied_low = min(implied_a, implied_b)
    implied_high = max(implied_a, implied_b)
    der.profit_yuan = profit_yuan
    der.eps_rounded = eps
    der.eps_rounding_unit = rounding_unit
    der.implied_low = implied_low
    der.implied_high = implied_high
    der.known_total_shares = KNOWN_TOTAL_SHARES
    # Unique only when exactly one integer share count lies in the interval
    # and that integer equals the known constant total.  O(1) check: an
    # EPS rounded to 2-3 decimals produces an interval millions of shares
    # wide, so the interval width check below almost always records the
    # ambiguity rather than iterating a huge integer range.
    interval_width = implied_high - implied_low
    if interval_width < Decimal("1"):
        der.status = "exact_derivation"
        der.derived_value = (implied_low + implied_high) / 2
        return der
    low_int = int(implied_low.to_integral_value(rounding="ROUND_CEILING"))
    high_int = int(implied_high.to_integral_value(rounding="ROUND_FLOOR"))
    if high_int == low_int and low_int == int(KNOWN_TOTAL_SHARES):
        der.status = "exact_derivation"
        der.derived_value = Decimal(low_int)
        return der
    der.status = EPS_ROUNDING_STATUS
    der.notes = (
        f"EPS rounded to {abs(eps.as_tuple().exponent)} decimals; implied "
        f"share interval [{implied_low:.0f}, {implied_high:.0f}] cannot "
        "uniquely determine the weighted-average share count"
    )
    return der


def reconcile_dual_source(
    *,
    evidence_ids: list[str],
    values: list[Decimal | None],
    source_roles: list[str],
) -> dict[str, Any]:
    """Reconcile two official disclosures for one economic value.

    Byte-identical issuer/SSE objects collapse to a single economic fact with
    two evidence aliases (handled by the cache registry).  Distinct official
    objects with equal values and equal scope produce a reconciled_derived
    fact.  Any disagreement is a source_conflict that blocks eligibility.
    """
    present = [
        (eid, v, role)
        for eid, v, role in zip(evidence_ids, values, source_roles, strict=False)
        if v is not None
    ]
    if len(present) < 2:
        return {
            "status": "single_source",
            "evidence_ids": [e[0] for e in present],
            "input_fact_ids": [],
            "evidence_set_digest": ",".join(sorted(e[0] for e in present)),
            "note": "single official source available; dual-source reconciliation not possible",
        }
    values_set = {str(v) for _, v, _ in present}
    if len(values_set) == 1:
        return {
            "status": "reconciled_consistent",
            "evidence_ids": [e[0] for e in present],
            "input_fact_ids": sorted(e[0] for e in present),
            "evidence_set_digest": ",".join(sorted(e[0] for e in present)),
            "note": "two official disclosures agree",
        }
    return {
        "status": "source_conflict",
        "evidence_ids": [e[0] for e in present],
        "input_fact_ids": [],
        "evidence_set_digest": ",".join(sorted(e[0] for e in present)),
        "note": "official disclosures disagree; no automatic selection",
    }


def build_version_lineage(
    *,
    concept_id: str,
    context_id: str,
    original_fact_id: str,
    original_value: float | None,
    original_available_at: str,
    later_evidence: list[str],
    restatement_facts: list[dict[str, Any]],
    conflicts: list[str],
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    """Build one version-chain record for the lineage report."""
    chain: dict[str, Any] = {
        "concept": concept_id,
        "context": context_id,
        "fiscal_year": context_id.split("|")[1],
        "period_start": period_start,
        "period_end": period_end,
        "original_fact_id": original_fact_id,
        "original_value": original_value,
        "original_available_at": original_available_at,
        "later_evidence": later_evidence,
        "restatement_fact_ids": [f["fact_id"] for f in restatement_facts],
        "restated_values": [f.get("value") for f in restatement_facts],
        "supersession": "original_visible_until_restatement"
        if restatement_facts
        else "no_restatement",
        "conflict_status": "source_conflict" if conflicts else "consistent",
        "conflicts": conflicts,
    }
    intervals: list[dict[str, str]] = []
    if restatement_facts:
        for fact in restatement_facts:
            intervals.append(
                {
                    "value": fact.get("restatement_version", ""),
                    "visible_from": fact.get("available_at", ""),
                    "supersedes": fact.get("supersedes_fact_id", ""),
                }
            )
    chain["pit_selected_intervals"] = intervals
    return chain


# ── restatement detection from comparative columns ─────────────────────────


def prior_comparative_tokens(
    cell_tokens: list[str],
    *,
    report_type: str,
    has_restatement: bool,
) -> dict[str, int]:
    """Return the token indices of the prior-period comparative value(s).

    Returns ``None`` indices when the layout does not provide that column.
    """
    toks = cell_tokens
    if report_type == "q3":
        # Cumulative block: 6 tokens (2020-2022/2024) or 8 (2023/2025).
        if has_restatement and len(toks) >= 8:
            return {"prior": 5, "prior_original": 6, "prior2": None, "prior2_original": None}
        return {"prior": 4, "prior_original": None, "prior2": None, "prior2_original": None}
    if has_restatement and len(toks) >= 4:
        if report_type == "annual" and len(toks) >= 6:
            return {"prior": 1, "prior_original": 2, "prior2": 4, "prior2_original": 5}
        return {"prior": 1, "prior_original": 2, "prior2": None, "prior2_original": None}
    if report_type == "annual" and len(toks) >= 4:
        return {"prior": 1, "prior_original": None, "prior2": 3, "prior2_original": None}
    return {"prior": 1, "prior_original": None, "prior2": None, "prior2_original": None}


def detect_restatements(
    cells: list[Any],
    facts: list[dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Detect restated comparatives and build the restated fact versions.

    A later filing that prints ``(追溯后)`` / ``(追溯前)`` comparatives for
    the prior-year same report type restates the prior-year fact when the two
    values differ.  The restated version becomes visible only from its own
    announcement date; the original remains visible until then.

    Returns ``(restated_facts, lineage_records)``.
    """
    # Original facts by (concept_id, report_type, fiscal_year).
    originals: dict[tuple[str, str, int], dict[str, Any]] = {}
    for f in facts:
        source_id = f.get("source_id", "")
        if not source_id.startswith("r4d:"):
            continue
        eid = source_id.split(":", 1)[1]
        entry = evidence_by_id.get(eid)
        if entry is None:
            continue
        originals[(f["concept_id"], entry["report_type"], entry["fiscal_year"])] = f

    restated_facts: list[dict[str, Any]] = []
    lineage: list[dict[str, Any]] = []
    seen_chains: set[tuple[str, str]] = set()

    for cell in cells:
        if cell.status != "acquired_reported_verified":
            continue
        if cell.role_id in ("equity_attributable_to_parent", "total_ordinary_shares_at_period_end"):
            continue
        entry = evidence_by_id.get(cell.evidence_id)
        if entry is None:
            continue
        prior_tokens = prior_comparative_tokens(
            cell.tokens,
            report_type=cell.report_type,
            has_restatement=cell.has_restatement_comparatives,
        )
        prior_idx = prior_tokens.get("prior")
        prior_orig_idx = prior_tokens.get("prior_original")
        if prior_idx is None or prior_idx >= len(cell.tokens):
            continue
        prior_year = cell.fiscal_year - 1
        original = originals.get((cell.role_id, cell.report_type, prior_year))
        if original is None:
            continue
        prior_value = str(cell.tokens[prior_idx])
        prior_orig_value = (
            str(cell.tokens[prior_orig_idx])
            if prior_orig_idx is not None and prior_orig_idx < len(cell.tokens)
            else None
        )
        key = (cell.role_id, cell.report_type, prior_year)
        if key in seen_chains:
            continue
        seen_chains.add(key)

        if prior_orig_value is not None and prior_orig_value != prior_value:
            # Explicit restatement: (追溯前) original differs from (追溯后).
            from decimal import Decimal

            from ashare_research.pit_valuation.extraction import parse_decimal_token

            restated_value = parse_decimal_token(prior_value)
            if restated_value is None:
                continue
            # The comparative token is in the report's raw unit; convert to the
            # canonical unit using the cell's deterministic multiplier.
            multiplier = Decimal(str(cell.conversion_multiplier or "1"))
            restated_value = restated_value * multiplier
            restated = dict(original)
            restated["fact_version"] = original.get("fact_version", 1) + 1
            restated["restatement_version"] = "restated_1"
            restated["supersedes_fact_id"] = original["fact_id"]
            restated["value"] = float(str(restated_value))
            restated["normalized_value"] = float(str(restated_value))
            restated["raw_value"] = float(str(restated_value))
            restated["available_at"] = entry["announcement_date"]
            restated["announcement_date"] = entry["announcement_date"]
            restated["source_id"] = f"r4d:{entry['evidence_id']}"
            restated["source_document"] = entry.get("proof_url", "")
            restated["verification_note"] = (
                "restated from comparative column; supersedes "
                + original["fact_id"]
            )
            from ashare_research.facts.identity import build_fact_id

            restated["fact_id"] = build_fact_id(restated)
            restated_facts.append(restated)
            chain = build_version_lineage(
                concept_id=cell.role_id,
                context_id=original["context_id"],
                original_fact_id=original["fact_id"],
                original_value=original.get("value"),
                original_available_at=original.get("available_at", ""),
                later_evidence=[entry["evidence_id"]],
                restatement_facts=[restated],
                conflicts=[],
                period_start="",
                period_end=entry.get("period_end", ""),
            )
            lineage.append(chain)
        elif original.get("available_at") and entry["announcement_date"] > original["available_at"]:
            # Corroborating comparative: same value reported again later.
            chain = build_version_lineage(
                concept_id=cell.role_id,
                context_id=original["context_id"],
                original_fact_id=original["fact_id"],
                original_value=original.get("value"),
                original_available_at=original.get("available_at", ""),
                later_evidence=[entry["evidence_id"]],
                restatement_facts=[],
                conflicts=[],
                period_start="",
                period_end=entry.get("period_end", ""),
            )
            lineage.append(chain)
    return restated_facts, lineage
