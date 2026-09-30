# Capsule builder output guard acceptance

Local verdict: PASS. Hosted delivery is pending at this commit; final PR, exact
head/merge identity and check results must be independently read from GitHub and
reported in the final evidence packet. This document does not claim a future merge.

Goal: agent/goals/2026-09-30_capsule_builder_output_guard.md.
Verified base: origin/main and live main
74418cc39c89945aa1a45e4627ee3873fced92b8.
Final implementation branch: codex/capsule-builder-output-guard.
Scope: capsule.py build_test_capsule, new builder-output tests, Goal,
agent/record/2026-09-30_06_capsule-builder-output-guard.md, this acceptance.

## Independent review and acceptance

Parent inspected actual source diff and entire new test module after one bounded
DSH worker froze. Only initial target guard, validation order, exclusive mkdir
and docstring change. Later builder code and runner are unchanged. Eight new passing
cases and two privilege-dependent symlink cases cover invalid/missing snapshot,
corrected retry, initial caller entries, dangling-link guard and deterministic
competing directory/file creation. Existing tests were not changed or weakened.

Parent real-fixture probe on baseline: invalid_input_left_output=true,
corrected_retry=blocked, competing_output=adopted,
caller_manifest_preserved=false. Identical repaired probe:
invalid_input_left_output=false, corrected_retry=success,
competing_output=rejected, caller_manifest_preserved=true. Both exit 0.
Exact probe command:
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src'); @'
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from ashare_research.reproducibility.capsule import build_test_capsule
snapshot = Path('tests/fixtures/stage2g/canonical_fact_snapshot_v1')
with tempfile.TemporaryDirectory(prefix='capsule-output-boundary-probe-') as owned:
    root = Path(owned)
    invalid_output = root / 'invalid-parent' / 'capsule'
    try:
        build_test_capsule(invalid_output, committed_snapshot_dir=root / 'missing-input')
    except (FileNotFoundError, ValueError):
        pass
    invalid_left_output = invalid_output.exists()
    try:
        build_test_capsule(invalid_output, committed_snapshot_dir=snapshot)
        corrected_retry = 'success'
    except FileExistsError:
        corrected_retry = 'blocked'
    competing = root / 'competing-capsule'
    sentinel = competing / 'capsule_manifest.json'
    original = b'caller-owned manifest: preserve'
    real_mkdir = Path.mkdir
    appeared = False
    def race_mkdir(path, *args, **kwargs):
        global appeared
        if path == competing and not appeared:
            appeared = True
            real_mkdir(competing, parents=True, exist_ok=False)
            sentinel.write_bytes(original)
        return real_mkdir(path, *args, **kwargs)
    with patch.object(Path, 'mkdir', race_mkdir):
        try:
            build_test_capsule(competing, committed_snapshot_dir=snapshot)
            race_result = 'adopted'
        except FileExistsError:
            race_result = 'rejected'
    print(json.dumps({'invalid_input_left_output': invalid_left_output, 'corrected_retry': corrected_retry, 'competing_output': race_result, 'caller_manifest_preserved': sentinel.read_bytes() == original}))
'@ | python -
```

Parent loaded baseline capsule.py via git show into a separate package-qualified
ModuleType and built old/new capsules from the same committed fixture in owned
TemporaryDirectory paths. Manifest dictionaries and capsule_manifest.json bytes
were equal; logical digest:
8d89d7d4a71f0e5dcaacccabc231e70411822f457c2dda9e03fe846c750f0ed1.
Initial probe harness used an unqualified module name and failed relative import;
corrected package-qualified name, no repository/source change. Exact successful command:
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
@'
import subprocess, types, tempfile, json
from pathlib import Path
from ashare_research.reproducibility import capsule
baseline = types.ModuleType('ashare_research.reproducibility.baseline_capsule')
source = subprocess.check_output(['git','show','74418cc39c89945aa1a45e4627ee3873fced92b8:src/ashare_research/reproducibility/capsule.py'],text=True,encoding='utf-8')
exec(compile(source,'baseline_capsule.py','exec'),baseline.__dict__)
with tempfile.TemporaryDirectory(prefix='capsule-builder-byte-parity-') as owned:
    root=Path(owned)
    fixture=Path('tests/fixtures/stage2g/canonical_fact_snapshot_v1')
    old=baseline.build_test_capsule(root/'old',committed_snapshot_dir=fixture)
    new=capsule.build_test_capsule(root/'new',committed_snapshot_dir=fixture)
    assert old==new
    assert (root/'old'/'capsule_manifest.json').read_bytes()==(root/'new'/'capsule_manifest.json').read_bytes()
    print(json.dumps({'manifest_dict_equal':True,'manifest_bytes_equal':True,'logical_digest':new['logical_digest']}))
'@ | python -
```

## Exact regression validation

PowerShell, isolated worktree:
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m pytest tests/test_capsule_builder_output_guard.py tests/test_capsule_runtime_db_isolation.py tests/test_capsule_output_preservation.py tests/test_capsule_input_bindings.py tests/test_capsule_manifest_validation.py tests/test_capsule_lineage_validation.py tests/test_capsule_context_validation.py tests/test_stage2g_reproducibility.py tests/test_stage2g_dividend_correction_and_valuation.py tests/test_m2_stage2k1r2_pit_capsule_confidence.py tests/test_m2_stage2k1r3_true_upstream_capsule.py -q -rs
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src tests
git diff --check
git diff --cached --check
```

Parent pytest: exit 0, **221 passed, 6 skipped in 49.45s**.
Four skips are symlink privileges (two new tests, two existing preservation tests);
two are absent external baostock snapshot. No new skip bypasses deterministic
competing-output/missing-input/retry coverage. Full-tree Ruff: All checks passed,
exit 0. Unstaged whitespace check clean; staged check required before commit.
No product validation failure. No real input acquisition or backtest.

## Preservation and limits

Exact primary status/diff/HEAD/stash snapshot equals initial snapshot.
Primary HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222.
Stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f retained.
research.duckdb SHA256 remains
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Unrelated user worktrees/dirty and ignored artifacts retained. Local main is
checked out elsewhere and intentionally not moved.

Known limit: failures after successful exclusive output mkdir may leave owned
partial output. This is an initial-boundary fix, not whole-directory atomic
publication or a hostile concurrent path/input guarantee. No blockers found.
DSH ran read-only AST, scoped lint and diff checks although validation was assigned
to parent; no pytest, network, Git mutation or other file edits reported/observed.
Parent independently executed all acceptance commands.

Delivery gate: push scoped branch only; inspect exact head/base, all 42 expected
checks across seven workflows (six checks each), MERGEABLE/CLEAN and unchanged live
main before guarded merge under tracked standing authorization. Stop on failure
or drift. Final remote identity and preserved-state review remain mandatory.
No next research/data stage authorized by this engineering task.
