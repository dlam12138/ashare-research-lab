# Work record: M2 Stage 2G.2 reproducible research capsule

## Basic information

- Date: 2026-08-02
- Agent: Codex
- Branch: `feat/m2-value-assessment-mvp`
- Starting HEAD: `d774667eec055de336c6d43a3d51538fdcd3e976`
- Task source: `agent/goals/2026-08-02_m2_stage2g2_reproducible_research_capsule.md`
- Module: value assessment / data foundation / engineering governance

## Objective

Close the Stage 2G.2 reproducibility and delivery gaps for the existing PetroChina PIT
valuation slice: portable canonical Fact and market test capsules, explicit real-input
resolution, strict Rule007 issuer-plus-exchange pairing, reproducibility manifests,
artifact verification, clean-clone tests, CI gates, and documented evidence limits.

## Scope and non-goals

Only the Stage 2G.2 contract is in scope. ROIC, scoring, Web, target price,
recommendations, automatic trading, market-mechanism work, protected-history rewrites,
default DB mutation, stash changes, real-data redistribution without permission, and
test-fixture fallback in real mode are out of scope.

## Starting state

- Worktree: only pre-existing untracked `agent/goals/` is present.
- Local branch is 8 commits ahead of `origin/feat/m2-value-assessment-mvp`.
- Stash `stash@{0}` is preserved and must remain unchanged.
- Starting HEAD matches the contract's expected `d774667e`.
- Default DB hash, protected baselines, test collection, registry hash, current run IDs,
  and cache availability are recorded below as the audit proceeds.

## Plan

1. Audit repository state and required contracts before code changes.
2. Add the portable snapshot/builder, market registry/resolver, strict Rule007 contract,
   capsule CLI, manifests/verifier, tests, CI workflow, documentation, and acceptance.
3. Run targeted, existing Stage 2G, identity/PIT/version-chain, full, static, capsule,
   clean-clone, and real-input acceptance gates.
4. Commit coherent scoped changes, push the current branch, and record the final report.

## Design review

The implementation will borrow pytest temporary-directory isolation, DuckDB explicit
read-only inputs plus deterministic import/export, OpenLineage-style run/input/output
metadata and checksummed facets, and GitHub Actions clean checkout validation. It will
not add plugins, external lineage services, catalogs, orchestration frameworks, network
fetches, or bundled third-party market data.

## Decision log

- Keep the committed Fact capsule as deterministic JSON, not a DuckDB binary. The
  canonical DB is read-only export input; temporary DuckDB import uses the existing
  `FactRepository` schema and preserves original IDs, contexts, lineages and version
  links.
- Generate the portable market capsule from a fixed algorithm and committed parameters.
  No Baostock/AKShare rows or raw responses are redistributed; real cache snapshots remain
  explicit external inputs.
- Use a single v2 registry resolver. A caller supplies either a real cache root or an
  explicitly synthetic test root. Missing and mismatched content fails closed; no local
  Parquet fallback remains.
- Centralize Rule007 source-pair semantics in a declarative registry. Only issuer official
  plus exchange official is eligible; designated disclosure platforms are separate states.
  Candidate selection is deterministic and contradictory candidates are errors.
- Use fixed contract timestamps and logical snapshot hashes for test-capsule inputs. DuckDB
  file bytes are temporary implementation state and are not used as the deterministic test
  input identity.

## Actual implementation

- Added `src/ashare_research/reproducibility/` for the market resolver, Rule007 pair
  registry, canonical snapshot exporter/builder, synthetic market generator and artifact
  manifest verifier.
- Added `src/ashare_research/tools/stage2g_reproducibility.py` with explicit
  `verify-contracts`, `export-facts`, `build-test-capsule`, `run-test-capsule`,
  `verify-real-inputs`, `run-real` and `verify-artifacts` modes.
- Reworked `petrochina_valuation_and_value_profile.py` to require explicit market mode and
  roots, use registry v2, enforce Rule007 candidate selection, and write v2 run/artifact
  manifests without absolute paths.
- Replaced the committed market registry with v2 logical object keys and removed the
  evidence ledger's local cache-root path.
- Exported the bounded canonical snapshot from the read-only Stage 2 canonical DB:
  33 Facts, 11 contexts, 33 lineage rows, six required concepts, Identity/version-chain
  PASS, Facts SHA-256 `68d63be1e5a5c13f9e3e136ac1297d867e1a9a72cae46c1444342e5e6602d45f`.
- Added clean-clone tests, the Stage 2G.2 acceptance and design documents, README usage,
  and `.github/workflows/stage2g-reproducibility.yml` for Python 3.11 Ubuntu/Windows jobs.

## Verification log

