# Goal — M3 Integration Closeout: README, Final-Tip CI, Tag, and PR Preparation

Status: `IN_PROGRESS`

## Objective

Perform integration closeout only for the already completed M3 Stage 3E
conditional disposition: repair confirmed README stale status wording, prove
the frozen research tree is unchanged, validate the exact feature tip, create
the annotated conditional-closeout tag, prepare a PR to `main`, and stop
without merging.

## Contract

- `stage_type = INTEGRATION_CLOSEOUT_ONLY`
- `research_change = PROHIBITED`
- `real_data_read = PROHIBITED`
- `network_research_acquisition = PROHIBITED`
- `m4 = NOT_AUTHORIZED`
- `merge = NOT_AUTHORIZED`
- final stop: `STOP_FOR_FINAL_MERGE_REVIEW`

## Verified baseline

- Feature branch: `feat/m3-mechanism-validation-mvp`
- Starting HEAD: `d38119cc033931b213fb06a9e625e72643380cd5`
- Feature remote was synchronized at start (`0/0`).
- `origin/main` was `7cc6a9bc51162ee3bac3748576070eb04d4904fb` and was an
  ancestor of the feature tip.
- The protected M2 worktree remained dirty at its original HEAD and was not
  touched.

## Allowed scope

README stale-status repair, integration governance Goal/acceptance/record,
lightweight consistency regression, frozen-baseline evidence, normal push/tag/
PR operations, and repository/CI validation.

## Forbidden scope

No real or external market data, acquisition, research model/result changes,
Stage 3A–3E frozen artifact changes, holdout changes, robustness, M4, minute or
index research, rebase, force-push, merge, branch deletion, or protected M2
worktree cleanup.

## Required invariants

The Stage3E decision contract must remain unchanged:

- `M3_MILESTONE_CONDITIONAL_CLOSEOUT_ALLOWED`
- `CONDITIONALLY_CLOSED`
- `M3_DAILY_MECHANISM_NOT_ESTABLISHED`
- `M3_PRIMARY_DEVELOPMENT_POSITIVE_ABNORMAL_PERFORMANCE_NOT_ESTABLISHED`
- `M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP`
- `full_evidence_completion = false`
- all recovery/escalation/M4 authorization flags remain false

## Acceptance criteria

README stale strings are absent and canonical M2/M3 statuses are readable;
frozen-artifact regression passes; local tests and exact final-tip CI pass; the
feature tip is synchronized; the annotated tag points to the exact final tip;
the PR targets `main` from `feat/m3-mechanism-validation-mvp`; no merge occurs;
and the final state is `PR_READY_FOR_SOL_REVIEW` / `STOP_FOR_FINAL_MERGE_REVIEW`.
