# Acceptance: M4 synthetic analysis matrix design

Verdict: **DESIGN_DELIVERED_PENDING_INDEPENDENT_REVIEW**. This is a design delivery only. It
contains no matrix implementation, no statistical execution and no execution authorization.
It is not self-accepting: the contract requires codex to verify independently. Round 1 was
independently reviewed and returned **CHANGES_REQUIRED** (5 findings); round 2 repaired the
four documents against those findings and was independently reviewed again, returning
**CHANGES_REQUIRED** (3 findings). Round 3 applied exactly those three targeted corrections.
The round-3 result still awaits Codex's independent re-verification and is **not**
self-declared as PASS.

- Task contract (outside this worktree):
  `D:/量化分析/agent/goals/2026-09-10_ds_matrix_design_closeout.md`.
- Existing Goal (untracked, preserved): [contract](../agent/goals/2026-09-10_m4_analysis_matrix_design.md).
- Normative design: [specification](../docs/m4_analysis_matrix_design_v1.md).
- Future acceptance cases: [synthetic matrix scenarios](../docs/m4_analysis_matrix_acceptance_cases_v1.md).
- Work record: [work log](../agent/record/2026-09-10_01_m4-analysis-matrix-design.md).

## Scope and baseline

Deliver exactly four authorized Markdown documents; implement nothing. Verified base branch
`codex/m4-analysis-matrix-design` at HEAD `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`,
matching origin's tracking ref and the PR #11 head (live-checked). `main` is
`bab24f981fef9336b84280544ce709702b9df116`. PR #11 remains **OPEN and unmerged**.

This is round 1 continued after an interruption. The interruption left one draft
(`docs/m4_analysis_matrix_design_v1.md`) and three temporary probes; no other documents, no
commit, no recorded exit codes. The draft was **not** deliverable as-is: its section 7
`matrix_digest` values were computed from a payload that contradicted the canonical shape its
own sections 4.3/6.3 declared. That was corrected and every affected digest was recomputed by
real measurement. See the work log section 4.2 for the full defect list.

Round 2 addressed the independent review's five findings (work log section 4.6):

1. the false claim that `FACTOR_CONTINUOUS` and `CONDITION_INDICATOR` share a
   `source_series_role` was removed everywhere; the real bindings from
   `compiler.py::_terms` and `tests/test_m4_stage4a2i_analysis_plan.py` are `"FACTOR"` and
   `"CONDITION_INDICATOR"` respectively, and the `term_role`-only dispatch rule is now justified
   by `term_role` being the column's semantic identity (round 3 replaced the round-2 wording
   "incomplete, non-injective source binding", which was itself factually wrong — see below);
2. the round-1 public projection-only entry that accepted just the preparation and the plan was
   deleted; the only public materialization entry is now the four-argument
   `materialize_design_matrix(preparation, contract, plan, bound_inputs)`, which must run
   `validate_dataset` first, then the quality gate, then project; pure projection was demoted to
   the private `_project_validated_matrix`, which is not an API or an acceptance entry;
3. the materialize/validate API was re-frozen coherently
   (`validate_design_matrix(matrix, preparation, contract, plan, bound_inputs)`), with fixed
   per-entry ordering, upstream `AdapterError` propagation, `MatrixError` only for matrix-layer
   failures, and a `REJECTED_QUALITY` scenario that no longer treats a non-existent rejected
   matrix object as a required input;
4. the round-1 pytest result (`187 passed + 3 setup errors`, exit 1) is preserved as the actual
   harness result, Codex's independent run of the identical contract command
   (`190 passed`, exit 0) is recorded as the authoritative passing evidence, and the
   direct-test-body invocation is no longer presented as equivalent to a pytest pass;
5. the round-1 residual directory `.tmp_matrix_design_verify/` was deleted by Codex during the
   exact verification path, so no user cleanup is requested and the final untracked state is
   exactly the existing Goal plus the four authorized documents.

Round 3 addressed the second independent review's three findings (work log section 4.7). Only
those findings were touched:

