# M4 user plan package export and reproduction

Objective: save and independently reproduce explicit compile-only hypothesis
plans offline. Current user continuation authorizes this bounded engineering
task, root alone, no DSH/agents. No automatic merge or subsequent stage.

Verified baseline: origin/main and live remote main
8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b. Clean isolated branch
codex/m4-user-plan-package; independent of unmerged PR88 ec1749a.
Primary feat/m2-value-assessment-mvp remains
3679b1bac7a1634c6452784a4d8f6d139966f222 with existing edits/untracked files.
Stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f retained. Database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
314 protected primary data/reports/config/events/fixture hashes and 54 foreign
worktree statuses/refs captured in ignored tmp/plan-package-baseline.json.

Allowed eight files: this Goal, agent/record/2026-10-08_02-m4-user-plan-package.md,
acceptance/2026-10-08_m4_user_plan_package.md, README.md,
src/ashare_research/tools/{research_plan,research_entry,research_plan_package}.py,
tests/test_research_plan_package.py. Ignored validation artifacts allowed.
Forbidden: existing tests, mechanism modules/frozen contracts/compilers/adapters/
executors/registry/schemas, fixtures/reports/config/events/CI, acquisition, real
data/research/statistics/outcomes/holdout, routing/governance edits, foreign
worktrees/user dirt/stash/databases, cleanup/force push/direct main push.

Required behavior: research plan-package --hypothesis JSON --output NEW_DIR
[--json], or --verify DIR [--json]. Factor original research_plan byte loading/
compilation without altering legacy report objects, renderers, errors or source
single-read behavior. Export captures source bytes once, compiles original config,
contract and plan and writes exactly hypothesis.json/report.json/report.md/
manifest.json. Manifest binds original source bytes, rendered file sizes/hashes,
original compiler digests and false execution boundaries. No host paths/clocks.
Render/bound all payloads before exclusive mkdir; existing outputs preserved.
Do not create parent directories, follow directory/file links or Windows reparse
points in managed package paths, or allow traversal. Writes use exclusive files,
read back before success; partial owned output retained on late write failure.
Verification reads each of four bounded regular files once, rejects missing/
extra/nonregular files, recompiles from captured source using original compiler,
regenerates exact report/Markdown/manifest and compares bytes. Rehashed forged
reports fail; formatting-only source changes require matching original-byte SHA.
Self-consistency and compiler reproduction are not independent provenance,
signature, seal, evidence readiness or execution authorization. Strict compatible
renderer/compiler required. Stable sanitized errors, no partial stdout.

Required tests: original identities/boundaries and public CLI export/verify,
determinism/relocation/source mutation after single capture; report and Markdown
tampering/forged rehash/manifest/source/membership corruption; invalid JSON and
policy/arguments; output collisions and late failure preservation; size limits,
links/ancestor links and Windows junctions, no database/network/executor access.
Exact validation (PYTHONPATH=src; D:/量化分析/.venv/Scripts/python.exe):
python -m pytest -q tests/test_research_plan_package.py tests/test_research_plan.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_entry.py tests/test_research_plan_package.py
git diff --check
Public subprocess export and verification under ignored tmp/, retained receipts,
source-byte preservation and deterministic four-file comparison. Review actual
committed diff/Goal/acceptance/test results and recheck primary/protected/foreign
statuses/stash/HEAD/local-origin-live remote before final verdict.

Acceptance: eight scoped files only, original legacy behavior preserved, exact
reproduced package bytes, strict corruption rejection/output preservation,
passing local tests/lint/diff and protected state unchanged.
Stop on unexpected changes, protected mismatch, failed gates, conflicts, remote
baseline drift or scope expansion; fix authorized defects, never bypass gates.
Commit/push: normal scoped commit and branch push, evidence-backed PR. Hosted CI
results reported independently with pending checks explicit; do not wait for
long full CI as a substitute for scoped local validation. No automatic merge
under current user governance; no automatic next stage.
