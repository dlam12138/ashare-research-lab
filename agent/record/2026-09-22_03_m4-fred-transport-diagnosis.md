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