1. **Factual precision.** The claim that `source_series_role` "lacks uniqueness" or is
   "non-injective" with respect to `term_role` was deleted globally. For the current
   `ordered_terms` set the mapping is in fact one-to-one: `null`, `FACTOR`, `CONTROL_0001`,
   `CONTROL_0002`, `CONDITION_INDICATOR` are pairwise distinct, and unequal
   `term_role`/`source_series_role` **names** do not make a mapping non-injective. Dispatch stays
   on `term_role`, now for the accurate reason: `term_role` is the authoritative identifier of
   column semantics **and projection rule**, while `source_series_role` only records the input
   origin and cannot by itself say whether the column takes the constant `1`, is read directly
   from `values`, or is derived from `complete_rows.condition_indicator`; `INTERCEPT` has
   `null`, and the indicator points at a transform output outside `role_order`/`values`, so a
   `role_order` lookup of `source_series_role` is insufficient — without claiming any current
   collision.
2. **Schema contradiction.** The real `QualityReportV1` has no `status`; `status` belongs to
   `DatasetPreparationV1`. The proposed `MatrixQualityV1` adds `status`, so the earlier
   "field-for-field mirror of `QualityReportV1` (no additions, no removals, no renames)" was
   false. It now reads: `status` explicitly inherits `preparation.status`, and the other seven
   fields are copied field-for-field from `preparation.quality` with no re-judgment. The design
   also states why the top-level `status` enters the matrix `quality` block: the matrix payload
   deliberately has no separate top-level `status` field, so the readiness/rejection status must
   be readable together with the quality detail in exactly one place, and no second,
   contradicting status field can exist.
3. **Wording.** `source_role` is not display-only: it enters the canonical payload, the
   serialized bytes and `matrix_digest`, and must agree with the plan. It is now called
   **audit/provenance metadata that does not participate in cell-value dispatch**.

## Reviewed decisions

1. **One source-verification entry.** The existing four-argument
   `validate_dataset(preparation, contract, plan, bound_inputs)` re-materializes and compares
   `serialize_dataset` bytes. The single public materialization entry
   `materialize_design_matrix(preparation, contract, plan, bound_inputs)` must call it before
   the quality gate and before any projection; there is no public projection-only entry. A
   self-consistent rehashed `preparation` passes `serialize_dataset` (`ACCEPTED`) but is
   rejected by the four-argument entry (`IDENTITY_CONFLICT`). A rehashed `bound_inputs` is
   likewise rejected. Checking `dataset_digest`, or running only the serializer, accepts forged
   indicator columns; both paths are measured, not assumed.
2. **Column order comes only from the plan.** `plan.design_plan.ordered_terms` is the sole
   authority; the frozen sequence is `INTERCEPT`, `FACTOR_CONTINUOUS`, registered-order
   `CONTROL_0001…`, `CONDITION_INDICATOR`. Fixed M3 column lists, fixed development windows,
   fixed control counts and alphabetical ordering are forbidden. Cell dispatch is by
   `term_role` only, because `term_role` is the authoritative identifier of both column
   semantics and projection rule, whereas `source_series_role` only records the input origin
   and cannot by itself determine whether the cell is the constant `1`, a direct member of
   `values`, or the derived `condition_indicator`. The real bindings, re-verified against
   `compiler.py::_terms` and `tests/test_m4_stage4a2i_analysis_plan.py`, are `INTERCEPT → null`,
   `FACTOR_CONTINUOUS → "FACTOR"`, `CONTROL_00nn → itself`, and
   `CONDITION_INDICATOR → "CONDITION_INDICATOR"` (a transform output role, not a member of
   `role_order`). On the current `ordered_terms` these values are pairwise distinct, so the
   mapping is in fact one-to-one; that correspondence is a product of current role naming, is
   not part of the projection contract, and must not be relied on by an implementation. The
   round-1 claim that the two roles were equal was factually wrong and has been removed; the
   round-2 claim that the mapping was non-injective was likewise wrong and was removed in
   round 3.
3. **Exact decimal identity.** Canonical decimal strings are carried through unchanged; no
   re-parsing, rounding or float conversion. `INTERCEPT` is frozen to the literal `"1"`;
   indicators are `"0"`/`"1"` from strict `int`; the only legal zero is `"0"`. The coverage
   gate is exact rational arithmetic (`Decimal.as_integer_ratio`), so `2/3` passes `0.66`
   and fails `0.67`.
