# M2 Stage 2K.1R4C.1 — Cross-Platform Identity Unification and ADR Share-Count Correction

Status: `CONDITIONAL PASS`
(R4C.1 identity implementation `LIKELY CORRECT`; cross-platform CI runner
provenance `NOT YET PROVEN` — awaiting the new paired-matrix CI run. The prior
run `30973420125` used the cartesian 4-job matrix and a flat v1 fingerprint with
no provenance, so it could not prove which runner produced which parse.)

## Objective

A single, small, complete governance stage that makes the score-input identity
chain cross-platform deterministic and corrects the ADR share-count figure:

1. **Diagnose first** — confirmed (by experiment, not speculation) that the first
   cross-platform identity difference is `artifact_sha256` of
   `reports/petrochina_value_profile.json` (CRLF on the Windows working tree vs
   LF in the committed blob / ubuntu clean clone).
2. **Shared content digest contract** — `content_digest.py` with
   `sha256_lf_normalized_bytes_v1` (text) and `sha256_raw_bytes_v1` (binary),
   fail-closed on unknown algorithms.
3. **Upstream digest contract** — `artifact_digest_contract` registered per
   artifact logical path; `ResolvedRecord` carries `artifact_digest_algorithm`
   and `artifact_byte_size`.
4. **Unified digest call sites** — lineage, capsule (`score_input_id` →
   ordered `artifact_digests`), artifact manifest (v2 schema), validator.
5. **ADR share-count correction** — `183,020,977,818` total ordinary shares
   (≈ 183.021 billion ≈ 1,830.21 亿股), recorded as factual evidence.
6. **Identity migration, not rewrite** — capsule v4, sensitivity v7, migration
   report, manifest v2; economic values / scores / bands / coverage / confidence
   / stability all unchanged; v3/v6 preserved as history.
7. **Cross-platform CI compare** — ubuntu + windows fingerprints compared with a
   first-mismatch report; any identity difference fails the run.

## Diagnosis (Phase 1)

The user directive required confirming the first difference before changing any
digest contract. The diagnosis proceeded as follows:

1. All 10 distinct artifact paths in the capsule's `resolved_records` are JSON.
   9 of them are LF on the Windows working tree. **`reports/petrochina_value_profile.json`
   is the single exception: 1286 CRLF on disk** (raw sha256 `f0f492da…` ≠
   LF-normalized `074b8564…`).
2. The committed blob is LF (49887 bytes); the working-tree file is 51173 bytes
   with CRLF. `git status` is clean because CRLF→LF normalizes to the blob. The
   file was regenerated locally by the value-profile tool in Windows text mode.
3. `market_manifest_resolver` hashed the file with raw bytes, so Windows
   computed `f0f492da…` while a ubuntu clean clone computed `074b8564…`.
4. **Confirmatory experiment:** with the file temporarily normalized to LF, the
   fresh capsule digest became `e60f8563…` — exactly the ubuntu CI digest. The
   file was then restored byte-for-byte.

**Conclusion:** the first difference IS `artifact_sha256`, and its mechanism is
specifically the one generated report's CRLF working-tree state — not a general
line-ending difference across all JSON fixtures. The propagation chain is
`artifact_sha256 → score_input_id → capsule_digest → scenario_id → ledger_digest`.

## Phase 2 — content digest contract

`src/ashare_research/scoring/content_digest.py`:

- `ContentDigest` frozen dataclass (`algorithm`, `sha256`, `byte_size`).
- `sha256_lf_normalized_bytes_v1`: CRLF→LF, lone CR→LF, no UTF-8 decode/encode;
  applies to text artifacts (JSON, CSV, MD, YAML).
- `sha256_raw_bytes_v1`: raw bytes, no normalization; applies to binary
  artifacts (Parquet, PDF, DuckDB, ZIP, images).
- `digest_text_artifact`, `digest_binary_artifact`, `digest_for_media_class`,
  `digest_file(path, *, algorithm)` — the algorithm is a mandatory keyword; any
  unknown algorithm raises `ContentDigestError` (fail-closed).

## Phase 3 — upstream digest contract

`config/value_dimension_scoring_upstream_registry_v1.json` gains
`artifact_digest_contract` (schema `artifact_content_digest_v1`), mapping each
artifact logical path → `{algorithm, media_class}`. All 12 registered paths are
JSON text artifacts → `sha256_lf_normalized_bytes_v1`. `ResolvedRecord` gains
`artifact_digest_algorithm` and `artifact_byte_size`; every resolver computes the
artifact digest through the registered algorithm (fail-closed on unregistered
paths).

## Phase 4 — unified digest call sites

- `lineage.py`: all resolvers use `artifact_digest_for_path` (registered
  algorithm, never raw-bytes guessing).
- `capsule.py`: `_record_dict` carries the algorithm + byte size;
  `score_input_id` is now an ordered `artifact_digests` list of
  `{artifact_logical_path, algorithm, sha256, byte_size}` (not bare hashes).
- `artifact_manifest.py`: v1 schemas keep the LF-normalized contract; new
  `m2_stage2k1r4c1_artifact_manifest_v2` entries carry `digest_algorithm` and
  are verified with the registered algorithm.
