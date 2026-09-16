# Work record: M4 core-readiness review integration

Date: 2026-09-16. Contract: [integration Goal](../goals/2026-09-16_m4_core_readiness_integration.md). Executor and Git operator: Codex. Independent read-only reviewer: DSH.

## Baseline and scope

PR #20 was rechecked at exact head `d593f40ee6cc17147164c67d31f84ce34da6785a` with 42/42 successful checks and merged only after explicit user authorization. Its merge commit is `966206f06262e43f40c1c7aadbfb8596839eac91`. Local `main`, `origin/main` and live main matched that commit before this integration branch was created.

The source deliverable `codex/m4-core-readiness-review@65d8abd3b896750d0f8d40ed7bcb08cb91dd88ae` added exactly the historical Goal and acceptance report. They were replayed byte-for-byte before the acceptance report received a bounded post-PR20 reconciliation. This stage changes no product code, test, CI, dependency, configuration, report or data file.

Protected state at start and review: original M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`; stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; default database SHA256 `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Reconciliation decision

The original review correctly identified one bounded missing demonstration: two structurally distinct legal synthetic hypotheses through the public pipeline. PR #20 now supplies that evidence. The replayed acceptance report therefore records that narrow item as accepted and updates the smallest next decision to a separate real-daily-adapter design gate.

The update does not convert the repository's generic identity-comparison jobs into M4 evidence. The M4 portability evidence is the same fixed pre-execution contract, plan, dataset and matrix fingerprints asserted by the new test inside full-suite Ubuntu and Windows jobs. Complete execution-envelope byte identity, real source/calendar/membership/PIT validation, real candidates, holdout and mechanism conclusions remain unestablished or unauthorized.

## Actual local validation

From `D:/量化分析-m4-core-readiness-integration`, with `PYTHONPATH=src`:

- `python -m pytest -q -p no:cacheprovider` on the ten Goal-listed M4/project test files: exit 0, **373 passed in 248.76s**.
- `python -m ruff check tests/test_m4_multi_hypothesis_portability.py`: exit 0, `All checks passed!`.
- `git diff --check` and `git diff --cached --check`: exit 0, no output.

The post-merge `main@966206f` push completed all seven repository workflows successfully, including Stage 2G full-suite clean-clone jobs on Ubuntu and Windows. The merge commit tree is identical to PR #20 head `d593f40`; this confirms the baseline without expanding the M4 claim beyond fixed pre-execution identities.

The first DSH read-only review independently confirmed the post-PR20 base, byte-exact replay source, Markdown-only scope, working links and UTF-8 hygiene, PR #20 evidence, protected identities and the substantive accuracy of the reconciliation. It returned `CHANGES_REQUIRED` because the reconciliation was still uncommitted, this record and the integration acceptance did not yet exist, and the branch had not been pushed. It also requested more precise wording around the repository's non-M4 identity-comparison jobs. These delivery issues were corrected within the existing Goal; no source or test change was needed.

## Delivery boundary

This branch may be committed, pushed and submitted as one review PR after the final DSH recheck. It must not be merged automatically. The real-daily-adapter design gate, design, K1/K2 implementation, provider access and real research remain separate stages.
