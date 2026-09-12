# Acceptance: M4 synthetic end-to-end pipeline design

Date: 2026-09-12. Final verdict: **PASS**.

## Contract and accepted surface

- Goal: [M4 synthetic end-to-end pipeline design](../agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md).
- Normative design: [design v1](../docs/m4_synthetic_end_to_end_pipeline_design_v1.md).
- Acceptance cases: [acceptance cases v1](../docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md).
- Work record: [work record](../agent/record/2026-09-12_01_m4-synthetic-end-to-end-pipeline-design.md).

This acceptance freezes the design only. It does not implement the proposed orchestrator, execute a
real hypothesis, create or load a real registry dataset, acquire literature, access a provider,
database, market data or holdout, run a backtest, rank or promote a candidate, make a recommendation,
or state a research or trading conclusion.

The accepted design specifies one in-memory synthetic-only composition entry, an immutable result
envelope, the S0–S8 composition sequence, G1–G14 gates, a closed 14-code pipeline error table, an
L1–L14 digest chain, V1–V6 envelope validation, optional read-only M4-B metadata binding, fixed
decimal context, a bootstrap resource ceiling, and AC-01–AC-30.

## Verified baseline

| Item | Verified value |
| --- | --- |
| Base | `origin/main@fd1cc35ee824aa9449f7e7800c12d0d80c845e05` |
| Goal commit / pre-design HEAD | `f6ec598ac819c2d8db14f7a2e8c910a6ed85b301` |
| Branch | `codex/m4-synthetic-pipeline-design` |
| Original M2 worktree | `feat/m2-value-assessment-mvp@3679b1bac7a1634c6452784a4d8f6d139966f222`; pre-existing dirty files preserved |
| Shared stash | `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; unchanged |
| Protected database SHA256 | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`; hashed only |

Protected Git blobs remained byte-identical:

```text
9617f64360b6c3d9a6148ec08c25fa0209a0f9f4  docs/m4_bounded_execution_and_evidence_design_v1.md
f857b9948c7f396a855a1e0f6506752f0065d667  docs/m4_bounded_execution_acceptance_cases_v1.md
6d9c292001c09a4b1a8e895e54619dc1e8826f3d  docs/m4b_hypothesis_registry_design_v1.md
4a9b227204fc1c0eabc28e1e8b3d60a53c46f0b2  docs/m4b_hypothesis_registry_acceptance_cases_v1.md
dfd41eaafc099e7748499f72de7ddd800bf97f69  reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json
```

At final pre-commit verification, `git fetch --prune origin`, `git rev-parse origin/main`, and
`git ls-remote origin refs/heads/main` all resolved the same live main commit `fd1cc35...`.

## Deliverables

| Path | Result |
| --- | --- |
| `agent/goals/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md` | Goal committed alone before design work |
| `docs/m4_synthetic_end_to_end_pipeline_design_v1.md` | 1,373-line normative design; SHA256 `40E1CB94624320F9689B630B48E70C6FB7A6A34968152EAB0833DD5140125527` |
| `docs/m4_synthetic_end_to_end_pipeline_acceptance_cases_v1.md` | 932-line AC-01–AC-30 specification; SHA256 `765A069D0F7C042E76A6ED889245D97757E0AECBE46BE722C548BCDB0F337A31` |
| `README.md` | Design-only capability, current boundary and roadmap wording; SHA256 `6FA770822B4B5611D255608ABE1C9B60BB50253AE8A59951BF12FF4F164FA4A4` |
| `agent/record/2026-09-12_01_m4-synthetic-end-to-end-pipeline-design.md` | Final work record |
| `acceptance/2026-09-12_m4_synthetic_end_to_end_pipeline_design.md` | This evidence packet |

No source, tests, workflow, dependency, configuration, report, fixture, database, cache, existing
frozen document, stash entry or original-worktree file was changed by this stage.

## DSH review evidence

DSH used four bounded read-only sub-agent roles during drafting: public API/composition audit,
error/digest/authorization audit, documentation-convention audit, and adversarial review. The first
adversarial review returned `CHANGES_REQUIRED`; the design was corrected rather than self-accepted.

Corrections included a public bound-input identity payload recipe, fixed decimal context,
`MAX_BOOTSTRAP_REPLICATIONS`, hex-encoded registry record bytes, a pre-execution registry-status
allow-list, reachable/unreachable error classification, explicit public-surface counts, and complete
acceptance-case reachability labels.

Two later read-only reviews found and corrected remaining public-count, nullable-field,
self-digest, error-table, gate-order and clause-ID inconsistencies. A final bounded DSH review of the
current design returned **PASS**, specifically confirming:

- exactly 20 unique public symbols and matching AC-02;
- a required but explicitly nullable `registry_record` and matching AC-08b;
- canonical projection excluding `pipeline_digest`, with nested restoration during serialization;
- all referenced `PIPELINE_*` errors covered by the closed 14-row table;
- deterministic S0/S3/S7 timing, with G7–G11 ordered within S3;
- ordered 8.1–8.7 sections and unique RB/BS/other clause identifiers;
- AC index and body both exactly AC-01–AC-30;
- AC-28/AC-29 coverage of resource and determinism requirements.

The reviewer recorded one non-blocking wording note: P4 calls the copied disposition a plan field,
while the frozen message template and AC-06 name its authoritative contract path. Both values are
identical by plan construction; implementation must use the explicit frozen contract path.

## Exact validation evidence

| Command | Result |
| --- | --- |
| Goal's literal six-suite pytest command using the shared venv | exit 1 at collection: the venv's editable install points to the older `D:/量化分析-m4a2i/src`, so `mechanism.datasets` and `mechanism.registry` are not resolved from this worktree |
| Same six-suite command with `PYTHONPATH=<current-worktree>/src` | **304 passed in 38.95s** |
| `pytest ... tests/test_project_entry.py tests/test_m4_stage4p_governance.py` with current `src` | **15 passed in 0.19s** |
| Goal's exact ruff command | `All checks passed!` |
| `git diff --check` | passed |
| Mechanical design consistency probe | 20/20 unique exports; 30/30 AC ids; headings `1,2,3,4,5,6,7`; no duplicate labels; 14 error rows; no unlisted error code; no malformed table row |
| Markdown relative-link and anchor validation over both new docs and README | passed; no repository artifact retained |
| `git fetch --prune origin`; local and live remote-ref comparison | passed; all main refs `fd1cc35...` before commit |

The shared-venv resolution defect is pre-existing and outside this design whitelist. It is recorded
as a validation-command deviation, not hidden and not misreported as a repository test failure.

## Acceptance and next-stage boundary

The Goal's design acceptance criteria are met. The stage may be committed, pushed, proposed as a PR,
and merged only after normal CI succeeds, under the user's explicit standing authorization.

Implementation remains a separate stage requiring its own committed Goal. Any real data, real
candidate, literature, provider, database, market, holdout or real-hypothesis execution remains
unauthorized by this design and must not be inferred from this PASS.
