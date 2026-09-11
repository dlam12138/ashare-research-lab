# Acceptance: M4 synthetic analysis matrix implementation

Verdict: **PASS**. This delivery implements the accepted matrix design as a pure,
deterministic module and adds its product tests. DeepSeek Harness completed the implementation
and recorded its linked-worktree sandbox restriction. Codex independently inspected the code,
repeated the exact targeted and regression commands outside that ACL sandbox, and obtained
`80 passed` and `270 passed`; Codex then staged exactly the four allowed implementation paths for
the required local commit. The protected state remains unchanged. The historical Harness failure
evidence below is retained because it accurately records that agent's environment; the independent
review resolution at the end of this document supersedes its temporary blocked status.

- Goal contract (committed at `125247d7401a3563c73a1b7ef31fa9a9587699d6`, unmodified):
  [implementation Goal](../agent/goals/2026-09-11_m4_analysis_matrix_implementation.md).
- Normative design (unmodified): [specification](../docs/m4_analysis_matrix_design_v1.md).
- Normative acceptance cases (unmodified):
  [synthetic matrix scenarios](../docs/m4_analysis_matrix_acceptance_cases_v1.md).
- Work record: [work log](../agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md).
- Base commit: `8a3b6a5d83d13aa9db71a0191f18b60af195b628` (design closeout), whose parent is the
  adapter commit `b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`; the Goal contract commit
  `125247d7…` sits directly on top of it.

## Scope and baseline

