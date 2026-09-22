# Goal: diagnose FRED transport and continue evidence acquisition

## Objective and baseline

User authorized diagnosis and continued operations after the PR #28 handoff.
PR #28 was independently checked (42 successful checks, clean diff, exact head)
and merged as `9c9ced90d109437b937cfcaa069388689db636f5`.
Branch: `codex/m4-fred-transport-diagnosis`, based on that origin/main commit.
Worktree was clean. Protected M2 HEAD is `3679b1bac7a1634c6452784a4d8f6d139966f222`;
stash is `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; database SHA256 is
`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Allowed scope and required behavior

This Goal, a matching work record, diagnostic evidence JSON, and ignored tmp
tooling/raw evidence only. Continue the existing approved FRED HTTPS GET scope
with one newly authorized diagnostic run: terms, legal, series, at most once
each; 15 seconds total per request, zero retries, >=15 seconds start spacing,
1 MiB total response body ceiling, no credentials or redirects. Instrument
proxy connection, TLS, response headers and body separately. Preserve prior
ledgers. Do not infer the historical timeout phase from a new measurement.
No CSV until licence and identity gates pass; this diagnostic run excludes CSV.
Use existing local proxy configuration without changing system settings.

## Forbidden scope and stop conditions

No provider substitution, new endpoints, disabled certificate verification,
database engine access, research/holdout use, historical evidence edits,
direct main push or force push. Stop acquisition if licence evidence is absent.
An exhausted diagnostic run is not permission for an automatic retry.

## Validation and acceptance

Validate ledger phase/status/elapsed/bytes, unique endpoints, intervals, ceiling,
raw SHA256 if retained, protected baselines, exact diff and clean working tree.
Commands: `python tmp/m4-provider-evidence-v2/diagnose.py`,
`git diff --check`, `git diff --cached --check`,
`Get-FileHash -Algorithm SHA256 D:\量化分析\data\research.duckdb`,
`git status --short --branch`, `git ls-remote origin`.
Acceptance requires an evidence-backed diagnosis distinguishing observations
from hypotheses; successful data acquisition is a separate gate.

## Delivery

Commit the Goal, work record and diagnostic JSON; push only the named topic
branch and open a reviewable PR. No automatic merge of the new PR.
