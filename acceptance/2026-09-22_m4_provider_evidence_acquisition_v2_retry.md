# M4 provider-evidence acquisition v2 retry acceptance

Verdict: `BLOCKED`.

## Goal, baseline and authorization

- Goal: `../agent/goals/2026-09-22_m4_provider_evidence_acquisition_v2_retry.md`.
- Base: `origin/main@6c76e6f63679c5751349bf19c06ccbf58f3427b6`.
- Branch: `codex/m4-provider-evidence-acquisition-v2-retry`.
- Authorization: `../evidence/m4/provider_evidence_authorization_v2_retry_01.json`.
- Authorization digest:
  `c20d955cc9875b1365b3989cd2ceba018e4223adc6726beba89d2a24bb23e45b`.
- Contract digest:
  `b5f6b8d54f5fe733d41ed018a89b3065fc05a0e7130c072c66d19e469221bdca`.
- Prior authorization digest:
  `22e9cea6118f844587a3b9e7f50b66b3912692e13198037b13c2fb6327e0d67f`.

The user explicitly authorized one new run containing three first-party FRED
licence/identity requests and a fourth CSV request only if every mandatory gate
passed. Each endpoint was limited to one HTTPS GET, 15,000 ms, zero retries,
15-second minimum request-start spacing, four requests per minute, no
credentials or pagination and a 1 MiB total response budget. Returned values
were evidence-only.

## DSH preflight

DSH returned `PASS`. It independently verified the branch/base, canonical
contract and authorization digests, all eleven required authorization fields,
the four-request envelope, unused dossier ID, terminal predecessor identity,
the ignored EIA raw identity, stash, protected M2 HEAD and database SHA256.

Before network access, the parent applied all DSH execution conditions:

- narrowed the ignored helper allowlist to exactly the four FRED paths;
- enforced endpoint uniqueness, four-request count, 15-second spacing, the
  stricter 1 MiB total budget and the exact conditional CSV query;
- clarified that this is one authorized run with `retry_count=0`.

DSH self-reported one deviation: it attempted `git ls-remote` despite its
no-network brief. Credential acquisition failed before data exchange; no
provider endpoint was contacted and no repository state changed. The parent
does not treat that failed GitHub attempt as provider evidence.

## Actual requests and immutable evidence

The ignored request ledger contains exactly three attempts and zero successful
response bytes:

| UTC start | Approved endpoint | Result | Retry | Retained bytes |
|---|---|---|---:|---:|
| 05:46:57 | `/docs/api/terms_of_use.html` | 15 s `TimeoutError` | 0 | 0 |
| 05:47:23 | `/legal/` | 15 s `TimeoutError` | 0 | 0 |
| 05:47:48 | `/series/DCOILBRENTEU` | 15 s `TimeoutError` | 0 | 0 |

All start intervals exceed 15 seconds. The canonical ignored ledger is 629
bytes with SHA256
`acbb16e3165bc57743a6a7a7c8e69ba6a57d9a63939cf1c82efe51d534ca1674`.
No response body, redirect, status page or FRED raw file was received or
retained.

The prior EIA raw file remains the only v2 quarantine response: 52,317 bytes,
SHA256
`4758216ebe7e50dc7a62b97234b4d208c3d48ffc92f1a0b81f1c78d26508b8d6`.
It remains ignored and unchanged, and it is not used as a substitute for FRED
licence or identity.

## Fail-closed decision

FRED licence and current series-identity mandatory gates are unproven. The
fourth endpoint, `/graph/fredgraph.csv`, was not requested. Therefore no
observation value, response date, development-period or holdout data was
received, scanned, stored or interpreted.

The stage stops with `REAL_LICENSE_EVIDENCE_MISSING`; endpoint identity is also
unproven. No `provider_licence_artifacts_v2.json` or
`provider_evidence_dossier_v2.json` exists, and the approved dossier ID
`eia_brent_oil_transport_v2_probe_01` remains unused. There was no mirror,
third-party substitution, credential, retry, database access, holdout access,
statistics, adapter work or research execution.

## Validation and protected state

The parent validation covers:

- strict duplicate-key/no-float parsing and canonical recomputation of the
  contract, prior authorization and retry authorization digests;
- exact equality of hosts, endpoints, dossier ID, dates, fields, timeout,
  retry, rate, method, credentials, total byte limit, retention and
  evidence-only acknowledgement;
- exact ledger attempt count/order, start spacing, zero successful bytes and
  ledger SHA256;
- EIA raw size/SHA/ignore status and absence of any new raw response;
- absence of licence artifact and dossier;
- UTF-8/LF/no-BOM checks, secret/path scans, `git diff --check`, exact scoped
  path review, worktrees/stash/M2/database checks;
- final bounded DSH read-only review.

At post-request review:

- working HEAD and `origin/main` remained
  `6c76e6f63679c5751349bf19c06ccbf58f3427b6`;
- protected M2 HEAD remained
  `3679b1bac7a1634c6452784a4d8f6d139966f222`;
- stash remained
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`;
- database SHA256 remained
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.

## Scope, synchronization and next-stage authority

Tracked changes are limited to the Goal, new authorization, record and this
acceptance file. No product, test, CI, dependency, configuration, database,
contract, prior authorization, v1 evidence or historical acceptance changed.
Ignored raw and temporary files will not be staged.

The final bounded DSH read-only review returned `PASS`. It independently
recomputed the canonical digests, verified all eleven authorization fields,
reconciled the three timeout attempts and request spacing, confirmed that CSV
was not requested, and rechecked the protected M2 HEAD, stash, database hash,
EIA raw identity and absence of conditional artifacts. The reviewer made no
file or network changes and confirmed the fail-closed `BLOCKED` outcome.

The exact four scoped paths were committed as `7b65bb5` (`docs: record blocked
FRED evidence retry`) and pushed to
`origin/codex/m4-provider-evidence-acquisition-v2-retry`. PR #28 was opened at
https://github.com/dlam12138/ashare-research-lab/pull/28. A documentation-only
handoff commit records this delivery evidence; the PR remains unmerged while CI
is monitored.

Merge, another network run, adapter work and research execution are not
authorized. Further progress requires a new explicit authorization or a change
in the external FRED transport condition.
