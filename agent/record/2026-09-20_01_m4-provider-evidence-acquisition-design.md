# Work record: M4 provider-evidence acquisition design

Date: 2026-09-20. Contract: [Goal](../goals/2026-09-20_m4_provider_evidence_acquisition_design.md). Author: Codex. Read-only design analyst/reviewer: DSH.

The worktree was created cleanly from `origin/main@8ba2945452ac52d9b80ce6cba9ca9d5fa33cebb4`, the PR #23 merge. DSH first returned `CHANGES_REQUIRED` for seven Goal defects: analyst/reviewer role conflict, unclear write authority and paths, incomplete state transitions, unfrozen error vocabulary, and underspecified licence/redaction rules. Codex corrected the Goal in commit `18474ae` before writing the deliverables.

The [design](../../docs/m4_provider_evidence_acquisition_design_v1.md) then froze the dossier schema and identity, state transitions, evidence gates, immutable raw/redacted-artifact split, licence artifact, stable failure cases, unverified candidate boundary and four separate later phases. No current provider facts were inferred; tracked provider names remain unverified only.

DSH's bounded final review found three near-synonym failure codes that were not part of the accepted tracked vocabulary. Codex replaced them with the existing `REAL_RAW_HASH_MISMATCH`/`REAL_SOURCE_ROLE_MISSING`, `REAL_ENDPOINT_UNBOUNDED`, and `REAL_SECURITY_IDENTITY_CONFLICT` codes; no new error code was added.

No network, browser, provider, credential, download, database contents, real observation or holdout was accessed. No source, test, configuration, CI, dependency or frozen contract changed. Protected M2 HEAD, stash and default database hash are verified at final review.

This stage stops after one documentation-only PR. Merge, evidence acquisition, provider selection, adapter implementation, real-data validation and execution remain unauthorized.
