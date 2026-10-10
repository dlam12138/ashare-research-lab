<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Financial analysis: consolidated local delivery

## Objective and verified baseline

Consolidate the delivered arbitrary-company financial core and its two accepted
corrections into a reviewable local commit, with discoverable README usage and
verification from an export of only staged tracked files.
User explicitly continued the project after the integration recommendation.
Owned branch codex/financial-json-review, HEAD
4446fb84c9b496d0654780c4ff4f0447f2ee07e7, two commits above origin/main.
origin/main and live main: 47dbb6780933f8fb7abab922aa47027a1342de41.
Seven existing task files comprise three tracked modifications and four
untracked contracts/records. Their bytes must remain unchanged.
Root remains feat/m2-value-assessment-mvp at 3679b1b with protected user edits.
No active non-sample Git hooks or configured hooksPath were found.

## Allowed scope and required behavior

Update README with a truthful local-delivery capability row and explicit CLI
examples/boundaries. Create this Goal and one combined acceptance/work record.
Stage and commit exactly these three documents plus the seven existing
correction files, preserving the existing feature commits and previous records.
This stage's local delivery supersedes the previous tasks' uncommitted stopping
points; it does not authorize pushing, PR creation or merging.
Prior financial code/tests/guide are packaging inputs, not new edits.
Explicit database/symbol/date/year selectors, existing formulas, context/PIT
gates, non-finite exclusions and no-implicit-data behavior must remain intact.

## Forbidden scope

No business-code or test changes, extra features, formula/schema/dependency
changes, source access, primary database connection, scoring, investment
recommendations, provider/holdout/DSH execution, other-agent file edits,
main checkout, merge, push, tag, amend or automatic next stage.
Do not distribute local governance or rewrite historical acceptance.

## Required checks and exact commands

Use the existing D:/量化分析-m4a2i/.venv/Scripts/python.exe.
Inspect index scope and export a complete staged tree to a new, absent
system-temp directory using git checkout-index. Record its absolute path and
write-tree hash. The clean export deliberately has no .git or copied ignored
environment/data; dependencies come only from the named existing interpreter.

```powershell
git diff --check
git diff --cached --check
git diff --cached --name-only
git write-tree
git checkout-index --all --prefix=<NEW_ABSOLUTE_TEMP_DIR>/
```

From that clean export:

```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py tests/test_research_entry.py tests/test_project_entry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/financial_analysis.py src/ashare_research/tools/financial_analysis.py src/ashare_research/tools/research_entry.py tests/test_financial_analysis.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ashare_research.cli research financial --help
```

Also execute a subprocess CLI smoke using a new temporary database rebuilt
from the exported committed stage2g snapshot: symbol 601857.SH, as-of 2024-06-30,
year 2023. Compare unified CLI JSON with the direct module JSON, expect
12 records / 7 computed / 5 missing, and verify DB hash unchanged.
Verify output has no score/production eligibility. Check README links,
UTF-8, provenance, whitespace and exact parameter examples.
Fresh selected tests are justified by the new clean-export reproducibility
boundary; the two project-entry tests validate the new README capability/link
contract. No unrelated full suite is required.

Before commit compare all seven packaging inputs to task-start SHA256s and
clean exported bytes. Only final work-record bytes may differ after tests.
Inspect scope/index/diff and protected state, then:

```powershell
git commit -m "fix(m2): deliver validated company financial analysis"
git show --stat --oneline HEAD
git status --short --branch
git rev-parse HEAD origin/main refs/stash
git ls-remote origin refs/heads/main refs/heads/feat/m2-value-assessment-mvp
```

## Acceptance, protections and stop conditions

Required checks pass and show the clean staged delivery is self-contained.
Final commit has exactly ten task paths; original seven inputs and runtime
code/test bytes equal the successfully tested export; owned worktree is clean.
Record actual commit in final chat rather than embedding a self-referential
commit hash inside its own tracked work record.
Snapshot C:/Users/111/AppData/Local/Temp/codex-financial-delivery-20261010-before.json
protects all original foreign tree HEAD/status, dirty/untracked files, prior
owned inputs, frozen reports/config/evidence, root north stars/DB and stash.
Owned branch HEAD/status may change only according to this contract.
Stop for concurrent changes, source-byte drift, failed gates or expanded scope.
Leave generated temporary test/export artifacts in place; no cleanup of user
paths. Ignore test-cache differences only as documented generated artifacts.

## Commit and push requirements

Create one scoped normal local commit after all checks. Do not amend, push,
merge or create a PR. Existing feature branch remains untouched; current
delivery branch is the sole commit target.