4. **Immutable, deterministic identity.** Frozen dataclasses, tuple containers, defensive
   copies, canonical JSON identical in shape to `serialize_dataset`/`serialize_analysis_plan`,
   and `canonical_digest` (which itself sorts keys). Input row permutation, dictionary key
   order and working directory do not change identity; semantic change always does. A nested
   contract field that does not alter any matrix cell still changes all four digests.
5. **Quality rejection yields no usable partial matrix.** The single public materialization
   entry runs `validate_dataset` first and then raises `MatrixError("DATASET_NOT_READY")` at
   the quality gate on `REJECTED_QUALITY`; no object is returned, and no legitimate rejected
   matrix object exists to be used as an input. There is no zero-row "empty matrix" and no
   truncated partial matrix object. `FAIL_CLOSED` rejects on any gap regardless of gate, so
   lowering the gate is not a bypass. Coverage denominator never shrinks.
6. **Hard separation from estimation and execution.** Matrix preparation asserts nothing about
   rank, identifiability, estimability, significance, tradability or execution authorization.
   No regression, bootstrap, robustness or evidence code is called. No A.1/A.2/dataset schema
   change is required; if one became necessary, implementation must stop and report.
7. **Quality is inherited, not re-judged.** The real `QualityReportV1` has exactly seven fields
   and no `status`; `status` is a top-level field of `DatasetPreparationV1`. The proposed
   `MatrixQualityV1` therefore inherits `status` explicitly from `preparation.status` and copies
   the other seven fields (`coverage_numerator`, `coverage_denominator`, `coverage_gate`,
   `missingness_policy`, `failure_disposition`, `reason_counts`, `rejected_dates`)
   field-for-field from `preparation.quality`, with no rename, recomputation or re-judgment.
   The top-level `status` is carried in the nested `quality` block because the canonical matrix
   payload deliberately has **no** separate top-level `status` field: the readiness/rejection
   verdict must be readable in exactly one place together with its quality detail, so that no
   second, potentially contradicting status field can exist. The matrix layer introduces no new
   status vocabulary (still only `READY_SYNTHETIC` / `REJECTED_QUALITY`).
8. **`source_role` is audit/provenance metadata, not decoration.** It enters the canonical
   payload, the serialized bytes and `matrix_digest`, and must agree with the plan's
   `source_series_role`, so it is frozen identity content. It does **not** participate in
   cell-value dispatch; dispatch is by `term_role` only.

## Actual validation (every command with its real exit code)

### Round 1 (preserved as measured)

From `D:/量化分析-m4-matrix-design`:

| # | Command | Exit | Result |
| --- | --- | --- | --- |
| 1 | `pytest -q tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py` | **1** | `187 passed, 2 warnings, 3 errors` — the 3 errors are setup-stage `pytest-of-*` `PermissionError`, see below |
| 2 | same with `TEMP` redirected into the worktree (auxiliary diagnosis) | **1** | same 3 errors |
| 3 | same with `--basetemp` on a non-`pytest-of-*` path (auxiliary diagnosis) | **1** | same 3 errors; plus `PermissionError` in `cleanup_dead_symlinks` at session finish |
| 4 | `git diff --check` | **0** | clean |
| 5 | `git diff --cached --check` | **0** | clean (empty index) |
| 6 | `git status --short` | **0** | see tracked/untracked state below |
| 7 | `git rev-parse HEAD` | **0** | `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef` |
| 8 | `git worktree list --porcelain` | **0** | 12 worktrees, all preserved |
| 9 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 10 | `git rev-parse refs/stash` | **0** | `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` = protected value |
| 11 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only; contents never read) |
| 12 | `git -c http.proxy= -c https.proxy= ls-remote origin` | **128** | `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS` — remote git refs **could not** be refreshed |
| 13 | `git rev-parse origin/main origin/codex/m4-synthetic-dataset-adapter` | **0** | `bab24f98…` / `b0c8fafb…` (local tracking refs) |
| 14 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222` = protected value |
| 15 | `gh pr view 11 --json …` | **0** | `state=OPEN`, `headRefOid=b0c8fafb…`, `baseRefName=main`, `mergeable=MERGEABLE`, `mergedAt=null` |
| 16 | `gh api repos/.../commits/b0c8fafb…/check-runs` | **0** | `total_count=42`, grouped by conclusion: **`success` × 42** |
| 17 | `gh api repos/.../commits/b0c8fafb…/status` | **0** | `pending` (no legacy commit status; check-runs only) |
| 18 | Markdown audit of the three pre-existing/required documents | **0** | UTF-8, no BOM, no CRLF, no TAB, no trailing whitespace, final newline present, no conflict markers, balanced fences |
| 19 | Local relative link resolution | **0** | all in-worktree links resolve |
| 20 | Direct execution of the 3 setup-blocked test bodies using real directories | **0** | 5 assertions all `True` (**auxiliary diagnosis only**, not equivalent to a pytest pass) |

### Round 1 pytest result and Codex's independent rerun (no equivalence substitution)

The round-1 harness result of command 1 is exactly **`187 passed, 2 warnings, 3 errors`,
exit 1**. All three errors occur during pytest **setup**, before the test body runs:

```text
PermissionError: [WinError 5] access denied:
  C:\Users\111\AppData\Local\Temp\dsh-6vjO3y\pytest-of-dlam12138
  D:\量化分析-m4-matrix-design\.tmp_matrix_design_verify\pytest-of-dlam12138
