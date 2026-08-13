# Work record: M2 Stage 2I.1R ROIC readiness contract and minimum acquisition batch closeout

## Basic information

- Date: 2026-08-02
- Agent: Codex
- Task source: user-provided Stage 2I.1R pasted contract
- Branch: `feat/m2-value-assessment-mvp`
- Starting HEAD: `5bea14b98aad0b62d525ae5b7f883f1886a4b090`
- Parent Stage 2I functional commit: `e0fb6d6b932134d58bab046534f56b5adde77d3d`

## Objective and non-goals

Close the ROIC readiness contract and lock the smallest FY2023/FY2024
acquisition batch. This is a contract/readiness closeout only. Do not acquire
new ROIC facts, run a shadow calculation, create a production ROIC Metric or
Metric Result, modify the current value profile, score, use Web, calculate a
target price, recommend, automate trading, or start market-mechanism work.

## Starting-state verification

- Branch and local/origin HEAD: `feat/m2-value-assessment-mvp` /
  `5bea14b98aad0b62d525ae5b7f883f1886a4b090`; expected Stage 2I ancestor
  `cae29f0` is present.
- Remote: `origin` is
  `https://github.com/dlam12138/ashare-research-lab.git`; upstream is
  `origin/feat/m2-value-assessment-mvp`; ahead/behind is `0/0`.
- Worktree: one worktree at `D:/量化分析`; only the user-owned untracked
  `agent/goals/` directory is present.
- Stash: `stash@{0}` remains
  `protect pre-existing Stage 1B.4 record edit before Stage 1C`.
- Default DB: `data/research.duckdb`, SHA-256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected baseline: `354 Fact / 102 Metric Result / 16 definitions`.
- Latest remote CI before edits: run `30748322522`, Ubuntu and Windows
  successful; prior Stage 2I closeout runs `30748089148` and `30747869003`
  were also successful.
- Existing Stage 2I reports/config/acceptance and the v1 canonical inventory
  were present before this record.

## Known review issues registered before implementation

1. DuckDB readiness query is not restricted by symbol/entity.
2. Any same-name row can currently be marked ready.
3. Readiness does not fully validate Context, scope, period, unit, source and
   verification.
4. PIT/restatement is metadata-only and does not parse a legal version chain.
5. The committed inventory lacks fields needed to revalidate the ROIC input
   contract.
6. Methodology, input contract, tool and acquisition plan use different
   concept names.
7. Documentation status enums differ from the tool's actual statuses.
8. The minimum acquisition batch is not constrained by one registry.

These issues must be fixed by stricter contracts, not by relaxing ROIC
readiness.

## Required reading

Read the two North-Star documents, `CLAUDE.md`, `agent/agent.md`,
`agent/record/README.md`, Stage 2I acceptance, methodology/config/input
contract/readiness matrix/acquisition plan/inventory/tool/tests, Fact
Identity/Context/Repository/FactService/AsOfQuery/version-chain code, Stage 2G
canonical snapshot/exporter, and ROE/ROA/financial-safety/debt-decomposition
contracts before implementation.

## Decision log

- The registry is the only concept/role authority. Old names are aliases for
  migration/error reporting and never make a Fact ready.
- Readiness uses only the nine formal statuses and validates exact symbol,
  Context, scope, period, unit/currency, source evidence, verification,
  eligibility and PIT visibility.
- The PIT selector validates identity-stable supersedes edges, strict version
  increments, non-backward availability and disconnected-chain conflicts.
- The v2 inventory was generated read-only from the explicit run-scoped
  canonical DB; it contains all 354 rows so reconciled Facts retain their
  official parent source evidence.
- The plan is deliberately three-layered and limited to FY2023 opening/FY2024
  closing. No official Fact was acquired in this task.

## Actual operations

- Created this record before code changes; preserved the four untracked
  `agent/goals/` files and the protected stash.
- Added `config/roic_concept_registry_v1.json` and
  `src/ashare_research/tools/roic_contracts.py`.
- Added the read-only exporter/validator
  `src/ashare_research/tools/roic_fact_snapshot.py` and generated
  `config/roic_canonical_fact_inventory_v2.json` from the existing canonical
  DB (354 Facts / 122 eligible / 11 Contexts / 270 source records).
- Replaced the presence-only readiness tool with strict v2 readiness and legal
  PIT/restatement selection in `roic_fact_readiness.py`.
- Added v2 acquisition plan/docs, independent contract tests, v1→v2 diff,
  acceptance closeout and current README status; preserved the historical v1
  report and acceptance as history.
- No production Metric, Metric Result, value-profile update, ROIC fact
  acquisition, shadow calculation or default DB write was performed.

## Verification

- Targeted Stage 2I tests: `9 passed`.
- Full pytest: `976 passed, 2 warnings in 176.88s`; the first 120-second
  attempt timed out before completion, then the bounded 300-second rerun
  passed and the test child exited normally.
- Ruff full `src/` and `tests/`: passed. `compileall` and imports: passed.
- Snapshot A/B: byte-identical; snapshot SHA256
  `cb675690dd619d01534872c2bc98e9e0f6da80ff4f2ff586978d464c70fece57`.
- Explicit real fact-db readiness: repository PIT probe saw 354 rows and only
  `601857.SH`; report remained `BLOCKED_WITH_EXPLICIT_GAPS` and shadow
  `NOT_RUN`. Historical as-of runs at 2024-04-01 and 2026-04-01 changed only
  visible readiness as the PIT gate requires.
- Clean clone at `8e53e89`: inventory loaded as 354 Facts and targeted 9 tests
  passed; no default DB or external canonical DuckDB was required.
- Default DB hash remained
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`;
  `stash@{0}` and the four untracked goal files remain unchanged.
- Remote CI run `30750543799` for HEAD `8e53e89` completed successfully on
  both `clean-clone (ubuntu-latest)` and `clean-clone (windows-latest)`;
  full offline suites and all preceding static/contract/capsule gates passed.

## Result

The contract implementation, local gates, push and remote Ubuntu/Windows CI
are complete. The official-fact evidence gate remains explicitly blocked for
the next acquisition stage, as intended by this closeout.

## Final decision

`M2 Stage 2I.1R: PASS`

Registry: `TRUSTED`

Evidence gate: `BLOCKED_WITH_EXPLICIT_GAPS` (expected; direct official ROIC
inputs are not acquired in this closeout)

Stage 2I decision: `ROIC_FACT_ACQUISITION_REQUIRED`

Next-stage acquisition: `ALLOWED`

Scoring, Web, target-price, recommendation, automatic-trading and
market-mechanism work: not started.

## Final Git state

Scoped commits before the record commit:

- `8bf4b2f feat: harden ROIC readiness contract`
- `1aff50a docs: close ROIC readiness acquisition contract`
- `8e53e89 chore: normalize ROIC acquisition plan ending`

The record is the only intended final commit after the three scoped commits;
`agent/goals/` is intentionally never staged.
