# FRED native-browser comparison

Goal: `agent/goals/2026-09-23_m4_fred_browser_comparison.md`.
Baseline: `337a5e6` on `codex/m4-fred-transport-diagnosis`, clean and synchronized.
Prior fixed curl request completed TLS but timed out awaiting origin response.
User authorized the proposed browser comparison. Existing proxy route is used;
this session does not claim to verify a distinct public exit.

Read Playwright skill and CLI reference. npx exists; offline CLI invocation
failed ENOTCACHED. Existing Chromium 1200 is available; no installation is
needed. Use local CDP with an isolated profile and bounded relay/interception
to obey the existing endpoint, no-credential, byte and time restrictions.
No UI element interaction, DOM quotation, screenshot or external asset load
is necessary for the transport comparison.

## Result

Native Chromium 143.0.7499.4 received HTTP 200 at the exact approved path via
HTTP/2 and TLS 1.3. The allowed CONNECT started at 2026-09-23T03:44:17.660Z;
loading finished after 934 ms. Exactly one document request and one upstream
tunnel were allowed. The relay forwarded 56236 upstream bytes, including
CONNECT/TLS overhead, below 1048576. Eighteen additional page requests and ten
other/redundant tunnels were rejected locally; no other upstream CONNECT was
allowed. No retries, redirected navigation or additional endpoint was allowed.

The CDP body has 48954 bytes, SHA256
`fff8abf2023694ee4602f97918f0702522c8ff2a2e65a0967cde8a064d41d213`, stored only at
ignored `output/playwright/fred-browser-01/browser_body.bin`. It is derivative
browser output, not certified original wire bytes. The HTML has terms text
and no matched captcha/access-denied markers, but transport success alone
does not validate the complete licence scope. No licence artifact, dossier,
CSV, database or research operation followed.

## Interpretation and limits

Read-only local proxy-log comparison found the same hashed route label for
the previous changed-node curl attempts and this browser attempt. This is
evidence of the same configured route, not proof of the same public egress IP.
The browser used HTTP/2; earlier Windows curl lacked HTTP/2 support. Browser
headers, TLS fingerprint and timing also differ. These observations prioritize
client/protocol behavior over a blanket internet-connectivity explanation.
They do NOT isolate HTTP/2 or User-Agent as the cause: previous curl evidence
was recorded on the prior day, so recovery over time is also a confounder.
No new curl request was issued to claim a simultaneous controlled A/B result.
JS and subresources were blocked; this is a restricted document-navigation
comparison, not a complete interactive website test.

## Validation and review

`node --check tmp/m4-provider-evidence-v2/browser_probe.cjs`: PASS.
`node tmp/m4-provider-evidence-v2/browser_probe.cjs`: exit 0; BROWSER_HTTP_200.
Parent independently checked the body length/SHA, exact URL and single-request
counts, relay byte count/deadline, HTTP status/protocol and ignored paths.
DSH performed a read-only code/Goal review and returned PASS for the request
allowlist and relay limits. The parent reviewed before execution; DSH's result
arrived after execution and is not represented as a completed pre-network gate.
DSH noted derivative storage differs from the original-wire quarantine path;
the Goal clarification above preserves that distinction. Browser certificate
verification was left enabled; no separate negative-certificate test was run.

## Delivery and stage status

Exactly three tracked files: this record, the dated Goal and browser JSON.
Baseline `337a5e6` had 42 successful CI checks, independently read from PR #29.
The diagnostic objective is met: native browser accessibility is demonstrated.
Full acquisition remains blocked on original evidence and licence/identity
gates; do not automatically merge or enter research. Commit/push updates PR #29.