at _pytest/pathlib.py find_prefixed -> os.scandir(root)
```

Auxiliary observations actually performed in round 1 (kept as raw facts, but **not** evidence
that the command passed):

1. Manual `mkdir` + `os.scandir` + `os.listdir` + `tempfile.mkdtemp` in the same parent
   directories all succeeded.
2. Calling pytest's own `find_prefixed(pytest-of-dlam12138, "pytest-")` and
   `make_numbered_dir(...)` directly both raised `PermissionError 5`.
3. Redirecting `TEMP` and `--basetemp` did not help (commands 2 and 3).
4. Running the three test bodies directly with real directories produced five `True`
   assertions (command 20).

**None of this substitutes for a pytest pass.** Direct test-body execution bypasses pytest's
collection, fixtures and setup, so it is not the same proposition as "the contract command
exits 0". Round 1's inference that the environment limitation "does not affect passing", and
any equivalence between direct invocation and pytest success, are removed; this document does
not itself declare the suite green.

The authoritative passing evidence is Codex's independent rerun: on the same HEAD
`b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`, with the **identical contract command**, Codex
obtained **190 passed, exit 0** (no errors). So:

```text
round-1 harness : 187 passed + 3 setup errors / exit 1   (real round-1 result, preserved)
Codex rerun     : 190 passed / exit 0                    (authoritative passing evidence)
```

The three-case difference is exactly the three setup-blocked `tmp_path` cases; the attribution
to the round-1 session sandbox is supported by Codex's rerun, not self-declared here. The final
judgement belongs to Codex. No test was modified, skipped, weakened or deleted.

### Round 2 repair run (measured after the fixes)

From `D:/量化分析-m4-matrix-design`; the pytest command was run exactly **once**, with no custom
`TEMP`/`--basetemp` and no probe file written.

| # | Command | Exit | Result |
| --- | --- | --- | --- |
| 1 | the same six-file `pytest -q` contract command | **1** | `187 passed, 2 warnings, 3 errors in 2.83s`; the 3 errors are the same setup-stage `pytest-of-dlam12138` `PermissionError [WinError 5]`; **not** reported as a pass |
| 2 | `git diff --check` | **0** | clean |
| 3 | `git diff --cached --check` | **0** | clean (empty index) |
| 4 | `git status --short` | **0** | exactly 5 untracked entries: the existing Goal + the four authorized documents |
| 5 | `git rev-parse HEAD` | **0** | `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef` (unchanged, uncommitted) |
| 6 | `git worktree list --porcelain` | **0** | 12 worktrees, all preserved |
| 7 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 8 | `git rev-parse refs/stash` | **0** | `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` = protected value |
| 9 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222` = protected value |
| 10 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only) |
| 11 | `git -c http.proxy= -c https.proxy= ls-remote origin` | **128** | `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS` — remote git refs still could not be refreshed |
| 12 | `git rev-parse origin/main origin/codex/m4-synthetic-dataset-adapter` | **0** | `bab24f98…` / `b0c8fafb…` (local tracking refs) |
| 13 | `gh pr view 11 --json …` | **0** | `OPEN`, head `b0c8fafb…`, base `main`, `MERGEABLE`, `mergedAt=null` (live) |
| 14 | `gh api --paginate repos/.../commits/b0c8fafb…/check-runs` | **0** | all **42** runs fetched via pagination, conclusion `success` for every one (the default first page returns only 30) |
| 15 | `gh api repos/.../commits/b0c8fafb…/status` | **0** | `pending` (no legacy commit status; check-runs only) |
| 16 | Markdown audit of the four deliverables + the existing Goal (UTF-8/BOM/CR/TAB/trailing whitespace/final newline/conflict markers/fences + relative links) | **0** | all five `issues=NONE`, no missing relative links |
| 17 | Round-2 self-check over the four documents (forbidden two-argument signature, retired `_verified` name, the false collision claim, `source_series_role` bindings) | **0** | no public two-argument entry, no `_verified` name, no collision claim (only framed correction records), bindings match `compiler.py::_terms` |
| 18 | Read-only stdin probe: real fixture → `build_analysis_plan` → `plan_to_canonical_dict`, printing the real `ordered_terms` / `response_role` / requirement roles / condition | **0** | real output matches the four documents: `INTERCEPT→null`, `FACTOR_CONTINUOUS→"FACTOR"`, `CONTROL_00nn→itself`, `CONDITION_INDICATOR→"CONDITION_INDICATOR"`; `requirement_roles=[TARGET_OUTCOME,FACTOR,CONTROL_0001,CONTROL_0002]` (the indicator role is indeed not in `role_order`); `threshold="-0.01"` |

