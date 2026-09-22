# Goal: M4 provider-evidence acquisition v2

Date: 2026-09-22. The user explicitly approved the complete bounded-probe
authorization envelope and the state `ACQUISITION_V2_EXPLICITLY_AUTHORIZED`.
The parent agent owns scope, Git operations, network execution and final
acceptance. DSH performs one bounded read-only preflight and one final review;
it must not recurse, contact the provider, modify files or fall back to Luna.

## Objective

Attempt one evidence-only, credential-free, bounded transport probe for the
FRED Brent series under `M4_PROVIDER_EVIDENCE_CONTRACT_V2`. Produce an immutable
authorization artifact and either a valid new terminal v2 dossier with retained
raw-byte proof, or a fail-closed record explaining why the probe did not run or
could not pass. No returned value may enter research, a database or holdout.

## Verified baseline

- Worktree: `D:/量化分析-m4-provider-evidence-acquisition-v2`.
- Branch: `codex/m4-provider-evidence-acquisition-v2`.
- Base and initial HEAD: `origin/main@e42ad8acdfb5c29f980c4258013da39ce6b14309`
  (PR #26 merge).
- Contract digest: `b5f6b8d54f5fe733d41ed018a89b3065fc05a0e7130c072c66d19e469221bdca`.
- Protected M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`.
- Protected stash: `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Protected database SHA256:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- The original M2 worktree, stale local `main`, all other worktrees, v1 raw
  responses and existing ignored artifacts are protected and out of scope.

## Explicit authorization envelope

- state: `ACQUISITION_V2_EXPLICITLY_AUTHORIZED`
- approved hosts: `fred.stlouisfed.org`, `www.eia.gov`
- approved endpoints: `/legal/`, `/series/DCOILBRENTEU`,
  `/about/copyrights_reuse.php`, `/graph/fredgraph.csv`
- approved new dossier ID: `eia_brent_oil_transport_v2_probe_01`
- requested start/end: `2015-03-09` / `2015-03-13`
- requested fields: `DATE`, `DCOILBRENTEU`
- method/credentials: HTTPS GET / none
- timeout: `15000` ms
- retry count: `0`
- request rate: at most `4` per minute; this task permits at most three
  licence/identity requests followed, only after their gates pass, by exactly
  one dataset request; no pagination
- response ceiling: `1048576` bytes
- raw retention: approved only below ignored
  `data/quarantine/m4_provider_evidence_v2/`, subject to first-party licence
  permission
- returned values are evidence-only and may not enter research, database or
  holdout flows

The authorization does not include any other host or path. The three added
licence/identity paths were explicitly approved by the user after the initial
DSH preflight stopped before network access.

## Allowed scope

Tracked writes are limited exactly to:

- this Goal;
- `evidence/m4/provider_evidence_authorization_v2.json`;
- `evidence/m4/provider_evidence_dossier_v2.json` only if a probe runs;
- `agent/record/2026-09-22_01_m4-provider-evidence-acquisition-v2.md`;
- `acceptance/2026-09-22_m4_provider_evidence_acquisition_v2.md`.

If and only if all preflight gates pass, one raw response may be written below
the ignored v2 quarantine namespace using its lowercase SHA256 as filename.
Temporary tooling may be created only below ignored `tmp/` and must never be
staged. Reading tracked evidence and Git metadata and hashing the protected
database as bytes are allowed.

## Forbidden scope

No credentials, POST, pagination, retry, redirect outside the exact approved
host/path, more than one dataset request, response over 1 MiB, date outside the
approved window, undeclared field, adapter/source implementation, product/test/
CI/dependency/config change, database open/query/write, holdout access,
statistics, aggregation, research execution, provider substitution, raw-byte
quotation, or v1 artifact mutation. Do not copy or move v1 raw responses. Do
not push `main`, force-push, merge, or start adapter work.

## Required behavior and stop conditions

1. Persist a deterministic authorization record containing every approved
   field and the contract digest.
2. Before the dataset request, use only the three explicitly approved
   licence/identity endpoints to prove from retained first-party evidence that original
   response retention and evidence-only use are permitted. User approval of raw
   retention is not a substitute for publisher licence permission.
3. If licence permission cannot be resolved from those endpoints, stop before
   the dataset request and record `REAL_LICENSE_EVIDENCE_MISSING`; do not infer
   permission or broaden the allowlist. `REAL_REDACTION_UNPROVEN` is reserved
   for the distinct case where original-response retention is forbidden or
   fails after permission was evaluated.
4. If preflight passes, perform exactly one bounded request, reject redirects
   that leave the exact host/path, stream with the byte ceiling, atomically
   retain SHA256-named raw bytes, and construct every transport-proof field.
5. Date-scan every raw row. Any ambiguous/unparseable or out-of-window date,
   undeclared field, development-window date or holdout date fails closed under
   the contract's exact code mapping.
6. The v1 terminal dossier and digest remain immutable. Any v2 dossier uses the
   new ID and exact predecessor lineage.
7. Stop immediately on any need to expand hosts/endpoints, use credentials,
   weaken a gate, access the database/holdout, or retain bytes without proven
   licence permission.

## Validation and acceptance

Run and record:

- strict JSON duplicate-key/no-float parsing for every new JSON artifact;
- canonical UTF-8 sorted-key compact JSON plus LF and recomputed top-level
  digest checks;
- authorization field equality against this Goal;
- dossier lineage and proof-digest checks if a dossier exists;
- `git diff --check` and `git diff --cached --check`;
- exact changed/untracked/ignored-path review;
- `git status --short --branch`, `git rev-parse HEAD origin/main refs/stash`;
- `git worktree list --porcelain`, `git stash list`;
- protected M2 HEAD and database SHA256 checks;
- DSH preflight and final read-only review.

PASS requires compliance with the authorization and all applicable gates. If
the licence precondition is unproven, the correct outcome is `BLOCKED` before
network access, with no raw v2 response or dossier falsely claimed. Commit and
push only after parent review, using an explicit branch refspec. Opening a PR
is allowed; merging and any next stage require new explicit authorization.
