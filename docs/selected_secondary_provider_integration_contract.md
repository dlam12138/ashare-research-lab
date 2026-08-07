# Selected Secondary Provider Integration Contract

M2 Stage 2K.1R4E.4 — formal integration of `tencent_via_akshare` as the
secondary market provider, registry v4, formal dual-source reconciliation and
the non-production PIT PE/PB/PS candidate v2 release.

## references_reviewed

- R4E.3 `docs/alternative_secondary_market_provider_preflight.md` — the bounded
  preflight that selected `tencent_via_akshare` (transport `akshare`, underlying
  `tencent`, endpoint `web.ifzq.gtimg.cn`, object `d760923a…`, table digest
  `e6cbee88…`, 1351 rows, 2021-01-04..2026-07-31).
- R4E.2 `docs/versioned_market_reacquisition*.md` (as recorded in the R4E series)
  — the versioned Baostock reacquisition that pinned `c6771aa5…` as the primary.
- R4E.1 `docs/*market*reconciliation*` — the dual-source reconciliation contract
  v1 and the series release gate.
- DuckDB ASOF JOIN semantics (used by the existing `temporal_join` oracle) —
  backward lookup, one-right-row-per-left-row, never forward/nearest.

## borrowed_designs

- **transport_library / underlying_provider separation** (from R4E.3): AKShare
  is only a calling tool; Tencent is the actual underlying provider.  Carried
  into the registry v4 provider entries.
- **provider-role resolution instead of provider-name contracts** (from the
  R4E.1/R4E.2 release path): the formal path resolves exactly one `primary` and
  exactly one `secondary` by role, fail-closed on 0 or >1 of either.
- **content-addressed immutable objects** (from R4E.2/R4E.3): SHA-256 pin +
  immutable registry version; the R4E.3 selected object is promoted byte-identical.
- **DuckDB ASOF backward semantics** (from R4E.1): the candidate PIT join matches
  a trade day to the most recent financial state at or before that day; the
  Python sweep + DuckDB oracle are both retained and must agree.

## why_applicable

- The free, independent Tencent daily source was proven in R4E.3 to match the
  pinned Baostock primary exactly (1351/1351 days, max close diff 0,
  adjustment TRUSTED), so formally integrating it as the secondary closes the
  R4E.1/R4E.2 gap where the AKShare/Eastmoney secondary was blocked.
- A registry v4 with role-based provider entries removes the hard-coded
  `primary=baostock / secondary=akshare` business contract from the formal
  release path while keeping legacy registries readable.
- The v2 reconciliation digest binds the provider-role identity so the candidate
  observation identity reflects the real dual-source provenance.

## not_copied

- No large generic provider plugin framework was introduced; provider resolution
  lives in one small `provider_roles` module.
- No new database, no large object store: the formal cache is the external
  content-addressed parquet cache already used by R4E.2/R4E.3.
- No forward/nearest ASOF join was introduced; the PIT time semantics are
  unchanged.
- No percentile, no scoring, no peer acquisition, no M3.

## repository_specific_cuts

- **Role-based provider modelling**: registry v4 entries carry `provider_id`,
  `provider_role`, `transport_library`, `underlying_provider`; legacy v2/v3
  entries keep the `provider` name and are adapted via a read-only compatibility
  map (`baostock -> primary`, `akshare -> secondary`).  Old registries are never
  modified and historical digest contracts are preserved.
- **v1/v2 reconciliation split**: the v1 contract
  (`pit_valuation_market_double_source_reconciliation_v1`) remains the
  historical contract; the v2 contract binds the role identity and the daily
  comparison digest.  The economic comparison is provider-name independent.
- **Only the formal dual-source path** was upgraded; the data-provider layer was
  not refactored.
- **Promotion, not re-acquisition**: the R4E.3 selected Tencent object is located
  in the preflight cache, identity-verified, and copied byte-identical into the
  formal external cache.  No pointless re-request; no Sina fallback.
- **Registry v4 is staged**: a draft (`PENDING_REAL_RECONCILIATION` /
  `reconciliation_status=pending`) is written first; it is frozen to `COMPLETE` /
  `pass` only after the real formal reconciliation passes.