- `validator.py`: capsule schema accepts v4; the audit snapshot comparison
  includes the new digest fields.
- `sensitivity.py`: `build_sensitivity_v7` (schema v7) — scenario ids derive
  from the cross-platform-deterministic capsule v4 digest.

## Phase 5 — ADR share-count correction

`ADR-VALUATION-002` line 28: `~18.302 billion` → **183,020,977,818 total
ordinary shares (≈ 183.021 billion shares ≈ 1,830.21 亿股)**, recorded as factual
evidence from the official dividend/announcement records
(`share_capital_on_record_date` in `events/dividend_events_2021_2026_v2.json`),
**not** a hard-coded valuation-series input. Static tests ban the old wrong
values (`18.302 billion`, `18,302,097,781`, `18,302,097,782`).

## Phase 6 — identity migration (not rewrite)

New reports (old v3/v6 preserved as history):

| Artifact | Old | New |
|---|---|---|
| Capsule | `petrochina_score_input_capsule_v3.json` (digest `fb3a2cc…`) | `petrochina_score_input_capsule_v4.json` (digest `3aa06441…`) |
| Sensitivity | `petrochina_dimension_scoring_sensitivity_v6.json` (ledger `213cdba0…`) | `petrochina_dimension_scoring_sensitivity_v7.json` (ledger `b21d5fb4…`) |
| Migration | — | `petrochina_stage2k1r4c1_identity_migration.json` |
| Manifest | `m2_stage2k1r4c_artifact_manifest.json` (v1) | `m2_stage2k1r4c1_artifact_manifest.json` (v2) |

Migration report verified: `economic_value_changed=false`,
`scores_changed=false`, `bands_changed=false`, `coverage_changed=false`,
`confidence_changed=false`, `stability_status_changed=false`; all 24
score-input ids changed (identity structure), 87/87 scenarios kept, no
scenario dropped.

## Phase 7 — cross-platform CI compare (v1, superseded)

The first attempt built a flat `scoring_identity_fingerprint_v1` on each
clean-clone job (cartesian `os × short` matrix → 4 jobs) and uploaded
`identity-fingerprint-ubuntu/windows` (no commit binding). A new
`identity-compare` job required identical artifact digest algorithms, artifact
SHA-256s, byte sizes, record ids, record digests, score-input ids, capsule
digest, time-contract digest, registry digest, scenario ids, and sensitivity
ledger digest (run `30973420125` PASS, fingerprint digest `8186848b…`).

**Limitation (root of the CONDITIONAL PASS):** the flat v1 fingerprint cannot
prove *which runner* produced which parse — the matrix was a cartesian product
(2 OS × 2 names = 4 jobs), artifact names carried no commit SHA, and provenance
(runner OS / matrix platform) was not part of the fingerprint. The
`identity-compare` outcome therefore proves identity equality but not
cross-platform runner provenance.

## Phase 8 — CI matrix + fingerprint provenance fix (minimal)

A small, complete governance fix (no scoring code, capsule, digest algorithms,
or ADR changed):

1. **Paired matrix include** — `strategy.matrix.include` with exactly two
   entries (`ubuntu-latest/ubuntu`, `windows-latest/windows`); the cartesian
   `os × short` form is removed, so exactly 2 `clean-clone` jobs run.
2. **Unique, commit-bound artifact names** —
   `identity-fingerprint-<platform>-<commit-sha>`; the `identity-compare` job
   downloads exactly these names.
3. **Envelope v2 with independent provenance** — schema
   `scoring_identity_fingerprint_envelope_v2`:
   `provenance {runner_os, matrix_platform, github_sha}` + cross-platform
   `identity` (artifact digests, record ids, score-input ids, capsule digest,
   time contract, registry digest, scenario ids, sensitivity ledger digest) +
   `identity_digest` (canonical SHA-256 of `identity` alone). Provenance is
   strictly outside `identity`, so the two full JSON files differ only in
   provenance.
4. **Hard-gated compare** — the `compare` subcommand first gates on provenance
   (left = ubuntu/`Linux`, right = windows/`Windows`, same `github_sha`), then
   verifies the stored `identity_digest` binds to its own identity payload, then
   deep-compares `identity` and reports the FIRST mismatch path. Any gate
   failure exits non-zero. The compare job also hard-counts exactly two
   fingerprint artifacts.
5. **Tests** — 12 new tests cover the paired matrix, artifact-name uniqueness +
   SHA binding, provenance isolation, both-ubuntu / both-windows compare
   failures, inconsistent runner/platform, differing/missing SHA, distinct
   provenance with identical identity → pass, and per-field identity mismatch →
   first mismatch path (identity_digest computed dynamically).

