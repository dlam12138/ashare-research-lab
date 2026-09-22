# M4 provider-evidence acquisition v2 acceptance

Verdict: `BLOCKED`.

## Goal and authorization

- Goal: `../agent/goals/2026-09-22_m4_provider_evidence_acquisition_v2.md`.
- Authorization artifact: `../evidence/m4/provider_evidence_authorization_v2.json`.
- State: `ACQUISITION_V2_EXPLICITLY_AUTHORIZED`.
- Authorization digest:
  `22e9cea6118f844587a3b9e7f50b66b3912692e13198037b13c2fb6327e0d67f`.
- Contract digest:
  `b5f6b8d54f5fe733d41ed018a89b3065fc05a0e7130c072c66d19e469221bdca`.

The user first approved the CSV probe envelope, then explicitly added three
read-only HTTPS GET endpoints for first-party licence and identity evidence.
No host, endpoint, method, credential, timeout, retry, rate, response-size,
field, date, retention or use scope was inferred beyond those approvals.

## Baseline

- Base branch/commit: `origin/main@e42ad8acdfb5c29f980c4258013da39ce6b14309`.
- Working branch: `codex/m4-provider-evidence-acquisition-v2`.
- Initial and pre-commit HEAD: `e42ad8acdfb5c29f980c4258013da39ce6b14309`.
- Protected M2 HEAD:
  `3679b1bac7a1634c6452784a4d8f6d139966f222`.
- Protected stash:
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Protected database SHA256:
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.

## Actual bounded requests

Exactly three requests were attempted within the authorized licence/identity
set and with at least 15 seconds between request starts. Every request used HTTPS GET, no
credentials, zero retry, a 15,000 ms timeout, identity encoding and a 1 MiB
read ceiling. Redirects were disabled rather than silently followed.

1. `fred.stlouisfed.org/legal/`: read timed out at 15 seconds. No retry, body,
   raw file or inferred licence fact.
2. `www.eia.gov/about/copyrights_reuse.php`: HTTP 200; final host and path
   exactly matched the allowlist; `text/html`; 52,317 bytes; SHA256
   `4758216ebe7e50dc7a62b97234b4d208c3d48ffc92f1a0b81f1c78d26508b8d6`;
   retained at the matching repository-relative ignored quarantine locator.
   The page is first-party EIA evidence for EIA reuse scope only; it does not
   substitute for FRED terms or current FRED series identity.
3. `fred.stlouisfed.org/series/DCOILBRENTEU`: read timed out at 15 seconds. No
   retry, body, raw file or inferred identity fact.

The fourth authorized request, `fred.stlouisfed.org/graph/fredgraph.csv`, was
not issued. Therefore no observation value, response date, development-period
or holdout data was received, scanned, stored, transformed or used.

## Fail-closed decision

The FRED licence and endpoint-identity gates remain unresolved. The applicable
pre-probe code is `REAL_LICENSE_EVIDENCE_MISSING`: mandatory first-party
licence evidence is absent. `REAL_REDACTION_UNPROVEN` is not asserted because
retention was neither forbidden nor attempted for a CSV response. No v2
dossier was created because the Goal permits it only after a probe runs; the
authorized identity `eia_brent_oil_transport_v2_probe_01` remains unused.

No provider substitution, mirror, retry, credential, database, holdout,
statistics, adapter work or research execution occurred.

## Validation evidence

The parent executed before commit:

- strict duplicate-key/no-float JSON parsing for the contract, v1 manifest and
  authorization artifact;
- recursive sorted-key compact digest recomputation for all three artifacts;
- exact authorization-to-Goal comparison;
- raw EIA file size and SHA256 verification;
- absence of a v2 dossier and CSV raw response;
- `git diff --check`, `git diff --cached --check`, exact path review and ignored
  quarantine review;
- branch, HEAD, `origin/main`, live remote main, stash, worktree, protected M2
  HEAD and protected database hash checks;
- final read-only DSH review: `PASS` for the correctly enforced `BLOCKED`
  outcome.

At the first protected-state check after requests:

- local and live `origin/main` remained `e42ad8acdfb5c29f980c4258013da39ce6b14309`;
- working HEAD remained the same base commit;
- M2 HEAD, stash and database SHA256 exactly matched the protected values;
- the only v2 raw file was the ignored EIA licence page above;
- no dossier file existed.

## Changed files and synchronization

Tracked scope is limited to the Goal, authorization JSON, record and this
acceptance file. There is no product, test, CI, dependency, configuration,
database, v1 evidence or frozen-contract change. The ignored quarantine file
and ignored temporary fetch helper are not eligible for staging or commit.

Final commit, push, PR and post-push synchronization evidence will be appended
only if the parent review and final DSH review confirm this `BLOCKED` outcome.

## Deviations, blocker and next-stage authority

- Expected success path: licence/identity proof followed by one CSV probe.
- Actual path: both FRED evidence endpoints timed out; the CSV probe was
  deliberately skipped.
- Blocker: current first-party FRED licence and series identity evidence is not
  retained and cannot be inferred from EIA evidence.
- No retry or alternative endpoint is authorized. Proceeding requires new
  explicit user authorization.
- Merge and adapter/real-data work are not authorized.
