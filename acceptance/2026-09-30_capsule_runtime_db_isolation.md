# Capsule runtime database isolation acceptance

Final verdict: PASS.

## Scope and implementation

Goal: agent/goals/2026-09-30_capsule_runtime_db_isolation.md.
Base: codex/capsule-postmerge-acceptance at
217c45fe53c2be978848d4f3f11d1295d4b2a4f7; remote main/origin/main
209b06c3507e9def970b43bcdc5ce03a61b223fc.
Repair branch: codex/capsule-runtime-db-isolation in the existing isolated worktree.

run_test_capsule now verifies the manifest first, builds a fresh database from
that verified snapshot in an owned system temporary directory, and keeps it
alive through formal execution and artifact verification. It never reads or
modifies the capsule's pre-built temporary_fact.duckdb. Missing/foreign/corrupt
caches do not alter results. Existing formal/real-mode algorithms, builder,
portable inventory, cache bytes, fixtures and frozen research contracts remain
unchanged. Normal cleanup removes only the owned runtime directory; cleanup
OSError warns with retained path while preserving the result or primary error.

Changed files (six in this repair):
- src/ashare_research/tools/stage2g_reproducibility.py
- tests/test_capsule_runtime_db_isolation.py
- tests/test_capsule_input_bindings.py
- agent/goals/2026-09-30_capsule_runtime_db_isolation.md
- agent/record/2026-09-30_04_capsule-runtime-db-isolation.md
- this acceptance file

The previous audit remains an honest historical CHANGES_REQUIRED result; this
new repair acceptance supersedes its runtime database gap only. No new research
stage or blanket whole-project safety verdict is implied.

## Independent baseline and repair evidence

Parent ran the same real synthetic probe before/after implementation. Only a
TemporaryDirectory-owned cache was altered; no real inputs used. The probe wraps
real run_formal to capture facts actually read and then executes real processing
and artifact verification. Six revenue facts were doubled in the unused cache.

Exact PowerShell probe (run in this worktree):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src'); @'
import hashlib
import json
import tempfile
from pathlib import Path
import duckdb
from ashare_research.reproducibility.capsule import build_test_capsule, verify_capsule_manifest
from ashare_research.tools import stage2g_reproducibility as runner
from ashare_research.tools.petrochina_valuation_and_value_profile import _load_canonical_facts
snapshot = Path('tests/fixtures/stage2g/canonical_fact_snapshot_v1')
with tempfile.TemporaryDirectory(prefix='capsule-runtime-binding-probe-') as owned:
    root = Path(owned)
    capsule = root / 'capsule'
    manifest = build_test_capsule(capsule, committed_snapshot_dir=snapshot)
    cache = capsule / 'temporary_fact.duckdb'
    original, _ = _load_canonical_facts(cache)
    with duckdb.connect(str(cache)) as db:
        db.execute("UPDATE financial_facts SET value = value * 2 WHERE concept_id = 'revenue'")
    before_hash = hashlib.sha256(cache.read_bytes()).hexdigest()
    assert verify_capsule_manifest(capsule) == manifest
    captured = {}
    real_run = runner.run_formal
    def capture_run(**kwargs):
        facts, _ = _load_canonical_facts(kwargs['fact_db'])
        captured['facts'] = facts
        captured['database'] = Path(kwargs['fact_db'])
        return real_run(**kwargs)
    runner.run_formal = capture_run
    result = runner.run_test_capsule(capsule, output_root=root / 'runs', run_id='binding-probe')
    expected = {r['fact_id']: r['value'] for r in original if r['concept_id'] == 'revenue'}
    consumed = {r['fact_id']: r['value'] for r in captured['facts'] if r['concept_id'] == 'revenue'}
    print(json.dumps({'revenue_facts': len(expected), 'consumed_verified_snapshot_values': expected == consumed, 'consumed_cache': captured['database'] == cache, 'cache_preserved': before_hash == hashlib.sha256(cache.read_bytes()).hexdigest(), 'runtime_db_exists_after_return': captured['database'].exists(), 'runner_status': result['status'], 'artifact_verification': result['artifact_verification']['status']}))
