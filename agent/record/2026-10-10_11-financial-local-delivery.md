<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Financial analysis local delivery

Date 2026-10-10, Asia/Shanghai; model GPT-5, executor Codex.
Module: value assessment.
[Goal/contract](../goals/2026-10-10_financial_local_delivery.md).
Base branch codex/financial-json-review, commit
4446fb84c9b496d0654780c4ff4f0447f2ee07e7.
Current main is locally/remotely 47dbb6780933f8fb7abab922aa47027a1342de41.

## Verified state and delivery decision

Re-read root AGENTS.md, active agent agreement and north-star v2, actual recent
records, runtime/index/diff and protected DB hash. Financial code is already
delivered on the feature branch, but the accepted finite-JSON and context
corrections still occupy seven uncommitted files and README omits the entry.
Other-agent EIA/K1 trees retain their separate local changes. No DSH used.

Under the current continuation, consolidate the owned delivery rather than
add more functionality. Earlier tasks' no-commit stopping points remain true
historical facts; this contract now permits one scoped local commit only.
No old task document is modified or silently reinterpreted as merge permission.
The implementation is unchanged; README and this stage's documents are new
work. Verify from a clean staged-file export before committing.

## Baseline and plan

Seven prior input files and all pre-existing worktree states are recorded in
the fresh snapshot at the Goal's system-temp path. Primary DB is only hashed:
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Plan: complete README discovery; stage exact ten-file scope; export index;
run clean regressions/CLI smoke and compare source/input bytes; verify
protections and finalize this record; make one reviewed local commit.

No source acquisition, raw observation use, new metric/formula, research
execution, scoring or milestone promotion is part of this work.
The frozen M2/M3 dispositions and strict K2/holdout boundaries remain.

## Artifact provenance exceptions

System-temp snapshot is strict generated JSON; no invalid comment is added.
Clean checkout-index export is a generated copy of repository artifacts;
original attribution is retained without rewriting copied files. Temporary
fixture database is binary; subprocess/test-generated reports and cache files
are generated evidence. Their task creation is attributed here:
model GPT-5, executor Codex, date 2026-10-10, action created. Actual artifact
paths and the reason for each applicable exception are recorded below.

## Actual operations and clean verification

Added the README capability row and explicit unified CLI examples. The README
labels the entry as this branch's local delivery with mainline review pending;
it does not claim a merge or change milestone dispositions. Included the
existing guide, tests and this acceptance record in discovery links.
No runtime code, previous tests/guide or prior task-record bytes were edited.

Explicit `git add --` staged the exact ten paths listed in the Goal. Index
scope and `git diff --cached --check` passed. Candidate `git write-tree`:
0dc2a27d58145ae544b1d26426175413ba9a0c93.
`git checkout-index --all
--prefix=C:/Users/111/AppData/Local/Temp/financial-delivery-clean-20261010/`
exported that index into a verified absent directory. No ignored files,
database, .git or virtual environment were copied.

Environment: named interpreter, Python 3.13.9 / DuckDB 1.5.5; PYTHONPATH=src.
From the clean export the exact Goal-listed regression command passed:
**196 passed in 59.70s**, exit 0. Includes the prior 194 financial/calculation/
PIT/TTM/entry cases plus the two README discovery/link tests. This is a new
clean-export run, not a relabeled historical result.
Goal-listed Ruff command: All checks passed, exit 0.
`python -m ashare_research.cli research financial --help`: exit 0,
explicit database/symbol/as-of/year and optional compare/metric/scope/output.

The following Python body was executed through the named interpreter's `-c`
argument, from the clean export, to verify real subprocess dispatch:

