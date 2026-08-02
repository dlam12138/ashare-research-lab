# M2 Stage 2G.2 clean-clone reproducibility and evidence contract

Status: **in progress**

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

## Explicit limits

Real market data is not redistributed because provider redistribution rights are
not asserted. The bounded evidence ledger retains nine exchange retrieval gaps
and the A/H split gap. Remote GitHub Actions status is reported separately from
local workflow validation.
