# Goal: diagnose FRED transport and continue evidence acquisition

## Objective and baseline

User authorized diagnosis and continued operations after the PR #28 handoff.
PR #28 was independently checked (42 successful checks, clean diff, exact head)
and merged as `9c9ced90d109437b937cfcaa069388689db636f5`.
Branch: `codex/m4-fred-transport-diagnosis`, based on that origin/main commit.
Worktree was clean. Protected M2 HEAD is `3679b1bac7a1634c6452784a4d8f6d139966f222`;
stash is `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256 is
`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Allowed scope and required behavior

This Goal, a matching work record, diagnostic evidence JSON, and ignored tmp
tooling/raw evidence only. Continue the existing approved FRED HTTPS GET scope
with one newly authorized diagnostic run: terms, legal, series, at most once
each; 15 seconds total per request, zero retries, >=15 seconds start spacing,
1 MiB total response body ceiling, no credentials or redirects. Instrument
proxy connection, TLS, response headers and body separately. Preserve prior
ledgers. Do not infer the historical timeout phase from a new measurement.
No CSV until licence and identity gates pass; this diagnostic run excludes CSV.
Use existing local proxy configuration without changing system settings.

## Forbidden scope and stop conditions

No provider substitution, new endpoints, disabled certificate verification,
database engine access, research/holdout use, historical evidence edits,
direct main push or force push. Stop acquisition if licence evidence is absent.
An exhausted diagnostic run is not permission for an automatic retry.

## Validation and acceptance

Validate ledger phase/status/elapsed/bytes, unique endpoints, intervals, ceiling,
raw SHA256 if retained, protected baselines, exact diff and clean working tree.
Commands: `python tmp/m4-provider-evidence-v2/diagnose.py`,
`git diff --check`, `git diff --cached --check`,
`Get-FileHash -Algorithm SHA256 D:\量化分析\data\research.duckdb`,
`git status --short --branch`, `git ls-remote origin`.
Acceptance requires an evidence-backed diagnosis distinguishing observations
from hypotheses; successful data acquisition is a separate gate.

## Delivery

Commit the Goal, work record and diagnostic JSON; push only the named topic
branch and open a reviewable PR. No automatic merge of the new PR.

## Authorized continuation: route comparison

The user's subsequent instruction to continue follows the proposed comparison
of network exits. Preserve run 01. Permit one diagnostic comparison with two
GET requests to the already approved `/docs/api/terms_of_use.html`: one with
the explicit application proxy disabled, one through the existing localhost
proxy. Each is a distinct test condition, not an automatic retry. Use curl
with default config disabled, verified TLS, no redirects, no credentials,
15-second wall-clock max-time, 524288-byte per-response ceiling (1048576 total),
and >=15 seconds between starts. Do not change global proxy settings or nodes.
The direct condition may still traverse system/TUN routing and must be named
explicit-proxy-bypassed, not asserted to be a physically independent exit.
Add `evidence/m4/fred_route_comparison_01.json`, preserve bounded output under
ignored tmp/quarantine, update this Goal and the existing record in PR #29.
Validate curl exit/status/timings and body sizes; stop after the two conditions.

## User-switched proxy node continuation

User explicitly reported switching to another proxy node. Authorize a fresh
conditional three-request run through the existing local proxy: terms first;
legal and series only if terms returns HTTP 200. Each endpoint once, no retry,
15-second curl wall-clock timeout, >=15-second start spacing, HTTPS verified,
no redirects or credentials, 1048576-byte total body budget. Preserve previous
evidence. Add `evidence/m4/fred_changed_node_01.json`; use ignored temporary
output and SHA-addressed quarantine for complete successful responses. Stop
on terms failure. No CSV or global network configuration edits. Record node
change as user-reported, not as proof of a distinct public IP.

## Explicit repair-verification approval

After the telemetry error, the user confirmed one verification with the fixed
tool. Baseline is `833b965e0fccce751ffcab3fa350dffa1e45c371`, clean and synced.
One GET to `/docs/api/terms_of_use.html` only, existing local proxy, 15000 ms,
zero retries, 1048576 body bytes maximum, verified HTTPS, no redirects or
credentials. Persist stdout/stderr before parsing; do not overwrite prior
ledgers. Add `evidence/m4/fred_changed_node_02.json` and update this Goal/record.
Run `python tmp/m4-provider-evidence-v2/test_changed_node.py` before
`python tmp/m4-provider-evidence-v2/changed_node.py`; independently compare
saved metrics with the ledger. Retain complete successful bytes by SHA256.
Stop after this one request; no automatic legal/series/CSV. Deliver on PR #29.
