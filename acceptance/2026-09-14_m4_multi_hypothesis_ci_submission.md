# M4 multi-hypothesis CI submission acceptance

Date: 2026-09-14. [Goal](../agent/goals/2026-09-14_m4_multi_hypothesis_ci_submission.md) · [execution record](../agent/record/2026-09-14_01_m4-multi-hypothesis-ci-submission.md).

## Pre-submit assessment

DSH read-only preflight: **PASS** with no submission blocker. Codex's local Windows validation: focused `3 passed`, nine-file regression `370 passed`, Ruff and Git whitespace checks passed. Protected M2 HEAD, stash and database hash matched the Goal baseline at pre-submit review. The branch adds only documents and one synthetic portability test relative to `origin/main`; this stage adds only its Goal, record and acceptance documents.

## Remote acceptance gate

Actual Ubuntu and Windows CI on the pushed exact head is **PENDING** at the time this file is committed. The final verdict for this stage must be issued only after reviewing the PR's exact head and per-OS job conclusions, with run links and hashes in the PR body and Codex's final evidence packet. A green result shows this test passed on both OS; it does not prove full execution-envelope byte identity or any real-data hypothesis. No merge or further stage is authorized by this file.