Round-2 honest statement: this harness **again** produced `187 passed + 3 setup errors`, exit 1
(the same `pytest-of-*` setup denial), so this document does **not** claim the suite passes in
this harness. The authoritative passing evidence remains Codex's independent `190 passed /
exit 0` on the same HEAD with the identical command. Round 2 performed no direct test-body
invocation and used no substitute to make the pytest command look green. No test was modified,
skipped, weakened or deleted.

### Round 3 repair run (measured after the three targeted fixes)

From `D:/量化分析-m4-matrix-design`. The contract pytest command was run exactly **once**, with
no custom `TEMP`, no `--basetemp`, no probe file and no test-body invocation. Every other command
below is read-only.

| # | Command | Exit | Real result |
| --- | --- | --- | --- |
| 1 | the same six-file `pytest -q` contract command | **1** | `187 passed, 2 warnings, 3 errors in 2.70s`; the 3 errors are setup-stage `pytest-of-dlam12138` `PermissionError [WinError 5]` under `C:\Users\111\AppData\Local\Temp\dsh-CxqUfP\pytest-of-dlam12138`, i.e. exactly the three `tmp_path` cases `test_cwd_and_from_dict_order_invariance`, `test_semantic_ab_equivalence_and_cwd_independence`, `test_yaml_loader_requires_mapping_and_rejects_object_tags`; the 2 warnings are `PytestCacheWarning` for `.pytest_cache\v\cache\{nodeids,lastfailed}` (same `WinError 5`); **not** reported as a pass |
| 2 | `git diff --check` | **0** | clean |
| 3 | `git diff --cached --check` | **0** | clean (empty index) |
| 4 | `git status --short` | **0** | exactly 5 untracked entries: the existing Goal + the four authorized documents |
| 5 | `git rev-parse HEAD` | **0** | `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef` (unchanged, uncommitted) |
| 6 | `git worktree list --porcelain` | **0** | 12 worktree entries, all preserved |
| 7 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 8 | `git rev-parse refs/stash` | **0** | `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` = protected value |
| 9 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222` = protected value |
| 10 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only; contents never read) |
| 11 | `git -c http.proxy= -c https.proxy= ls-remote origin` | **128** | `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS` — remote git refs **not** refreshed |
| 12 | `git rev-parse origin/main origin/codex/m4-synthetic-dataset-adapter` | **0** | `bab24f98…` / `b0c8fafb…` (local tracking refs, cached) |
| 13 | `gh pr view 11 --json state,headRefOid,baseRefName,mergeable,mergedAt` | **1** | `Post "https://api.github.com/graphql": EOF` — GitHub API **unreachable** this round; PR state **not** refreshed |
| 14 | `gh api --paginate .../commits/b0c8fafb…/check-runs` and `gh api .../commits/b0c8fafb…/status` | **1** | `EOF` for both; check-runs **not** re-read in round 3 |
| 15 | repeat `gh pr view 11` + `gh api rate_limit` (reachability confirmation) | **1** | `EOF` for both again — the API was genuinely unreachable, not a one-off parse error |
| 16 | Markdown audit of the four deliverables + the existing Goal (UTF-8/BOM/CR/TAB/trailing whitespace/final newline/conflict markers/fence balance + relative-link resolution) | **0** | all five `OK`, `MISSING_RELATIVE_LINKS=NONE` |
| 17 | Round-3 global phrase scan over the four documents (forbidden `source_series_role` uniqueness/non-injectivity assertions, "field-for-field mirror (no additions/removals)", "display-only") | **0** | design / acceptance-cases / acceptance documents: 0 hits; the work record: hits exist **only** inside the labelled round-2/round-3 finding-and-fix correction rows |
| 18 | Static check of the real schema in `datasets/synthetic.py` | **0** | `QualityReportV1` has exactly 7 fields and **no** `status`; `DatasetPreparationV1` **has** top-level `status`; therefore "7 copied fields + inherited `status`" is the true statement |
| 19 | Read-only stdin probe (no file written): real fixture → `build_analysis_plan` → `plan_to_canonical_dict`, plus `compiler.py::_terms` for 0/2/3 controls | **0** | real pairs `INTERCEPT→None`, `FACTOR_CONTINUOUS→"FACTOR"`, `CONTROL_00nn→itself`, `CONDITION_INDICATOR→"CONDITION_INDICATOR"`; for 0/2/3 controls `term_role` values pairwise distinct, `source_series_role` values pairwise distinct, mapping injective = `True` in all three cases |

