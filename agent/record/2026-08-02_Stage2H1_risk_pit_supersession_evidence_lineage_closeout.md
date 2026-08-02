# Work record: M2 Stage 2H.1 Risk Search PIT, Supersession and Evidence-Lineage Closeout

## Basic information

- Date: 2026-08-02
- Agent: Codex
- Branch: `feat/m2-value-assessment-mvp`
- Starting HEAD: `d3b0680e2bceb766a1fa113102873aad739c1f3f`
- Task source: `C:\Users\111\.codex\attachments\a97c8d34-211a-4709-8c28-6cd08411b0da\pasted-text.txt`
- Scope: Stage 2H trusted-contract closeout only

## Starting-state verification

- Branch and origin tracking branch are both `feat/m2-value-assessment-mvp` at
  `d3b0680`; remote is `https://github.com/dlam12138/ashare-research-lab.git`.
- Intervening commits after the expected Stage 2H implementation are
  `197b94b feat: add Stage 2H PetroChina risk veto evidence` and
  `d3b0680 docs: record Stage 2H delivery gates`; the latest remote CI is run
  `30742256299`, completed successfully on `d3b0680`.
- The primary worktree is `D:/量化分析`; no additional worktree is listed.
  The only untracked entry is the preserved `agent/goals/` directory.
- `stash@{0}` remains: `protect pre-existing Stage 1B.4 record edit before Stage 1C`.
- Default DB `data/research.duckdb` is 4,468,736 bytes with SHA-256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected baseline remains `354 Fact / 102 Metric Result / 16 definitions`.
- Pre-edit hashes: Stage 2H acceptance
  `d4e233af097a1699a39a9ce750aeb525b6acbde33312f5592549201028e2f53c`;
  methodology `ba5a5cde7f8404cfab02958ca6a176245c468a4eb345f1b61559e02f65ec961`;
  value profile JSON `4cc80c677fbfc7293bd85318a88e8fc84b756ebd84bcee71ec4b2bd6d95272e6`;
  value profile Markdown `af9f55aea26d680887ed7384f4e8151edcc15aa3b175488a34c9a1d1dfca258e`;
  formal report `1f9d71a1c599729207f9a800955f1a15a9797adf8610507bf710349dac57a60f`.

## Required pre-edit defects to close

The current implementation has five independent contract gaps that must be
closed rather than bypassed to preserve the six historical non-trigger
conclusions:

1. Event PIT filtering and search-register PIT are separate logic; the current
   search-register mapping is a single `risk_id` map with no version selection.
2. `supersedes` is recorded but active event versions are not resolved before
   trigger evaluation.
3. Event inputs and evidence fields have no field-level, transform-verifiable
   lineage binding.
4. A real formal run can run or publish without validating the full official
   cache; the existing resolver check is only a one-way subset check and only
   asserts a partial source pair.
5. The observation contract does not require or identity-hash `available_at`.

## Scope boundaries

Only search PIT/version chains, event supersession, evidence normalization and
lineage, official-cache enforcement, observation availability, tests, reports
and acceptance documentation are in scope. Do not start ROIC, scoring, Web,
target price, recommendations, automatic trading or market-mechanism work. Do
not modify the default DB, stash, protected baseline or untracked goals files.

## Plan

1. Read the mandatory North-Star, agent, acceptance, methodology, contracts,
   runner, ledgers, tests and Stage 2G.2 infrastructure files.
2. Version and PIT-bound search registers; implement fail-closed selection and
   event supersession resolution.
3. Add normalization records and field-level reconstruction/validation; make
   event source types and availability derived from evidence.
4. Enforce complete cache validation for real formal and publication; tighten
   observation identity and availability contracts.
5. Add targeted regression tests, rerun real/history/synthetic/A-B/clean-clone
   gates, update old-to-new reports and acceptance docs, then commit and push.

## Execution log

Implementation and verification results will be appended in order. No PASS
verdict is recorded until the final remote Ubuntu/Windows CI run succeeds.

## Final result

Pending Stage 2H.1 implementation and full remote verification.
