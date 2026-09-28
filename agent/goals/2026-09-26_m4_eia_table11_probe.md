# Goal: one authorized historical Table 11 CSV

User authorized the specific March 18, 2015 Table 11 CSV acquisition, structural
date/Brent/version review, encrypted retention, no research/database admission.
Base: codex/m4-eia-archive-discovery ff72a1690944ba5875de55c5b0ef92ade066bb7c;
main 544be8011cf9d5b0abaecdb4c0b09683204dd2fb. PR #31 remains unmerged.
Working branch codex/m4-eia-archive-table11 initially clean.
Protected M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Allowed: this Goal/record, dedicated one-shot probe/tests and metadata ledger;
ignored AES-GCM original bytes and fresh DPAPI-wrapped key in separate namespace.
One local landing-page request to resolve the real Table 11 CSV link, then at
most one CSV GET; >=15s separation, 15s timeout each, cumulative 1 MiB local
response-body limit, no retries/redirects. Prior web directory lookup failed;
it was not a price request. Do not replay the prior four-request API probe.
TLS verified; no credentials needed. Reject links outside the exact issue path.
No PDF/other table requests, plaintext disk retention, value output, database,
backtests, provider changes, relaxed PIT contract or merging PR #31.
Full authorized CSV may contain other dates/products; retain encrypted only,
report coverage honestly, never admit off-window observations into research.
Stop after any request failure, size limit, unresolvable link or exhausted request.
Acceptance: hash-verified encrypted single response or accurately recorded failure;
structural review must not claim row-level historical availability from issue date.
Tests: node --test agent/tools/eia_archive_probe.test.cjs;
node agent/tools/eia_archive_probe.cjs verify (after successful retention);
python agent/tools/validate_eia_artifacts.py; git diff --check;
git diff --cached --check; ignored raw and protected-state checks.
Local commit of scoped changes; no push/PR/merge without explicit authorization.
