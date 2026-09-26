# FRED HTTP/2 evidence acquisition

Goal: `agent/goals/2026-09-23_m4_fred_http2_evidence_acquisition.md`.

Baseline `9238eeb` is clean and synchronized on
`codex/m4-fred-transport-diagnosis`. PR #29 current-head checks are running;
no failure was reported at task start. Protected stash/M2/database values match
the Goal. Native Chromium previously received the terms page over h2 in 934 ms;
Windows curl HTTP/1.1 attempts had timed out after TLS.

Plan: use Node 24's built-in nghttp2 client over the existing local CONNECT
proxy, retain HTTP/2 DATA payload bytes before decoding, validate raw identity,
then review terms/legal/series evidence. No package or dependency installation.
Actual requests, validation and delivery state will be appended after execution.

## Execution

DSH first reported a byte-cap defect, but its arithmetic overlooked the
existing in-flight chunk subtraction. The parent nevertheless replaced the
repeated reduction with an explicit in-flight counter and immediate stream
destruction on violation. A second DSH pass verified the critical implementation
constraints but guessed the Goal filename and did not read it; the parent read
the actual Goal and verified equivalence. `node --check` and `git diff --check`
passed before network.

The bounded run retained all three first-party responses:

- terms: HTTP 200, h2, identity, 48,954 bytes, SHA256
  `fff8abf2023694ee4602f97918f0702522c8ff2a2e65a0967cde8a064d41d213`;
- legal: HTTP 200, h2, identity, 131,707 bytes, SHA256
  `d69f84e9a2f8739fcaae5ce4d3bf50f6ab56c02fe904bf0dfeafc6f58bb8c3ac`;
- series: HTTP 200, h2, identity, 79,337 bytes, SHA256
  `2032451f521dde95eea620a81b0f5055a6a0a31c9b4dfa35531199f536f0d055`.

Starts were 03:52:28.797Z, 03:52:43.797Z and 03:52:58.808Z, satisfying
the 15-second interval. Elapsed times were 1471/563/1954 ms. All three used the
same verified certificate digest and ALPN h2; no retry, redirect, credential,
cookie or decoding occurred. Total retained body bytes: 259,998, below 1 MiB.
The ledger is `evidence/m4/fred_http2_acquisition_01.json`; raw files are ignored
and SHA-addressed under the v2 quarantine.

## Offline evidence review

The retained FRED legal page grants bounded non-commercial/personal/educational
access and use while requiring source attribution and observance of series
copyright status. The series page identifies DCOILBRENTEU, U.S. EIA as source,
daily dollars-per-barrel identity, and a Public Domain: Citation Requested
label, while also warning that sharing follows copyright notes. The existing
first-party EIA reuse page states that EIA government data products are public
domain, with third-party, photo and logo exclusions. These sources support
private evidence retention and the proposed evidence-only probe with citation;
they do not authorize republishing FRED page content or third-party materials.

`evidence/m4/provider_licence_artifacts_v2.json` records the exact raw
references, permitted-use limits, attribution/display constraints and explicit
non-redistribution assumptions. Current series observations embedded in the
identity page were not extracted into research or interpreted. No CSV was
requested in this stage.

## Final review

The final DSH read-only review returned PASS for the bounded acquisition and
licence-artifact scope. It independently confirmed endpoint order, HTTP 200
status, 15-second start spacing, h2/identity transport, zero retries, total
bytes and raw hashes. The parent independently verified every required licence
field and the contract digest. The ledger now records `final_path` explicitly;
because redirects were disabled, each final path equals its authorized endpoint.

Delivery remains limited to this Goal, this record and the two evidence JSON
files. The ignored helper and SHA-addressed raw bodies remain untracked. The
next CSV/adaptor/research stage is still outside this Goal and requires a later
explicit stage authorization.
