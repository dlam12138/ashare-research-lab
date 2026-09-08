# Acceptance: M4 synthetic dataset adapter

Verdict: PASS (bounded synthetic implementation, local delivery).

## Baseline, Goal and scope
Goal: [task contract](../agent/goals/2026-09-08_m4_synthetic_dataset_adapter.md).
Record: [work log](../agent/record/2026-09-08_01_m4-synthetic-dataset-adapter.md).
Base: codex/m4-dataset-adapter-design, 40d10b46c2e7e4a7e0cac0f28ccea07ef50d784d.
Main/origin/live main at start: bab24f981fef9336b84280544ce709702b9df116.
Implementation branch: codex/m4-synthetic-dataset-adapter in D:/量化分析-m4-adapter.
Source/test implementation and this evidence are delivered as one scoped local commit;
the final response records its exact SHA outside its own content.

Seven new files only: two files in src/ashare_research/mechanism/datasets,
tests/test_m4_synthetic_dataset_adapter.py, tests/test_m4_dataset_adapter_review.py,
this acceptance and linked Goal/work record. No existing source, tests, design,
research artifact, North-Star, dependency, workflow or README was modified.

## Implemented behavior
Frozen typed synthetic evidence/inputs/outputs and four public APIs are available:
materialize_analysis_dataset, dataset_to_canonical_dict, serialize_dataset and
validate_dataset. BoundDatasetInputsV1.from_dict accepts an explicit document matching
the [design](../docs/m4_dataset_adapter_design_v1.md); no default file/database is read.

```python
from ashare_research.mechanism.datasets import (
    BoundDatasetInputsV1, materialize_analysis_dataset,
    serialize_dataset, validate_dataset,
)
inputs = BoundDatasetInputsV1.from_dict(document)  # caller supplies full evidence/digests
prepared = materialize_analysis_dataset(contract, plan, inputs)
validate_dataset(prepared, contract, plan, inputs)
encoded = serialize_dataset(prepared)
```

Original A.1 contract strictly recompiles to exactly the supplied A.2 plan bytes.
Date domain fixes coverage denominator independently of observed rows. Each role's
identity, evidence, value and availability is validated; missing data stays explicit.
Duplicate/conflicting inputs fail closed. Exact integer ratio comparison determines
coverage eligibility. REJECTED_QUALITY exposes audit gaps but no complete rows.
READY_SYNTHETIC still has execution_authorized=false. No regression, bootstrap,
provider, real data or holdout execution was added.

Serializer verifies output structure, quality recomputation and complete-row consistency;
four-argument validation additionally recomputes the exact predicate/source binding.
No claim that a self-supplied hash proves real provenance. First slice supports only
synthetic fixed membership, precomputed decimal returns, 1D CLOSE_TO_CLOSE and RETURN
factor semantics. Bounded identifier and serializer clarifications are in the Goal.

## Actual model routing and review
One worker was explicitly gpt-5.6-luna / medium / fork_turns=none, no recursive delegation.
Luna wrote initial source and focused tests. Two inadequate deliveries were rejected;
parent reproduced validation failures, invoked the documented escalation rule, and
explicitly took over source repairs. Luna then owned its test file only. Parent added
independent review tests and ran final verification. This was not a wholly Luna-authored
implementation, and no model/token savings claim is made.

## Verification
From this worktree, with the existing declared-dependency interpreter:
```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m ruff check src/ tests/
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m compileall -q src tests
git diff --check
git diff --cached --check
```
- New suites: 58 passed in 2.29s (34 worker cases, 24 independent review cases).
- Baseline A.1/A.2/protection/entry suite: 132 passed in 2.64s.
- Ruff: all checks passed. Compileall: exit 0.
- Full suite: **2544 passed, 4 skipped, 2 warnings in 400.28s**, exit code 0.
  Four skips are existing environment/external-fixture skips; both warnings are
  existing pandas date inference warnings in tests/test_quality.py. No tests were
  weakened or skipped by this task. JUnit contains 2548 cases, zero errors/failures.
- Final unstaged/staged diff checks: exit 0; exactly seven additive task files.

The first full-run session became unavailable after task continuation; only progress
through 67% without failures had been observed. Its final result is unknown and is
not counted as a pass. A repeat is required for unresolved evidence, using
`-m pytest -q --junitxml=tmp/adapter-validation/full-pytest.xml`; combined output is
saved in tmp/adapter-validation/full-pytest.log and exit code in full-pytest.exit.
These files are ignored runtime evidence, not committed artifacts. No source or tests
changed between these full runs.

Fixed fixture identities (existing test fixture uses LTE and the A.1 default gate):
- Input: c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602.
- Dataset: c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b.
- Serialized SHA256: 32533abc2e9cefc7f0fe66923afc9a3f5d6ca5b0def7d1228c33ead8d071a060.
Actual LT/LTE/GT/GTE tests assert their different exact indicators; these identities
are for the named fixture, not fabricated hashes of the design document's LT example.

## Protection and stop
Original M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222, existing dirty files and
all worktrees preserved. Stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f.
Original DB SHA256: 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
No source/artifact protection hash was changed. Local-only delivery: no push, PR,
merge, next-stage work or PR #10 integration. Fresh Linux/remote CI has not been run
for this unpublished commit; fixed identities and cwd invariance were checked locally.
Next executor/real-data work requires separate authorization.

Final audit: original DB hash and stash match the baseline above; all original
worktree HEADs and dirty M2 files remain intact. origin/main remains bab24f9; last
successful live lookup matched it and found no remote implementation branch. Final
live lookup and retry failed because Git's 127.0.0.1 proxy could not connect to GitHub.
Current remote state cannot be freshly confirmed; no remote mutation was attempted.
This limitation does not prevent local-only implementation acceptance. Local delivery
includes the prior design commit plus this implementation commit. Worktree is clean
after the scoped commit; generated ignored test caches/logs are retained.
