# Goal: bind capsule input declarations to validated artifacts

- Objective: prevent internally inconsistent capsule input hashes/counts and
  misleading real/test labels from passing verification and entering run reports.
- User authorization: continued engineering stability and existing functionality.
- Execution route (reverified 2026-09-30): DSH via dsh --profile headless,
  per primary agent/agent.md and explicit user correction. This supersedes stale
  Luna entries in the isolated worktree. No built-in subagents or recursive delegation.
- Baseline: clean codex/capsule-manifest-completeness at
  43bf85958ec4fe92c0ed0e220b4fa169f86efa89; new codex/capsule-input-bindings.
  origin/main and live main ae00efe7d5aa7cd592339b199c65281b9c1c441d.
- Protected M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
  stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; database SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
- Allowed: src/ashare_research/reproducibility/capsule.py,
  tests/test_capsule_input_bindings.py, this Goal and corresponding record.
- Forbidden: data/provider acquisition, real backtests, fixture/schema/threshold
  changes, other modules, deletion or mutation of user data, remote push/merge.
- Required behavior: keep current generated manifest bytes unchanged. Verifier
  requires mode=test_capsule, network_used is False, default_db_mutated is False;
  exactly canonical_fact_snapshot and market_snapshot input mappings, canonical
  relative paths, authoritative is False and test_only is True for both inputs.
  Facts hash and integer (not bool) count match validated snapshot; market hash
  matches verified CSV output and count matches CSV DictReader records. Missing,
  malformed or inconsistent declarations raise ValueError. Optional fact
  contract_version, if present, must match SNAPSHOT_CONTRACT (runner consumes it).
  Do not modify builder labels, actual data, or runtime DB selection in this task.
- Tests: rehash each deliberately altered manifest; cover input shapes, missing
  fields, paths, both hashes/counts including bool/string values, exact bool flags,
  mode and optional fact version. Confirm malformed capsule rejected before
  run_formal or output creation. Valid capsule runs/comparisons remain compatible.
- PowerShell validation prerequisite:
  $env:PYTHONPATH = (Join-Path (Get-Location) 'src')
- Validation commands:
  python -m pytest tests/test_capsule_input_bindings.py -q
  python -m pytest tests/test_capsule_input_bindings.py tests/test_capsule_manifest_validation.py tests/test_capsule_output_preservation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
  python -m ruff check src/ashare_research/reproducibility/capsule.py tests/test_capsule_input_bindings.py
  git diff --check; git diff --cached --check
- Acceptance: actual baseline reproduction, meaningful new tests and related
  compatibility suite pass with explicit skips; parent independent review and
  unchanged protected state. Record exact commands/results and limitations.
- Stop on scope expansion, valid manifest incompatibility, two failed repairs.
- Delivery: scoped local commit; no push, PR merge or new research stage.
