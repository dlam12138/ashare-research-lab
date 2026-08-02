# Stage 2G.2 reproduction guide

## Clean clone

From a clean checkout with Python 3.11:

```powershell
python -m pip install -e ".[dev]"
python -m ashare_research.tools.stage2g_reproducibility verify-contracts
python -m ashare_research.tools.stage2g_reproducibility verify-clean-clone
python -m ashare_research.tools.stage2g_reproducibility build-test-capsule --output tmp/stage2g2-local/capsule-a
python -m ashare_research.tools.stage2g_reproducibility build-test-capsule --output tmp/stage2g2-local/capsule-b
python -m ashare_research.tools.stage2g_reproducibility compare-capsules --left tmp/stage2g2-local/capsule-a --right tmp/stage2g2-local/capsule-b
python -m ashare_research.tools.stage2g_reproducibility run-test-capsule --capsule-dir tmp/stage2g2-local/capsule-a --output tmp/stage2g2-local/run-a --run-id stage2g2_local_ab
python -m ashare_research.tools.stage2g_reproducibility run-test-capsule --capsule-dir tmp/stage2g2-local/capsule-b --output tmp/stage2g2-local/run-b --run-id stage2g2_local_ab
python -m ashare_research.tools.stage2g_reproducibility compare-runs --left tmp/stage2g2-local/run-a/stage2g2_local_ab --right tmp/stage2g2-local/run-b/stage2g2_local_ab
pytest -q
ruff check src/ tests/
python -m compileall -q src
```

The capsule's market rows are deterministic synthetic test data. They are not
PetroChina provider data and must not be published into the real profile. The
temporary DuckDB is created inside the caller's capsule directory and is not a
repository input or committed artifact.

## Real local acceptance

Supply both real inputs explicitly. The registry's `object_key` values are
relative to the market root (`market-data/601857.SH` in the local cache layout):

```powershell
python -m ashare_research.tools.stage2g_reproducibility verify-real-inputs `
  --fact-db <canonical-db> `
  --market-cache-root <external-cache-root> `
  --output <preflight.json>
python -m ashare_research.tools.stage2g_reproducibility run-real `
  --fact-db <canonical-db> `
  --market-cache-root <external-cache-root> `
  --output <run-root> `
  --run-id stage2g2_real_local
```

The real path is offline after preflight. Missing or mismatched external files
produce an explicit `missing_external_research_input` or hash error; there is no
fallback to a tiny local Parquet file or to the test capsule. Reports are only
published with an explicit `--publish-reports`.

## Artifact checks

Every run writes `artifact_manifest.json`, `checksums.sha256` and
`reproducibility_report.json`. Paths are relative, all outputs are hashed, and
the verifier detects missing, extra or changed files. The manifest records
logical inputs, contract versions, hashes, row counts, network/default-DB
flags, evidence gaps and the not-started forbidden features.

The A/B commands deliberately build in separate directories and run in separate
directories. They compare capsule manifests/checksums, artifact manifests,
checksums, reproducibility reports and logical digests. A run directory or test
capsule cannot be overwritten; tampering or deletion fails verification. The
run ID and caller output root are excluded from the logical digest.

## Current evidence gaps

Only one bounded event currently satisfies the strict Rule007 pair. Nine
exchange payloads remain unavailable, the A/H split is not present in the
registered share-capital payloads, and real provider redistribution is not
claimed. The value profile remains descriptive and PIT-safe within its bounded
inputs. ROIC, scoring, target price, recommendation and market mechanism remain
unstarted.
