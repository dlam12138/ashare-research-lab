# Stage 2G.2 reproducibility contract

This contract makes the existing PetroChina PIT valuation slice portable and
auditable. It does not add a valuation metric, investment opinion, target price,
ROIC, scoring, Web, automatic trading, or market-mechanism implementation.

## Three input lanes

| Lane | Inputs | Allowed state | Consumer |
|---|---|---|---|
| Clean clone | committed JSON contracts, the canonical Fact read-model snapshot, and the deterministic synthetic CSV market series | no network, no default DB, no external cache | CI and ordinary tests |
| Test capsule | the same snapshot plus a temporary DuckDB built under a caller-owned temporary directory and the synthetic market registry | explicitly `test_capsule`; never a real-mode fallback | reproduction CLI |
| Real research | an explicitly supplied canonical Fact DB and an explicitly supplied external market-cache root | offline after preflight; hashes required; no downloads | local real acceptance only |

The committed Fact snapshot is a bounded canonical export/read model. It keeps
original Fact IDs, contexts, available dates, restatement lineage, source hashes,
verification fields and lossless decimal strings. It is not a second source of
truth and it is not a committed DuckDB binary.

## Threat model

The gates reject or make explicit:

- ignored `output/` or local DuckDB dependencies;
- machine-specific paths and private cache paths;
- default-DB mutation;
- test fixture fallback in real mode;
- stale or tampered snapshots;
- missing contexts and broken version chains;
- future-data leakage in PIT selection;
- source-pair substitution, including designated disclosure platforms used as
  the exchange side;
- hidden network access;
- unstable or unhashed output artifacts;
- reports whose input manifest no longer matches their outputs;
- raw responses, secrets and private paths entering committed contracts.

## Borrowed designs and cuts

`pytest` temporary directories provide per-test isolation. DuckDB is opened
read-only for real input and is rebuilt through the existing
`FactRepository` schema for a test capsule. Run metadata borrows the
OpenLineage shape of run/input/output datasets and checksummed facets without
adding a lineage service. GitHub Actions uses clean checkout and isolated
validation on Ubuntu and Windows with Python 3.11.

The project does not add pytest plugins, OpenLineage/Marquez services, data
catalogues, orchestration frameworks, network fetches, or redistributed
Baostock/AKShare raw responses. Synthetic market rows are generated from a
committed fixed algorithm and are labelled `synthetic_test_only`.

## CLI modes

```text
python -m ashare_research.tools.stage2g_reproducibility verify-contracts
python -m ashare_research.tools.stage2g_reproducibility build-test-capsule --output <tmp>
python -m ashare_research.tools.stage2g_reproducibility run-test-capsule --capsule-dir <tmp>
python -m ashare_research.tools.stage2g_reproducibility verify-real-inputs --fact-db <db> --market-cache-root <root> --output <manifest>
python -m ashare_research.tools.stage2g_reproducibility run-real --fact-db <db> --market-cache-root <root> --output <runs> --run-id <id>
```

`verify-contracts` and test-capsule mode are offline. Real mode fails closed
with `missing_external_research_input` when an explicit cache is absent or a
content hash does not match. It never reads `data/research.duckdb` implicitly.

## Explicit limits

The real market snapshots remain external because provider redistribution terms
are not asserted by this repository. The current bounded evidence ledger has
one exact eligible issuer/exchange Rule007 event and nine exchange retrieval
gaps. The A/H share split remains an evidence gap. These limits remain visible
in manifests and reports.
