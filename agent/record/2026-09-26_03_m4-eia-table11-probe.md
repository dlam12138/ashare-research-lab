# Table 11 evidence probe

Goal: agent/goals/2026-09-26_m4_eia_table11_probe.md.
Base ff72a16, branch codex/m4-eia-archive-table11. Protected baseline verified.
Plan: resolve real link from official landing page, make one bounded request,
retain exact bytes encrypted, inspect metadata without disclosing values.
Spreadsheet skill read-only guidance applies: no workbook edits/exports and
no raw value displays. Existing seal/unseal/DPAPI functions reused without
modifying or replaying the predecessor probe. New request ledger is separate.

## Executed requests and retention

The web directory lookup failed before local acquisition. One local landing GET
at 2026-09-26T05:44:24.778Z retained 61,777 bytes. Its real Table 11 link was:
https://www.eia.gov/petroleum/supply/weekly/archive/2015/2015_03_18/csv/table11.csv

One CSV GET at 2026-09-26T05:44:49.976Z retained 2,669 bytes, elapsed 634 ms.
Both passed the transport's exact HTTP 200 check. Local body total 64,446 bytes;
start separation 25.198 seconds; no redirects followed or retries performed.
CSV SHA256: 552aafb7ddb97cd00c7f63af8a0f2ae07613d9fa1617035829123a6c7febb864.
Exact bytes are AES-256-GCM retained under ignored data/quarantine/m4_eia_table11_01,
with a separate Windows DPAPI CurrentUser wrapped key. No API key was accessed.

## Structural finding

CSV parses as 21 records, varying widths 16/15/1. Header columns after four
STUB identifiers are Jan..Dec; first-column year labels are 2014 and 2015.
Brent text is present; RBRTE text and slash/ISO full-date tokens are absent.
This is monthly-layout material, not the required five daily observations.
No monthly value is converted into daily data. No price is printed or tracked.
Issue date and archive URL do not establish first-publication, availability or
immutable vintage. This CSV candidate does not resolve the strict-PIT gap.
No other table, PDF, CSV or API request was made. Request allowance exhausted.

## Validation and review

`node --test agent/tools/eia_archive_probe.test.cjs`: seven tests cover same-issue
link resolution, denied targets, ambiguity, CSV quoting/malformed data, numeric
value suppression and monthly-versus-daily classification.
`node agent/tools/eia_archive_probe.cjs verify`: both encrypted raw hashes checked.
`node agent/tools/eia_archive_probe.cjs inspect`: metadata-only result above.
`python agent/tools/validate_eia_artifacts.py`: predecessor integrity passed.
`git check-ignore data/quarantine/m4_eia_table11_01/key.dpapi`: ignored as intended.
Scoped DSH read-only transport review reported PASS, explicitly not reviewing
imported crypto primitives or claiming automated network-boundary test coverage.
Parent inspected the imported primitives and later CSV inspection changes.
No production-adapter or complete network test suite is claimed.

## Delivery and stopping point

Five added files: Goal, this record, probe, synthetic tests, metadata ledger.
No predecessor file changes. Local commit only; no push/PR/merge authorized here.
Research gate remains closed. To investigate a different artifact requires a new
specific authorization; repeated fetching of this CSV cannot fix its granularity.
