# Compare original input evidence alongside metric changes

Objective: root executes without DSH/subagents. Extend research compare --evidence
to show original metric comparison plus per-role input/source/parent changes.
Verified origin/live main41454760e901ad683b92fd92dad436592b01f971;
owned codex/m2-input-evidence-comparison, primaryHEAD3679b1b/main966206f/
stashcb568efd, exact dirty/untracked snapshot and427protected hashes unchanged.
DatabaseSHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Allowed eight files: this Goal;
acceptance/2026-10-06_m2_input_evidence_comparison.md;
agent/record/2026-10-06_03-m2-input-evidence-comparison.md; README.md;
src/ashare_research/tools/{session_compare,research_entry,evidence_comparison}.py;
tests/test_input_evidence_comparison.py. Ignored review/demo evidence allowed.
Forbidden: existing tests, comparison engine/formulas, package builders/verifiers/
existing export bytes/schema, CI/baselines/data/acquisition/backtests/holdout,
foreign trees/user changes/stash/databases, force/main push or cleanup.

Required: compare's existing source and view selectors plus --evidence [--json].
Reject --evidence with --output before touching files. Without flag byte-identical
existing report/render/export behavior. Original whole verification/load path used
once per side; compare only its complete original rows. New explicit evidence
schema wraps unchanged original comparison; roles aligned within metric/year only.
Keep complete bindings, list exact original fields changed with field presence
distinguished from null, distinguish metric unselected/input missing/role absent.
Retain every role including unchanged ones. Markdown original metric table plus
per-role before/after values/IDs/status and changed fields; evidence detail includes
source_reference, missing source fields and original parent records/status.
Original financial states/units/nulls unchanged; no arithmetic or causal/transitive
inference, no filling missing inputs or adjudicating source quality. Existing
symbol/scope/view/argument/tamper errors fail2 without partial success.

Exact local commands (PYTHONPATH=src, D:/量化分析/.venv/Scripts/python.exe):
python -m pytest -q tests/test_input_evidence_comparison.py
python -m ruff check src/ashare_research/tools/evidence_comparison.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_input_evidence_comparison.py
git diff --check
Two meaningful cases using actual pinned session/ZIP: original record/state and
binding equality, changed and unchanged roles, missing values and selector changes,
public CLI/default compatibility and invalid export/views, full ZIP outer forgery
and verified canonical handoff. One targeted run, affected failures only; no full
local suite. Retained delivery evidence comparison demo without data generation.

Acceptance: precise original field/role differences and all original limitations
visible, old behavior/export bytes unchanged, targeted/lint/diff pass, exact eight
files and physical primary/stash/database/427hash protection. Normal scoped commit/
push/PR; independent actual HEAD/diff/Goal/acceptance/tests/refs/baseline review,
all hosted gates/exact head/base/CLEAN before standing-authorized merge. Stop on
failure/conflict/drift/scope expansion without bypass. Final PASS/CHANGES_REQUIRED/
BLOCKED evidence packet. Next stage requires user continuation authorization.
