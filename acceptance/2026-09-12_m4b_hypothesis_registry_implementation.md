# M4-B hypothesis registry implementation acceptance

Date: 2026-09-12. Goal:
`agent/goals/2026-09-12_m4b_hypothesis_registry_implementation.md`.

## Accepted surface

The minimum M4-B metadata registry is implemented in
`src/ashare_research/mechanism/registry/`. It provides exactly the frozen 13 function entry points
for parsing, canonical projection/serialization, validation/digests, explicit state transitions,
and bounded immutable snapshots. AC-01 through AC-22 are represented by executable tests in
`tests/test_m4b_hypothesis_registry.py`.

The implementation preserves the frozen 26-key record, 22 identity-bearing fields, two SHA-256
canonical digests, 12 states, 20 legal edges, V1–V12 fail-closed order, stable errors, maximum three
snapshot records and maximum three feasible real-demo candidates. Registry metadata cannot contain
research outcomes and is not evidence.

## Evidence

- New registry suite: `24 passed`.
- Project-entry and Stage4P governance: `15 passed`.
- Synthetic-only bounded execution regression: `49 passed`.
- Upstream M4 regression group: `255 passed`.
- Ruff and Git diff hygiene: passed.
- Frozen design/acceptance/Stage4P blobs remained byte-identical.
- Protected database SHA256 remained
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.
- Original M2 HEAD remained `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash remained
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.

## Authorization boundary

This acceptance covers an in-memory synthetic/schema validation API only. It does not authorize or
create a real registry dataset, a real candidate, literature acquisition, provider/database access,
market data, holdout, statistical execution, ranking, promotion, recommendation, trading or a
research conclusion. It does not authorize push, PR, merge or a later stage.
