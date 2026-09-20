# Goal: M4 provider-evidence acquisition design v1

Date: 2026-09-20. Executor and Git operator: Codex. Design analyst and independent reviewer: DSH.

## Objective and verified baseline

Turn the accepted K2 fail-closed preflight into a provider-agnostic,
design-only acquisition contract. Freeze how a later authorized stage would
evaluate candidate providers, retain and hash raw bytes, prove revisions and
PIT timing, register calendar/membership evidence, bound transport, and record
license/redistribution rights. Do not select a provider or acquire data.

- Worktree: `D:/量化分析-m4-provider-evidence-design`.
- Branch: `codex/m4-provider-evidence-design`.
- Base: `origin/main@8ba2945452ac52d9b80ce6cba9ca9d5fa33cebb4`
  (PR #23 merge).
- Protected M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`;
  stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; default database SHA256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Scope

Allowed: tracked repository evidence only; this Goal; one design document, one
record and one acceptance file; Markdown/link/Git validation; commit, push and
one documentation-only PR.

Forbidden: network/browser/provider/API access, credentials, downloads,
database open/query/write, real observations, holdout, provider selection,
adapter/source/test/config/CI/frozen-contract changes, implementation,
statistics or execution. Candidate names already present in tracked evidence
may be listed only as `UNVERIFIED_CANDIDATE`; current terms/specifications may
not be inferred.

## Required design

- Define a provider evidence dossier schema covering provider/publisher,
  endpoint/method/dataset, requested window, raw-byte retention and SHA,
  revision/vintage, publication/availability, calendar/suspension/half-day,
  identity/per-date membership, return/unit/adjustment semantics, transport
  bounds, license/redistribution and credential constraints.
- Define states `UNVERIFIED_CANDIDATE`, `EVIDENCE_COMPLETE`, `REJECTED`, with
  `EVIDENCE_COMPLETE` requiring every mandatory field and independently
  retained bytes; no default/fallback source selection.
- Freeze fail-closed review cases, minimum artifact paths, redaction rules,
  license evidence requirements, and deterministic dossier identity.
- Separate later phases: evidence acquisition, provider adapter implementation,
  real-data validation and execution. This design authorizes none of them.
- DSH must remain read-only.

## Validation and acceptance

Run `git diff --check`, `git diff --cached --check`, `git status --short
--branch`, `git rev-parse HEAD origin/main refs/stash`, `git worktree list
--porcelain`, `git stash list`, protected M2 HEAD and database SHA checks. All
new Markdown must be strict UTF-8, final-newline, whitespace/conflict-marker
clean, with valid relative links.

Acceptance requires complete schema, state machine, cases, boundaries, exact
tracked citations, DSH final `PASS`, clean worktree, unchanged protected state,
and synchronized remote delivery. Stop on any need for external/current facts,
provider contact, credentials, real data or implementation.

Local commits, push to `codex/m4-provider-evidence-design`, and one PR are
authorized after validation. Direct main push, force-push, merge, acquisition,
selection, implementation and all later stages are not authorized.
