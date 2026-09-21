# M4 provider-evidence acquisition report v1

Status: bounded, fail-closed evidence review. No provider is selected and no
dataset observation endpoint was called.

## Disposition

The manifest contains exactly four `M4_PROVIDER_EVIDENCE_DOSSIER_V1` entries;
all are `REJECTED`. The retained bytes are private, ignored, content-addressed
documentation responses only.

* `baostock_trade_calendar` — the BaoStock first-party landing page
  <https://baostock.com/> returned HTTP 200 and was retained. The older
  documentation URL <https://baostock.github.io/baostock/> returned HTTP 404.
  Neither response proves a current calendar method, authoritative version or
  bounded transport.
* `baostock_target_daily` — the same landing page and 404 documentation
  response were retained; the history endpoint was not called because
  observations are forbidden. Bounded transport, PIT, rights and licence gates
  therefore remain unproven.
* `cninfo_historical_issued_shares` — CNINFO first-party landing page
  <https://www.cninfo.com.cn/new/index> was retained. AkShare documentation
  <https://akshare.akfamily.xyz/data/stock/stock.html#stock-share-change-cninfo>
  is retained only as third-party-declared transport metadata. Neither page
  proves dataset semantics, PIT timing, complete history, rights or retention;
  the CNINFO endpoint was not called.
* `eia_brent_oil_transport` — EIA official petroleum page
  <https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm> was retained. FRED’s
  first-party series URL <https://fred.stlouisfed.org/series/DCOILBRENTEU>
  timed out within the bounded request and no response bytes were retained.
  The FRED CSV observation endpoint was not called.

These are observed retrieval facts; they do not establish provider suitability.
The rejection codes and every mandatory null are recorded in
`evidence/m4/provider_evidence_manifest_v1.json`. Documentation alone cannot
produce `EVIDENCE_COMPLETE`; no calendar, membership, factor or market
observation data was acquired.

## Boundary and unresolved evidence

No credentials, login, provider contact, forms, database, holdout, code,
adapter, tests, real-data validation, statistics or study execution were used.
License artifacts with exact content hashes, permitted-use/redistribution
scope, retention/display constraints, source-side publication/availability
timestamps, dataset-window date scans, revisions/vintages and PIT evidence
remain unresolved. The next stage is not authorized.

Raw response locators, response SHA256/length/status/media type, retrieval time,
redirect chain, header digest, credential class and request-shape digest are
recorded per retrieval item in the manifest. Raw bytes are not committed or
quoted wholesale.
