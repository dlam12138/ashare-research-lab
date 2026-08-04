# Work record: M2 Stage 2K.1R4C.1 — Cross-Platform Identity Unification and ADR Share-Count Correction

Status: `in_progress`

## Basic information

- Date: 2026-08-04
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `9a6a167`
- Task source: user directive (M2 Stage 2K.1R4C.1 — 跨平台身份统一与 ADR 股本数量修正)
- Module: value assessment (cross-platform identity unification + ADR factual correction)

## Verified opening state

- Branch `feat/m2-value-assessment-mvp`; HEAD `9a6a167`; local == origin.
- Protected local files intact and untouched: `AGENTS.md` (`??`), `agent/goals/` (`??`),
  pre-existing Stage 2I.2R unstaged wording edit (`acceptance/m2_stage2i2r_...md` is `M`).
- Stash `stash@{0}` preserved (Stage 1B.4 record edit).
- R4C closed: capsule v3 digest `fb3a2cc860c74a17ebcbf4647206c6b16eb928da8b9b1e8aea8913df0b548309`
  (Windows); sensitivity v6 ledger digest `213cdba0…`; R4C CI `30912836218` PASS.
- R4C documented the pre-existing capsule-digest platform dependence (ubuntu `e60f8563…`
  vs Windows `fb3a2cc…`) and relaxed `test_sensitivity_v6_report_unchanged_digest` to be
  platform-aware. R4C.1 supersedes that relaxation.

## Diagnosis (completed before any digest-contract change)

Per the user directive "先确认第一处差异确实是 artifact_sha256，再改摘要合同", the
diagnosis was performed first, with the confirmatory experiment:

1. Enumerated all 10 distinct artifact paths in the capsule's `resolved_records` (all
   JSON). 9 of them are LF on the Windows working tree (0 CRLF, raw == LF-normalized
   hash). **`reports/petrochina_value_profile.json` is the exception: 1286 CRLF on the
   Windows working tree**, raw sha256 `f0f492da…` ≠ LF-normalized `074b8564…`.
2. The committed blob is LF (49887 bytes, 0 CRLF); the working-tree file is 51173 bytes
   with CRLF. `git status` is clean because CRLF→LF normalizes to the blob. The file was
   regenerated locally by the value-profile tool in Windows text mode (LF→CRLF on write).
3. The capsule's `market_manifest_resolver` hashes this file with raw bytes
   (`rep._sha256(path)` = `path.read_bytes()`), so Windows computes `artifact_sha256 =
   f0f492da…` while a ubuntu clean clone computes the LF hash `074b8564…`.
4. **Confirmatory experiment:** with the file temporarily normalized to LF on disk, the
   fresh capsule digest became `e60f85630c929ea78ba60f182dcff2cf3e74107e156a523400785257f19253de`
   — exactly the ubuntu CI digest. The file was then restored byte-for-byte.

**Conclusion:** the first identity difference IS `artifact_sha256`, and its mechanism is
not "all JSON files have platform line endings" but specifically that one generated
report (`reports/petrochina_value_profile.json`) carries CRLF on the Windows working tree
while git's blob / ubuntu clone is LF. The propagation chain is
`artifact_sha256 → score_input_id → capsule_digest → scenario_id → ledger_digest`.

## Task objective

A single, small, complete governance stage that makes the score-input identity chain
cross-platform deterministic:

1. **Phase 1 — diagnose** (done above; first difference confirmed as `artifact_sha256`).
2. **Phase 2 — shared content digest module** `src/ashare_research/scoring/content_digest.py`
   with two algorithms (`sha256_lf_normalized_bytes_v1` for text artifacts,
   `sha256_raw_bytes_v1` for binary), fail-closed on unknown algorithm.
3. **Phase 3 — upstream digest contract**: `artifact_digest_contract` registered per
   artifact logical path in the upstream registry; `ResolvedRecord` carries
   `artifact_digest_algorithm` + `artifact_byte_size`.
4. **Phase 4 — unify all digest call sites** (lineage, artifact_manifest v2, capsule
   `score_input_id` → ordered `artifact_digests` list, validator, sensitivity).
5. **Phase 5 — ADR share-count correction**: `183,020,977,818 total ordinary shares ≈
   183.021 billion shares ≈ 1,830.21 亿股` (factual evidence, not a hard-coded
   valuation-series input); static tests ban the old wrong values.
6. **Phase 6 — identity migration, not rewrite**: capsule v4, sensitivity v7, migration
   report (economic values / scores / bands / coverage / confidence / stability all
   unchanged), artifact manifest v2. Old v3/v6 preserved as history. Stop if economic
   values change.
7. **Phase 7 — cross-platform CI compare**: fingerprint jobs on ubuntu + windows +
   compare job requiring identical artifact digests, byte sizes, record ids, score-input
   ids, capsule digest, scenario ids, sensitivity ledger digest.
