# Complete portable research package verification

Objective: one read-only command verifies the entire existing value/session/
review/audit/compare package, including outer reports and root manifest, not
only the embedded session. Verified base origin/live main
7e72d2c4e029bf01ed4fe84b93d81af6be0961a5; clean owned worktree
D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance, new branch
codex/m2-package-verification. Protect primary feat/m2-value-assessment-mvp3679b1b,
full dirty/untracked snapshot, stashcb568efd, localmain966206f and DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6,
plus captured reports/config/events/evidence/mechanism/fixtures hash map.

Allowed seven files: src/ashare_research/tools/package_verification.py;
src/ashare_research/tools/research_entry.py; tests/test_package_verification.py;
README.md; this Goal; agent/record/2026-10-02_04-m2-package-verification.md;
acceptance/2026-10-02_m2_package_verification.md. Own execution/no DSH/subagents.
Forbidden modifications to previous tools/engines/tests/fixed inputs, source
acquisition/messages, formulas/metrics/scores, research eligibility, default DB,
cache/holdout/backtests, destructive operations or direct main push.

Required research verify --package DIR [--json]. Detect only five known manifest
schemas. Reject root/manifest/file/directory symlinks and unreadable layouts;
manifest paths never determine reads. Rebuild canonical package through public
exports and session verified-byte loader, in tool-owned TemporaryDirectory only.
Compare exact file/directory sets, all retained bytes including full outer
manifest. View-package comparison selectors must be explicit/known and match
regenerated complete package. Rehashed report/metadata tampering still fails.
No supplied-path writes or cleanup; no caching, clock, machine paths or network.
Default readable summary / JSON evidence with kind, counts, request/views,
manifest digest and verification limits. Errors2, stable sanitized codes and
no partial stdout. Existing inventories remain inventories; this command proves
reproducibility against compatible installed fixed baseline, not signatures,
authenticity, historical publication/availability or research admission.

Exact local commands, owned worktree, PYTHONPATH=src, primary venv:
python -m pytest -q tests/test_package_verification.py
python -m ruff check src/ashare_research/tools/package_verification.py src/ashare_research/tools/research_entry.py tests/test_package_verification.py
python -m ashare_research.cli research verify --package tmp/m2-session-compare-reused --json
python -m ashare_research.cli research verify --package tmp/m2-research-review
python -m ashare_research.cli research verify --package tmp/m2-evidence-audit
git diff --check
Four meaningful cases: all five real package kinds/unchanged files; rehashed
outer-report/root-metadata tampering and forged compare views; confinement,
extra/missing/link layout and invalid schema; real CLI/no legacy initialization,
portable moved verification, sanitized failures/no mutation. One targeted run,
repeat only actual fixes, no full local suite. Required hosted42checks all pass,
expected base/head/clean mergeability before standing-authorized merge. Commit/
push only seven files. Independently review actual diff/Goal/protected snapshots/
DB/stash/worktree/task origin0/0 and live main. Stop on failures/conflicts/baseline
changes/scope expansion. Final PASS/CHANGES_REQUIRED/BLOCKED evidence packet.
Engineering may continue; new data/real research stage not authorized.
