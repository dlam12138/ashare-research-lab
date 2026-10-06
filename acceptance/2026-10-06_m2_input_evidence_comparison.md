# Original input evidence comparison acceptance

Base origin/live main41454760e901ad683b92fd92dad436592b01f971;
branch codex/m2-input-evidence-comparison; own root execution without DSH/agents.
Goal agent/goals/2026-10-06_m2_input_evidence_comparison.md.

Existing research compare now accepts --evidence [--json]. Its original verified
comparison is preserved inside an explicit evidence schema; per metric/year,
all input roles retain complete original bindings and exact original changed
fields, including per-field presence separate from null. Markdown starts with
the unchanged original metric comparison, then before/after roles/values/units/
facts/status, source gaps, parent entries and full changes. Missing inputs and
unselected metrics distinct. No source quality/causal/indirect dependency judgments,
arithmetic, missing filling, retained reread or new research. Whole original
load/verification path per side; export with evidence rejected before source load.
Without flag original display, JSON schema and export bytes remain unchanged.

Exact local commands (owned tree PYTHONPATH=src; python means
D:/量化分析/.venv/Scripts/python.exe):
```powershell
python -m pytest -q tests/test_input_evidence_comparison.py
python -m pytest -q tests/test_input_evidence_comparison.py::test_original_comparison_bindings_changes_missing_and_default_compatibility
python -m ruff check src/ashare_research/tools/evidence_comparison.py src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_input_evidence_comparison.py
git diff --check
```
Initial2cases:1passed/1failed32.27s. Failure was new expected Markdown constructed
from canonical JSON (sorted state keys), while original renderer preserves label
order. Corrected new expected label order to existing LABELS without changing
product/old tests. Affected-case rerun1passed16.36s. Scoped Ruff/diff pass.
No full local suite or repeats of unaffected tests. Actual pinned sessions/ZIP
verify exact original rows/financial states/input bindings, changed/unchanged
roles, missing values, selector differences, default Markdown/JSON compatibility,
mixed export/invalid views fail2 with no output creation, forged outer ZIP
rejected, canonical map used once after mutation and next fresh read rejects it.

Retained source demo, exit0:
python -m ashare_research.cli research compare --left-archive
tmp/m2-handoff-walkthrough/delivery.zip --right-archive
tmp/m2-handoff-walkthrough/delivery.zip --right-view compare_with --evidence --json
Saved tmp/m2-input-evidence-comparison-demo/{comparison.json,comparison.md,summary.md}.
Markdown/summary rendered from the already verified envelope, no reread of ZIP.
Seven original metrics,15input roles,15changed bindings across original requested
2024-03-31/2025-03-31 views, original states/units/values/source/parent gaps retained.
Original ZIP SHA256 unchanged
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.

Eight-file scope. Exact original primary dirty/untracked snapshot, primaryHEAD
3679b1b/main966206f/stashcb568efd and427protected hashes freshly compared before
implementation; databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 unchanged.
Package builders/verifiers, original comparison engine/formulas, old tests,
baselines/CI/data unchanged. Independent actual scope/HEAD/diff/Goal/acceptance/
tests/refs/physical baselines review and hosted gates before standing-authorized
merge. Hosted/postmerge final evidence in ignored
tmp/m2-input-evidence-comparison-final-review.md. No automatic next stage.
