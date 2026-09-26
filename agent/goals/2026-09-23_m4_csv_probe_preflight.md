# Goal: M4 CSV probe preflight and evidence disposition

## Objective and verified baseline

The user instructed continued project progress after the proposed complete
CSV/proof/dossier milestone. Reuse the existing explicit request envelope,
review prerequisite evidence and execute a single probe only if all applicable
licence gates pass. A discovered contradiction must be recorded before contact.

- Branch: `codex/m4-fred-transport-diagnosis`, clean at
  `174d33a594c496b106d163b1ffd5c376378bbb75`; origin/live remote match.
- Base main: `9c9ced90d109437b937cfcaa069388689db636f5`.
- Protected M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`.
- Protected stash: `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Protected database SHA256:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Authorization: `evidence/m4/provider_evidence_authorization_v2.json`.
- Contract: `evidence/m4/provider_evidence_contract_v2.json`.

## Scope and behavior

Write this Goal, its matching record, a preflight disposition JSON and
acceptance file. Correct the existing licence artifact if an unsupported claim
is demonstrated; preserve raw evidence and historical acquisition ledgers.
Conditional CSV/proof/dossier implementation must be specified before execution
and cannot begin while licence scope is unresolved. No provider request is
authorized by a passing transport check alone. The existing single-request
authorization (2015-03-09..13, DATE/DCOILBRENTEU, HTTPS GET, 15 seconds,
zero retries, 4/minute, 1 MiB, evidence only) remains the maximum envelope.

No research values, database connection/write, holdout access, adapter change,
provider substitution, credentials, main push, merge or historical dossier
mutation. DSH performs bounded read-only review without recursive delegation.

## Validation and acceptance

- `python tmp/m4-provider-evidence-v2/validate_preflight.py`: strict JSON,
  canonical bytes/digest, raw hashes, exact licence references, contradiction
  disposition, unused dossier identity, and unchanged tracked baselines.
- `git diff --check` and `git diff --cached --check`.
- `git status --short --branch`, `git rev-parse HEAD refs/stash`,
  `git ls-remote origin refs/heads/codex/m4-fred-transport-diagnosis`.
- `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'`.

Acceptance is an evidence-supported preflight result. Unresolved permitted-use
scope blocks the request under `REAL_LICENSE_EVIDENCE_MISSING`; do not assert
`REAL_LICENSE_SCOPE_FORBIDDEN` without resolving that the intended use is outside
the permitted scope. No terminal dossier is created if no probe runs.

## Delivery and stops

Commit scoped files and push the existing topic branch with an explicit refspec;
update PR #29 with the actual final result. A licence contradiction stops network
execution, not the offline correction and review. Do not ask the user to
re-authorize an already approved request to substitute for publisher permission.
