# M2 Stage 2F.1 dividend evidence correction acceptance

Date: 2026-08-01
Contract: `agent/goals/2026-08-01_m2_stage2g_dividend_correction_and_valuation_profile.md`

## Phase A result

`PASS WITH EXPLICIT GAPS`.

The corrected v2 ledger contains all 10 2021–2025 interim/final events and 20 exact source locators. Each event retains its v1 identity through `supersedes_event_id`; the v1 ledger remains unchanged. Source types are not relabelled: issuer URLs are `issuer_official`, SSE URLs are `exchange_official`, and no CNINFO/designated-disclosure URL is called issuer official.

| Fiscal event | Issuer payload | Exchange payload | Result |
|---|---|---|---|
| 2021 interim/final | real PDF hashes | exact locator, endpoint challenge | issuer-only, gap |
| 2022 interim/final | real PDF hashes | exact locator, endpoint challenge | issuer-only, gap |
| 2023 interim/final | real PDF hashes | exact locator, endpoint challenge | issuer-only, gap |
| 2024 interim | real PDF hash `5b66e02d…e70211` | real PDF hash `20406d62…9b220` | dual-official eligible |
| 2024 final | real PDF hash | exact locator, endpoint challenge | issuer-only, gap |
| 2025 interim/final | real PDF hashes | exact locators, endpoint challenge | issuer-only, gaps |

There are 11 real content SHA-256 hashes and 9 missing exchange payloads. Locator hashes are stored only as locator hashes. No URL hash is used as a content hash. The six anti-bot HTML challenge responses are excluded from evidence and are not committed. The one dual-official event has independently extracted numeric values, CNY, ordinary-share scope, and distinct content hashes; `same_content_mirror=false`.

The only eligible corrected event is `dve2_6817eeec70d11eeba283eab9` (2024 interim). Its six source Facts are in the run-scoped `rule007_facts.json`; the three reconciled v2 Facts are:

- `reconciled_div_fact_82484456cc965e8fe5f00751`
- `reconciled_div_fact_87fe4a80bf0124be020d3c39`
- `reconciled_div_fact_e63b169496fc6d6d8abc76e9`

The values satisfy the existing numeric/dividend relation and are kept separate from issuer-only events. The finite gaps block only affected dividend inputs; non-dividend valuation continues.

## Corrected event semantics

Interim records use `approval_type=prior_shareholder_authorization` and `prior_authorization_is_event_specific=false`; final records use `shareholder_approval`. The v2 chronology allows prior authorization before proposal, then proposal ≤ implementation publication ≤ payment. `event_status_as_of()` returns `implementation_announced` after publication and `payment_completed` only on/after payment. There is no `implemented` or `paid/implemented` v2 state.

## Protected invariants

The pre-Stage2F baseline remains frozen at 354 Fact, 102 Metric Result, and 16 definitions. The Stage2F additive 90 Facts/20 Results are historical and are not silently rewritten. ROE/ROA, financial safety, Identity/PIT gates, stash, and default database remain protected. Default DB SHA-256 remains `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Phase A gate

`PASS WITH EXPLICIT GAPS`: no numeric conflict, share-scope conflict, currency ambiguity, or source-identity hard stop was found. Exact URLs and evidence metadata are committed in `events/dividend_source_evidence_2021_2026.json`; PDFs remain external at `D:/量化分析-cache/official-dividend-docs`.
