# M2 Stage 2I.1R2 ROIC acquisition gate consistency closeout

Status: `ACCEPTED_WITH_ACQUISITION_REQUIRED`

## Scope and historical correction

This closeout changes contracts, readiness, validation and documentation only.
It acquired no official ROIC Fact, ran no shadow calculation, created no ROIC
Metric or Metric Result, changed no value profile, and did not start scoring or
market-mechanism work. Stage 2I and Stage 2I.1R acceptance remain historical;
their then-current hand-written acquisition permission is superseded by this
validator-governed decision.

## Frozen formula dependency

`config/roic_formula_dependency_graph_v1.json` is the primary formula
authority. Finance cost uses composition scheme 1:

```text
finance_cost_adjustment
  = finance_cost_excluding_lease_interest + lease_interest_expense
```

Only the composite parent enters NOPAT once. Both components must be ready,
source-note reconciliation is mandatory, and a missing/inseparable component
keeps the parent unready. Investment income, fair-value net change and
asset-disposal gain/loss are independent primary adjustments. Other
non-operating income/expense is secondary because it follows CAS operating
profit. Direct operating tax remains an independent hard blocker with no rate
fallback.

## Methodology and registry migration

Registry v1 is unchanged historical evidence. Registry v2 materializes v1 plus
explicit migration overrides and validates every role against the dependency
graph. The mixed v1 non-operating-asset boundary is replaced by resolved,
amount-free `policy.non_operating_asset_classification` and monetary,
deterministic `invested_capital.qualifying_non_operating_assets`. The decision
never deducts all cash, treats restricted cash as free, guesses operating cash,
uses unproven financial assets, mismatches associate/JV income and capital, or
creates a balance-sheet plug.

## Readiness correction

The historical v2 report had 156 cells and incorrectly presented six mixed
methodology/value cells as not applicable. The corrected report has 186 cells.
The six old cells remain migration tombstones; six replacement policy cells
are `ready` from a versioned resolved rule, while six separate amount cells are
`partially_ready` until their direct components are ready. Full old-to-new
evidence is in
`reports/petrochina_roic_fact_readiness_v2_to_v2_r2_diff.json`.

## Minimum plan and validator result

Plan v3 has exactly 11 acquisition items:

- A: FY2024 finance core, investment income, fair-value change,
  asset-disposal gain/loss and direct operating tax;
- B: FY2024 lease interest, plus FY2023/FY2024 NCI, associate investment and
  joint-venture investment;
- C: FY2023/FY2024 restricted cash and officially proven non-operating
  financial assets;
- D: no items; secondary roles do not block primary feasibility.

The policy and three deterministic parents are not acquired. Already-ready
operating profit, parent equity, debt and lease-liability components are not
reacquired.

The structured coverage artifact currently reports PASS with 38 covered
blocker/year cells and empty uncovered, orphan, mislayered and duplicate lists.
Plan digest:
`aedaebcaa5b85fd4bbfa39f77c2ac09a55c548cf2bb099cdc008271aa3340215`.
All required local, clean-clone, Ubuntu and Windows gates passed.

## Portability and safeguards

Formal outputs serialize repository-relative logical paths and digests, never
the runtime working directory. Tests cover Windows drive paths, Unix
home/temp paths and different working directories. Shadow remains `NOT_RUN`;
production ROIC and scoring remain closed.

## Engineering gates and remote CI

- Stage 2I/2I.1R/2I.1R2 targeted: `29 passed`.
- Full local and correctly rooted clean-clone suites: `996 passed, 2` existing
  date-format warnings each.
- Fact Identity/PIT/restatement: `106 passed`; ROE/ROA/financial safety:
  `130 passed`; Stage 2G: `32 passed`; Stage 2H/2H.1R: `15 passed`.
- Ruff, compile/import, `git diff --check`, readiness/coverage A/B,
  alternate-working-directory portability, secret and pollution scans passed.
- GitHub Actions run `30752858635` at head `6aebbb5` passed both clean-clone
  jobs: Ubuntu job `91509863079` and Windows job `91509863101`, including the
  full offline suite and all Stage 2G/2H capsule gates.
- The default DB SHA-256, protected inventory, stash and untracked goals remain
  unchanged.

## Final decision

- M2 Stage 2I.1R2: `PASS`
- ROIC formula dependency graph: `TRUSTED`
- Finance-cost/lease-interest composition: `TRUSTED`
- Primary/secondary role classification: `TRUSTED`
- Methodology-choice readiness: `TRUSTED`
- Non-operating-asset policy: `FROZEN`
- Acquisition-plan blocker coverage: `COMPLETE`
- Acquisition-plan validator: `TRUSTED`
- Committed-artifact portability: `TRUSTED`
- Shadow feasibility: `NOT RUN`
- Production ROIC Metric/Result: `NOT CREATED`
- Stage 2I decision: `ROIC_FACT_ACQUISITION_REQUIRED`
- Next-stage acquisition: `ALLOWED`
- Scoring: `STILL NOT YET`
- Market mechanism: `NOT STARTED`