Round-3 honest statement: this harness produced `187 passed + 3 setup errors`, exit 1 again (the
same `pytest-of-*` setup denial), so this document does **not** claim the suite passes here. The
authoritative passing evidence remains Codex's independent `190 passed / exit 0` on the same HEAD
with the identical command. Round 3 performed no direct test-body invocation and used no
substitute to make the pytest command look green. No test was modified, skipped, weakened or
deleted. Unlike round 2, the GitHub API was unreachable in round 3, so the PR #11 / check-run
values below are round-2 measurements and are **not** claimed as freshly re-verified.

## Remote synchronization (partial)

- In all three rounds `git ls-remote` failed (exit 128, TLS credential failure), so the **remote
  git refs were never refreshed** and no synchronization with live remote git state is claimed.
  The local tracking refs match the declared baseline, but they are cached values.
- Rounds 1 and 2 refreshed PR #11 through the `gh` API: `OPEN`, unmerged, `MERGEABLE`, head
  `b0c8fafb…`, and all **42/42** check-runs `success` when fetched with `--paginate` (the API's
  default first page returns only 30 runs). **Round 3 could not refresh any of this**: every
  `gh` call returned `EOF` (confirmed twice, including a bare `gh api rate_limit`), so the PR
  state and check-runs are the round-2 live values and are not claimed as freshly re-verified.
- This branch has no remote counterpart and was not pushed in any round.

## Protected state

```text
branch / HEAD          codex/m4-analysis-matrix-design @ b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef (uncommitted, round 3)
index                  empty (nothing staged; no git add)
modified tracked files none (git diff --check and git diff --cached --check both exit 0)
original M2 HEAD       3679b1bac7a1634c6452784a4d8f6d139966f222 = protected
stash                  cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f = protected (not applied, not dropped)
DB SHA256              4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 = protected
worktrees              12, all preserved, none switched or cleaned
untracked (exactly 5)  agent/goals/2026-09-10_m4_analysis_matrix_design.md (existing Goal, unmodified)
                       docs/m4_analysis_matrix_design_v1.md
                       docs/m4_analysis_matrix_acceptance_cases_v1.md
                       agent/record/2026-09-10_01_m4-analysis-matrix-design.md
                       acceptance/2026-09-10_m4_analysis_matrix_design.md
temporary/probe files  none (confirmed absent; round 3 wrote none)
ignored preserved      pre-existing .tmpv4/.tmpv5/.tmpv6/.tmp_local_verify untouched
```

