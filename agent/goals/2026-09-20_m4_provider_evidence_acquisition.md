# Goal: M4 public provider-evidence acquisition v1

Date: 2026-09-20. Author, executor and Git operator: Codex. DSH performs
read-only contract analysis and final independent review; it must not write
repository artifacts or contact providers.

## Objective and verified baseline

Acquire citation-grade, current public evidence for the provider candidates
already named in the accepted provider-evidence design. Produce a bounded,
fail-closed disposition for each candidate without selecting a provider,
implementing an adapter, downloading market observations, or running a study.

- Worktree: `D:/量化分析-m4-provider-evidence-acquisition`.
- Branch: `codex/m4-provider-evidence-acquisition`.
- Base: `origin/main@781f7fb035eb3fdebc3b2c03ed5f642f2094d29e`
  (PR #24 merge).
- Protected M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`;
  stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; default database SHA256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Scope and authority

Candidate set is frozen to:

1. BaoStock public documentation for `query_trade_dates` and
   `query_history_k_data_plus`;
2. CNINFO publisher evidence and the tracked AkShare-mediated access surface;
3. U.S. EIA public documentation for the tracked factor-source surface.

Allowed: read-only HTTPS retrieval of official provider/publisher pages,
official documentation, official terms/licence/privacy/access-policy pages,
and official API metadata; browser/search use to locate those official pages;
response headers and byte-level SHA256/length computation in memory; tracked
repository evidence; writing only the deliverables below; local validation,
commit, push and one PR.

Forbidden: credentials, account creation, login, provider contact, form
submission, circumvention, bulk crawling, robots bypass, authenticated or
rate-limited API calls, market-price/factor/calendar/membership observation
downloads, database access, holdout access, provider selection, adapter/source
code, tests/config/CI/dependency changes, real-data validation, statistics,
study binding or execution. No external response body may be committed or
quoted beyond a short citation-safe excerpt. A body that cannot be retained
under the accepted contract cannot support `EVIDENCE_COMPLETE`.

Deliverables are exactly:

- `docs/m4_provider_evidence_acquisition_report_v1.md`;
- `evidence/m4/provider_evidence_manifest_v1.json`;
- `agent/record/2026-09-20_01_m4-provider-evidence-acquisition.md`;
- `acceptance/2026-09-20_m4_provider_evidence_acquisition.md`.

## Required behavior

- Use only authoritative first-party sources for provider/publisher facts.
- Record retrieval time with explicit timezone, final URL, HTTP status, media
  type, response byte length, SHA256 and whether redirects occurred. Do not
  record cookies, tokens, credentials, query secrets or host-absolute paths.
- For every candidate, assess identity, endpoint/method/dataset claims,
  revision/vintage evidence, PIT timestamps, calendar/membership evidence,
  semantics, bounded transport, retention, permitted use and redistribution.
- Every factual claim must cite both a manifest entry and its official URL.
  Search snippets and third-party summaries are discovery only, never proof.
- State remains `UNVERIFIED_CANDIDATE` unless every mandatory design field and
  independently retainable raw-byte requirement is proven. A definitive
  incompatible or impossible condition may yield `REJECTED` with an existing
  frozen reason code. Missing evidence must not be converted into a positive
  claim or provider selection.
- The manifest must be deterministic JSON: UTF-8, LF, sorted keys, two-space
  indentation, no floats, no local-clock defaults, and a top-level SHA256 over
  canonical compact JSON excluding the digest field.
- Separate observed fact, inference and unresolved evidence. State explicitly
  that this stage authorizes no adapter implementation or acquisition of
  market observations.

## Validation and acceptance

Run JSON parse/canonical-digest verification, URL/citation cross-reference,
duplicate-entry and forbidden-secret/path scans, Markdown-link checks,
`git diff --check`, `git diff --cached --check`, and repository state checks.
All new files must be strict UTF-8 with LF and final newline.

Acceptance requires all three candidates to have a bounded disposition,
official-source citations, reproducible response metadata, no unsupported
current fact, no committed external response body, DSH final `PASS`, clean
worktree, unchanged protected state, synchronized remote branch and one open
PR. Network errors or inaccessible/ambiguous terms remain explicit missing
evidence and do not authorize substitutions.

Stop immediately on any need for credentials, provider contact, observation
data, restricted content, database access, holdout, implementation or broader
candidate search. Direct main push, force-push, merge and every later phase are
not authorized.
