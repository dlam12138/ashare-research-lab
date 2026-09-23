# Goal: bounded FRED HTTP/2 evidence acquisition

## Objective and baseline

After native Chromium proved the exact FRED terms path reachable over HTTP/2,
the user instructed continued project progress. Acquire immutable first-party
response-body bytes for the three already approved evidence endpoints using a
bounded HTTP/2 client. This is a new explicitly authorized continuation run;
it does not reuse a consumed request or alter historical ledgers.

- Branch: `codex/m4-fred-transport-diagnosis`.
- Initial HEAD: `9238eebb40248a34059dfc7261b9a9bc19c165d3`.
- Base main: `9c9ced90d109437b937cfcaa069388689db636f5`.
- Existing authorization digest:
  `c20d955cc9875b1365b3989cd2ceba018e4223adc6726beba89d2a24bb23e45b`.
- Contract digest:
  `b5f6b8d54f5fe733d41ed018a89b3065fc05a0e7130c072c66d19e469221bdca`.
- Protected M2 HEAD:
  `3679b1bac7a1634c6452784a4d8f6d139966f222`.
- Protected stash:
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Protected database SHA256:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Allowed scope and envelope

Tracked writes: this Goal, matching record, one acquisition ledger JSON, and
only evidence artifacts supported by successful retained bytes. Ignored helper
under tmp and SHA256-addressed raw bodies under the existing v2 quarantine.

Exactly one HTTPS GET per path, in this order:

1. `/docs/api/terms_of_use.html`
2. `/legal/`
3. `/series/DCOILBRENTEU`

Use `fred.stlouisfed.org` only, existing localhost proxy, verified TLS with
ALPN exactly `h2`, no credentials/cookies, no redirects, no retry/pagination,
15-second total deadline per endpoint, at least 15 seconds between request
starts, maximum three requests, and 1048576 response-body bytes total. Request
`accept-encoding: identity`. HTTP/2 DATA payload bytes are retained before any
text decoding and identified by SHA256. Record status, final path, ALPN, TLS
certificate digest, response-header digest, body length/hash/locator and exact
timings. Stop the run on any failed endpoint or byte/deadline violation.

No CSV in this run. No database, holdout, statistics, adapter or research use.
Do not create a licence artifact until retained terms/legal bytes have been
reviewed for the intended private evidence-only retention/use. Documentation
cannot override contrary terms. Series bytes may establish endpoint identity
only after content review.

## Validation and acceptance

Before network: syntax check and DSH bounded read-only review of this Goal and
helper. After network: duplicate-key/no-float parsing for tracked JSON,
endpoint/order/count/spacing/deadline/rate checks, raw SHA/length/locator and
header digest checks, encoding checks, exact tracked scope, `git diff --check`,
protected Git/database state, and DSH final evidence review. Acceptance is
retained first-party evidence or an accurately recorded fail-closed outcome.

## Delivery and stop

Commit scoped tracked paths, push the existing topic branch and update PR #29.
Do not merge PR #29, request CSV, start adapters/research, push main, force-push
or broaden endpoints without a later explicit stage authorization.
