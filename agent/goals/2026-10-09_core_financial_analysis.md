<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-09 -->

# Core company financial analysis

## Objective and verified baseline

Enable any caller-selected A-share company with existing reconciled financial
facts to obtain a multi-year PIT financial profile, rather than a fixed
PetroChina snapshot. Root works directly; no DSH or delegation.
Base branch codex/m4-preparation-byte-diff, commit
ce7650267d4867d52b59e7c70e3d6bf4adb571e7; origin/live main
0818edff8a2aae454c41145f5ef55184cf0d3a46. Main locally remains 966206f.
Root dirty files and stash cb568efd are preserved. Primary database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Pre-code evidence: tmp/core-financial-analysis/baseline.json.

## Allowed and forbidden scope

Add a financial analysis core, read-only CLI, meaningful tests, user guide,
entry help, work record and acceptance. Reuse the public AsOfQuery and all
12 existing MetricEngine-supported definitions from growth, cash flow,
earnings quality and capital return registries. Selected database is explicit.
No data acquisition, formula changes, ranking, scores, ROIC substitution,
valuation recommendations, research execution, holdout or frozen baseline edits.
Do not open the primary database; demonstrate using a newly created test DB
populated with committed historical facts. Do not touch other worktrees.

## Required behavior

Explicit symbol, as-of, bounded annual window and scope. Public PIT selection
precedes analysis; bind only annual flows and year-end instant balances.
Preserve exact engine decimal calculations and non-computability states.
Report role-level missingness, selected inputs, source references, lineage and
input availability bounds. Show year-to-year metric changes separately from
same-period revisions across two optional PIT dates. Never imply metric
publication time or independent source verification. Existing DOUBLE storage
supports only finite exact integers within 2^53-1 for this engine; incompatible
inputs must be visibly excluded, never rounded/coerced or silently substituted.
Read-only DB connection, one consistent transaction for both PIT dates.
No schema initialization/migration or default DB path.

## Required tests and exact commands

From the owned worktree using D:/量化分析-m4a2i/.venv/Scripts/python.exe:

```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py tests/test_research_entry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ashare_research/financial_analysis.py src/ashare_research/tools/financial_analysis.py src/ashare_research/tools/research_entry.py tests/test_financial_analysis.py
git diff --check
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' tmp/core-financial-analysis/verify_protections.py
```

Test numeric outputs against independent expected values/public engine,
multi-company isolation, annual/instant/scope bindings, future versions and
parent evidence, same-year revision versus adjacent-year change, missing,
zero/negative denominators, incompatible values, invalid selectors before
opening database, real CLI, source hash unchanged and no database creation.
Adjust regression filename only if actual repository uses another name.

## Acceptance, stop conditions and delivery

Core/CLI produce 12 metrics per requested year for arbitrary eligible symbols;
actual committed PetroChina fixture computes existing seven metrics and
honestly reports absent expanded inputs. Tests/lint/protection review pass.
Stop on concurrent foreign changes, frozen evidence changes or scope expansion.
Write acceptance with actual commands/results, failures and limits.
Create one scoped local commit after final review; no push, PR, merge or
automatic next stage. Current user governance overrides tracked standing
merge authorization and DSH default.