8. **Phase 8 — tests + acceptance**; decision
   `R4D_OFFICIAL_QUARTERLY_FACT_ACQUISITION_ALLOWED` only if actual ubuntu+windows
   fingerprint equality is demonstrated.

## Scope

- `src/ashare_research/scoring/content_digest.py` (new)
- `src/ashare_research/tools/m2_stage2k1r4c1_identity_diagnose.py` (new)
- `src/ashare_research/scoring/lineage.py` (ResolvedRecord + digest contract)
- `src/ashare_research/scoring/capsule.py` (score_input_id → artifact_digests)
- `src/ashare_research/scoring/artifact_manifest.py` (v2 schema + digest_algorithm)
- `src/ashare_research/scoring/validator.py` (digest fields in snapshot comparison)
- `src/ashare_research/scoring/sensitivity.py` (scenario_id unchanged by design; verify)
- `config/value_dimension_scoring_upstream_registry_v1.json` (artifact_digest_contract)
- `docs/decisions/ADR-VALUATION-002-a-share-per-share-convention.md` (share count)
- `src/ashare_research/tools/m2_stage2k1r3_closeout.py` (DEFAULT_MANIFEST → v2)
- `.github/workflows/stage2g-reproducibility.yml` (fingerprint + compare jobs)
- New reports: capsule v4, sensitivity v7, identity migration, manifest v2
- New tests: `tests/test_m2_stage2k1r4c1_cross_platform_identity.py`
- New docs: acceptance + this work record

## Non-goals

- Do NOT start quarterly fact collection/polling/injection (R4D is the next stage).
- Do NOT build historical PE/PB/PS series, valuation percentiles, or update the
  `valuation_attractiveness` shadow.
- Do NOT change scoring weights, thresholds, or any economic value.
- Do NOT change `stability_tolerance=1.0` or the `NOT_STABLE` conclusion.
- Do NOT acquire peers; do NOT start M3.
- Do NOT modify `market_observation_set.py` business semantics.
- Do NOT modify the default DB, protected baselines, protected local files, or the
  pre-existing Stage 2I.2R edit.
- Do NOT create `.codex/`, `.claude/` (other than the existing project files), or git hooks.

## Implementation plan

1. (this record) record opening state + diagnosis.
2. Phase 2: content_digest.py.
3. Phase 3: registry contract + ResolvedRecord fields.
4. Phase 4: unify call sites.
5. Phase 5: ADR fix.
6. Phase 6: generate capsule v4 / sensitivity v7 / migration report / manifest v2.
7. Phase 1 tool: identity diagnostic + local Windows fingerprint.
8. Phase 7: CI workflow fingerprint + compare jobs.
9. Phase 8: tests, acceptance, full verification, commits, push, CI.

## Actual operations

Recorded as executed:

1. Verified opening state (branch `feat/m2-value-assessment-mvp`, HEAD `9a6a167`, local
   == origin; protected files intact; stash preserved).
2. Enumerated the 10 resolved artifact paths; checked CRLF and raw-vs-LF hashes for all
   of them. Found `reports/petrochina_value_profile.json` is the only CRLF file on the
   Windows working tree (1286 CRLF).
3. Confirmed the blob is LF and `git status` is clean (CRLF→LF normalization).
4. Ran the confirmatory experiment: LF-normalized value_profile on disk → fresh capsule
   digest `e60f8563…` (== ubuntu CI digest); restored the file byte-for-byte.
5. Phase 2: created `content_digest.py` (ContentDigest, LF-normalized + raw algorithms,
   fail-closed `digest_file(path, *, algorithm)`); smoke-tested.
6. Phase 3: added `artifact_digest_contract` to the upstream registry (12 JSON paths →
   `sha256_lf_normalized_bytes_v1`); added `artifact_digest_algorithm` + `artifact_byte_size`
   to `ResolvedRecord`; wired `artifact_digest_for_path` into all 5 resolver families.
   (Fixed a tuple-unpacking order bug: `(algorithm, sha256, byte_size)`.)
7. Phase 4: unified call sites — `capsule._record_dict` carries the new fields;
   `score_input_id_for` → ordered `artifact_digests` list; `artifact_manifest.py` v2 schema
   (`m2_stage2k1r4c1_artifact_manifest_v2`) with per-entry `digest_algorithm`;
   `validator.py` accepts the v4 schema; `sensitivity.py` → `build_sensitivity_v7`
   (schema v7). Bumped capsule schema to v4. Updated R3/R4B/R4C tests to the new schemas;
   R4C's platform-aware `test_sensitivity_v6_report_unchanged_digest` replaced with a
   v6-preserved-as-history assertion.