No source, test, README, dependency, workflow, historical design, frozen artifact or protected
hash was modified. No database connection was opened; only a SHA256 of the DB file was
computed. No provider, real market data, holdout or statistics were touched.

### Temporary artifacts: no residual deviation (round-3 recheck)

- The three leftover probes from the interrupted round (`.matrix_design_probe.py`,
  `.matrix_design_probe2.py`, `.matrix_design_probe3.py`) were deleted in round 1 and are
  confirmed **absent** in rounds 2 and 3.
- Round 1 created a diagnostic directory `.tmp_matrix_design_verify/` inside the worktree while
  investigating the `tmp_path` errors and could not remove it in that sandbox; it was reported
  as needing manual cleanup outside the sandbox. **Codex deleted it after the exact verification
  path**, and round 2 confirms it is **absent**.
- Therefore no cleanup is requested from the user, no temporary probe or verification directory
  from this task remains, and the untracked state is exactly the existing Goal plus the four
  authorized documents.
- Round 3 wrote no probe file and created no directory: the schema/mapping confirmation was
  executed through standard input only, and the round-3 recheck confirms the same five-item
  untracked state.
- `.tmpv4/`, `.tmpv5/`, `.tmpv6/` and `.tmp_local_verify/` are pre-existing ignored
  runtime/cache directories that predate this task and were left untouched.

## Exact deliverables

```text
docs/m4_analysis_matrix_design_v1.md                  revised (round-1 draft corrected; round-2 and round-3 findings fixed)
docs/m4_analysis_matrix_acceptance_cases_v1.md        new (AC-01 … AC-15, plus AC-08b; AC-15 synced in round 3)
agent/record/2026-09-10_01_m4-analysis-matrix-design.md  new (round-1 work log + round-2 and round-3 repair logs)
acceptance/2026-09-10_m4_analysis_matrix_design.md    new (this document)
```

Plus the pre-existing, unmodified Goal `agent/goals/2026-09-10_m4_analysis_matrix_design.md`,
which together with these four documents forms the five-document package. The contract itself
deliberately stays in `D:/量化分析/agent/goals/` and is not copied into this worktree.

## What is NOT claimed

- No matrix implementation exists; no implementation test passed.
- The `matrix_digest` values in the design and cases documents are **design-specification
  recomputations** produced by an independent read-only projection over real upstream outputs.
  They are not outputs of a matrix product.
- No statistical validity, full rank, estimability, significance, tradability or execution
  authorization is claimed or implied.
- No M4-B entry, no holdout execution, no PR #11 merge.
- Synthetic-source evidence is not real research evidence.

## Stop conditions and next step

This delivery stops at design. No commit, push, PR, merge or next stage was performed, and
none is authorized by this task. Per the contract, codex must independently verify the real
branch, HEAD, diffs, changed and untracked files, test results, all worktrees and stashes,
protected baselines and live remote state, then compare the four documents against the real
interfaces and recompute the examples. The verdict must be exactly one of PASS,
CHANGES_REQUIRED or BLOCKED; this document reports evidence only and does not assign that
verdict itself. Matrix implementation, PR #11 merge and any M4-B or statistical execution stage
each require separate explicit user authorization.

## Codex independent final review — 2026-09-11

Verdict: **PASS**.

Codex independently inspected the branch, HEAD, all changed and untracked paths, the four
deliverables, the existing Goal, all worktrees, the stash, protected files and live remote
state after round 3. The exact contract regression command completed with `190 passed in
2.26s` and exit code 0. `git diff --check` and `git diff --cached --check` both exited 0.
UTF-8, final-newline, whitespace, conflict-marker and relative-link checks found no issue in
the five-document package. The embedded canonical matrix example recomputed to
`a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a`, exactly matching
the documented `matrix_digest`.

The final worktree remains on `codex/m4-analysis-matrix-design` at
`b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`. The pre-existing Goal and its hash are
unchanged; the only task outputs are the four authorized Markdown files. Stash
`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` and database SHA256
`4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` remain unchanged.
Live `main` is `bab24f981fef9336b84280544ce709702b9df116`; live adapter is
`b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`. PR #11 remains open and unmerged at that
adapter HEAD, with 42 checks and no non-success conclusion.

This PASS closes the design stage only. No commit, push, merge, matrix implementation,
statistical execution or next-stage authorization is included.
