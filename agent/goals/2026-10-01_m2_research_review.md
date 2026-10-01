# Verified research archive review

Objective: readable annual metric tables, before/after revision comparisons and
missing-role diagnostics from a verified research session, with complete portable
evidence export. Existing M2 engineering only; no new calculations or research.
Verified base origin/live main3245e5c77efe832e82b6b8eebedcd903b38560f4;
branch codex/m2-research-review; owned clean worktree
D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance. Preserve primary
feat/m2-value-assessment-mvp HEAD3679b1b/full dirty state, stashcb568efd,
local main966206f, DB SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6
and captured protected reports/config/events/evidence/mechanism/fixtures hashes.

Allowed seven files: new src/ashare_research/tools/research_review.py;
src/ashare_research/tools/research_entry.py; tests/test_research_review.py;
README.md; this Goal; agent/record/2026-10-01_10-m2-research-review.md;
acceptance/2026-10-01_m2_research_review.md.
User explicitly directs own implementation without DSH; no delegation this task,
superseding default executor instructions. Forbidden existing tools/engines/tests,
fixed baselines/DB/runtime modifications, network data/messages, new formulas,
scores/ranks/interpretation/valuation, real research/backtests/holdout/admission.

Required: research review --session DIR; Markdown default, --json or --output
NEW_DIR exclusive. First public session verifier validates complete input, then
public build_session reconstructs canonical verified request; project original
results without numeric conversion, scaling, rounding or arithmetic. Preserve
exact decimal strings/units/status/engine identity/input IDs/date bounds and
missing roles. Explicit years/date/scope headers, annual tables at both dates,
original comparison states, empty/missing outputs remain honest. Distinguish
mixed-date value compilation and input availability bounds/publication proof.
Export review.md/review.json/root manifest plus complete unchanged24file session
under session/:27files/26managed. Relative source links only in portable export;
default stdout has source filenames rather than broken implied local links.
All bytes rendered before exclusive output mkdir; existing file/dir/link refused,
invalid/tampered input leaves output absent; late IO may retain owned partial root.
Stable sanitized errors2/no partial stdout, no clock or machine paths. No new
verifier claims for outer view manifest: nested session retains original verifier.

Exact local commands with PYTHONPATH=src and primary venv python:
python -m pytest -q tests/test_research_review.py
python -m ruff check src/ashare_research/tools/research_review.py src/ashare_research/tools/research_entry.py tests/test_research_review.py
python -m ashare_research.cli research review --session tmp/m2-research-session --output tmp/m2-research-review
python -m ashare_research.cli research session --verify tmp/m2-research-review/session
git diff --check
Four meaningful cases: original precision/status/identity/revision projection;
missing history/empty scope diagnostics; portable exact evidence/hash export and
relocated nested verification; CLI/help/error/foreign-output/tampered-input safety.
One targeted run, repeat only fixes, no broad local regression; all mandatory CI.
Acceptance actual27file artifact/nested verifier, checks pass, independent final
diff/Goal/commit review and unchanged protected state, clean task tree/origin sync.
Commit/push seven task files only; exact live base/head and42 successful hosted
checks/clean mergeability before merge under standing authorization; never main
push. Stop on CI/conflict/protection changes/scope expansion. Final evidence packet
PASS/CHANGES_REQUIRED/BLOCKED. Further scoped engineering allowed; new research or
data stage unauthorized. No automatic next-stage work.
