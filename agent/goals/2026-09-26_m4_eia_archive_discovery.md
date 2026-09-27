# Goal: official historical archive discovery

User explicitly authorized PR #30 merge and read-only official archive discovery.
PR #30 merged as 544be8011cf9d5b0abaecdb4c0b09683204dd2fb after 42 successful checks.
Baseline: origin/main at that merge; clean codex/m4-eia-archive-discovery branch.
Protected M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222, stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Objective: locate official archive index/landing metadata relevant to
2015-03-09..13, distinguish candidates from verified row-level PIT evidence.
Allowed: official HTML directory/landing metadata and links, this Goal and record.
Forbidden: opening price tables, PDF/XLS/CSV datasets, API calls, credentials,
raw decryption, backtests, database/code/previous evidence changes, next-stage merge.
Stop at links requiring observation acquisition; do not infer historical time
from current schedules. No artifact contents or immutable vintage proven by URLs.
Acceptance: traceable official URLs, observed date metadata, explicit unresolved
row identity/time/version issues, no research gate changes.
Validation: python agent/tools/assess_eia_pit.py --check;
python agent/tools/validate_eia_artifacts.py; git diff --check;
git diff --cached --check; inspect final diff/protected state/remote synchronization.
Commit/push only these two Markdown files and create a draft PR; no automatic merge.
