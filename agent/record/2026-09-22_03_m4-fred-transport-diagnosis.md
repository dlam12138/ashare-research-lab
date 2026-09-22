# FRED transport diagnosis

User authorized diagnosis and continued project operations. Goal:
`agent/goals/2026-09-22_m4_fred_transport_diagnosis.md`.

Baseline: `origin/main@9c9ced90d109437b937cfcaa069388689db636f5` after
authorized PR #28 merge; new branch `codex/m4-fred-transport-diagnosis`.
Only diagnostic tools/evidence and this task's governance files are in scope.

Initial observations: previous helper used urllib's default proxy discovery.
It resolves HTTPS to local proxy 127.0.0.1:10808 without credentials.
DNS resolution succeeded. A bounded CONNECT/TLS-only check returned proxy
200 at 4 ms and verified TLSv1.3 at 814 ms; no provider GET was sent by that
check. Historical TimeoutError alone does not establish its failure phase.

Plan: instrument a new bounded request run, record phases without exposing
response values or proxy credentials, validate evidence, commit and push.

## Results and diagnosis

`python tmp/m4-provider-evidence-v2/diagnose.py` completed all three authorized
GET attempts once, without retries or redirects. Terms/legal/series reached
verified TLS at 318/340/166 ms from request start, respectively. All timed out
in the response_headers phase at 15004/15002/15005 ms; no HTTP status was
parsed and no response body was received or retained. Start spacing was
15.007 and 15.003 seconds. Evidence:
`evidence/m4/fred_transport_diagnosis_01.json`.

The observed problem is response-header completion after successful TLS on
the current proxy route. This does not identify whether the cause is the
proxy exit, an intermediary, upstream filtering or FRED application behavior.
It does not prove zero header bytes arrived: HTTPResponse.begin did not finish.
The previous ledger cannot retrospectively locate its historical failure phase.

Two prior conclusions required correction: a passing repository CI does not
validate external FRED availability; repeated TimeoutError is insufficient to
call a service unreachable. The old helper also used per-operation socket
timeouts rather than a proven wall-clock deadline and omitted failure phases.
The diagnostic records phase, cumulative milestones and elapsed time. It is
not promoted to a production fetcher: HTTPResponse.begin can consume multiple
socket reads, and a trickling response could exceed the nominal total deadline.
Actual measured attempts ended within 15.005 seconds; this observation is not
a guarantee for all responses. No raw artifacts were written on this run.

## Validation and protected state

Python assertions on JSON: PASS for unique paths, exactly three attempts,
>=15-second spacing, successful TLS, response_headers/TimeoutError and zero
body bytes. `git diff --check`: PASS. M2 HEAD and stash equal Goal baseline;
database byte hash rechecked equal before execution. No database engine used.
Only this Goal, record and diagnostic evidence are staged for delivery.

DSH independently reviewed the four scoped files and requested changes.
Accepted findings: finish the record, distinguish harness deadline exceptions
from socket exceptions, and make TLS provenance available in future runs.
The ignored helper now uses DeadlineExceeded and records error_source plus TLS
version/certificate digest. No request was repeated and no existing evidence
was retroactively enriched. Remaining header-byte and wall-clock limitations
are explicitly disclosed above; this helper is not accepted for production.
Some reviewer claims were not adopted: a two-second timeout is not required by
the authorized 15-second envelope; missing raw hashes are expected when no body
was received; the byte-budget guard is reachable at exactly the budget. DSH's
review is not represented as PASS. Evidence acceptance is limited to the
measured three attempts, not future fetcher correctness.

## Remaining work and delivery

Stage remains BLOCKED: REAL_LICENSE_EVIDENCE_MISSING, with endpoint identity
unproven. CSV, adapter and research execution remain gated. A useful next
acquisition run must change or establish the failing transport condition;
blindly repeating the same requests adds no diagnosis. System proxy settings
were not modified. PR #28 is merged; this diagnostic change is committed and
pushed separately for review, with concrete commit/PR status in the handoff.

## Continued route comparison

Baseline `c2765d44ead8ea65609f2439edf4494af0b0238b` is synchronized with origin;
PR #29 is draft, with 42/42 checks successful. User instructed continuation
after the proposed exit comparison. Compare the approved terms endpoint with
explicit proxy bypassed and with the current local proxy, using curl's total
15-second deadline and 512 KiB per response. This changes no system settings.
The preceding Goal section defines the two-condition budget before requests.

Both conditions failed identically after verified TLS, with curl exit code 28
and no origin HTTP status or body. Explicit-proxy bypass: TLS 406380 us,
total 15015307 us, response header bytes 0, proxy_used=0. Existing proxy:
TLS 771446 us, total 15006322 us, proxy_used=1; 39 header bytes include the
CONNECT response and are not evidence of an origin response. Each sent 161
request bytes; redirects/retries=0; ssl_verify_result=0. The second command
started after the first 15.015-second command completed. Timing overruns of
6-15 ms reflect observed curl termination/scheduling, not an increased timeout.
No body output files were created. Structured metadata is parent-transcribed
from tool output in `evidence/m4/fred_route_comparison_01.json`; exact start
timestamps were not captured and are not invented.

