# EIA encrypted transport acceptance

Goal: agent/goals/2026-09-25_m4_eia_encrypted_probe.md.
Record: agent/record/2026-09-25_02_m4-eia-encrypted-probe.md.
Verdict scope: successful bounded evidence-only transport, not research approval.

- User-authorized credential and encrypted-original contract is recorded in
  evidence/m4/eia_direct_authorization_01.json; old v2 contract is immutable.
- Exactly four authorized GETs, all HTTP 200, no retries/redirects, >15-second
  spacing, each <15 seconds, cumulative 53787 bytes below 1048576.
- First-party terms and metadata retained before the one dataset request.
- Five distinct requested dates only, complete count, exact Brent series/unit
  and frozen columns; no observation value in tracked artifacts.
- AES-256-GCM ciphertext decrypts to original SHA256 under both Node and .NET;
  tamper/wrong-key tests fail as required. Key wrapped with Windows CurrentUser
  DPAPI; encrypted originals and wrapped key ignored, never staged.
- Canonical proof/dossier and file digests, terminal predecessor lineage and
  protected files validated. Acquisition identity is new and FRED ID unused.
- PIT/revision availability is UNPROVEN. Values remain evidence-only; no
  database/holdout/research flow was opened. No production-provider selection.

Reproduce using the five commands in the record (offline only). Original-byte
verification requires this worktree's ignored ciphertext and the original
Windows user profile. Clean clones can run synthetic tests but cannot recover
private evidence. Do not describe CI as reproducing private raw verification.