Branch `codex/m4-analysis-matrix-implementation` at Goal commit `125247d7…` before this work.
Verified at start: local `origin/main = bab24f981fef9336b84280544ce709702b9df116`, stash
`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`, protected M2 HEAD
`3679b1bac7a1634c6452784a4d8f6d139966f222`, all 13 worktrees present, and the protected
database SHA256 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`.
No baseline drift. Exact deliverables (the four allowed implementation paths):

```text
src/ashare_research/mechanism/planning/matrix.py              new (520 lines)
tests/test_m4_analysis_matrix.py                              new (1213 lines, 33 functions / 80 cases)
agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md  new (this round's work log)
acceptance/2026-09-11_m4_analysis_matrix_implementation.md    new (this document)
```

Nothing else was added or changed: no `__init__.py`, no accepted design document, no existing
source, test, README, dependency, workflow, schema, frozen artifact or protected hash.

## Implementation summary

**One public materialization entry.** `materialize_design_matrix(preparation, contract, plan,
bound_inputs)` first calls the existing four-argument `validate_dataset` (upstream `AdapterError`
values propagate unchanged, including upstream `IDENTITY_CONFLICT` and `CONTRACT_PLAN_MISMATCH`),
then applies the quality gate, then projects. There is no preparation-only public entry and no
public projection function; `_project_validated_matrix(preparation, plan)` is private, absent
from `__all__`, and is not an acceptance entry. `validate_design_matrix(matrix, preparation,
contract, plan, bound_inputs)` validates the matrix object (V1), re-runs `validate_dataset` (V2),
re-projects (V3) and compares canonical bytes (V4), raising `MatrixError("IDENTITY_CONFLICT")`
on mismatch.

**Frozen immutable types.** `MatrixColumnV1`, `MatrixRowV1`, `MatrixQualityV1` and
`MatrixPreparationV1` are frozen dataclasses with tuple containers. A private `_shape` performs
strict runtime type checking (exact dataclass type, `tuple` containers, `type(x) is int` so
`bool` is rejected); failures raise `MatrixError("INVALID_INPUT_STRUCTURE")`.

**Column order and dispatch.** Ordered columns come only from `plan.design_plan.ordered_terms`
(read through `plan_to_canonical_dict`), asserted against
`INTERCEPT, FACTOR_CONTINUOUS, role_order CONTROL_*, CONDITION_INDICATOR`; an unknown
`term_role` raises `UNSUPPORTED_TERM_ROLE`, a sequence/position/response-role mismatch raises
`PLAN_TERM_ROLE_MISMATCH`, a non-frozen `plan.schema_version` raises `UNSUPPORTED_PLAN_SCHEMA`.
Cell values are dispatched by `term_role` only: intercept is the literal `"1"`, the factor and
control cells are copied from `complete_rows[*].values` by role position, and the condition cell
is formatted from the row's strict integer `condition_indicator` as `"0"`/`"1"`. `source_role`
is audit/provenance metadata taken from the plan's `source_series_role`: it enters the canonical
payload and the digest, but never dispatches a cell.

**Canonical decimal identity.** Inputs are never re-parsed, rounded, reformatted or converted to
float; a non-canonical decimal or non-canonical date is rejected as `INVALID_INPUT_STRUCTURE`
rather than repaired. Quality is inherited, not re-judged: `quality.status` is
`preparation.status`, the other seven fields are copied field-for-field from
`preparation.quality`, and `execution_authorized` / `statistics_computed` are always strict
`False`.

**Rejection is total.** `status != "READY_SYNTHETIC"` or an empty `complete_rows` raises
`MatrixError("DATASET_NOT_READY")` before projection; no zero-row or truncated matrix object can
be returned, and `FAIL_CLOSED` rejects on any gap regardless of gate.

**Identity and serialization.** `matrix_to_canonical_dict` returns an independent dict/list tree
without `matrix_digest`; `matrix_digest = canonical_digest(payload)`; `serialize_matrix` emits
compact sorted UTF-8 JSON with exactly one trailing `\n` after adding `matrix_digest`.
Construction self-validates: after computing the digest the materializer re-checks every frozen
invariant, so it can never return an object its own validator rejects.

Three design-reading decisions are recorded explicitly in the work log section 4.4 for
independent review: (1) `matrix_digest` is excluded from the canonical dict (design section 6.5
listing plus constraint 5) and added only by `serialize_matrix` — both frozen example digests
reproduce exactly; (2) matrix-object (M1) invariant violations raise
`INVALID_INPUT_STRUCTURE` while `PLAN_TERM_ROLE_MISMATCH`/`UNSUPPORTED_TERM_ROLE` are raised
while reading the plan in the projection pipeline (design section 5.2's M1 sentence); (3) the
projection pipeline performs a final full invariant self-check (design section 4.4 "construction
validates"). All three tighten or preserve the gate and change no measured identity value.

## Acceptance-case coverage (real implementation calls, no mirror oracle)

Every product assertion calls the real module and the real adapter/compiler/digest; fixtures are
reused from `tests/test_m4_stage4a1_typed_contract.py` and
`tests/test_m4_synthetic_dataset_adapter.py`; no re-implementation of the production projection
is used as an oracle, and the private projection is never used as an entry point.

| Case | Coverage |
| --- | --- |
| AC-01 | `test_no_control_plan_projects_exactly_three_columns` — 3 columns, exact rows, `dataset_digest e0e52d46…`, `matrix_digest f6df25c4…` |
| AC-02 | `test_three_controls_grow_the_matrix_to_six_columns` — 6 columns, `dataset_digest 4c060328…`, `matrix_digest 13c18306…` |
| AC-03 | `test_reversed_control_registration_order_changes_identity_not_rows` — identical rows, `input_digest 4a863864…`, `dataset_digest d4cddef0…`, `matrix_digest 48f8a5b3…` |
| AC-04 | `test_condition_operator_boundaries_are_exact_at_zero` (4 operators, plan/indicator/matrix values at threshold `0`) and `test_condition_threshold_is_normalized_without_float_tolerance` (threshold `-0.0100` → `-0.01`; `-0.01` is inside `LTE`/`GTE`, outside `LT`/`GT`) |
| AC-05 | `test_missing_rows_keep_the_denominator_and_a_distinct_identity` (5 deletions, denominator stays 3, five distinct `dataset_digest`/`matrix_digest` pairs, rejected date disappears entirely) and `test_exact_gate_comparison_separates_0_66_from_0_67` (exact rational comparison) |
| AC-06 | `test_pit_invisible_rows_are_reasoned_and_identity_bearing` (`PIT_UNPROVEN 52298a8c…`, `PIT_NOT_AVAILABLE fce3d11e…`, both 2/3) |
| AC-07 | `test_rejected_quality_never_returns_a_partial_matrix` (4 sub-cases incl. `value=null`; `validate_dataset` passes first, then `MatrixError("DATASET_NOT_READY")`, no object, `complete_rows == ()`) |
| AC-08 | `test_self_consistent_source_tamper_is_rejected_before_projection` (rehashed indicator tamper: `serialize_dataset` accepts, four-argument entry raises upstream `AdapterError("IDENTITY_CONFLICT")`) |
| AC-08b | `test_forged_matrix_without_digest_refresh_fails_the_structure_stage` (V1 `MATRIX_DIGEST_MISMATCH`) and `test_rehashed_forged_matrix_fails_the_reprojection_stage` (V4 `MatrixError("IDENTITY_CONFLICT")`) |
| AC-09 | `test_rehashed_bound_inputs_are_rejected_by_the_source_gate` (`input_digest e877c147…`, `dataset_digest 2788e8ec…`, upstream `IDENTITY_CONFLICT`) |
| AC-10 | `test_nested_contract_change_moves_identity_but_not_cells` (four digests change, cells identical, mixed plan raises upstream `CONTRACT_PLAN_MISMATCH`) |
| AC-11 | `test_observation_permutation_and_roundtrip_preserve_identity` (reversed observations and `from_dict` round trip keep digest and bytes) |
| AC-12 | `test_key_order_and_working_directory_do_not_change_identity` (key-shuffled payload digest unchanged; `monkeypatch.chdir` re-materialization byte-identical; no path/host metadata in the bytes) |
| AC-13 | four tests: canonical values accepted, non-canonical values rejected `INVALID_VALUE`, cells copied without reformatting, bool/text/out-of-range indicators rejected, non-canonical complete-row value rejected upstream |
| AC-14 | `test_upstream_adapter_errors_propagate_unchanged` (6 codes, exact `AdapterError` type) and `test_validation_order_prefers_source_errors_over_the_quality_gate` (source error precedes quality gate; V1 precedes V2; V2 precedes V4, asserted through error **type** + code) |
| AC-15 | exact base shape/digest/bytes, exact frozen canonical payload shape, row/column/response-role invariants, quality inheritance, strict `False` authorization flags, immutability and defensive copies, 19 structurally forged matrices rejected as `INVALID_INPUT_STRUCTURE`, public-surface check (only the four callables, no preparation-only entry), and an AST import check proving no statistics/database/provider dependency |

## Actual validation commands and exit codes

Run from `D:/量化分析-m4-matrix-implementation` with
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`, exactly as the Goal specifies. No custom
`TEMP`, no `--basetemp`, no probe file, no direct test-body invocation.

| # | Command | Exit | Real result |
| --- | --- | --- | --- |
| 1 | `python -m pytest -q tests/test_m4_analysis_matrix.py` | **0** | `80 passed, 1 warning in 4.51s`; re-run on the final (documentation-edited) state: `80 passed, 1 warning in 4.56s`; the warning is the sandbox `PytestCacheWarning` for `.pytest_cache\v\cache\nodeids` |
| 2 | `python -m pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py` | **1** | `267 passed, 2 warnings, 3 errors in 14.86s`; re-run on the final state: `267 passed, 2 warnings, 3 errors in 7.47s`; the 3 errors are the pre-existing `tmp_path` sandbox denials (below); **not** reported as a pass |
| 3 | `python -m ruff check src/ashare_research/mechanism/planning/matrix.py tests/test_m4_analysis_matrix.py` | **0** | `All checks passed!` |
| 4 | `git diff --check` | **0** | clean |
| 5 | `git diff --cached --check` | **0** | clean (empty index) |
| 6 | `git status --short --branch` | **0** | branch line plus exactly two untracked new files (module and test) |
| 7 | `git rev-parse HEAD origin/main refs/stash` | **0** | `125247d7…` (Goal commit, pre-implementation-commit) / `bab24f98…` / `cb568efd…` (the latter two are the contract and protected values) |
| 8 | `git worktree list --porcelain` | **0** | 13 worktree entries, all preserved; protected M2 HEAD `3679b1ba…` unchanged |
| 9 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 10 | `git -c http.proxy= -c https.proxy= ls-remote origin` | **128** | `Failed to connect to github.com port 443` then `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS` — remote git refs **not** refreshed |
| 11 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | success (cmdlet sets no `$LASTEXITCODE`) | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only; database never opened) |
| 12 | `gh pr view 11 --json number,state,headRefOid,mergeable,url` | **0** | `state=OPEN`, `headRefOid=b0c8fafbfeea4c14837f6eafef2b2ff60c5df9ef`, `mergeable=MERGEABLE` (live refresh) |
| 13 | `gh pr checks 11` | **0** | **42 checks, all `pass`** — no new failure or regression at the adapter HEAD |
| 14 | `git add src/ashare_research/mechanism/planning/matrix.py tests/test_m4_analysis_matrix.py agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md acceptance/2026-09-11_m4_analysis_matrix_implementation.md` (Goal-required commit step) | **128** | `fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4-matrix-implementation/index.lock': Permission denied` — sandbox denies writes to the parent repository metadata |
| 15 | `git commit -m "feat: materialize immutable M4 design matrices from validated plans"` | **128** | same `index.lock` denial; no commit created, HEAD remains `125247d7…`, the four files stay untracked, index stays empty |