## Requirements status

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Diagnosis confirms first difference is `artifact_sha256` | DONE | LF-normalization experiment reproduced the ubuntu digest `e60f8563…` |
| 2 | content_digest.py shared module (LF/raw, fail-closed) | DONE | `test_text_lf_and_crlf_same_digest`, `test_binary_crlf_different_digest`, `test_unknown_algorithm_fails_closed` |
| 3 | Algorithm is part of identity | DONE | `test_algorithm_part_of_identity` |
| 4 | Digest path/cwd-independent | DONE | `test_digest_path_independent` |
| 5 | Upstream digest contract registered per path | DONE | `test_registry_digest_contract_covers_all_resolved_paths` |
| 6 | ResolvedRecord carries algorithm + byte size | DONE | `test_resolved_records_carry_digest_algorithm_and_byte_size` |
| 7 | value_profile digest is LF-normalized | DONE | `test_value_profile_digest_is_lf_normalized` |
| 8 | Simulated Windows/Linux → identical identity | DONE | `test_capsule_simulated_windows_linux_identical_identity` |
| 9 | Algorithm/size/SHA tamper fails validator | DONE | `test_capsule_{algorithm,byte_size,sha}_tamper_fails_validator` |
| 10 | Capsule v4 report matches fresh build | DONE | `test_capsule_v4_report_matches_fresh_build` |
| 11 | Sensitivity v7 deterministic scenario ids | DONE | `test_sensitivity_v7_scenario_ids_deterministic` |
| 12 | Sensitivity NOT_STABLE preserved | DONE | `test_sensitivity_v7_not_stable_preserved` |
| 13 | Migration economics unchanged | DONE | `test_migration_report_economics_unchanged` |
| 14 | v3/v6 preserved as history | DONE | `test_v3_v6_preserved_as_history` |
| 15 | Fingerprint envelope v2 + compare first mismatch | DONE | `test_envelope_schema_and_identity_determinism`, `test_identity_field_tamper_reports_first_mismatch` |
| 16 | ADR share count corrected | DONE | `test_adr_share_count_corrected`, `test_adr_share_count_old_wrong_values_banned` |
| 17 | No quarterly facts / no series / no shadow / no weights | DONE | `test_no_quarterly_facts_collected`, `test_no_historical_series_generated`, `test_valuation_shadow_not_modified`, `test_scoring_weights_thresholds_unchanged` |
| 18 | No peer acquisition / no M3 | DONE | `test_no_peer_acquisition_started`, `test_no_m3_started` |
| 19 | Default DB + fact baseline unchanged | DONE | `test_default_db_unchanged`, `test_fact_baseline_unchanged` |
| 20 | R4C.1 manifest v2 verifies and is default | DONE | `test_r4c1_artifact_manifest_v2_verifies_and_is_default` |
| 21 | Paired matrix has exactly two include entries | DONE | `test_ci_matrix_has_only_two_paired_include_entries` |
| 22 | Artifact names unique and bound to commit SHA | DONE | `test_ci_artifact_names_unique_and_sha_bound` |
| 23 | Compare job hard gate + SHA-bound paths | DONE | `test_ci_compare_job_has_hard_gate_and_sha_bound_paths` |
| 24 | Provenance does not pollute identity payload | DONE | `test_provenance_does_not_pollute_identity` |
| 25 | Different provenance + identical identity → PASS | DONE | `test_different_provenance_identical_identity_passes` |
| 26 | Both-ubuntu / both-windows / disguise compare failures | DONE | `test_both_provenances_ubuntu_fails`, `test_both_provenances_windows_fails`, `test_ubuntu_cannot_disguise_as_windows`, `test_inconsistent_runner_platform_fails` |
| 27 | SHA mismatch / missing SHA fails | DONE | `test_different_github_sha_fails`, `test_missing_github_sha_fails` |
| 28 | identity_digest computed dynamically (not the old v1 digest) | DONE | `test_compare_success_identity_digest_is_dynamic` |

## Validation

Covered in the work record's verification section (full suite + static checks + CI).

## Final project state

```text
M2 Stage 2K.1R4C.1:                    CONDITIONAL PASS
Cross-platform implementation:         LIKELY CORRECT
Cross-platform CI runner provenance:   NOT YET PROVEN (awaiting paired-matrix run)
Quarterly denominator acquisition:     NOT STARTED
R4D:                                   BLOCKED BY CI MATRIX PROVENANCE ONLY
```

(Intermediate verdict until the paired-matrix + envelope-v2 CI run proves that
the ubuntu runner produced the left envelope and the windows runner the right
one for the same commit with identical identity payloads.)

```text
ADR share-count factual accuracy:   TRUSTED (183,020,977,818 total ordinary shares)
Artifact digest contracts:          TRUSTED (content_digest_v1, per-path)
Economic values:                    UNCHANGED
Sensitivity:                        NOT_STABLE (unchanged)
PIT quarterly denominators:         ACQUISITION REQUIRED
Historical PE/PB/PS:                NOT IMPLEMENTED
Production scoring:                 NOT ALLOWED
Peer acquisition:                   NOT ALLOWED
M3:                                 NOT STARTED
```

## Git state

- Branch: `feat/m2-value-assessment-mvp`; pushed to `origin`; the paired-matrix
  + envelope-v2 fix is committed locally and awaiting push + CI (replaces the
  cartesian 4-job matrix of run `30973420125`).
- Protected files (AGENTS.md, agent/goals/, Stage 2I.2R edit, default DB, stash) untouched.
- No force push, no reset --hard, no git clean.