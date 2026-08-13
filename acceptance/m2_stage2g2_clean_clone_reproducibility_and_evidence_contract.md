# M2 Stage 2G.2 clean-clone reproducibility and evidence contract

Status: **CONDITIONAL PASS**

This acceptance closes reproducibility for the existing Stage 2G.1 PetroChina
PIT value-profile slice. It does not create a new valuation feature.

## Starting protection

- Branch: `feat/m2-value-assessment-mvp`
- Starting HEAD: `d774667eec055de336c6d43a3d51538fdcd3e976`
- Default DB SHA-256: `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`
- Canonical export source SHA-256: `47a09e98a8062f72b6907bc6ec55927588e4a815517ba8b4c0b595507ada7f0e`
- Protected baseline: 354 Facts / 102 Metric Results / 16 definitions
- Stash: `stash@{0}` is preserved

## Implemented contracts

1. Canonical Fact snapshot v1 is generated from the trusted canonical DB through
   existing repository/PIT/version-chain interfaces. It contains 33 bounded Fact
   rows, 11 contexts, 33 lineage rows, deterministic ordering and lossless
   decimal strings. The Fact file SHA-256 is recorded in its manifest.
2. The temporary Fact DB builder uses `FactRepository` schema creation, preserves
   original IDs and lineage, validates identity/version chains, and is scoped to
   the caller's temporary directory.
3. Market registry v2 contains relative content-addressed object keys only. The
   resolver requires an explicit real cache root or an explicit synthetic test
   fixture root and verifies hashes before reading.
4. Rule007 is exact issuer-official plus exchange-official. Designated platforms
   remain separate evidence states. Candidate selection is deterministic and
   contradictory candidates fail.
5. Runs write v2 manifests, checksums and reproducibility reports. Test capsule
   and real research inputs are distinct and test mode cannot publish reports.

## Gates

The final update records exact commands and results for targeted tests, full
pytest, Ruff, compileall/import, two capsule builds/runs, artifact verification,
clean-clone validation, real preflight/run, pollution scans, protected baselines,
default DB hash, stash, final worktree and push equality.

## Final gate results

- Historical implementation head for the prior Stage 2G.2 closeout was
  `53a65539d6c02ffd25a85079b8004bf5c931ce10`; local/origin tracking refs were
  equal (`0 0`) at that historical observation.
- Fresh clone: `D:\tmp\stage2g2-clean-clone-中文-20260802-v7` (redacted operational
  path; spaces/non-ASCII path requirement exercised). Before testing it contained
  no `output/` and no `data/research.duckdb`. Installation used
  `python -m pip install -e ".[dev]" --no-deps`; no research/cache download was used.
- Clean-clone commands passed: `verify-contracts`; two `build-test-capsule` runs;
  two `run-test-capsule` runs; two `verify-artifacts` runs; targeted Stage 2G
  tests (`21 passed`); `pytest -q` (`941 passed, 40 warnings` in `169.88s`);
  Ruff; `compileall`; and import checks. Both capsule runs covered 1,351 market
  days and 8,106 observations. The logical artifact verifier hash was
  `f2e81c7b3700a76adea9f35e8b7deec87c06e67cbfd073433997b10a3c3f498d`, and the
  two `artifact_manifest.json` files were byte-identical with file SHA-256
  `4f4a29e90f7daa75479afe15cced69e1a2e84c77e91cd32b637cd9df752b9337`.
- The full legacy suite generated only ignored run-scoped test outputs under
  `output/value_assessment` after starting from an empty clone; no ignored
  output, DuckDB, cache or network input was required. No tracked DuckDB/WAL,
  PDF, PNG, Parquet or raw-response artifact was present, and Stage 2G
  deliverables contain no private absolute paths.
- Canonical snapshot: 33 Facts / 11 contexts / 33 lineage rows; Facts SHA-256
  `68d63be1e5a5c13f9e3e136ac1297d867e1a9a72cae46c1444342e5e6602d45f`; source
  canonical DB SHA-256 `47a09e98a8062f72b6907bc6ec55927588e4a815517ba8b4c0b595507ada7f0e`.
  Portable market rows are synthetic-test-only, 1,351 rows, SHA-256
  `b89ba02fd664fad1e7c5ac765d3e02464e4268410402626b07c0c472787a4630`.
- Rule007 has exactly one eligible event and nine explicit evidence gaps. The
  eligible pair is `issuer_official + exchange_official`; designated disclosure
  platforms are never used as the exchange side.