```python
import collections, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
import ashare_research.financial_analysis as core
from ashare_research.reproducibility.capsule import build_temp_fact_db
root = Path.cwd()
assert root in Path(core.__file__).resolve().parents
assert not (root / '.git').exists()
workspace = Path(tempfile.mkdtemp(prefix='financial-delivery-smoke-20261010-'))
database = build_temp_fact_db(root / 'tests/fixtures/stage2g/canonical_fact_snapshot_v1', workspace / 'facts.duckdb')
before = hashlib.sha256(database.read_bytes()).hexdigest()
env = dict(os.environ, PYTHONPATH=str(root / 'src'), PYTHONIOENCODING='utf-8')
arguments = ['--database', str(database), '--symbol', '601857.SH', '--as-of', '2024-06-30', '--year', '2023', '--json']
commands = [[sys.executable, '-m', 'ashare_research.cli', 'research', 'financial', *arguments], [sys.executable, '-m', 'ashare_research.tools.financial_analysis', *arguments]]
results = [subprocess.run(command, cwd=workspace, env=env, capture_output=True, check=True) for command in commands]
assert all(not result.stderr for result in results)
assert results[0].stdout == results[1].stdout
report = json.loads(results[0].stdout)
counts = collections.Counter(row['status'] for row in report['as_of']['records'])
assert counts == {'computed': 7, 'missing_input': 5}, counts
assert len(report['as_of']['records']) == 12
assert not report['boundary']['production_eligible']
assert not report['boundary']['score_eligible']
assert hashlib.sha256(database.read_bytes()).hexdigest() == before
print(json.dumps({'status': 'PASS', 'temporary_database': str(database), 'records': 12, 'states': dict(counts), 'cli_outputs_identical': True, 'input_database_unchanged': True}, sort_keys=True))
```

Exit 0: PASS; 12 records, 7 computed / 5 missing_input; identical CLI bytes,
false production/score eligibility and input database hash unchanged.
Binary fixture artifact:
C:/Users/111/AppData/Local/Temp/financial-delivery-smoke-20261010-q4fp4bzk/facts.duckdb.
It is rebuilt solely from committed test facts, not acquired data.
The exported directory, generated test caches and temporary fixture DB are
retained outside the project; no user-path cleanup is performed.

## Independent review, protections and acceptance

Actual cumulative implementation/test/guide diff and new README were reviewed.
All prior seven files match their task-start SHA256s; all ten delivery files
matched exported bytes before finalizing this acceptance record.
Finalization changes only this Markdown record. Runtime/test/README bytes
are still exactly those successfully tested; no repeated test run is needed
for the record-only result update.

Snapshot assertions passed for all 410 protected hashes, all 68 original
worktree HEADs, all 67 foreign statuses and the original stash. Protections
include prior owned records/source inputs, foreign dirty/untracked files,
frozen reports/config/evidence, root north stars and primary database.
Owned HEAD/status are permitted to advance only through the reviewed commit.
No ignored-runtime whole-inventory preservation claim is made.

README links and scope are covered by the clean project-entry tests; final
UTF-8, provenance, new-record whitespace and staged diff checks are required
after this record update. Existing model headers on packaging inputs remain
unchanged. No formatter, gate or test was weakened; no failed selected check.
No hosted CI, cross-platform reproduction or complete milestone acceptance
is claimed. Unrelated full business/foreign-agent suites were not run.

## Final delivery evidence packet

- Goal: agent/goals/2026-10-10_financial_local_delivery.md.
- Acceptance evidence: this record, clean test results and Git commit contents.
- Base branch/commit: codex/financial-json-review at
  4446fb84c9b496d0654780c4ff4f0447f2ee07e7.
- Final branch: codex/financial-json-review; final commit is the normal local
  commit containing this record. Record its exact hash in the final chat and
  verify with git show/rev-parse; do not embed a circular self hash here.
- New work: README.md, this Goal and this record.
- Preserved packaged work: financial_analysis.py, its tests and guide, both
  preceding correction Goals and both preceding records. Exact ten paths
  are named by the Goal and verified in the index.
- Implementation: existing arbitrary-company 12-metric financial analysis,
  accepted finite-JSON and fact/context fixes, plus discoverable usage.
- Commit gate: all selected checks passed; commit follows the final document/
  index/protection review. Do not report successful completion if it fails.
- Synchronization: observed origin/live main 47dbb678 and live M2 ecb74a4;
  this local branch is unpublished, its base already contains two feature
  commits above main. Original M2 worktree remains one commit behind origin.
- Stash: cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f unchanged, one entry.
- Primary DB SHA256: unchanged, never connected.
- Deviations/blockers: none. Remaining limit: caller-source authenticity and
  external evidence are not established; feature is still off main.
- Delivery authorization: one scoped local commit; no push, merge, PR, tag,
  amend, DSH or automatic next stage. Remote integration remains separate.
- Acceptance status: validated for local commit.
- Verdict: PASS.
