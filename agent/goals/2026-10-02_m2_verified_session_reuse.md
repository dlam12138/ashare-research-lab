# Reuse the exact canonical bytes established by session verification

Objective: remove redundant full archive builds from review/audit/compare, with
byte-identical outputs and unchanged strict verification/error behavior.
Verified base origin/live main d2657d2deaeaa48b7789980a76bb4195e43687fd; clean
owned worktree D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance, branch
codex/m2-verified-session-reuse. Primary feat/m2-value-assessment-mvp3679b1b,
full dirty/untracked snapshot, stashcb568efd, local main966206f,
DB SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6
and protected reports/config/events/evidence/mechanism/fixtures hash map retained.

Allowed nine files: src/ashare_research/tools/research_session.py,
research_review.py, evidence_audit.py, session_compare.py in same directory;
tests/test_verified_session_reuse.py; README.md; this Goal;
agent/record/2026-10-02_03-m2-verified-session-reuse.md;
acceptance/2026-10-02_m2_verified_session_reuse.md. Own execution, no DSH or
delegation per latest user. No fixed sources/engines/formulas/tests changed,
no financial data fetching/messages/default DB/cache/research/backtests/holdout,
no destructive filesystem/Git operations and no direct main push.

Required public load_verified_session(Path) returns verification metadata and
the canonical bytes from that same completed verification. Full request/source
pins/layout/no-symlink/every-file/root-manifest comparison remains unchanged.
Legacy verify_session API returns identical metadata and errors via the new
loader. Each call must freshly verify the input; no cross-call/path/global cache.
Returned dictionaries are caller-owned and cannot poison subsequent loads.
Review/audit each build once instead of twice; compare builds once per side
instead of twice. Render from verified in-memory bytes, never reopen mutable
retained files after verification. All existing output bytes/boundaries/error
codes and exclusive-root behavior remain unchanged.

Exact local commands, owned worktree, PYTHONPATH=src, primary venv:
python -m pytest -q tests/test_verified_session_reuse.py
python -m ruff check src/ashare_research/tools/research_session.py src/ashare_research/tools/research_review.py src/ashare_research/tools/evidence_audit.py src/ashare_research/tools/session_compare.py tests/test_verified_session_reuse.py
python -m ashare_research.cli research compare --left tmp/m2-research-session --right tmp/m2-research-session --right-view compare_with --output tmp/m2-session-compare-reused
git diff --check
Four cases: loader exact bytes/legacy metadata/one build; caller mutation and
post-load tamper not cached; consumers use one build per archive and unchanged
prior report bytes; rehashed tampering/layout/real CLI/no partial output safety.
One targeted run; repeat only actual fixes, no full local suite. Actual new export
must match every51file byte of prior tmp/m2-session-compare. Required hosted CI
42successful checks, expected base/head/clean mergeability before standing-
authorized merge. Independently inspect commit/diff/Goal/evidence/clean task
tree/protected snapshots/stash/DB/local+origin+live state. Stop on failures,
conflict, baseline changes or scope expansion. Commit/push only nine allowed
files. Final PASS/CHANGES_REQUIRED/BLOCKED packet; further authorized engineering
allowed, no new data/research stage authorization.
