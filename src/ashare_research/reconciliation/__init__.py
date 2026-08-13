"""M2 Stage 1C-A.2.1 - Minimal official dual-source reconciliation.

This package implements a minimal reconciliation engine that cross-verifies
a company-official fact against an exchange-official fact for the same
context and, when they match exactly, produces a ``reconciled`` canonical
fact eligible for metrics.

Contract closure (Stage 1C-A.2.1):

- The engine is symbol-agnostic (no company-specific literals); the
  reconciled ``source_id`` is built from the symbol + rule.
- Decimal is used for comparison and unit normalization only; v1 persists
  only exact integral canonical-unit (万元) values within the DOUBLE
  safe-integer range (2**53 - 1).
- ``unit`` is not compared before conversion, so cross-unit pairs
  (万元 vs 元) are comparable.
- The service runs the full FactValidator on inputs and output, checks
  context existence, and enforces FACT_RECON_INPUT_001 before any write.
"""
