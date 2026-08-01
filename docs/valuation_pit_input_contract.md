# Valuation PIT input contract

The valuation runner consumes the existing `stock_daily` normalized model, a registered external market cache snapshot, the committed corrected dividend evidence ledger, the existing annual financial Fact fixtures, and the ordinary-share-capital timeline.

Market inputs must state provider, provider version, raw-response hash, date range, row count, `adjustment=none`, field units, and reconciliation status. Baostock and AKShare are acquisition providers, not exchange-official sources. The normalized snapshot must contain unadjusted close and must not create a second canonical market-observation downloader.

Financial inputs must carry Fact identity, fiscal period, unit/currency, source evidence IDs, and `available_at`. The runner selects the latest annual Fact with `available_at <= trade_date`; it never uses a report-period date as availability.

Dividend inputs must carry v2 event ID, superseded v1 ID, approval type, implementation announcement date, payment date, evidence status, and source evidence IDs. The announced and paid yields use distinct date predicates.

Share inputs distinguish A shares, H shares, total ordinary shares, effective date, currency, and evidence status. A-share close multiplied by total ordinary shares is a diagnostic called `a_share_price_implied_total_ordinary_equity_value`, not canonical market capitalization.

All missing or partial inputs remain explicit. The contract has no zero-fill convention and no opinion fields.
