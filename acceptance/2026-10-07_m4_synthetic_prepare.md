# Explicit synthetic preparation acceptance

Goal: agent/goals/2026-10-07_m4_synthetic_prepare.md.
Verified base codex/m4-plan-compare@cf05289cfc8c6f1779c0f7a043cc3ecf260b989c.
Root worked directly, no DSH/delegated agents. Eight-file scope only.

research prepare verifies the complete plan directory/native ZIP, rebuilds typed
contract/plan and compares their full canonical content to that verified snapshot.
The verified canonical config's absent holdout null is omitted only for the original
input parser's optional-key convention; no original parser/compiler/schema changed.
Explicit BoundDatasetInputsV1 JSON is once-read, bounded1MiB, strict UTF8/unique keys/
finite constants/object root, linked/reparse ancestors and nonregular files rejected.
Existing adapter quality gates/input digest/row evidence are unchanged. READY_SYNTHETIC
permits matrix preparation only; quality rejection retains audit/quality and null
matrix. Output JSON/Markdown preserve complete canonical artifacts and original
identities. Outcome-read flag truthfully true for invented inputs; execution,
statistics, holdout, real-source evidence and research readiness remain false.

Exact commands (PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe):
```
python -m pytest -q tests/test_synthetic_prepare.py
python -m ruff check src/ashare_research/tools/synthetic_prepare.py src/ashare_research/tools/research_entry.py tests/test_synthetic_prepare.py
git diff --check
python tmp/m4-synthetic-prepare-demo.py
```
Final local result3passed2.03s; Ruff all checks passed; diff check passed.
First run3failed: canonical absent-holdout null incompatible with original parser;
fixed adapter's parser-shaped copy and retained full canonical identity checks.
Ruff initially found two long test lines, wrapped. Second run2passed1failed due
new test expecting tool error for the existing top-level global-option rejection;
corrected assertion to exact existing code2/empty-stdout/two-line message, no CLI
behavior change. Third run3passed. No existing tests modified/full local run.

Cases: public directory/ZIP equivalence and exact direct-API dataset/matrix output;
input byte identities, unchanged input files, service/network/database/pipeline/
executor guards; missing observations/null values/unproven or late PIT preserve
denominator4 with numerator3, exact reasons/audit rows and no matrix projection;
real mode, wrong contract/input/evidence hashes, wrong units, nonstring values,
outside-development/domain dates fail closed without repair; malformed/duplicate/
oversized JSON, missing/nonregular/reparse inputs, unsupported flags/global flags,
complete plan tampering, one-read immutable loaded snapshot all verified.

Actual CLI subprocess demo: directory and ZIP JSON byte-identical, Markdown emitted,
READY_SYNTHETIC,4rows5columns,7input hashes unchanged. Actual Windows directory
junction in input ancestor fails LINKED_INPUT_PATH/code2/empty stdout.
Retained tmp/m4-synthetic-prepare-demo/evidence.json and preparation.json/preparation.md.
Example docs/examples/m4_bound_inputs.json contains only16invented observations over
four declared fictional calendar dates; bound by existing canonical digest helper.
It does not establish a real trading calendar or financial PIT provenance.

Final gate pending committed independent review and exact-head hosted checks:
eight-file diff/Goal, original408protected hashes, primary dirt/refs/stash/database,
three dependencies and foreign worktree registrations unchanged; owned clean/synced,
normal commit/push, stacked PR base codex/m4-plan-compare depends70/69/68. Final
immutable head/PR/all42checks/actual four full-suite summaries and repeated protection
evidence go in tmp/m4-synthetic-prepare-final-review.md after actual gate. Pending
results not claimed successful here. No automatic merge or following stage.