Supplementary (not Goal commands, used for attribution only): the identical regression command
was executed **before any modification** and produced `187 passed, 2 warnings, 3 errors in 2.87s`,
exit 1.

### Command 14/15: local commit blocked (real failure evidence kept)

```text
git add <four allowed paths>
  -> fatal: Unable to create
     'D:/量化分析/.git/worktrees/量化分析-m4-matrix-implementation/index.lock': Permission denied
  -> exit 128
git commit -m "feat: materialize immutable M4 design matrices from validated plans"
  -> fatal: Unable to create
     'D:/量化分析/.git/worktrees/量化分析-m4-matrix-implementation/index.lock': Permission denied
  -> exit 128
```

Cause and evidence: this session's file policy is workspace-write, which permits changes only
under `D:\量化分析-m4-matrix-implementation`; the worktree is a **linked worktree** whose `.git`
is a pointer file (`gitdir: D:/量化分析/.git/worktrees/量化分析-m4-matrix-implementation`), so the
index, object store and `refs/heads/*` all live in the parent repository outside the workspace. A
diagnostic write into `D:/量化分析/.git` was likewise denied (`UnauthorizedAccessException`), while
writes inside the workspace succeed; there was **no** stale `index.lock` (both the worktree and
common lock paths test `False`), so this is a policy denial, not a leftover lock. The sanctioned
escalation retry of the same command with `sandbox_permissions: danger-full-access` was rejected
with `requires approval, but no approval channel is available`, so the denial is final. No
workaround was attempted (no custom `GIT_INDEX_FILE`, no second repository, no hand-written
objects/refs). After the failure the worktree is unchanged: `git status --short --branch` lists
exactly the four untracked deliverables, `git diff --cached --check` exits 0 (empty index), and
`git rev-parse HEAD` is still `125247d7…`.

