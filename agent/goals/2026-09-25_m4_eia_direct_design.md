# Goal: EIA direct-source design

User continuation authorizes the previously proposed official-document and
endpoint investigation. Objective: a concrete bounded EIA plan, with unresolved
requirements stated before observation acquisition.

Baseline: clean `codex/m4-fred-transport-diagnosis` at
`2eab70bc799ab503e28a53f2ff901751fe392295`, matching origin/live remote;
main `9c9ced90d109437b937cfcaa069388689db636f5`. PR #29 is draft, 42/42
checks passed. M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`, stash
`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`, database SHA256
`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

Allowed: read EIA official documentation/registration/rights pages and API
browser metadata; write this Goal, matching record and design; scoped DSH
review; commit/push topic branch and update PR description.
Search is discovery only, not immutable licence acquisition evidence.
Forbidden: observation/download requests, registration submission, credential
lookup/use, provider selection in production, database/holdout/research access,
changes to frozen contracts/authorization, merge or main push.

Required result: candidate host/routes, dates, fields, rate/size/timeout,
credential handling, first-party support and gaps, next decision. Distinguish
documented API capabilities from tested endpoint behavior. Do not declare a
provider accepted from documentation.

Validation: DSH read-only review; `git diff --check`;
`git diff --cached --check`; `git status --short --branch`;
`git rev-parse HEAD refs/stash`; protected database file hash; explicit remote
branch comparison. Docs-only work does not warrant repeated local product tests.
Acceptance: concrete reviewable design with honest remaining prerequisites.
Stop observation execution at any credential/permission or raw-retention conflict.