'@ | python -
```

Baseline result (exit 0): consumed_verified_snapshot_values=false,
consumed_cache=true, cache_preserved=true, runtime_db_exists_after_return=true,
runner_status=pass, artifact_verification=pass.
Repair result (exit 0): consumed_verified_snapshot_values=true,
consumed_cache=false, cache_preserved=true, runtime_db_exists_after_return=false,
runner_status=pass, artifact_verification=pass. Both observed six revenue facts.

Independent regression against baseline source, loaded in memory without
changing worktree files:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
@'
import subprocess
import pytest
from ashare_research.tools import stage2g_reproducibility as runner
source = subprocess.check_output(['git', 'show', '217c45f:src/ashare_research/tools/stage2g_reproducibility.py'], text=True, encoding='utf-8')
exec(compile(source, '<verified-baseline-runner>', 'exec'), runner.__dict__)
raise SystemExit(pytest.main(['tests/test_capsule_runtime_db_isolation.py::test_changed_snapshot_values_are_consumed_and_cache_is_untouched', '-q', '--tb=short']))
'@ | python -
```

Expected exit 1: one failed assertion, old cached value 9216100.0 versus verified
snapshot value 9216101.0. This confirms the new regression detects the defect.

## Parent validation

The exact ten-module focused pytest command is in the Goal. Initial run:
3 failed, 210 passed, 4 skipped in 102.09s. All three failures were new test
configuration errors: compared runs used different run IDs, which appear in
summary.json/run_manifest.json and summary.md. Parent inspected actual outputs
and confirmed the differing fields/line. DSH corrected compared run IDs to the
same value in separate roots, matching the existing reproducibility contract;
all checksum and comparison assertions retained, comparator/source unchanged.

After correction:
`python -m pytest tests/test_capsule_runtime_db_isolation.py -q -rs`:
14 passed in 16.57s. Final exact ten-module retry: exit 0,
213 passed, 4 skipped in 102.78s. Two symlink cases lack account privilege;
two real-baostock cases lack external snapshots. These existing skips were not
introduced or relaxed by the repair; no new skip conditions were added.
`& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests`:
all checks passed, pinned Ruff 0.13.2.
`git diff --check` and `git diff --cached --check`: passed.

Regressions cover actual foreign/corrupt/missing-cache formal runs, changed
snapshot values/row counts/context/lineage versus stale caches, fresh paths on
repeated runs, build/run/artifact errors, pre-existing output preservation,
runtime lifecycle during verification and cleanup OSError result/error handling.
Only the obsolete cache-path assertion in existing binding tests changed; it
now asserts stronger runtime ownership, in-run existence, post-run cleanup and
cache-byte preservation while retaining all declared-input assertions.

Validated product/test SHA256:
- runner: 5dbcfe4b722354b39e3db95bbe58b5cde4673ddb62a12291d98be2e9d10d1c5e
- new regressions: 903114667a8490d27fed1f436d2a27d7b5ce66fb788916ecb01dfe935993dcee
- existing binding tests: e2db6f7f1c6afe519acde051ef8db55b2b7b3cf553794cb3d2d6a5ecd3706abc

## Protected state and delivery

Final parent review: actual diff and six staged paths match Goal; source/test
hashes match the validated final suite. Protected primary status, binary diff,
HEAD and stash exactly equal captured baseline. Primary HEAD remains
3679b1bac7a1634c6452784a4d8f6d139966f222, stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, and database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
All pre-existing user changes, ignored runtime data and other worktrees retained.
No forbidden tracked paths changed. Final repair commit identity is reported in
the final handoff; local repair branch will be two commits ahead of origin/main
(one prior audit plus this repair). No tracked/untracked task residue remains
after the scoped commit; normal ignored test/lint caches are retained.
No push/PR/merge required by this Goal. Remote main retains the old runner until
this local repair is integrated; do not claim this commit has hosted CI evidence.
No next stage begun.

Limits: each test run rebuilds the bounded snapshot database. Cleanup failures
can retain owned temporary data and emit warnings; non-OSError/logging failures
are not suppressed. This repair does not authenticate source provenance or
protect against concurrent mutation of portable inputs. Real-data research,
provider acquisition and holdout execution remain unauthorized.
