# Goal: failure-safe capsule database publication

- Objective: build_temp_fact_db publishes only a fully validated, closed DuckDB;
  failed builds and competing destination creation preserve caller-owned output.
- Verified baseline: origin/main and live main ae00efe7d5aa7cd592339b199c65281b9c1c441d.
  Clean dedicated branch codex/capsule-atomic-publication at that commit.
- Protected: primary M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
  stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; research.duckdb SHA256
  4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
  Preserve all dirty/untracked primary files and existing worktrees.
- Allowed: src/ashare_research/reproducibility/capsule.py,
  tests/test_capsule_output_preservation.py, this Goal and corresponding record.
- Forbidden: provider calls, real-data admission, backtests, fixtures/schema edits,
  threshold changes, other product modules, remote publication or merging.
- Required behavior: retain early existing-file/directory/symlink refusal and
  invalid-snapshot behavior; construct in owned temporary directory beside target,
  close on every exit, publish with atomic no-clobber hard link. No overwrite fallback
  if filesystem disallows hard links. Remove only owned temporary artifacts.
- Tests: injected insertion/validation failures leave no target or staging debris;
  a target created during build survives byte-for-byte; successful database is
  readable with expected contents; unsupported publication fails closed.
- Exact commands (PowerShell, PYTHONPATH set to absolute src):
  python -m pytest tests/test_capsule_output_preservation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
  python -m ruff check src/ashare_research/reproducibility/capsule.py tests/test_capsule_output_preservation.py
  git diff --check; git diff --cached --check
- Acceptance: meaningful regressions pass, existing behavior passes with explicit
  platform/data skips, parent reviews actual diff and independent test evidence,
  protected hashes/stash unchanged. Record limitations honestly.
- Stop: scope expansion, unexpected protected changes, two failed repair attempts.
- Commit: scoped local commit after review; no push, PR merge or next research stage.