- Baseline: branch `feat/m2-value-assessment-mvp`, HEAD `d774667eec055de336c6d43a3d51538fdcd3e976`,
  local ahead of origin by 8 commits, default DB SHA-256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`, canonical DB SHA-256
  `47a09e98a8062f72b6907bc6ec55927588e4a815517ba8b4c0b595507ada7f0e`, registry v1 SHA-256
  `0cec00868c2d3e07977c8bbd7275246b3a195459789a9634bc77db5f56ee9f66`, 933 tests collected,
  no workflow, stash preserved.
- `python -m ... verify-contracts`: PASS WITH EXPLICIT GAPS; 1 Rule007 eligible event,
  9 evidence gaps, path-independent market registry, network false.
- Stage 2G targeted and reproducibility tests: `21 passed`.
- Full pytest: `941 passed, 2 warnings` in `191.01s`; initial 120-second command limit was
  insufficient, then the same full suite completed under a 300-second bound.
- Ruff, compileall, import and `git diff --check`: PASS after import-order correction.
- Real explicit preflight: PASS; canonical DB 201 rows/33 used, market 1,351 rows, both
  provider hashes verified, Identity/version-chain PASS, network false.
- Real local formal run twice: PASS WITH EXPLICIT GAPS; artifact manifest verification PASS,
  identical artifact-manifest hash `d0067121c317c2576ef95048a3f7404bd76c9326470da63402311b7cbef93ae2`.
- Test capsule build/run: PASS; 1,351 synthetic rows, 8,106 observations, artifact
  verification PASS; repeated run hash was identical.

The final pushed implementation added two portability corrections found by the real
fresh-clone gate: deterministic LF checkout for Stage 2G contracts without changing
historical evidence semantics, and clean-clone-safe guards for legacy no-mutation probes
and protected text-blob checks. Protected production blobs and historical baselines were
not rewritten.

## Historical final acceptance after push

- Historical implementation head: `53a65539d6c02ffd25a85079b8004bf5c931ce10`;
  the historical push of `feat/m2-value-assessment-mvp` succeeded and
  local/origin tracking refs were equal `0 0`.
- Fresh clone: `D:\tmp\stage2g2-clean-clone-中文-20260802-v7`, containing no `output/` or
  `data/research.duckdb` before testing. Exact installation command:
  `python -m pip install -e ".[dev]" --no-deps`.
- Fresh-clone commands and results: `verify-contracts` PASS; two capsule builds PASS;
  two capsule runs PASS; two artifact verifications PASS; targeted Stage 2G tests
  `21 passed`; full `pytest -q` `941 passed, 40 warnings` in `169.88s`; Ruff PASS;
  compileall/import PASS. Both capsule runs were 1,351 synthetic market days and
  8,106 observations. Logical artifact hash:
  `f2e81c7b3700a76adea9f35e8b7deec87c06e67cbfd073433997b10a3c3f498d`; both artifact
  manifest files were byte-identical, file SHA-256
  `4f4a29e90f7daa75479afe15cced69e1a2e84c77e91cd32b637cd9df752b9337`.
- The clean clone had no pre-existing ignored input. The full legacy suite created only
  ignored run-scoped test outputs under `output/value_assessment`; no tracked artifact,
  default DB, external cache or network input was required. Stage 2G deliverables passed
  private-absolute-path, secret and forbidden-artifact scans. Historical acceptance
  records retain their prior cache-path prose and were not rewritten.
- Final explicit real preflight: PASS; canonical DB 201 rows/33 used, market 1,351 rows,
  both provider hashes verified, reconciliation PASS, Identity/version-chain PASS,
  network false. Two formal runs: PASS WITH EXPLICIT GAPS; 19 files each, byte-identical,
  artifact verifier PASS, logical hash
  `6f6c68535090fc85c17fd7e052bd5b9d404e47b68f0a02b05e6b2a246b2e36a8`.
- Final default DB SHA-256 remains
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`; protected
  baseline remains 354 Facts / 102 Metric Results / 16 definitions; stash remains
  `stash@{0}` with message `protect pre-existing Stage 1B.4 record edit before Stage 1C`.
  Final worktree contains only the preserved untracked `agent/goals/` directory.

## References and borrowed designs

- Reviewed before implementation: North-Star/project guidance, `agent/agent.md`,
  `CLAUDE.md`, `agent/record/README.md`, the latest Stage 2G/2F records, README,
  Stage 2G.1 acceptance, the target valuation runner and Stage 2G tests, Fact
  Identity/Context/Repository/Service/AsOf/version-chain/storage modules, both
  ledgers, `.gitignore`, `pyproject.toml`, existing scripts and all protected-baseline
  tests.