Common command options: `curl.exe -q --proto '=https' --max-time 15
--connect-timeout 15 --retry 0 --max-filesize 524288 --max-redirs 0
--header 'Accept-Encoding: identity'
--user-agent 'ashare-research-lab-evidence-probe/2' --silent --show-error`.
Both URLs were `https://fred.stlouisfed.org/docs/api/terms_of_use.html`.
Bypass used `--noproxy '*'`; proxy used `--proxy http://127.0.0.1:10808
--noproxy ''`. Each used its distinct ignored `route_*_01.body` output path
and curl write-out metrics. No certificate verification was disabled.

`Find-NetRoute -RemoteIPAddress '96.7.98.197'` and source-address lookup
resolved the bypass condition to WLAN. This does not establish distinct public
egress IPs, nor exclude transparent upstream routing. The result rules out an
explanation confined to Python urllib or the explicit localhost proxy setting;
it does not identify the failing upstream component or prove global FRED outage.
The local request settings alone have not restored access. Further diagnosis
needs an independently reachable exit; no system proxy configuration was changed.

Continuation validation: JSON parsing, two distinct routes, exact shared URL,
zero body bytes, no retries/redirects and successful TLS assertions; byte-level
database hash and protected Git refs; `git diff --cached --check`. The old
diagnostic JSON remains unchanged. The tracked delta is the Goal, work record
and new comparison JSON. Continue delivery on the same PR #29; no new PR or
automatic merge. Acquisition remains BLOCKED, and CSV remains unrequested.

DSH's bounded read-only review of the new comparison returned PASS: metrics
match the record, proxy CONNECT headers are distinguished from origin headers,
and the diagnosis does not overstate independent exits or global outage.
This review does not supersede the historical helper review or accept a
production fetcher. Parent independently verified the new evidence assertions,
unchanged old ledger, stash/M2 refs and database hash. Delivery is an update
to https://github.com/dlam12138/ashare-research-lab/pull/29 on the same branch.

## User-reported node change

User reported changing the Clash node after the route comparison. A new run
will first test the same terms path through the existing local proxy, keeping
the request parameters and 15-second timeout unchanged. Continue to legal and
series only if terms returns HTTP 200. Prior ledgers remain immutable.

The terms attempt started at 2026-09-22T11:55:14.217302+00:00. The wrapper
failed at JSON parsing (Expecting comma delimiter, column 29) after curl
returned. The custom format emitted the HTTP code as a bare number; curl's
no-response token 000 is invalid JSON. This is reproduced offline. Original
stdout was not persisted, so exact curl status/timings are unrecoverable and
must not be asserted for this attempt. No body output file exists. The initial
STARTED ledger was reconciled to TELEMETRY_ERROR with unknown body_bytes,
rather than leaving a false active request or asserting measured zero bytes.
Legal/series/CSV were not requested and the terms request was not repeated.

Fixed the ignored wrapper to quote the HTTP status, normalize it after JSON
parsing, save stdout metrics before parsing, and persist a telemetry error if
parsing fails. `python tmp/m4-provider-evidence-v2/test_changed_node.py` checks
invalid bare 000, quoted 000, success 200 and corrupt JSON without networking.
This corrects instrumentation only; it does not establish changed-node
availability. The changed-node outcome remains inconclusive.

All three offline regression tests passed. Parent reconciliation assertions
passed: one consumed attempt, TELEMETRY_ERROR, unknown byte count, no body file;
both previous evidence JSON files are unchanged. DSH's bounded read-only review
returned PASS for evidence honesty/reconciliation only, not acquisition success.
The changed-node evidence and record are delivered on the existing PR #29.

## Explicitly approved repaired-tool verification

User confirmed one further 15-second terms request after the parser repair.
Baseline `833b965` is clean and synchronized. Protected stash, M2 HEAD and
database byte hash match the Goal. Run 02 has separate ledger/output paths,
one endpoint only, no retries, and preserves stdout/stderr before parsing.

Run 02 completed with valid telemetry: started 2026-09-22T11:59:37.935735Z,
curl/process exit 28, HTTP code 0, proxy_used=1, verified TLS at 770399 us,
total 15008501 us, body bytes 0, header bytes 39 (including proxy CONNECT),
redirects/retries=0. The wrapper returned 0 because it successfully recorded
the failure; that is not acquisition success. No raw body file was created.
Saved metrics SHA256 is
`c17f627f48f7c4813fed027eaa4323b27abbd3ef42dac4fec0d506d2a1db317b`;
saved stderr SHA256 is
`ea19e8bd94c7252a82b81a35a17f04ed5451d3ca7f827f2ee46c69df4c80ce8f`.
Both remain in ignored tmp storage and are referenced by the new ledger.

The fixed parser passed three offline regression tests before execution and
parsed real no-response telemetry correctly. The user-reported changed node
still did not return a terms response within the authorized deadline. Public
exit identity and the upstream cause remain unproven; no global FRED outage
or licence refusal is inferred. One authorized request was consumed; no
legal/series/CSV or further request followed. Acquisition remains BLOCKED.

Parent independently verified both retained output digests, metric/ledger
equality and unchanged historical JSON files. DSH reviewed all three run-02
files read-only and returned PASS for failure-evidence consistency; it did
not independently recompute digests. Its phrase "within 15000 ms" is imprecise:
curl was configured to 15000 ms, while observed elapsed was 15008.501 ms.
Database hash was rechecked unchanged. `git diff --check` passed. Exact scoped
delivery comprises this Goal/record and the new run-02 JSON on existing PR #29.