Recovery (needs a session with write access to `D:/量化分析/.git`, or an available approval
channel):

```powershell
cd D:/量化分析-m4-matrix-implementation
git add src/ashare_research/mechanism/planning/matrix.py tests/test_m4_analysis_matrix.py `
        agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md `
        acceptance/2026-09-11_m4_analysis_matrix_implementation.md
git commit -m "feat: materialize immutable M4 design matrices from validated plans"
git show --stat --oneline HEAD
```

### Command 2: real failure evidence kept, not dressed up

```text
267 passed, 2 warnings, 3 errors in 14.86s      exit code 1
ERROR tests/test_m4_synthetic_dataset_adapter.py::test_cwd_and_from_dict_order_invariance
ERROR tests/test_m4_stage4a2i_analysis_plan.py::test_semantic_ab_equivalence_and_cwd_independence
ERROR tests/test_m4_stage4a1_typed_contract.py::test_yaml_loader_requires_mapping_and_rejects_object_tags

isolated reproduction:
E  PermissionError: [WinError 5] access denied:
   'C:\Users\111\AppData\Local\Temp\dsh-bjpYza\pytest-of-dlam12138'
   at _pytest/pathlib.py:175 find_prefixed -> os.scandir(root)   (setup stage; test body never ran)
```

Attribution evidence: the same three errors already existed on the untouched baseline, so they
pre-date this implementation (187 baseline + 80 new = 267 passed); all three fail in pytest's own
`tmp_path` setup path, unrelated to any matrix call; `TEMP`/`TMP` point at the harness sandbox
temp area. No substitute run, no custom `TEMP`/`--basetemp` and no direct test-body invocation
was used to make the command look green, and the new test module deliberately avoids `tmp_path`
(AC-12 uses `monkeypatch.chdir` into `src/ashare_research`), so the new coverage runs fully in
this harness. The suite's pass/fail verdict belongs to Codex.

### Design-value recomputation