- Borrowed pytest `tmp_path` isolation, DuckDB read-only real inputs plus repository
  schema rebuild for temporary capsules, OpenLineage-shaped run/input/output metadata
  with checksummed facets, and GitHub Actions clean-checkout OS/version matrices.
- Not copied: pytest plugins, lineage services, Marquez, catalogs, orchestration
  frameworks, network fetches, or third-party raw market responses.
- Repository-specific cuts: bounded canonical JSON read-model export rather than a
  committed DuckDB, deterministic synthetic market rows rather than redistributed
  provider data, explicit external roots for real research, fixed logical test
  timestamps, strict Rule007 issuer/exchange pairing, and no next-stage valuation,
  ROIC, scoring, recommendation, Web, trading or market-mechanism work.

## Final verdict

```text
M2 Stage 2G.2: CONDITIONAL PASS
Clean-clone default test suite: TRUSTED
Portable canonical Fact capsule: TRUSTED
Portable market test capsule: TRUSTED
Real market input resolver: TRUSTED
Rule007 issuer-exchange pair contract: TRUSTED
Artifact manifest and reproduction verifier: TRUSTED
Historical remote CI observation: NOT OBSERVED
PetroChina real value profile: COMPLETE WITH EXPLICIT GAPS
ROIC: NOT YET
Scoring: STILL NOT YET
Market mechanism: NOT STARTED
Next-stage implementation: NOT STARTED
Next-stage selection: NORTH-STAR REVIEW REQUIRED
```

## M2 Stage 2G.2R remote CI and reproducibility closeout

HEAD/evidence fields (the final remote head is intentionally not written into
this committed record):

```text
task_start_head: 29c1e221eaec994d597e2b634fc4be4f6543d19a
implementation_head: b4c450b4b1eb0e83100c7455e6c6df8ab5ef3dde
acceptance_evidence_generated_at_commit: b4c450b4b1eb0e83100c7455e6c6df8ab5ef3dde
reviewed_branch_head_at_time: b4c450b4b1eb0e83100c7455e6c6df8ab5ef3dde
final_remote_head: not committed; final response/external review only
workflow_run_commit: b4c450b4b1eb0e83100c7455e6c6df8ab5ef3dde
workflow_run_id: 30730670937
workflow_run_url: https://github.com/dlam12138/ashare-research-lab/actions/runs/30730670937
```

The later remote run passed independently on Ubuntu and Windows with Python
3.11 and `fail-fast: false`. Both jobs passed clean-clone preflight, contract
validation, independent A/B capsule builds and comparison, independent A/B
artifact runs and comparison, and the full offline suite. The earlier run
`30729995619` exposed a single Ubuntu-only hard-coded path-separator assertion;
its Windows job was cancelled by the previous fail-fast matrix. This was
classified as a test portability defect, not an infrastructure outage.

Local closeout evidence at `b4c450b`:

- Targeted tests: `93 passed`; full suite: `952 passed, 2 warnings`; Ruff,
  compileall/import and diff checks passed.
- Test capsule A/B logical digest:
  `8d89d7d4a71f0e5dcaacccabc231e70411822f457c2dda9e03fe846c750f0ed1`.
  Test run A/B logical artifact digest:
  `27f878b7e7f6743f9f638916817fe881b891cd447ed9a18361de5dc8748d7da8`.
- Explicit real preflight: 201 Fact rows / 33 used, 1,351 market rows, both
  provider hashes, Identity/version-chain PASS, reconciliation PASS and
  `network_used=false`. Real A/B logical artifact digest:
  `4ddb72f6ad05cdc75bf40834f5ec78d94b74586465e17b8737a23f496e9a7a14`;
  Rule007 remained 1 eligible event / 9 explicit gaps.
- Rule007 now distinguishes exact issuer+exchange eligibility, three-source
  supplemental designated evidence, issuer-only, exchange-only,
  designated-only, no retrieved official source, conflicting official sources,
  and incomplete/invalid evidence. Designated evidence is excluded from
  reconciled Fact `input_fact_ids`; overwrite, tamper and deletion tests fail
  closed.

## Stage 2G.2R final verdict

```text
M2 Stage 2G.2R: PASS
Ubuntu remote CI: PASS
Windows remote CI: PASS
Independent dual-build reproducibility: TRUSTED
Independent dual-run reproducibility: TRUSTED
Rule007 supplemental-source contract: TRUSTED
Rule007 empty-source semantics: TRUSTED
Clean-clone reproducibility: TRUSTED
PetroChina real value profile: COMPLETE WITH EXPLICIT GAPS
ROIC: NOT YET
Scoring: STILL NOT YET
Market mechanism: NOT STARTED
Next-stage implementation: NOT STARTED
Next-stage selection: NORTH-STAR REVIEW REQUIRED
```
