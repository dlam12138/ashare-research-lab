# Goal: M4 provider-evidence acquisition v2 retry

Date: 2026-09-22. After PR #27 merged, the user explicitly authorized one
new bounded FRED evidence run and instructed continuous progress within this
round until the stage requirement is met or a contract stop condition occurs.
The parent agent owns all network and Git actions. DSH performs bounded
read-only preflight and final review; it must not recurse, contact providers,
modify files or fall back to Luna.

## Objective and verified baseline

Acquire current first-party FRED terms and series-identity evidence within the
new authorization. If every mandatory pre-probe gate passes, perform exactly
one evidence-only bounded CSV probe for `DCOILBRENTEU`, retain immutable raw
bytes, construct the exact transport proof and terminal v2 dossier, and stop
before any adapter, database, holdout, statistics or research use.

- Worktree: `D:/量化分析-m4-provider-evidence-acquisition-v2`.
- Branch: `codex/m4-provider-evidence-acquisition-v2-retry`.
- Base/initial HEAD: `origin/main@6c76e6f63679c5751349bf19c06ccbf58f3427b6`
  (PR #27 merge).
- Contract digest:
  `b5f6b8d54f5fe733d41ed018a89b3065fc05a0e7130c072c66d19e469221bdca`.
- Prior authorization digest:
  `22e9cea6118f844587a3b9e7f50b66b3912692e13198037b13c2fb6327e0d67f`.
- Prior outcome: `BLOCKED / REAL_LICENSE_EVIDENCE_MISSING`; the dossier ID
  `eia_brent_oil_transport_v2_probe_01` remains unused.
- Existing ignored EIA first-party reuse artifact: 52,317 bytes, SHA256
  `4758216ebe7e50dc7a62b97234b4d208c3d48ffc92f1a0b81f1c78d26508b8d6`.
- Protected M2 HEAD:
  `3679b1bac7a1634c6452784a4d8f6d139966f222`.
- Protected stash:
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Protected database SHA256:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Explicit authorization envelope

- state: `ACQUISITION_V2_EXPLICITLY_AUTHORIZED`
- approved host: `fred.stlouisfed.org`
- approved endpoints, one request each in this run:
  `/docs/api/terms_of_use.html`, `/legal/`, `/series/DCOILBRENTEU`, and,
  conditionally, `/graph/fredgraph.csv`
- approved dossier ID: `eia_brent_oil_transport_v2_probe_01`
- requested CSV query: series `DCOILBRENTEU`, start `2015-03-09`, end
  `2015-03-13`, fields `DATE` and `DCOILBRENTEU`
- HTTPS GET only; no credentials, cookies or authorization headers
- timeout `15000` ms, retry count `0`, at most `4` requests per minute and
  exactly four possible requests in the run; no pagination
- response ceiling `1048576` bytes per request
- raw retention approved below ignored
  `data/quarantine/m4_provider_evidence_v2/`
- returned values are evidence-only and cannot enter research, database or
  holdout flows

The approval does not include another host, endpoint, method, retry, redirect
outside the exact allowlist, fallback provider or larger response.

## Allowed scope

Tracked writes are limited exactly to:

- this Goal;
- `evidence/m4/provider_evidence_authorization_v2_retry_01.json`;
- `evidence/m4/provider_licence_artifacts_v2.json` only if the licence gate can
  be supported by retained first-party bytes;
- `evidence/m4/provider_evidence_dossier_v2.json` only if the CSV probe runs;
- `agent/record/2026-09-22_02_m4-provider-evidence-acquisition-v2-retry.md`;
- `acceptance/2026-09-22_m4_provider_evidence_acquisition_v2_retry.md`.

Raw responses may be written only under the ignored v2 quarantine namespace,
named by lowercase SHA256. Temporary tooling may exist only under ignored
`tmp/` and is never staged. Reading tracked evidence and Git metadata and
hashing the database as bytes are allowed.

## Forbidden scope

No credentials, POST, pagination, automatic retry, fifth request, off-list
redirect, response over 1 MiB, undeclared CSV field, date outside the approved
window, provider substitution, adapter/source/product/test/CI/config/dependency
change, database open/query/write, holdout access, statistics, aggregation,
research execution, raw-byte quotation over 25 words, v1 mutation, direct main
push, force-push, merge or next-stage start.

## Required behavior and stop conditions

1. Persist a new deterministic authorization artifact before network access.
2. Attempt the three first-party evidence endpoints once each. Retain only
   successful immutable bytes, exact URL/status/size/SHA and bounded metadata.
3. Licence evidence must explicitly support the intended private evidence-only
   retention/use. EIA evidence cannot substitute for FRED terms; documentation
   cannot override terms. Missing, contradictory or unclear scope stops before
   CSV with `REAL_LICENSE_EVIDENCE_MISSING` or
   `REAL_LICENSE_SCOPE_FORBIDDEN` as applicable.
4. Current series identity must be retained from the exact approved FRED path.
   Timeout, redirect or ambiguity stops before CSV with
   `REAL_ENDPOINT_UNBOUNDED`.
5. Only if all pre-probe gates pass, request the exact CSV query once. Reject
   redirects; stream with the byte ceiling; atomically retain SHA256-named raw
   bytes; record method/host/endpoint, window, fields, timeout/retry/rate,
   response date extrema and counts, undeclared fields, raw identity/locator,
   headers digest and exact `proof_digest`.
6. Any ambiguous/unparseable date, date outside `2015-03-09..2015-03-13`, date
   in `2015-03-16..2022-12-30`, date on/after `2023-01-01`, or undeclared field
   fails closed under the contract mapping. No value is interpreted.
7. A dossier, if created, uses the approved new ID and exact predecessor ID
   `eia_brent_oil_transport` with digest
   `b748ac51d7bb3e22b8b42c444404183d3a1d7a1b44065f92b87870cbbc5cf9b2`.
8. Stop on any need to broaden authorization or weaken a gate. A successful
   dossier does not authorize adapter or research work.

## Validation, acceptance and Git boundary

Run strict duplicate-key/no-float parsing, canonical JSON/digest checks, exact
authorization comparison, raw locator/SHA/length checks, licence resolution,
lineage and proof-digest checks, CSV structural/date firewall checks if a probe
runs, encoding/link/secret/path scans, `git diff --check`, exact staged-path
review, worktree/stash/M2/database protection checks, and DSH final read-only
review. Record actual commands and outcomes.

The parent may commit the exact allowed tracked paths, push only with
`git push origin HEAD:refs/heads/codex/m4-provider-evidence-acquisition-v2-retry`
and open one PR. Do not merge or start adapter/research work without new
explicit authorization. Final verdict is exactly `PASS`, `CHANGES_REQUIRED`
or `BLOCKED`.
