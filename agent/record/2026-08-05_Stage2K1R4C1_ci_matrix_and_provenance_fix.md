# Work record: M2 Stage 2K.1R4C.1 — CI matrix + fingerprint provenance minimal fix

Status: `in_progress`

## Basic information

- Date: 2026-08-05
- Agent: Claude Code
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `b4a63f7` (R4C.1 CI-backed closeout evidence, run `30973420125`)
- Task source: user directive (最小修复方案 — CI 矩阵 + 指纹 provenance，不回到大阶段)
- Module: value assessment (cross-platform CI governance)

## Task objective

Small, complete governance fix. Do NOT change scoring code, capsule, digest
algorithms, or ADR. Only change CI and a small part of fingerprint provenance:

1. **Paired matrix include** — replace the cartesian `os × short` matrix (4 jobs)
   with two explicit include pairs (`ubuntu-latest/ubuntu`, `windows-latest/windows`),
   so exactly 2 clean-clone jobs run.
2. **Unique, commit-bound artifact names** — `identity-fingerprint-<platform>-<sha>`
   (e.g. `identity-fingerprint-ubuntu-b4a63f7…`); compare job downloads these exact
   names.
3. **Independent provenance, not polluting the identity payload** — new envelope
   schema `scoring_identity_fingerprint_envelope_v2` with separate
   `provenance {runner_os, matrix_platform, github_sha}` and cross-platform
   `identity` sections plus `identity_digest`. Compare must first gate on
   provenance (left = ubuntu/Linux, right = windows/Windows, same sha), then
   compare only `identity` + `identity_digest`.
4. **Compare job hard gates** — exactly 2 artifacts, unique names, valid ubuntu
   provenance, valid windows provenance, same github_sha, same identity_digest,
   identical identity payload; any failure exits non-zero.
5. **Tests** — matrix has only the two include entries; ubuntu artifact name !=
   windows artifact name; artifact name contains commit SHA; ubuntu envelope
   cannot disguise as windows; both-ubuntu compare fails; both-windows compare
   fails; different sha fails; different provenance with identical identity
   passes; any identity field difference reports first mismatch; identity_digest
   computed dynamically (not the old v1 digest).
6. **Re-run CI** — expect exactly `clean-clone (ubuntu)`, `clean-clone (windows)`,
   `identity-compare` and two unique artifacts; then update acceptance to
   `Cross-platform runner provenance: TRUSTED` /
   `Ubuntu/Windows identity payloads: IDENTICAL` / `R4D ... ALLOWED`.

## Scope

- `.github/workflows/stage2g-reproducibility.yml` (matrix include, artifact names,
  compare download + hard gates)
- `src/ashare_research/tools/m2_stage2k1r4c1_identity_diagnose.py` (envelope v2,
  provenance, identity_digest, gated compare)
- `tests/test_m2_stage2k1r4c1_cross_platform_identity.py` (fingerprint section
  updated + new envelope/provenance/matrix tests)
- `acceptance/m2_stage2k1r4c1_cross_platform_identity_closeout.md` (CONDITIONAL
  PASS state, then TRUSTED after the new CI run proves provenance)
- `agent/record/2026-08-05_Stage2K1R4C1_ci_matrix_and_provenance_fix.md` (this record)
- `reports/m2_stage2k1r4c1_artifact_manifest.json` (regenerate — covers the
  workflow, diagnose tool, test file, acceptance doc)

## Non-goals

- Do NOT modify scoring code, capsule schema, digest algorithms, or ADR.
- Do NOT change economic values, sensitivity NOT_STABLE, or any report content.
- Do NOT start quarterly fact acquisition (R4D) — it stays blocked until the new
  CI run proves cross-platform provenance.
- Do NOT touch protected files (AGENTS.md, agent/goals/, Stage 2I.2R edit, default
  DB, stash).

## Opening state (verified)

- Branch `feat/m2-value-assessment-mvp`; HEAD `b4a63f7`; local == origin (0 ahead).
- Final CI run `30973420125` PASS; evidence commit `b4a63f7` pushed.
- Current fingerprint schema `scoring_identity_fingerprint_v1` (flat); current
  workflow matrix is the cartesian `os × short` (4 jobs). This is the design flaw
  being fixed: 4 jobs (2 per platform) and no cross-platform provenance proof.
- Protected files intact; `yaml` 6.0.3 available for workflow-content tests.
- Diagnose tool referenced only by the workflow and the R4C.1 test file.

## Implementation plan

1. (this record) record task + opening state.
2. Diagnose tool → envelope v2: `build_identity()`, `build_envelope()`,
   `identity_digest()`, `compare_envelopes()` with provenance gates; CLI args
   `--matrix-platform` / `--github-sha` (default `GITHUB_SHA` env).
3. Workflow → paired include matrix, sha-bound artifact names, exact-name
   downloads, hard-gate step (exactly 2 files), compare command.
4. Tests → update fingerprint section to envelope API; add matrix/provenance/
   compare tests.
5. Acceptance → intermediate CONDITIONAL PASS verdict block.
6. Regenerate manifest; verify; commit; push; CI run (expect 3 jobs).
7. After CI PASS: update acceptance to TRUSTED + R4D allowed; regenerate
   manifest; evidence commit; final report.