All design and acceptance-case expected values were re-measured on the real implementation by a
read-only stdin probe: base `matrix_digest a3c40269…` and `sha256(serialize_matrix) 70d9926e…`;
AC-01 `f6df25c4…`; AC-02 `13c18306…`; AC-03 `48f8a5b3…`; AC-04 all eight operator/threshold
scenarios (`6b7687e3…`, `a862e23b…`, `7b170345…`, `7fbfcf8f…`, `9d0c1f09…`, `a3c40269…`,
`e228c48e…`, `7a093d21…`); AC-05 all five deletion identities and the `0.66`/`0.67` gate pair;
AC-06 `52298a8c…`/`fce3d11e…`; AC-07 `c75953b9…` for the `value=null` rejection; AC-10
`b75877ee…`. Every value matched the frozen design example exactly.

## Remote synchronization (partial)

`git ls-remote` failed twice (exit 128: connection failure, then a TLS credential failure), so
remote **git** refs were not refreshed and no synchronization with live remote git state is
claimed; `origin/main = bab24f98…` is a cached local tracking ref matching the declared baseline.
The GitHub API was reachable through `gh`: PR #11 is still **OPEN and unmerged** at adapter HEAD
`b0c8fafb…` with **42/42 passing checks**. This branch has no remote counterpart and was not
pushed; no PR was opened and nothing was merged.

## Protected state

```text
branch / HEAD          codex/m4-analysis-matrix-implementation @ 125247d7401a3563c73a1b7ef31fa9a9587699d6
                       (Goal contract commit; the implementation commit could NOT be created — see above)
index                  empty (git add was denied; git diff --cached --check exits 0)
modified tracked files none
untracked (exactly 4)  src/ashare_research/mechanism/planning/matrix.py
                       tests/test_m4_analysis_matrix.py
                       agent/record/2026-09-11_01_m4-analysis-matrix-implementation.md
                       acceptance/2026-09-11_m4_analysis_matrix_implementation.md
original M2 HEAD       3679b1bac7a1634c6452784a4d8f6d139966f222 = protected, unchanged
stash                  cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f = protected, not applied, not dropped
DB SHA256              4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6 = protected, unchanged
worktrees              13, all preserved, none switched, cleaned or modified
ignored runtime data   untouched
```

No database connection was opened and no database content was read (only a file SHA256). No
provider, real market input, holdout or statistical computation was touched. The implementation
module imports only `json`, `re`, `dataclasses`, `datetime`, `decimal`, `types`, `typing` plus the
existing `datasets.synthetic`, `model_digest` and `planning` modules — asserted by an AST test.

Known environmental residue: pytest's cache provider left inaccessible, empty
`pytest-cache-files-*` directories in the worktree root; this session's sandbox denies all access
to them (`Get-ChildItem` / `Remove-Item` / `cmd rd` all "Access is denied"), so they cannot be
removed from inside this session. They are untracked, empty, excluded from the commit, and are
reported for cleanup by the reviewer. `git status` only prints a
"could not open directory … Permission denied" warning for them.

## What is NOT claimed

- No statistical validity, full rank, identifiability, estimability, significance, economic
  significance or tradability is claimed; `execution_authorized` and `statistics_computed` are
  always `False` and no regression, rank, bootstrap, robustness or evidence code is called.
- No real-data or provider evidence; synthetic-source identity is not real research evidence.
- No M4-B entry, no holdout access, no PR #11 merge, and no push.
- The suite pass/fail verdict is not self-assigned; the three pre-existing `tmp_path` setup
  errors are reported as they occurred.

## Stop conditions and next step

Implementation, independent review, product tests, and the required local commit are complete.
This stage stops here. Any push, PR, merge, statistical execution, or M4-B stage requires separate
explicit user authorization.

## Codex independent review resolution

Codex reviewed the real implementation rather than accepting the Harness report. The public API,
validation order, immutable payload, projection dispatch, quality inheritance, canonical digest,
serializer, and stable error behavior match the frozen design. The changed-path inventory contains
exactly the four implementation deliverables allowed by the Goal; the separately committed Goal is
unchanged. Independent commands produced `80 passed in 5.71s`, `270 passed in 14.92s`, and
`ruff: All checks passed!`. The three `tmp_path` setup errors recorded above did not reproduce
outside the Harness ACL sandbox. Codex resolved the Harness-only Git metadata restriction by
creating the required scoped local commit as the final action. No push, PR, merge, M4-B entry, or
statistical execution was performed.