- Real local acceptance used explicit `--fact-db` and `--market-cache-root`.
  Preflight passed with 201 Fact rows / 33 used, 1,351 market rows, both
  provider hashes verified, reconciliation PASS, Identity/version-chain PASS,
  and `network_used=false`. Two formal runs passed artifact verification,
  covered 19 files, and were byte-identical; logical artifact hash
  `6f6c68535090fc85c17fd7e052bd5b9d404e47b68f0a02b05e6b2a246b2e36a8`.
- Default DB SHA-256 remains
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6` and
  `stash@{0}` remains `protect pre-existing Stage 1B.4 record edit before Stage 1C`.
  Final worktree has only the preserved untracked `agent/goals/` directory.
- Historical remote-CI observation scope: `NOT OBSERVED` at the prior Stage 2G.2
  closeout. The Stage 2G.2R section below records the later observed run.
  Real provider data was not redistributed because redistribution rights were not
  asserted.

## Historical Stage 2G.2 verdict (before Stage 2G.2R)

```text
M2 Stage 2G.2: CONDITIONAL PASS
Clean-clone default test suite: TRUSTED
Portable canonical Fact capsule: TRUSTED
Portable market test capsule: TRUSTED
Real market input resolver: TRUSTED
Rule007 issuer-exchange pair contract: TRUSTED
Artifact manifest and reproduction verifier: TRUSTED
Remote CI: NOT OBSERVED
PetroChina real value profile: COMPLETE WITH EXPLICIT GAPS
ROIC: NOT YET
Scoring: STILL NOT YET
Market mechanism: NOT STARTED
Next-stage implementation: NOT STARTED
Next-stage selection: NORTH-STAR REVIEW REQUIRED
```

## Explicit limits

Real market data is not redistributed because provider redistribution rights are
not asserted. The bounded evidence ledger retains nine exchange retrieval gaps
and the A/H split gap.

## M2 Stage 2G.2R remote delivery closeout

The following HEAD model avoids a self-referential committed final-head claim:

```text
task_start_head: 29c1e221eaec994d597e2b634fc4be4f6543d19a
implementation_head: b4c450b4b1eb0e83100c7455e6c6df8ab5ef3dde
acceptance_evidence_generated_at_commit: b4c450b4b1eb0e83100c7455e6c6df8ab5ef3dde
reviewed_branch_head_at_time: b4c450b4b1eb0e83100c7455e6c6df8ab5ef3dde
final_remote_head: not committed; report only in the final response/external review
workflow_run_commit: b4c450b4b1eb0e83100c7455e6c6df8ab5ef3dde
workflow_run_id: 30730670937
workflow_run_url: https://github.com/dlam12138/ashare-research-lab/actions/runs/30730670937
```

The observed run used Python 3.11 on `ubuntu-latest` and `windows-latest`, with
`fail-fast: false`. Ubuntu job `91450419099` and Windows job `91450419127` both
passed every step: clean-clone preflight, contract validation, independent A/B
capsule builds and comparison, independent A/B runs and artifact comparison, and
the full offline suite. The prior run `30729995619` had one Ubuntu test failure
from a hard-coded Windows path separator at
`tests/test_reconciliation_contract_closure.py:367`; the Windows job was then
cancelled by the old fail-fast matrix. This was a test portability failure, not
an infrastructure failure, and is now normalized for both operating systems.

Local implementation evidence at `implementation_head`:

- Targeted Stage 2G/Rule007/reconciliation tests: `93 passed`; full suite:
  `952 passed, 2 warnings`; Ruff, compileall/import and diff checks passed.
- Independent test-capsule A/B builds compared six manifest outputs with logical
  digest `8d89d7d4a71f0e5dcaacccabc231e70411822f457c2dda9e03fe846c750f0ed1`.
  Independent test runs compared 16 artifacts with logical digest
  `27f878b7e7f6743f9f638916817fe881b891cd447ed9a18361de5dc8748d7da8`.
- Explicit real-input preflight passed with 201 Fact rows / 33 used, 1,351
  market rows, both registered provider hashes, Identity/version-chain PASS,
  reconciliation PASS and `network_used=false`. Two real runs compared 16
  artifacts with logical digest
  `4ddb72f6ad05cdc75bf40834f5ec78d94b74586465e17b8737a23f496e9a7a14` and
  Rule007 remained 1 eligible event / 9 explicit gaps.
- Rule007 now has explicit states for the exact pair, issuer/exchange plus a
  designated supplemental source, issuer-only, exchange-only,
  designated-only, no retrieved official source, conflicting official sources,
  and incomplete/invalid evidence. Designated evidence is excluded from
  reconciled `input_fact_ids`.

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
