# Capsule post-merge acceptance

Final verdict: CHANGES_REQUIRED.

The merged PR #36 cleanup fix passes its scoped regression gates. The wider
caller audit independently reproduced an existing runtime input-binding defect;
passing capsule checks must not be presented as complete runner input integrity.

## Verified baseline and delivery

- Base: remote main / origin/main 209b06c3507e9def970b43bcdc5ce03a61b223fc.
- PR #36: https://github.com/dlam12138/ashare-research-lab/pull/36.
- Published head: 05b4a5597cce21425f244e5208cb7020427048b6.
- Actual merge: 209b06c3507e9def970b43bcdc5ce03a61b223fc.
- All 42 hosted checks SUCCESS; no non-success check returned.
- Product/test/frozen paths equal the PR head at the merged commit.
- Local main is separately checked out elsewhere at
  966206f06262e43f40c1c7aadbfb8596839eac91, 65 commits behind origin/main.
  It was preserved; remote main is what 'live main' means in this task's Goal.

## Required change: bind the database actually consumed

`src/ashare_research/tools/stage2g_reproducibility.py:118` verifies portable
artifacts, but lines 120-122 reuse any existing `temporary_fact.duckdb`.
That database is deliberately excluded from the six portable inventory paths.
Lines 127 and 132-139 pass the existing database to the formal runner while
reporting the trusted snapshot hash/count from the manifest.

An isolated synthetic reproduction doubled revenue values in that database
without touching any portable artifact or its manifest. Manifest verification
still succeeded. The real canonical loader consumed six doubled revenue facts;
the real capsule runner returned status pass and artifact verification pass.
This demonstrates mismatched declared and consumed inputs, not a hypothesis
about hostile concurrent mutation. The original cleanup fix did not introduce
this defect. Source provenance authentication remains a separate limitation.

Exact successful reproduction in this worktree (PowerShell):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
@'
import json
import tempfile
from pathlib import Path
import duckdb
from ashare_research.reproducibility.capsule import build_test_capsule, verify_capsule_manifest
from ashare_research.tools.stage2g_reproducibility import run_test_capsule
from ashare_research.tools.petrochina_valuation_and_value_profile import _load_canonical_facts
snapshot = Path('tests/fixtures/stage2g/canonical_fact_snapshot_v1')
with tempfile.TemporaryDirectory(prefix='capsule-postmerge-probe-') as owned:
    root = Path(owned)
    capsule = root / 'capsule'
    before = build_test_capsule(capsule, committed_snapshot_dir=snapshot)
    database = capsule / 'temporary_fact.duckdb'
    original, _ = _load_canonical_facts(database)
    with duckdb.connect(str(database)) as db:
        db.execute("UPDATE financial_facts SET value = value * 2 WHERE concept_id = 'revenue'")
    assert verify_capsule_manifest(capsule) == before
    actual, _ = _load_canonical_facts(database)
    left = {r['fact_id']: r['value'] for r in original if r['concept_id'] == 'revenue'}
    right = {r['fact_id']: r['value'] for r in actual if r['concept_id'] == 'revenue'}
    assert left and all(right[k] == 2 * v for k, v in left.items())
    result = run_test_capsule(capsule, output_root=root / 'runs', run_id='stale-db-probe')
    print(json.dumps({'manifest_still_valid': True, 'changed_loaded_revenue_facts': len(left), 'runner_status': result['status'], 'artifact_verification': result['artifact_verification']['status']}, ensure_ascii=False))
'@ | python -
```

Exit 0. Output:

```json
{"manifest_still_valid": true, "changed_loaded_revenue_facts": 6, "runner_status": "pass", "artifact_verification": "pass"}
```

Only owned TemporaryDirectory synthetic files were modified, then removed by
normal cleanup. No default or existing runtime database was opened or changed.

Repair acceptance: use a fresh owned database built from the verified snapshot,
or compare all consumed fact/context/lineage semantics before admitting a cached
database. Preserve existing cache bytes and unrelated output paths. A changed
or foreign cache must never produce a successful report declaring snapshot
inputs that were not consumed. Cover altered values, missing/additional rows,
context/lineage differences, repeated runs and build failure ownership behavior.

## Parent validation

Exact focused pytest command is in the Goal. Executed once on the merged base:
199 passed, 4 skipped in 68.82s. Skips: two symlink cases require account
privileges; two cases require absent real baostock snapshots. No tests weakened.
Pinned Ruff command in the Goal: all checks passed. Whitespace checks passed.
No redundant full-suite rerun; inspected existing hosted full-suite gates.

Protected primary status, binary diff, HEAD and stash were compared byte-for-byte
with the captured start state: unchanged. research.duckdb SHA256 remains
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Product, fixture, report, workflow and frozen-contract paths were not edited.

## Scope and stop

This evidence task changes only its Goal, record and this acceptance document.
Local evidence commit only; no push, PR, merge or next stage. Reproducible defect
triggered the Goal stop condition. A repair must establish a bounded contract
for the runner and its regression tests. Real-data research remains unauthorized.
The parent verdict takes precedence over a narrow PR-only review verdict.
DSH read-only audit exited 0 and also identified the database-binding gap; its
PASS applies only to the merged cleanup change. Parent independently reproduced
the gap and retains CHANGES_REQUIRED for composed runner acceptance.
