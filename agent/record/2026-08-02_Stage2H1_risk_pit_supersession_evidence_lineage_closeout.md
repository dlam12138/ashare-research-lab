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

- North-Star Review was completed before implementation and remained `ALLOWED`
  for the bounded Stage 2H risk-veto slice.
- Preserved v1 search/event ledgers and added v2 PIT search, v2 event grouping,
  v2 official registry and field-level normalization contracts. The source
  evidence ledger now also carries the required 2021 going-concern field.
- Implemented fail-closed search version chains, PIT selection, event active /
  superseded resolution, evidence-to-normalization reconstruction, conflict
  checks, complete official-cache mapping, and observation availability/id
  requirements. Stage 2G.2 resolver/artifact/clean-clone infrastructure is
  reused.
- Contract gate: `pass_with_explicit_gaps`; 8 risks, 10 evidence IDs, 8 unique
  registry objects, 36 events, 105 normalization records, and 8 search
  registers.
- Real cache preflight: `pass`, 10/10 evidence mappings verified by real
  content SHA-256, object key and byte size; no network and no default DB
  mutation.
- Real formal run `petrochina_stage2h1_real_final`: `conditional_pass`, 8
  observations, 0 observed triggers, and 2 explicit `missing_evidence` risks.
  Artifact logical digest:
  `a18db13689cb28c1492b068800740039f1a34ac72b5d55865c135c04fb50e36e`.
- Historical as-of run `petrochina_stage2h1_historical_20250401` retained
  seven missing-search observations because current v2 registers were not
  PIT-visible at that date.
- Synthetic correction capsule passed before/after PIT evaluation and
  supersession; two independent capsule artifacts compare identically.
- Focused Stage 2H.1 tests: `9 passed`. Full offline suite: `961 passed, 2
  warnings`; warnings are the existing pandas date-format warnings in
  `tests/test_quality.py`.
- Clean clone: Stage 2G.2 `verify-clean-clone` pass, Ruff pass, compile pass,
  Stage 2H.1 contract pass and focused tests `9 passed`.
- Coherent commits were created and pushed: `eb31e35` implementation closeout
  and `1c0abf6` lineage fail-closed hardening. Remote branch and local HEAD
  both equal `1c0abf624bf2cb8f2b7cc563806d190647b58d34`.
- Remote CI run `30743985521` completed successfully on both
  `clean-clone (ubuntu-latest)` at 10:36:07 and
  `clean-clone (windows-latest)` at 10:38:50.

## Final result

Final Stage 2H.1 result is `CONDITIONAL PASS`: the contracts and execution
gates are trusted, while the two bounded search gaps remain explicit
`missing_evidence`. No ROIC, scoring, Web, target-price, recommendation,
automatic-trading or market-mechanism work was started.

Final artifacts:

- Risk-veto report SHA-256:
  `e86a6153e1162e54675b959742e150e53c4ab7ad9b346f7642f980c86996e616`.
- Integrated value-profile JSON SHA-256:
  `6f63edc96a5736fd4c69c08d517107566ee3a6d012450da3edf5457b6f877780`.
- Default DB SHA-256 remains
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Stash remains present; the only worktree entry is preserved untracked
  `agent/goals/`.
