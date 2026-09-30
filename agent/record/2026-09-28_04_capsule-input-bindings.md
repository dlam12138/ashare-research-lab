# Capsule input bindings

Date: 2026-09-28. Module: reproducible value-assessment infrastructure.
User requested continuation of engineering stability work.
Goal: agent/goals/2026-09-28_capsule_input_bindings.md.
Baseline: clean codex/capsule-manifest-completeness at 43bf85958ec4fe92c0ed0e220b4fa169f86efa89.
Working branch: codex/capsule-input-bindings, existing isolated worktree.

Inspected branch/HEAD/worktrees/remote/stash/protected DB hash and recent records.
Verified runner uses declared fact hash/count/version in report input contract.
Reproduced in TemporaryDirectory using committed fixture: set fact hash to 64
zeroes, count to 999, mode to real, market test_only false, recompute logical
digest. Unmodified baseline verifier accepted it. No real inputs accessed.

Plan: bind metadata to verified artifacts and enforce current test-only labels;
delegate bounded code/tests per routing; parent checks integration/protected state.
Keep builder output bytes and research methods unchanged. No claim of provenance
authentication against coordinated file-and-manifest rewrites.

Implementation and final validation completed on 2026-09-30; evidence below.

## 2026-09-30 resumption through DSH

User corrected routing: primary agent/agent.md requires DSH, superseding stale
Luna rules in this worktree. Previous built-in worker was interrupted; its
unvalidated 79-insertion/1-deletion capsule.py draft remains for inspection.
No tests from that worker exist and no commit/push occurred. Parent verified
actual HEAD 43bf859, origin/live main ae00efe, unchanged protected DB/stash and
primary user changes. DSH executable is available. Only DSH will receive the
bounded implementation continuation; parent retains Git and independent review.

## Final implementation and independent acceptance (2026-09-30)

Verdict: PASS.

Executed one bounded `dsh --profile headless` task in this worktree, explicitly
overriding stale Luna routing. DSH reviewed the inherited draft, tightened hash
shape checks and added 60 regression/compatibility cases in the authorized test
module. No built-in subagent was resumed. Parent inspected actual implementation,
all new tests and caller behavior; no Git authority was delegated.

Verifier now binds fact hash/count to validated snapshot, market hash/count to
verified CSV, and requires canonical paths, exact input mappings, strict bool
test labels, test_capsule mode, false network/default-DB flags and optional
fact contract version consistency. Invalid metadata fails before runner output.
Builder, dataset bytes, DB selection, schemas and research methods are unchanged.

DSH validation caveat: its literal focused pytest command failed with WinError 5
on temporary directory permissions. Its escalation attempt was rejected because
the harness had no approval channel. DSH reported a transient in-process mkdir
mode shim run: 60 passed; baseline source run 52 failed / 8 passed, then restored
the draft byte-exactly. Those shimmed results are not treated as the exact-command
acceptance evidence. DSH scoped Ruff and whitespace checks passed.

Parent independently reran baseline reproduction from `git show 43bf859:src/ashare_research/reproducibility/capsule.py`
in memory: incorrect hash/count/labels accepted by baseline, confirming the defect.
Parent exact compatibility validation, without DSH's shim:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests/test_capsule_input_bindings.py tests/test_capsule_manifest_validation.py tests/test_capsule_output_preservation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
python -m ruff check src/ashare_research/reproducibility/capsule.py tests/test_capsule_input_bindings.py
git diff --check
```

Results: 181 passed, 4 skipped in 38.90s; Ruff all checks passed; whitespace passed.
Two skips require symlink privilege; two require absent real baostock snapshots.
No tests weakened or skipped to obtain acceptance. Parent loaded old/new builders
against the same committed fixture in TemporaryDirectory: full manifest equality,
manifest byte equality and cross-version compare_capsules all passed.

Stable validated SHA256 after DSH restored and froze edits:
- capsule.py: 222366608759c86ed2c8d9572101e271d94cabf3b12d305c8824f7254ca3bc2b
- new test module: 5fd904625ff9586dfa97c62868691013d97c176bd1f58290df89b4ffed7a3892

Protected DB remains 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6;
stash remains cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f. Primary status, tracked
diff and HEAD exactly match resumption baseline. Other user worktrees untouched.
DSH removed its untracked .pytest-tmp-run before final handoff; ignored diagnostic
scratch remains under tmp/capsule-input-bindings-scratch. It is not committed,
and no unrelated ignored data is cleaned up.

Changed files: capsule.py, test_capsule_input_bindings.py, this record and Goal.
Final branch codex/capsule-input-bindings, scoped local commit identified in
handoff; base codex/capsule-manifest-completeness@43bf85958ec4fe92c0ed0e220b4fa169f86efa89.
origin/main and live main remain ae00efe7d5aa7cd592339b199c65281b9c1c441d;
no remote feature branch, push, PR or merge. Staged diff and final clean state
checked during commit delivery. Existing two local prerequisite fixes included
in branch ancestry, unchanged by this task.

Limits: consistent metadata is not provenance authentication against coordinated
artifact/manifest rewrites. Runtime temporary DB selection and filesystem races
remain outside scope. No provider acquisition, real backtest or new research stage
started. Engineering increment complete; continuing research needs its own scope.
