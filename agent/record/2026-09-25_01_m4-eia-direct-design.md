# EIA direct-source design record

Goal: `agent/goals/2026-09-25_m4_eia_direct_design.md`.
Date: 2026-09-25. Module: M4 source evidence. Parent: Codex; reviewer: DSH.
Starting branch `codex/m4-fred-transport-diagnosis@2eab70b` clean,
origin/live remote equal. PR #29 draft, historical HEAD checks 42/42 passed.
M2 HEAD, stash and database byte hash match the Goal.

User accepted continued investigation of EIA official documentation and routes.
Read official technical documentation, registration/terms and reuse pages via
web tools; no dataset endpoint or download requested. Browser/search output is
discovery evidence, not original raw evidence for a licence artifact.

Findings: APIv2 documents server-side date filtering and individual free keys.
This conflicts with the frozen v2 credential-free envelope. Its documented
response envelope can echo api_key, creating a second conflict with exact raw
retention. The design will require resolution before a keyed request; merely
redacting a response cannot satisfy original-byte proof. A key must not be sent
in chat or tracked files. No credential presence/value is inspected.

Delivered `docs/m4_eia_direct_source_plan.md`: candidate metadata/observation
routes, bounded query parameters, rights/credential prerequisites and an
authenticated-encryption retention proposal. No frozen contract amended.

DSH read-only review returned CHANGES_REQUIRED on the draft. Parent corrected
per-request timeout wording, persistently shared byte/request budgets around
metadata review, streaming-cap enforcement, five-date completeness/response
total checks, and explicit pre-keyed-call encryption gates. Metadata identity
and units remain unverified prerequisites; requesting the measured value does
not assert that the service omits contextual metadata. DSH's suggested second
user approval between metadata and observation is not adopted as inherently
necessary: a future explicit conditional authorization can cover both, while
requiring the evidence gate to pass. DSH did not verify endpoints or Git state.

Parent validation: `git diff --check` PASS; changed scope is exactly three
Markdown files. `git diff --cached --check` is required before commit. No product
tests are needed for documentation-only planning. Previous commit CI 42/42
passed; new commit results must not be inferred from those checks.

Outcome: EIA route investigation/design complete; live acquisition remains
pending credential-aware contract approval and user key provisioning. Commit
and push this three-file change to PR #29; leave it draft/unmerged. No source
observation, credential or database content was read; protected artifacts remain
unchanged. Final delivery SHA and synchronization are reported in the handoff.
