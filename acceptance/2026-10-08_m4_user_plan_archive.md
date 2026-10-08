# M4 compile-only plan ZIP local acceptance

Verdict: PASS (local implementation and validation).
Hosted CI and merge eligibility are separate, not claimed complete here.

Goal: agent/goals/2026-10-08_m4_user_plan_archive.md.
Verified base: codex/m4-user-plan-package
83b2c99159ce1d1497e0f52f6701a1a06f3d268e, PR89 dependency.
Origin/live main: 8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Final branch: codex/m4-user-plan-archive. Resolve final commit from Git;
post-push evidence packet is tmp/archive-final-review.json.

Eight allowed changed files:

- agent/goals/2026-10-08_m4_user_plan_archive.md
- agent/record/2026-10-08_04-m4-user-plan-archive.md
- acceptance/2026-10-08_m4_user_plan_archive.md
- README.md
- src/ashare_research/tools/research_plan_package.py
- src/ashare_research/tools/research_plan_archive.py
- src/ashare_research/tools/research_entry.py
- tests/test_research_plan_archive.py

Requirements checked against actual code and tests: exactly four deterministic
stored members; complete original manifest/identities/boundaries; single bounded
capture; directory reproduction remains compatible; source recompile rejects
rehashed forged reports; central metadata bounded before ZipFile allocation;
member metadata/size/corruption/extra content rejected; no extraction;
exclusive new output and readback with preserved collisions/late partial files;
Windows junction/parent traversal guards; no database/network/execution.

Exact commands in isolated worktree, PYTHONPATH=src, executable
D:/量化分析/.venv/Scripts/python.exe:

    python -m pytest -q tests/test_research_plan_archive.py tests/test_research_plan_package.py tests/test_research_plan.py tests/test_research_entry.py
    python -m ruff check src/ashare_research/tools/research_plan_archive.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_entry.py tests/test_research_plan_archive.py
    git diff --check

Final results: 46 passed in 45.76s; Ruff all checks passed; diff check exit 0.
Earlier one Ruff line-length failure fixed; no existing tests changed.
Public subprocess export/verify: three commands exit 0, empty stderr.
tmp/archive-demo/evidence.json retains exact argv/receipts.
ZIP SHA256 19310fbc1d4a866e4ec9e4abecd75f65b884a0c74aeda720d662105c7026099e,
19741 bytes; source-byte preservation and all six false boundaries confirmed.

Protection evidence: tmp/archive-baseline.json and
tmp/archive-protection-review.json. All 1355 protected primary hashes, 56 foreign
worktree refs/statuses, primary HEAD and existing edits, stash unchanged.
Database SHA256 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Final review must additionally check committed scope, clean task worktree and
local/origin/live branch equality; post-push evidence records those actual checks.

No scope deviations, research execution, new data or holdout access.
Limits: depends on unmerged PR89; requires compatible original compiler/renderer
and canonical stored ZIP; checkpoint path guards are not OS-level isolation.
No automatic merge or next stage allowed under current user governance.
