# Reverse fact lookup acceptance

Baseline origin/live main f3c2d18bae387c134647f92b347651618d6c8d65;
branch codex/m2-fact-evidence-trace. Goal
agent/goals/2026-10-06_m2_fact_evidence_trace.md, own root execution, no DSH/agents.

Implemented --fact ID in existing research trace. Whole fresh directory/ZIP
verification precedes lookup in canonical session/workflow metrics. Exact input
and explicit direct-parent matches enumerate original selected views/metric/year/
roles, complete original rows/bindings/matched parent entries, original request,
boundaries/limitations, full verification and archive receipt. Markdown separates
input/parent references, original values/status/units, source gaps and full input
evidence. No transitive or causal inference, arithmetic, missing-data filling,
output directory, retained reread/cache or new research. Old metric/year path and
original result schema are preserved. Selectors fail before load; unknown fact
fails FACT_NOT_REFERENCED, all errors sanitized exit2/no partial stdout.

Exact local commands (owned tree, PYTHONPATH=src, python below means
D:/量化分析/.venv/Scripts/python.exe):
```powershell
python -m pytest -q tests/test_fact_evidence_trace.py tests/test_metric_evidence_trace.py
python -m pytest -q tests/test_fact_evidence_trace.py::test_all_original_shared_input_and_missing_parent_references
python -m ruff check src/ashare_research/tools/metric_evidence_trace.py src/ashare_research/tools/research_entry.py tests/test_fact_evidence_trace.py
git diff --check
```
Initial targeted run: 1 failed, 3 passed in226.96s. New test incorrectly used
parent key retained rather than retained_in_snapshot. Corrected to the actual
canonical field and made the shared-input fixture selection explicit by role/year;
expected matches now independently specified as two known metrics/input roles,
not a copy of the lookup algorithm. No product defect, existing tests unchanged.
Affected-case rerun:1passed79.05s. All four targeted cases now have passing evidence.
Ruff/diff PASS. No full local suite or repeated unaffected tests.

Actual retained ZIP demo commands (each once, exit0):
research trace --archive tmp/m2-handoff-walkthrough/delivery.zip --fact
7eb6dbc54c5804849fc89cbfb3cb6434406d8cb4e38d29498f2c5eafbd8d1289 --json
research trace --archive tmp/m2-handoff-walkthrough/delivery.zip --fact
dd37a724277e9cceb6c05c50c78b14d7c53690700dc8a43cad094298a8b7b76a
Saved tmp/m2-fact-evidence-trace-demo/fact.json and parent.md. Both expose original
2024-03-31/2023 references for cash proxy, cash-flow/net-profit ratio and cash-flow
YoY; parent remains unresolved_absent_from_snapshot. Full source gaps retained.
Original ZIP SHA256 unchanged
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.

Original primary dirty/untracked snapshot, HEAD3679b1b/main966206f/stashcb568efd
and427protected hashes freshly compared before implementation. Database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 unchanged.
Seven-file scope; verifiers/builders/calculation/old tests/CI/baselines untouched.
Independent final actual diff/Goal/HEAD/refs/protection and all hosted gates required
before standing-authorized merge. Final hosted and postmerge evidence retained
in tmp/m2-fact-evidence-trace-final-review.md. No automatic next stage; installed
compatible fixed baseline still required, history/source gaps remain.
