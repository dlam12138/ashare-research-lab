<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Financial context binding work record

Date 2026-10-10, Asia/Shanghai; model GPT-5, executor Codex.
Module: value assessment.
[Task contract](../goals/2026-10-10_financial_context_binding.md).
Base/current branch codex/financial-json-review at
4446fb84c9b496d0654780c4ff4f0447f2ee07e7.
Root governance and north-star v2 are binding; no DSH invoked.

## Recent agents' work and mainline decision

Independently checked actual branch/HEAD/status/diff scope and read recent
records. Counts below are attributed historical evidence, not fresh runs or
full independent acceptance of those tasks:

| Area | Actual local delivery | Record evidence and boundary |
| --- | --- | --- |
| Core company financial analysis | codex/core-financial-analysis-mainline, 4446fb84; clean, two commits above main | Record 2026-10-10_01 reports 166 feature/foundation and 32 entry tests, plus temporary CLI smoke. Arbitrary-company, read-only, existing 12 definitions; not merged. |
| EIA shared validation | codex/eia-transport-consistency, 47dbb678; three modified Python files and four task documents | Record 2026-10-10_08 reports 90 passing cases. Common metadata loader rejects contradictory dossiers in both CLIs; does not establish historical PIT or K2 readiness. |
| K1 proof structure | codex/k1-raw-shape, 47dbb678; two modified Python files and six task documents | Record 2026-10-10_06 reports 135+5 distinct passing cases in separate runs, plus valid-byte checks. Shape checks do not prove source authenticity. |
| EIA historical candidate review | codex/north-star-handoff, 47dbb678; local documentation delivery | Record 2026-10-10_03 concludes NO_CANDIDATE_NOMINATED_FOR_ACQUISITION within its metadata budget. Do not repeat acquisition or reopen holdout. |
| Financial finite JSON | current tree, five existing changed/new files | Prior record 2026-10-10_09 reports 172 regressions and six pre/post cases. Preserve that correction and its evidence. |

Thread tools were searched but none were available. Repository records and
actual files are the evidence inspected; no live agent-status claim is made.
No agent contacted or new thread created.

Decision: advance the delivered financial core's binding correctness rather
than duplicate existing EIA/K1 repairs or add another export/view feature.
Public AsOfQuery correctly selects versions and scope, but joins contexts
without verifying symbol, fiscal year or duration. The financial projection
loads these fields but currently checks only period_type. A partial-year flow
or mismatched company/year context can therefore look like an annual input.
Reproduce this on invented temporary facts before correction.

## Plan, protections and data

Capture state; establish contract; add failing tests; correct local binding;
run selected regressions; independently inspect diff/protections and report.
No real source acquisition, hypothesis execution or primary DB content read.
Primary DB SHA256 remains
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Strict operational JSON snapshot at the Goal's temp path is generated evidence:
action created, model GPT-5, executor Codex, date 2026-10-10. Comments would
invalidate JSON; provenance is recorded here instead.
Snapshot contains tree states, file hashes and pre-edit bytes of the three
allowed existing files. Previous task documents are protected.

Initial regression run: 20 failed, 2 passed, 36 deselected in 4.00s.
Seventeen failures reproduced incorrectly computed metrics; two were fixture
setup failures because fiscal_year has a NOT NULL database constraint, and
one was a fixture identity failure after changing a revision's context_id.
Before implementation, corrected these fixtures: use fiscal_year=0 to model
a representable invalid year, and recompute the revision's canonical identity
with the existing make_verified_fact helper. Do not weaken storage rules or
claim setup failures as report behavior evidence.

## Implementation and actual validation

Corrected-fixture pre-repair run used the Goal's focused command:
20 failed, 2 passed, 36 deselected in 4.87s, exit 1. All 20 failures now
reproduce incorrectly computed metrics, without fixture setup errors.
The two valid instant conventions already pass.

Loaded the context symbol and added local `_context_matches_fact` validation:
same symbol/year/scope, matching December 31 endpoints, approved period type,
annual January 1 start and duration, or instant semantics with absent/same-day
start. The existing exclusion code is reused. PIT selection is not changed,
so an incompatible latest version cannot trigger fallback to an older version.
Updated the guide and appended tests without changing existing assertions.

Validation from the owned tree with PYTHONPATH=src and the Goal's interpreter:

| Exact Python arguments / command | Actual result |
| --- | --- |
| `-m pytest -q tests/test_financial_analysis.py -k context_binding --tb=short` | 22 passed, 36 deselected in 3.58s; exit 0 |
| `-m pytest -q tests/test_financial_analysis.py tests/test_metric_engine.py tests/test_cashflow_metric_engine.py tests/test_earnings_quality_metric_engine.py tests/test_ttm_business_boundaries.py tests/test_pit_date_boundaries.py tests/test_research_entry.py` | 194 passed in 58.82s; exit 0 |
| `-m ruff check src/ashare_research/financial_analysis.py tests/test_financial_analysis.py` | final All checks passed; exit 0 |
| `git diff --check` and `git diff --cached --check` | exit 0 |
| `git status --short --branch` | three modified tracked files and four untracked task documents; two documents belong to this task |
| `git rev-parse HEAD origin/main refs/stash` | 4446fb84, 47dbb678 and cb568efd respectively |
| `git ls-remote origin refs/heads/main refs/heads/feat/m2-value-assessment-mvp` | main 47dbb6780933f8fb7abab922aa47027a1342de41; M2 ecb74a4178afd7de49b12f39eb58e541fc6fc4dd |

Initial Ruff found one E501 line in the new annual fixture setup. Wrapped that
line, then reran Ruff and performed the full selected regression run on the
final code/test state. No rule, threshold, assertion or existing test changed.
No unresolved validation failure remains.

## Independent review and protections

Reviewed task-specific core/guide differences against snapshot bytes, plus
cumulative Git diff and appended tests. After removing only the added identical
provenance line and normalizing checkout newlines, the previous test file is an
exact prefix of the final test file. Previous finite-JSON projection and strict
serializer remain present and covered by the current full selected run.

PowerShell assertions against the fresh snapshot passed for 405 protected
hashes, all 68 original worktree HEADs, all 67 foreign worktree statuses and
stash. Only the three expressly allowed existing files were exempted from
hash equality. Checks cover foreign dirty/untracked files, prior task records,
owned frozen reports/config/evidence and root north-star/database hashes.
Primary database was not connected. Original root edits and other agents'
working files remain unchanged.
No whole-inventory assertion is made about ignored runtime/cache artifacts.

Acceptance evidence: malformed annual/instant contexts now yield excluded
roles and missing metric values; a two-date revision case computes the valid
original at the earlier PIT date and excludes the malformed latest revision
later, without selecting the original again. Both valid instant conventions
and the committed-fixture/independent-engine regression retain their results.
Temporary database hashes are preserved.

Other-agent source inspection confirms progress and standalone assessor call
the same verified EIA loader, and K1 canonical proof projection validates
identity/count/gap shapes. Their historical test counts are orientation
evidence only; those unrelated suites were not rerun or independently accepted
as part of this financial correction. No hosted CI or open-PR status claim.

## Final evidence packet

- Goal: agent/goals/2026-10-10_financial_context_binding.md.
- Acceptance/work evidence: this record.
- Base/final branch: codex/financial-json-review; base/final commit:
  4446fb84c9b496d0654780c4ff4f0447f2ee07e7.
- Current-task modified files: src/ashare_research/financial_analysis.py,
  tests/test_financial_analysis.py, docs/core_financial_analysis_guide_v1.md.
- Current-task added files: the Goal and this record. Cumulative tree has seven
  changed/new files because the previous finite-JSON task remains uncommitted.
- Model attribution: new created entries on task documents; a new modified
  entry appended in the header of each existing file, retaining earlier
  task entries. The operational snapshot is the sole strict-JSON exception
  recorded above.
- Worktree/index/stash: scoped local changes retained, no staged files;
  cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f remains the one original stash.
- Synchronization: origin/main equals live main at 47dbb678; this unpublished
  branch contains the two existing financial-feature commits above main.
  Root is unchanged and remains one commit behind its remote M2 branch.
- Commit/tag/push/PR/merge: none. Final working changes inspected; new committed
  diff and hosted CI are not applicable to this uncommitted local delivery.
- Tests omitted: full unrelated suite and foreign-agent suites, because the
  local binding change is covered by financial/PIT/TTM/calculation/entry tests.
  Prior agent evidence is not substituted for required current checks.
- Deviations: fixture corrections and one lint wrapping fix recorded above;
  no implementation scope expansion or weakened gates.
- Limitations: caller database/source authenticity is still not independently
  established. No real-source, M4, mechanism, scoring or milestone promotion.
  Financial feature and both corrections remain off main.
- Next step: prioritize reviewable integration of the financial feature and
  corrections over duplicate EIA discovery or additional presentation tooling.
  No automatic merge or subsequent stage is authorized.
- Status: completed.
- Verdict: PASS.
