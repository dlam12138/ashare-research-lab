# Per-metric delivered evidence trace

Objective: continue the user's selected research-use direction with a direct
metric/year evidence trace from verified session/workflow directory or ZIP.
Root executes, no DSH/subagents. Show original records for both requested views,
original comparison entry, input roles/values/fact IDs/source fields/parent gaps.

Verified base origin/live main4bfea9d684c5d8be0e61a28b79d9fa59328ac886;
owned branch codex/m2-metric-evidence-trace in capsule-postmerge-acceptance.
Primary original snapshot unchanged, HEAD3679b1b/localmain966206f/stashcb568efd;
427protected path/hash lines freshly compared; databaseSHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 unchanged.

Allowed seven tracked files: this Goal;
acceptance/2026-10-06_m2_metric_evidence_trace.md;
agent/record/2026-10-06_01-m2-metric-evidence-trace.md; README.md;
src/ashare_research/tools/metric_evidence_trace.py;
src/ashare_research/tools/research_entry.py; tests/test_metric_evidence_trace.py.
Owned ignored demo/evidence allowed. Forbidden: existing tests/builders/verifiers/
comparison/formulas/baselines/CI/data, new acquisition/research/backtests/holdout,
foreign trees/runtime/stash/database/user changes, force/main push/cleanup.

Required: research trace (--package DIR | --archive ZIP) --metric ID --year YEAR
[--json]. Explicit selectors; complete fresh parent verification before fixed
canonical metrics path selection. Session/workflow only. Preserve complete original
selected metric rows and comparison entry without arithmetic/reclassification.
Absent selectors fail explicitly; no today/default year/input imputation. Original
missing values remain null; selected absent views remain absent; original request,
boundary/limitations and full verification retained. Markdown highlights original
values, inputs, missing source fields and unresolved parents; JSON contains every
original input/context/lineage/source field. No retained reread/cache/caller output/
arbitrary member names. Sanitized2/no partial success.

Validation with PYTHONPATH=src, D:/量化分析/.venv/Scripts/python.exe in owned tree:
python -m pytest -q tests/test_metric_evidence_trace.py
python -m ruff check src/ashare_research/tools/metric_evidence_trace.py src/ashare_research/tools/research_entry.py tests/test_metric_evidence_trace.py
git diff --check
Two meaningful cases using actual fixed workflow/session: exact records/comparison/
metadata, ZIP/directory/CLI equivalence, computed and missing inputs, one/two views;
invalid selectors/kinds/args, forged outer report rejection, fresh verified handoff
and source preservation. One targeted run, repeat only fixes; no full local suite.
Actual retained ZIP trace saved as Markdown/JSON without new source generation.

Acceptance: exact original selected rows/comparison; source/parent gaps visible;
missing stays missing; both public formats work; targeted/lint/diff PASS, seven-file
scope and primary/stash/database/427hashes unchanged. Commit/push scoped branch/PR;
independent actual commit/diff/Goal/acceptance/test/refs/protection review. Required
hosted gates and exact head/base/CLEAN before standing-authorized merge. Stop on
failure/conflict/drift/scope expansion, no bypass. Final PASS/CHANGES_REQUIRED/
BLOCKED with full evidence. Another stage requires user authorization.