## Actual operations

Recorded as executed:

1. Verified opening state (branch `feat/m2-value-assessment-mvp`, HEAD `b4a63f7`,
   local == origin; protected files intact). Confirmed `yaml` 6.0.3 available; the
   diagnose tool is referenced only by the workflow and the R4C.1 test file.
2. Diagnose tool rewritten to envelope v2: `build_identity()` (cross-platform
   payload), `build_envelope()` (provenance from `platform.system()` +
   `--matrix-platform` + `GITHUB_SHA`/`--github-sha`), `identity_digest()`
   (canonical SHA-256 of `identity` alone), `compare_envelopes()` with hard gates
   (schema → provenance_left ubuntu/Linux → provenance_right windows/Windows →
   github_sha → identity walk first-mismatch → identity_digest binding). CLI:
   `fingerprint --output [--matrix-platform P] [--github-sha S]` + `compare a b`.
3. Local Windows smoke test: an ubuntu envelope cannot be produced on Windows
   (runner_os is honest — `--matrix-platform ubuntu` still fails the left gate),
   confirming the provenance honesty property.
4. Workflow: cartesian `os × short` matrix → paired `matrix.include` (2 jobs);
   fingerprint build passes `--matrix-platform`; artifacts named
   `identity-fingerprint-<platform>-<github.sha>`; compare job downloads the two
   exact names, hard-counts exactly 2 files, and runs the gated compare.
5. Tests: fingerprint section rewritten to the envelope API; 12 new tests added
   (matrix include, artifact naming, provenance isolation, both-ubuntu /
   both-windows / disguise / inconsistent-runner failures, SHA mismatch/missing,
   identical-identity-different-provenance pass, first-mismatch path, dynamic
   identity_digest). R4C.1 file: 38 → 50 tests.
6. Fixed a dropped `provenance_left` gate introduced while line-wrapping the
   compare gates (ruff E501) — caught by the both-windows test.
7. Acceptance doc updated to `CONDITIONAL PASS` with the Phase 8 section and the
   intermediate verdict block (runs 21–28 added to the requirements table).
8. Manifest regenerated (covers workflow, diagnose tool, test file, acceptance).

## Verification

- R4C.1 test file (bare pytest): **50 passed**.
- `ruff check` on the diagnose tool + test file: All checks passed.
- Workflow YAML parses; jobs = `clean-clone`, `identity-compare`.
- CLI e2e: ubuntu-vs-windows → `identical: true` (gate ok); ubuntu-vs-ubuntu →
  gate `provenance_right`, exit 1; exit codes 0/1 correct.
- Manifest v2 verify: pass.
- Full suite (bare pytest, CI-like): **1327 passed, 2 warnings** (151.34s).

## Result

- CI run `30974967062` **PASS** — exactly 3 jobs as specified:
  `clean-clone (ubuntu-latest, ubuntu)`, `clean-clone (windows-latest, windows)`,
  `identity-compare`; 2 unique sha-bound artifacts.
- Provenance-gated compare: `identical: true`, `gate: ok`; left provenance
  `Linux`/`ubuntu` and right provenance `Windows`/`windows`, both bound to the
  same commit `f5a6ab552e3dc72da936bad8abd0a47b97a106ae`; identity digest
  `1843da77159fbc55b9dd66185caab8c4af8d29560584b872c66e503808ec5665`.
- **Cross-platform runner provenance: TRUSTED**; **ubuntu/windows identity
  payloads: IDENTICAL**; acceptance updated from CONDITIONAL PASS to PASS;
  `R4D_OFFICIAL_QUARTERLY_FACT_ACQUISITION_ALLOWED`.
- No scoring code, capsule, digest algorithms, or ADR changed; economic values,
  NOT_STABLE, and all business state unchanged.

## Remaining issues

- Quarterly denominator acquisition (R4D) is now ALLOWED but NOT started (next
  stage, outside this fix's scope).
- Historical PE/PB/PS series NOT implemented (by design).
- No production score, no peer acquisition, no M3.

## Final files and Git state

- Commits: `9f391b3` (paired matrix + envelope v2 provenance fix),
  `f5a6ab5` (acceptance CONDITIONAL PASS + work record), then the CI-evidence
  commit below (recorded as executed).
- Branch `feat/m2-value-assessment-mvp`; pushed to origin; protected files
  (AGENTS.md, agent/goals/, Stage 2I.2R edit, default DB, stash) untouched.

## Decision records

- **Envelope vs flat fingerprint**: identity payload stays free of provenance so
  the two full JSON files differ only in `provenance`; `identity` + `identity_digest`
  are the cross-platform-identical parts. Alternative (flat v1) cannot prove
  provenance because adding platform fields to the flat payload makes the files
  differ. Adopted envelope v2.
- **runner_os from `platform.system()`** on CI: ubuntu runners → Linux, windows
  runners → Windows — matches the user-specified provenance contract.
- **identity_digest computed dynamically in tests** (not the old `8186848b…`,
  which was the v1 flat-schema digest). The v2 identity_digest is a new value.
- **Matrix platform passed explicitly** (`--matrix-platform` from the workflow
  matrix); github_sha read from `GITHUB_SHA` env (set by GitHub Actions), with a
  CLI override for tests/local.