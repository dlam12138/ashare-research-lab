# Alternative Secondary Market Provider Preflight — Design Reference

M2 Stage 2K.1R4E.3. This document records what was reviewed and borrowed from
upstream provider conventions, why each borrowed design applies here, what was
deliberately **not** copied, and the repository-specific cuts made so the result
fits the existing PIT valuation series contract.

## references_reviewed

- AKShare Tencent interface (`stock_zh_a_hist_tx`): specified-date, unadjusted
  (`adjust=""`) daily OHLCV semantics.
- AKShare Sina interface (`stock_zh_a_daily`): historical daily, unadjusted
  (`adjust=""`) semantics.
- Pytdx: daily K-line query and explicit pagination over TongdaXin quote servers.
- Tushare: tokenised API contract (credential-gated daily bar access).
- The existing R4E.2 versioned acquisition contract
  (`config/pit_valuation_market_snapshot_acquisition_v1.json`) and the pinned
  Baostock primary object (`c6771aa5…`).

## borrowed_designs

- **Specified-date, unadjusted daily semantics** from AKShare Tencent — the
  candidate is pinned to `start_date=20210101`, `end_date=20260731`, `adjust=""`
  so it is directly comparable to the Baostock `adjustflag=3` primary.
- **Historical daily + unadjusted** from AKShare Sina — same frozen window and
  `adjust=""`, comparable to the primary.
- **Daily K + explicit pagination** from Pytdx — chunks are validated for
  overlap/gap/ordering and a single run pins one server; it mirrors the
  repository's strict, auditable ordering contract.
- **Tokenised API contract** from Tushare — a credential gate is modelled as a
  first-class preflight state (`credential_not_available`), not as a silent skip.

## why_applicable

The R4E.2 pipeline is fail-closed: a secondary source is only usable if it is a
real, independent, unadjusted daily series that fully covers the 1351 required
trade days and matches the Baostock closes within 0.01 CNY/share. These borrowed
conventions (frozen window, unadjusted, explicit pagination, explicit credential
gate) are exactly what lets a candidate be compared byte-for-byte against the
pinned primary under the repository's canonical Decimal rules.

## not_copied

- **AKShare's float identity representation** — the repository forbids float repr
  in business identity; all OHLC/amount are canonical `Decimal(str(...))`.
- **Pytdx automatic server selection and opaque fallback** — the repository pins
  one server per run and records the actual server address; no silent switch.
- **Tushare's credential storage** — no token is ever written to config, logs,
  reports or Git.
- **The SSE paid historical-data product** — free-data-first is preserved.
- **Any provider's default "already adjusted" judgement** — adjustment is always
  explicitly pinned to `none` and verified against company-action windows.
- **Any ready-made PE/PB/PS field** — this preflight only concerns daily market
  bars; valuation ratios remain the business of the PIT valuation series.

## repository_specific_cuts

- **Unified canonical row** (`symbol`, `trade_date`, OHLC, `volume`, `amount`,
  `is_trading`, `adjustment`, `transport_library`, `underlying_provider`,
  `provider_version`, `endpoint_identity`) so every candidate is comparable to the
  Baostock primary and to each other.
- **transport_library vs underlying_provider are kept separate** — AKShare is only
  a calling tool; Tencent/Sina are the actual underlying providers. Independence
  is judged on the underlying provider and endpoint host, not the function name.
- **Permitted network surface** is limited to `probe`/`acquire`; `verify-contracts`,
  `compare` and `fixtures` are fully offline.
- **CI uses synthetic fixtures only** (`evidence_class =
  SYNTHETIC_ENGINEERING_ONLY`); a real provider selection can only come from a real
  local preflight.