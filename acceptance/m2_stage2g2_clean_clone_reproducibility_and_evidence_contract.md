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

- Final pushed commit: `11884a92269f150bcddf5df0f71676c188348982` on
  `feat/m2-value-assessment-mvp`; local/origin tracking refs are equal (`0 0`).
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
- GitHub Actions workflow is committed and locally validated; remote CI was not
  observable and is therefore `NOT OBSERVED`. Real provider data was not
  redistributed because redistribution rights were not asserted.

## Final verdict

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
and the A/H split gap. Remote GitHub Actions status is reported separately from
local workflow validation.
