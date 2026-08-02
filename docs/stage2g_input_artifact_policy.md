# Stage 2G.2 input and artifact policy

All paths in committed contracts are logical or repository-relative. A resolved
external path may exist only in the caller's process and must not enter a
manifest or report.

| Class | Commit? | Third-party data | Size/schema/hash | Formal runner | CI | Authority |
|---|---|---|---|---|---|---|
| Contract and evidence ledgers | yes | metadata and bounded evidence only | JSON contract, SHA-256 in run manifest | yes | yes | authoritative ledger |
| Canonical test snapshot | yes, bounded | bounded canonical read-model rows | v1 JSON, deterministic order, file SHA-256 | explicit test mode only | yes | export/read model, not source of truth |
| Synthetic test data | yes | no provider rows | fixed algorithm + CSV SHA-256 | explicit test mode only | yes | test-only |
| External real cache | no | provider data may be present locally | registry logical key + expected SHA-256 | explicit real mode only | no | external research input |
| Local canonical research DB | no | real research data | caller path and preflight hash | explicit real mode only | no | authoritative local input |
| Generated run artifacts | no by default | derived data only | run-scoped manifest and checksums | yes | must remain temporary | derived |
| Published reports | tracked only when explicitly published | derived summary only | report hash tied to run/input hashes | explicit `--publish-reports` | no | derived publication |

The canonical snapshot exporter opens the supplied database read-only, validates
canonical identity and version chains through the existing repository/PIT
interfaces, and writes atomically. The temporary builder uses the existing
repository schema and deletes with its temporary directory. No DuckDB binary is
committed.

Raw PDFs, raw provider responses, secrets, user names, drive letters, absolute
cache paths and private environment details are not committed.
