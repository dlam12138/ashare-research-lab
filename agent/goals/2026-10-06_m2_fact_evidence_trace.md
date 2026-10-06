# Reverse fact evidence lookup

Objective: root executes without DSH/delegation. Extend research trace with a
fact-ID lookup across original selected metrics and both requested views, including
explicit direct-parent references. No inferred transitive or causal impact.

Verified origin/live main f3c2d18bae387c134647f92b347651618d6c8d65;
owned branch codex/m2-fact-evidence-trace. Primary HEAD3679b1b/main966206f/
stashcb568efd, exact dirty/untracked snapshot and 427 protected hashes unchanged.
Database SHA2564a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Allowed seven files: this Goal; acceptance/2026-10-06_m2_fact_evidence_trace.md;
agent/record/2026-10-06_02-m2-fact-evidence-trace.md; README.md;
src/ashare_research/tools/metric_evidence_trace.py;
src/ashare_research/tools/research_entry.py; tests/test_fact_evidence_trace.py.
Ignored evidence/demo allowed. Forbidden: existing tests, baseline/verifier/builders/
formula/comparison/CI/data changes, acquisition/backtests/holdout/real research,
foreign trees/user changes/stash/databases, force/main pushes/destructive cleanup.

Required: research trace (--package DIR | --archive ZIP) --fact ID [--json].
Existing --metric ID --year YEAR remains identical. Fact and metric selectors
mutually exclusive; year forbidden for fact mode, required for metric mode.
Whole package freshly verified, canonical bytes only, session/workflow only.
Enumerate every exact original input fact-ID match and explicit direct-parent-ID
match across all selected metric rows/views, retaining whole original records,
bindings and matched parent entries. Unknown ID fails FACT_NOT_REFERENCED.
No recursive lineage guesses, numeric recomputation, filled missing evidence,
classification changes, output directory or post-verification file rereads.
Markdown distinguishes input/parent references and shows roles, metric results,
source gaps and parent status; JSON includes request/boundary/limitations and full
verification. Sanitized exit2/no partial stdout on any failure.

Exact local validation (PYTHONPATH=src; D:/量化分析/.venv/Scripts/python.exe):
python -m pytest -q tests/test_fact_evidence_trace.py tests/test_metric_evidence_trace.py
python -m ruff check src/ashare_research/tools/metric_evidence_trace.py src/ashare_research/tools/research_entry.py tests/test_fact_evidence_trace.py
git diff --check
One targeted run, repeat affected failures only; no full local suite. New tests
cover independently selected direct/parent references, shared inputs, missing roles,
directory/ZIP/CLI, invalid selectors, unknown ID, tampering and canonical handoff.
Retained delivery demo without regenerating or changing its source.

Acceptance: exact original matching references and complete records; parent lookup
does not claim missing parent is retained; old metric behavior preserved; local
tests/lint/diff pass; seven-file scope and protected snapshots unchanged.
Commit/push scoped branch/PR, independently inspect actual diff/HEAD/evidence and
all required hosted checks/exact head/base/mergeability before standing-authorized
merge. Stop on failure/conflict/drift/scope expansion without bypass. Final packet
PASS/CHANGES_REQUIRED/BLOCKED with refs/tests/sync/protection/limits. No automatic
next stage without user authorization.