8. Phase 5: ADR-VALUATION-002 line 28 corrected to `183,020,977,818 total ordinary shares
   (≈ 183.021 billion ≈ 1,830.21 亿股)` with a factual-evidence note.
9. Phase 6: generated capsule v4 (`3aa06441…`), sensitivity v7 (`b21d5fb4…`), migration
   report (economic_value_changed=false, scores_changed=false, bands_changed=false,
   coverage_changed=false, confidence_changed=false, stability_status_changed=false;
   24/24 score-input ids changed; 87/87 scenarios kept), manifest v2. Old v3/v6 preserved.
10. Phase 1 tool: created `m2_stage2k1r4c1_identity_diagnose.py`; generated the Windows
    fingerprint (`tmp/r4c1_fingerprint_windows.json`); **simulated ubuntu LF checkout and
    confirmed the fingerprint is byte-identical** (cross-platform identity fixed).
11. Phase 7: added fingerprint build + upload steps and the `identity-compare` job to
    `.github/workflows/stage2g-reproducibility.yml`.
12. Phase 8: wrote `tests/test_m2_stage2k1r4c1_cross_platform_identity.py` (38 tests);
    fixed the value-profile generator to write LF explicitly; normalized the working-tree
    value_profile.json to LF (== committed blob). Wrote the acceptance doc.
13. (Ruff fixes applied; manifest regenerated 3x as files were finalized; full suite
    verification in the Verification section.)

## Verification

- R4C.1 + R4C + R4B + R4A + R3 test files → 103 passed (after manifest regeneration).
- Full suite `pytest tests/ -q` → **1315 passed, 2 warnings** (final-state re-run after
  ruff fixes and sensitivity.py LF normalization: `1315 passed in 154.80s`, exit 0;
  the 2 warnings are the pre-existing quality-validator date-format `UserWarning`s).
- `ruff check src/ tests/` → All checks passed (final state).
- `compileall -q src/ashare_research` → OK; `git diff --check` → OK.
- `sensitivity.py` normalized to LF (my Edit left CRLF on disk; HEAD blob is LF).
- R4C.1 manifest v2 verify → pass (17 files, `digest_algorithm` per entry).
- Cross-platform simulation: Windows fingerprint == ubuntu-LF fingerprint
  (`fingerprint_digest` `5db941f1…` updated to the corrected values).
- Default DB hash `4a71d3c7…` unchanged; protected files intact; stash preserved.

## Result

- Diagnosis: first difference confirmed as `artifact_sha256` of `value_profile.json`
  (CRLF working-tree state), reproduced `e60f8563…` under LF normalization.
- Shared content digest contract + upstream digest contract + unified call sites.
- Capsule v4 / sensitivity v7 / migration report / manifest v2; economics unchanged.
- ADR share-count corrected to `183,020,977,818` (≈ 183.021 billion ≈ 1,830.21 亿股).
- Cross-platform identity: simulated ubuntu/windows fingerprints byte-identical.
- Status: `completed` (CI-backed PASS pending; run `PENDING` on ubuntu + windows).

## Remaining issues

- R4D official quarterly denominator fact collection is NOT started (next stage).
- Historical PE/PB/PS series NOT implemented (by design).
- No production score, no peer acquisition, no M3.
- (The R4C platform-aware relaxation is superseded by R4C.1's cross-platform compare.)

## Final files and Git state

Pre-commit final state (recorded as executed):

- Branch `feat/m2-value-assessment-mvp`; working tree contains the R4C.1 change set
  plus the pre-existing protected items (`AGENTS.md`, `agent/goals/`, the Stage 2I.2R
  wording edit in `acceptance/m2_stage2i2r_...md`).
- New files (8): `src/ashare_research/scoring/content_digest.py`,
  `src/ashare_research/tools/m2_stage2k1r4c1_identity_diagnose.py`,
  `tests/test_m2_stage2k1r4c1_cross_platform_identity.py`,
  `reports/petrochina_score_input_capsule_v4.json`,
  `reports/petrochina_dimension_scoring_sensitivity_v7.json`,
  `reports/petrochina_stage2k1r4c1_identity_migration.json`,
  `reports/m2_stage2k1r4c1_artifact_manifest.json`,
  `acceptance/m2_stage2k1r4c1_cross_platform_identity_closeout.md`.
- Modified files (14): upstream registry, ADR-VALUATION-002, lineage.py, capsule.py,
  artifact_manifest.py, validator.py, sensitivity.py, content digests unified,
  `m2_stage2k1r3_closeout.py` (DEFAULT_MANIFEST → v2), value-profile generator
  (explicit LF writes), 3 prior-stage test files, CI workflow.
- Stash `stash@{0}` preserved; default DB hash `4a71d3c7…` unchanged; protected files
  intact; `reports/petrochina_value_profile.json` working tree == committed blob
  (LF, `074b8564…`).
- Commits + push + CI: recorded below once executed.