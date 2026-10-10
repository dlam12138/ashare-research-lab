<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Record: CI-parity preflight for the mainline landing

## Task contract (this record doubles as contract and acceptance)

Objective: de-risk the authorized push/PR of codex/financial-json-review by
pre-executing, locally at the landing tip and read-only outside tmp/, every
commit-triggered CI step that can run on a single platform; record exact
results, environmental deviations and residual cross-platform risk. Docs-only
single commit; no push, PR, merge or DSH.

Baseline at task start: delivery worktree clean at
1e63fe59637d3ee7ce10d453f3a8bd70620fa133; live remotes unchanged (main
47dbb678, feat/m2-value-assessment-mvp ecb74a41, delivery branch absent);
root worktree, primary database and stash unchanged. All seven workflows in
.github/workflows trigger on `push: branches ["**"]` and `pull_request`, so a
branch push and the PR will run all of them (ubuntu+windows matrix).

## What CI will run (inventory)

- stage2g-reproducibility: verify-clean-clone; ruff/compileall; stage2g,
  m2_stage2k1r4d and petrochina_risk_veto verify-contracts; test-capsule
  build A/B + compare; run A/B + verify-artifacts + compare-runs; full
  `pytest -q`; identity fingerprint (ubuntu+windows) + cross-platform
  compare.
- m3-integration-closeout: three governance test files; Stage 3E closeout
  validator; README closeout consistency gate; ruff/compileall; integration
  identity envelope (ubuntu+windows) + compare.
- m3-stage3car2-digest-identity: digest probe (ubuntu+windows) + compare.
- m3-stage3cb / m3-stage3cc / m3-stage3da / m3-stage3db: targeted synthetic
  test selections; static gates; offline validators/envelopes + compares.

## Executed evidence at tip 1e63fe5 (windows side and portable steps)

Commands ran from the delivery worktree with
D:/量化分析-m4a2i/.venv/Scripts/python.exe and PYTHONPATH=src; full output
logs left at tmp/ci-parity-20261010/batch1..4.log (ignored).

- Clean-clone gate: in the long-lived worktree `verify-clean-clone` fails on
  protected `stash` (cb568efd) and ignored `output/value_assessment` residue
  (.gitignore:34 default output dir) - both environmental. In a true clean
  clone (C:/Users/111/AppData/Local/Temp/financial-clean-clone-20261010,
  branch at 1e63fe5, no stash, no output dir) the gate reports
  `"status": "pass"`, `output_or_cache_present: false`, `stash_present:
  false`. CI uses fresh checkouts, so it will pass there.
- Static gates: `ruff check src/ tests/`, `ruff check src tests`,
  `compileall -q src`, `compileall -q src tests` - all exit 0.
- Contract gates: stage2g verify-contracts (pass_with_explicit_gaps),
  m2_stage2k1r4d verify-contracts, petrochina_risk_veto verify-contracts -
  all exit 0. README closeout consistency gate prints
  M3_README_CLOSEOUT_STATUS_CONSISTENT.
- Targeted pytest union of every CI selection (stage3e closeout, 3dbr1,
  3dbr2, 3cb, 3cc, 3ca pipeline, 3car2 portability, 3da, 3db, project entry,
  research entry, financial): 239 passed, 1 skipped in 94.17s (the skip is
  the known symlink-privilege skip).
- Capsule sequence: build A/B pass; compare-capsules pass; run A +
  verify-artifacts pass (sha256 44690ca0d58fc22048c7e083e28d75e182bfbb3c65a6768b2cef1d4b36f790aa);
  run B + verify-artifacts pass with the identical sha256; compare-runs
  pass. Identity fingerprint envelope written
  (keys: identity, identity_digest, provenance, schema, version).
- M3 validators and identity envelopes: m3_stage3e_closeout_check PASS;
  m3_stage3car2 digest probe envelope + compare MATCH; stage3cb envelope +
  compare MATCH; stage3cc envelope + compare MATCH;
  m3_stage3da_contract_check -> M3_STAGE3DA_HOLDOUT_CONTRACT_READY +
  compare MATCH (`holdout_status: SEALED`); m3_stage3db_preunseal_check ->
  M3_STAGE3DB_PREUNSEAL_READY + compare MATCH (`stage3db_status:
  PRE_UNSEAL_READY`).
- Full `pytest -q` reuse: 3206 passed / 8 skipped / 2 warnings at 11874aa,
  the code-identical ancestor of the current tip (the commits after it add
  only review/landing markdown documents, no runtime code). No test reads
  agent/goals or agent/record beyond five fixed, untouched paths, so the
  evidence is unaffected by the docs-only delta; the fresh 239-test union
  above re-covers every CI-specific test selection at the exact tip.

## Cross-platform comparison integrity

- .gitattributes forces `eol=lf` for *.md/*.py/*.yml/*.json/*.csv/*.yaml;
  README.md and the new source files hash identically as blobs and worktree
  bytes locally, so the identity envelopes' file hashes are byte-stable
  across ubuntu/windows checkouts.
- The car2 envelope embeds no platform field
  (`repository_absolute_path_in_payload: false`); the closeout envelope
  carries head_sha/README hash/decision fields only.
- Local compare simulations exercised the exact CI compare code and field
  asserts (self-pair on one platform); ubuntu legs themselves are not
  locally reproducible.

## Residual risks (stated, not suppressed)

- Ubuntu matrix legs and the cross-platform compare jobs cannot run on this
  machine; they depend on GitHub runners. Mitigations: LF-forced bytes,
  deterministic JSON, no platform fields, and the same workflows green at
  main 47dbb678 for the unchanged inputs.
- CI uses Python 3.11; local interpreter is 3.13.9 (DuckDB 1.5.5). The full
  suite and every gate above pass on 3.13; 3.11 was not available locally.

## Acceptance, protections, stop conditions, commit

- Acceptance: exactly one local docs commit containing only this record;
  owner worktree clean afterwards; protection sweep (68 trees, 404 hashes,
  primary DB SHA256, stash, origin refs) unchanged except this branch's own
  HEAD advancing.
- Forbidden in this task: code/test/README changes, push, PR creation,
  merges, force-push, DSH, primary-database access, foreign worktree edits,
  cleanup of the environmental `output/` or the user stash.
- Stop conditions: any unexplained failure, protection drift, or scope
  expansion. All observed failures were attributed and shown environmental.
- The landing itself remains blocked on explicit user authorization; this
  record only upgrades its risk evidence.
