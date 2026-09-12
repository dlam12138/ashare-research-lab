# Acceptance: M4 synthetic-only bounded execution implementation

Final Codex reviewer verdict: **PASS**. The Harness verdict below records its sandbox-local commit
blocker. Codex independently reproduced the implementation checks in a host shell, resolved that
mechanical blocker with the contract-authorized explicit-path commit, and accepted the content.
The commit hash is reported in the external final evidence packet because the commit is created
after this document's final validation.

Harness verdict before reviewer resolution: **BLOCKED** — the implementation, tests, README
synchronization, record and this document are complete and validated in the working tree, but the
Goal-mandated scoped local commit cannot be created because this sandbox denies every write to the
linked git directory (see "Blocking condition").  This is **not** a self-acceptance: the Goal and
`AGENTS.md` make Codex's independent verdict authoritative, and the missing commit is the single
unmet requirement.  No push, PR, merge or next stage is attempted or authorized.

Verdict scope: the frozen M4 bounded-execution design is implemented for **synthetic fixtures
only** on the whitelist paths of
[the Goal contract](../agent/goals/2026-09-12_m4_bounded_execution_implementation.md).  No real
data, provider, database content, holdout or M4-B access occurred, and no upstream schema, digest
algorithm, planning/dataset module, top-level mechanism file, dependency, workflow or protective
test was changed.

- Task contract: [Goal](../agent/goals/2026-09-12_m4_bounded_execution_implementation.md).
- Normative design: [specification](../docs/m4_bounded_execution_and_evidence_design_v1.md).
- Acceptance cases: [bounded execution scenarios](../docs/m4_bounded_execution_acceptance_cases_v1.md).
- Work record: [work log](../agent/record/2026-09-12_01_m4-bounded-execution-implementation.md).
- New implementation: [execution package](../src/ashare_research/mechanism/execution/__init__.py),
  [bounded executor](../src/ashare_research/mechanism/execution/bounded.py).
- New tests: [bounded execution acceptance tests](../tests/test_m4_bounded_execution.py).

## Baseline and scope

Verified independently at task start: branch `codex/m4-bounded-execution-implementation`, HEAD
`070a26ad967016580d56f046d73c52f3d41010e9`, worktree clean, `main` and `origin/main`
`f34adcb17c9995392690a1df6bb5a10ee102eb09`, 15 worktrees preserved, only the pre-existing
`stash@{0}` present, protected M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`, protected
database SHA256 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` (hash only; the
database was never opened).

Changed paths are exactly the Goal whitelist: the two new files under
`src/ashare_research/mechanism/execution/`, the new test file, `README.md`, the two allow-listed
test files, the work record and this document.  No other path is added, changed or deleted; in
particular there is **no diff** under `planning/**`, `datasets/**`, any top-level
`src/ashare_research/mechanism/*.py`, `reports/**`, the north-star documents, dependencies,
workflows or configuration.

## Implementation summary

`execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs)` is the only
statistical-execution entry.  It runs the frozen order X1-X16:

| Step | Behaviour |
| --- | --- |
| X1 | recursive frozen-dataclass/tuple/strict-type shape check of the five source-bound objects |
| X2 | the existing five-argument `validate_design_matrix`; upstream `AdapterError`/`MatrixError` propagate unchanged |
| X3 | `analysis_method_id`/`model_family` allow-lists (`UNSUPPORTED_ANALYSIS_METHOD`/`UNSUPPORTED_MODEL_FAMILY`) |
| X4 | quality precondition (`status`, non-empty rows, exact rational coverage gate) carrying the plan's quality word on the refusal |
| X5 | `mode == "SYNTHETIC"` and the fail-closed holdout boundary (authorization bit plus row-window check) |
| X6 | plan `ordered_terms` ↔ matrix columns, unique `INTERCEPT`/`CONDITION_INDICATOR`, response role, row alignment and indicator cross-check, conditional-summary role consistency, evidence binding text |
| X7 | single deterministic conversion of every cell and response value: canonical decimal → exact range gate → float64 → finiteness |
| X8-X10 | `matrix_rank` gate, `numpy.linalg.lstsq`, rank/residual contract, finite output validation |
| X11-X13 | bootstrap allow-lists, plan-declared seed/replications, exact integer block length, one `PCG64` draw per replication in ascending order, per-resample rank gate (fail-closed), exact order-statistic endpoints |
| X14 | strict `"0"`/`"1"` indicator coding, plan-required role set/order, frozen mean/median/difference rules |
| X15 | direction allow-list and the frozen D2-D10 precedence table with strict, tolerance-free comparisons |
| X16 | immutable construction, canonical self digest, forbidden-key/absolute-path rejection |

`prepare_registered_robustness_dispatch(..., robustness_ids)` runs R0-R6 (= X1-X7, source
verification first), then R7 request validation (ordered, non-empty, duplicate-free, fully
registered, dispatch-only plan boundary), R8 registry binding (`method_id` identifier and
`FrozenJSONObject` parameters, forwarded verbatim and immutably) and R9 dispatch-artifact
construction with `statistics_computed = False` and `outcome_read = False`.  No robustness
statistic, parameter interpretation, selection, ranking, aggregate or "best result" exists in the
schema, and the serializer rejects such key names.

`validate_execution_artifact`/`validate_robustness_artifact` run V1 (artifact structure,
invariants, content rules, self digest), V2 (`validate_design_matrix`), V3 (re-execution, or
re-dispatch for the dispatch artifact, with the same seed) and V4 (byte-for-byte comparison).
The primary `artifact_digest` binds the full source chain, provenance, full method configuration
(including `numeric_runtime`), sample facts, every float64 output through
`Float64ValueV1{float64_hex, canonical_decimal}` and the three status bits; the dispatch artifact's
digest binds the source chain, provenance, method configuration, sample facts, request order,
registry order, `method_id` and the complete canonical parameters — and no float64 statistic,
because that schema has none.

Both entries are IO-free, take the full five-object chain, expose no `**kwargs`, and compute
randomness only from the plan-declared `seed` with `PCG64`.  `execution_authorized` is `False`
everywhere; `provenance` is an explicit `SYNTHETIC_TEST_ONLY` marker; the frozen
`interpretation_boundary` literal is part of the primary artifact and of its digest.

## Acceptance-case coverage (AC-01..AC-19)

All cases are implemented against real code in
`tests/test_m4_bounded_execution.py` and none is skipped, xfailed or weakened.

| ID | Test | Kind |
| --- | --- | --- |
| AC-01 | `test_ac01_full_rank_synthetic_artifact_structure` | genuine: 24x5 full-rank synthetic fixture, full artifact structure, digest recomputation, canonical bytes, `validate_execution_artifact` |
| AC-02 | `test_ac02_base_fixture_is_rejected_as_singular` | genuine: untouched 3x5 fixture, `rank <= 3 < 5`, `SINGULAR_DESIGN` |
| AC-03 | `test_ac03_source_tamper_is_an_upstream_error_at_x2` | genuine: rehashed preparation and rehashed bound inputs both refused with upstream `AdapterError("IDENTITY_CONFLICT")` |
| AC-04 | `test_ac04_forged_matrix_and_forged_artifact_stages` | genuine: `M1` rehashed matrix → upstream `IDENTITY_CONFLICT`; `M2` stale digest → `MATRIX_DIGEST_MISMATCH`; `M3` authorization flag → `INVALID_INPUT_STRUCTURE`; forged artifact `A1` (disposition changed, digest recomputed) → V4 `IDENTITY_CONFLICT`; `A2` (field changed, digest stale) → V1 `ARTIFACT_DIGEST_MISMATCH` |
| AC-05 | `test_ac05_order_source_errors_precede_method_quality_and_dispatch`, `test_ac05_order_legal_source_with_multiple_defects_and_quality_first` | genuine for 5a/5b/5e/5f/5g (source error first, `EMPTY_ROBUSTNESS_DISPATCH`, `UNREGISTERED_ROBUSTNESS_ID`) plus structural marker-order assertions; 5c/5d are unreachable by construction (see deviations) |
| AC-06 | `test_ac06_unsupported_methods_fail_closed_without_downgrade` | upstream refusal for 6a-6d (a forged method/family/bootstrap value is rejected by the plan validator at X2) plus the frozen allow-list assertions |
| AC-07 | `test_ac07_cell_range_and_non_finite_gates` | genuine: `1000001` and `1e18` → `CELL_OUT_OF_RANGE` on both entries, exact upper bound `1000000` passes X7, non-finite renderings → `NON_FINITE_ESTIMATE` |
| AC-08 | `test_ac08_bootstrap_enabled_exact_indices`, `test_ac08_endpoints_are_exact_order_statistics_and_bounded_below_two_replications` | genuine: the seven `level`/`B` rows with exact `interval_alpha`/indices; `B=8` endpoints independently recomputed from the frozen sampling contract; `B=1` → `INSUFFICIENT_REPLICATIONS` |
| AC-10 | `test_ac10_disposition_table_all_directions`, `test_ac10_zero_endpoints_are_never_supported_and_confidence_precedes_direction` | genuine: POSITIVE/NEGATIVE/TWO_SIDED × above/below/includes zero, exact `0.0` endpoints, confidence precedence, tiny positive effect, no tolerance helpers |
| AC-11 | `test_ac11_quality_rejection_produces_no_executable_matrix`, `test_ac11_incomplete_coverage_is_explicit_and_does_not_rewrite_disposition` | genuine: FAIL_CLOSED and RETAIN_IN_DENOMINATOR rejections produce `REJECTED_QUALITY`/no matrix; incomplete coverage stays `READY_SYNTHETIC` with explicit `coverage_complete = False`; the refusal carries the plan's quality word |
| AC-12 | `test_ac12a_verbatim_registered_dispatch_on_the_unmodified_fixture`, `test_ac12_dispatch_request_validation_and_ordering_cases`, `test_ac12_defense_in_depth_registry_mutation_is_refused_upstream` | genuine: verbatim `{"trim":"0.0100","window":["1","2","3"]}` forwarding, request/registry order, unrequested entries absent, empty/duplicate/unregistered refusal, forged registry refused upstream |
| AC-13 | `test_ac13_holdout_is_unreachable_by_signature_and_plan` | genuine: `TypeError` for undeclared `holdout`/`window`/`split`/`real_data` on both entries, declared holdout window stays unauthorized and executes, `HOLDOUT_EXECUTION_NOT_AUTHORIZED` propagates as `AdapterError("CONTRACT_PLAN_MISMATCH")`, plus structural X2 < X5 |
| AC-14 | `test_ac14_input_permutation_key_order_and_cwd_invariance` | genuine: reversed observations, key-shuffled payload and a changed working directory all reproduce the same digest and bytes |
| AC-15 | `test_ac15_byte_reproducibility_roundtrip_and_cross_process` | genuine: twice in-process, canonical-dict independence, JSON round trip, fresh-interpreter subprocess hash, V1-V4 validation |
| AC-16 | `test_ac16_nested_mutations_change_every_identity_layer` | genuine: `trim`, `confidence_requirement`, `seed` and nested `window` element mutations each change the bound identities (and the main artifact is unaffected by `trim`); mixing a new contract with an old plan → `CONTRACT_PLAN_MISMATCH` |
| AC-17 | `test_ac17_synthetic_provenance_and_forbidden_content_rejection` | genuine: provenance fields, frozen literal, no forbidden keys/absolute paths, serializer actively rejects an absolute-path runtime and a forbidden `best` parameter key, `synthetic_test_only=False` refused |
| AC-18 | `test_ac18a_...`, `test_ac18b_...`, `test_ac18c_18d_...`, `test_ac18f_18g_...` | genuine: upstream bytes unchanged by execution, every numeric field is `Float64ValueV1` (no bare float in the payload), `float64_hex` is part of the primary identity while `0.0`/`-0.0` share a disposition, `numeric_runtime` is bound, the dispatch artifact has no statistic block and binds source chain/order/`method_id`/parameters/provenance |
| AC-19 | `test_ac19a_enabled_is_a_strict_copy_and_never_downgrades`, `test_ac19b_disabled_path_is_explicit_and_never_touches_randomness`, `test_ac19c_plan_level_pairing_error_propagates_and_is_not_loosened` | genuine: strict plan copy, disabled path with `null` method fields and no randomness API, fail-closed `INSUFFICIENT_REPLICATIONS` and `SINGULAR_RESAMPLE` (a 3-row full-rank fixture whose resamples are rank-deficient), plan-level `INVALID_BOOTSTRAP_POLICY` unchanged |

Additional structural coverage: the frozen public surface is exactly the eight entries with no
`VAR_KEYWORD`, the private helpers are not exported, the step markers appear in the frozen order,
every artifact dataclass field name matches the design, no forbidden import or IO surface exists,
and the public entries run with `open`/socket denied.

## Validation commands (real exit codes)

Run from `D:/量化分析-m4-executor-implementation` with
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')` and interpreter
`D:/量化分析-m4a2i/.venv/Scripts/python.exe`.

| # | Command | Exit | Real result |
| --- | --- | --- | --- |
| 1 | `python -m pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py` | **0** | `49 passed` |
| 2 | `python -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `15 passed` |
| 3 | `python -m pytest -q -p no:cacheprovider tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | **1** | `252 passed, 3 errors` — identical to the pre-implementation baseline; the 3 errors are the pre-existing sandbox `tmp_path` denial analysed below |
| 4 | `python -m ruff check src/ashare_research/mechanism/execution tests/test_m4_bounded_execution.py tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `All checks passed!` |
| 5 | `git diff --check` | **0** | clean |
| 6 | `git diff --cached --check` | **0** | clean |
| 7 | `git status --short --branch` | **0** | exactly the whitelist paths (3 modified + 4 untracked entries), branch `codex/m4-bounded-execution-implementation` |
| 8 | `git rev-parse HEAD origin/main refs/stash` | **0** | `070a26ad967016580d56f046d73c52f3d41010e9` (unchanged: the delivery commit is blocked, see below) / `f34adcb…` / `cb568ef…` |
| 9 | `git worktree list --porcelain` | **0** | 15 worktrees, all preserved |
| 10 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 11 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | **0** | `f34adcb17c9995392690a1df6bb5a10ee102eb09` (live) |
| 12 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | **0** | `[]` (live) |
| 13 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only) |
| 14 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222` = protected value |
| 15 | explicit writable `--basetemp=tmp/pytest-basetemp` reproduction of command 3 | **1** | `252 passed, 3 errors` — the explicit basetemp does **not** fix it; see the analysis below |
| 16 | changed-path whitelist, forbidden imports, UTF-8/BOM/CR/tab/trailing-whitespace/final-newline/conflict-marker audit over the changed files, and repository-relative Markdown link resolution | **0** | all clean; all links resolve |

### Pre-existing sandbox `tmp_path` failure (reproduced, not hidden)

Command 3 exits 1 because three `tmp_path` cases fail during pytest **setup** before any test body
runs.  This reproduces identically on the untouched baseline (measured before any edit:
`252 passed, 3 errors`, exit 1) and on the implementation tree, so it is not caused by this
delivery:

```text
ERROR tests/test_m4_synthetic_dataset_adapter.py::test_cwd_and_from_dict_order_invariance
ERROR tests/test_m4_stage4a2i_analysis_plan.py::test_semantic_ab_equivalence_and_cwd_independence
ERROR tests/test_m4_stage4a1_typed_contract.py::test_yaml_loader_requires_mapping_and_rejects_object_tags

PermissionError: [WinError 5] access denied:
  C:\Users\111\AppData\Local\Temp\dsh-<session>\pytest-of-dlam12138
at _pytest/pathlib.py find_prefixed -> os.scandir(root)
```

The explicit writable `--basetemp` reproduction (command 15) fails the same way, which localises
the cause: this sandbox denies enumerating and removing directories created with POSIX mode
`0o700`, and pytest creates both its basetemp root and every numbered temp directory with
`mode=0o700` (`_pytest/tmpdir.py` lines 139/141/158 and `_pytest/pathlib.py` line 224).  Measured
in this session:

```text
os.mkdir(path, 0o700) -> os.scandir(path) -> PermissionError [WinError 5]   (and rmdir denied)
os.mkdir(path, 0o777) -> os.scandir(path) -> OK
os.mkdir(path, 0o755) -> os.scandir(path) -> OK
os.mkdir(path, 0o750) -> os.scandir(path) -> OK
```

Because pytest always recreates the basetemp and its children with `0o700`, no `--basetemp`
location can avoid the denial; the three node IDs, the setup stage and the counts are otherwise
identical.  The command is reported as measured and is **not** claimed green.  No test was
modified, skipped or weakened.

## Deviations, interpretations and residual risks

1. **X3/X4/X5/X6 method, quality, mode and alignment gates are unreachable end-to-end.**  The
   frozen source chain is byte-compared against a re-projection, so a plan whose method family or
   direction was forged, a non-synthetic mode, a rejected preparation or a mis-aligned matrix is
   refused by the upstream validator at X2 before the executor's own gate runs.  The gates are
   still implemented with the frozen codes and are covered by genuine upstream-refusal tests plus
   structural order assertions, exactly as the cases document requires for defense-in-depth
   cases.  Measured nuance for AC-05a/5c: with an illegally forged plan the first error is
   `AdapterError("CONTRACT_PLAN_MISMATCH")`, not `IDENTITY_CONFLICT`, because the plan check runs
   inside `validate_dataset` before the preparation byte comparison; no error is masked and the
   ordering assertion (X2 before X3-X16/R7-R9) holds.
2. **AC-11c is unreachable by construction.**  A matrix whose quality facts contradict the exact
   coverage gate cannot survive X2 (the re-projection inherits the adapter's own quality
   computation).  The `DATA_QUALITY_REJECTED` path, its `.disposition` carrier and the
   `status`/rows/gate three-way check are implemented and asserted structurally; the refusal
   contract is exercised directly (`ExecutionError("DATA_QUALITY_REJECTED").disposition ==
   "FAIL"`, and `"FAIL"` is not a disposition word).
3. **Design 10.5 vs 10.1/10.2 inconsistency (reported, not silently resolved).**  Design 10.5
   says *every* artifact must carry the frozen `interpretation_boundary` literal, but the frozen
   `RobustnessArtifactV1` field list in 10.1 and the structural constraints in 10.2 give the
   dispatch artifact no field able to carry it (and no `evidence` block).  Because the Goal
   requires the artifact fields to match the frozen schema, the literal is carried by the primary
   artifact (`evidence.interpretation_boundary`, part of its digest) and the dispatch artifact
   carries the explicit `provenance.provenance_class = "SYNTHETIC_TEST_ONLY"` marker instead.
   Adding a new field would have been a schema change, which the Goal forbids; this remains an
   open design-wording question for the reviewer.

   **Codex resolution:** the explicit frozen `RobustnessArtifactV1` field list and AC-18f are the
   controlling requirements. They prohibit an `evidence` block and float statistics on the
   dispatch-only artifact. Adding an unspecified field would violate the implementation Goal's
   no-schema-change rule. The dispatch artifact therefore carries its boundary through digest-bound
   `SYNTHETIC_TEST_ONLY` provenance and false authorization/statistics/outcome flags; the primary
   artifact alone carries `evidence.interpretation_boundary`. This interpretation is accepted and
   does not authorize real-data or holdout execution.

## Codex independent review resolution

Codex inspected the real branch, HEAD, changed and untracked paths, implementation/diff,
worktrees/stash/database/remote state, and the design ambiguity above. In the host shell, Codex
independently obtained `49 passed`, `15 passed`, and `255 passed`; ruff and diff checks passed. The
Harness-only three `tmp_path` setup errors did not reproduce outside its sandbox, confirming they
were environmental. No product or test change was needed to obtain the green host results. Codex
then stages only the eight Harness-delivery whitelist paths and creates the required scoped local
commit; no push, PR, or merge follows.
4. **Design 8.4 wording.**  "该词不出现在 `DISPOSITIONS` 里" is exact only for the `FAIL` word:
   `INCONCLUSIVE` is both a quality-failure word and one of the five disposition words.  The
   implementation keeps the two vocabularies separate by carrier (quality word only on the
   refusal, artifact dispositions only in artifacts), and the test asserts that `FAIL` is not a
   disposition word.
5. **Exact zero endpoints.**  The frozen estimator path cannot produce an exact `0.0` endpoint in
   general, but an exactly zero synthetic response makes `numpy.linalg.lstsq` return exactly
   `0.0` coefficients, so `AC-10i`/`AC-18d` use such a fixture: endpoints are literally
   `0x0.0p+0`, the disposition is `NOT_SUPPORTED`/`INTERVAL_INCLUDES_ZERO`, and flipping the
   endpoint to `-0x0.0p+0` keeps the disposition while changing the artifact identity.
6. **`method_configuration.artifact_schema_version`** stays `M4_BOUNDED_EXECUTION_ARTIFACT_V1`
   inside both artifacts, following the frozen field comment in design 10.1; the per-kind schema
   version lives in the artifact's top-level `artifact_schema_version`.  For the dispatch artifact
   `method_configuration.block_length` is `None` (no resampling was executed), which is the only
   honest value for the field the design defines as "the block length actually used".
7. **Byte reproducibility** is claimed only for a fixed `numeric_runtime` (numpy 2.5.3 here);
   cross-version/BLAS drift is detectable through `method_configuration.numeric_runtime` but not
   prevented.  The cross-process check runs under the same interpreter and runtime.
8. **Statistical scope.**  The numeric outputs are synthetic-fixture values used to exercise the
   frozen contract.  Nothing here claims estimability, significance, economic validity,
   tradability or an A-share mechanism result; synthetic readiness is not real-research
   authorization.
9. **The pre-existing sandbox `tmp_path` denial** (analysis above) is an environment limitation
   reproduced verbatim; it is not a code defect and it is not concealed.

## Blocking condition (the single unmet requirement)

The Goal's "Commit and push requirements" state that this Harness creates scoped local
implementation and evidence commit(s) using explicit path staging only.  The exact staging command
was executed after validation and was denied:

```text
$ git add -- src/ashare_research/mechanism/execution/__init__.py \
    src/ashare_research/mechanism/execution/bounded.py tests/test_m4_bounded_execution.py \
    README.md tests/test_project_entry.py tests/test_m4_stage4p_governance.py \
    agent/record/2026-09-12_01_m4-bounded-execution-implementation.md \
    acceptance/2026-09-12_m4_bounded_execution_implementation.md
fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4-executor-implementation/index.lock': Permission denied
[exit code: 128]
```

This worktree is linked to the repository at `D:/量化分析/.git`, outside this session's workspace
root `D:/量化分析-m4-executor-implementation`.  Permission probes measured in this session:

```text
D:/量化分析/.git/worktrees/量化分析-m4-executor-implementation/.dsh_write_probe -> DENIED (UnauthorizedAccessException)
D:/量化分析/.git/.dsh_write_probe                                              -> DENIED (UnauthorizedAccessException)
D:/量化分析-m4-executor-implementation/.dsh_write_probe                       -> WRITABLE
index.lock after the failure                                                   -> absent (nothing left behind)
```

The one-shot escalation of the identical command (the sanctioned retry after a real denial) was
refused: "sandbox escalation to \"danger-full-access\" requires approval, but no approval channel
is available".  Per the runtime rules that refusal is final, so **no workaround was attempted** —
no alternate `GIT_INDEX_FILE`, no alternate git directory, no repository re-initialisation, no path
aliasing, no `git add -A`.  `git commit --only <paths>` was also attempted through the standard CLI
and cannot work for the five untracked paths (they are not yet known to git), which is the same
blocked staging step.

Consequence: all eight whitelist paths exist as validated working-tree changes, `HEAD` is still the
baseline `070a26ad967016580d56f046d73c52f3d41010e9`, and the contract's commit requirement is
unmet.  This single unmet requirement is the whole reason for the `BLOCKED` verdict; every content
acceptance criterion is met as evidenced above.  The exact command sequence that resolves it, to be
run under Codex's authority in a shell with write access to `D:/量化分析/.git`:

```powershell
cd D:/量化分析-m4-executor-implementation
git add -- src/ashare_research/mechanism/execution/__init__.py `
    src/ashare_research/mechanism/execution/bounded.py `
    tests/test_m4_bounded_execution.py `
    README.md tests/test_project_entry.py tests/test_m4_stage4p_governance.py `
    agent/record/2026-09-12_01_m4-bounded-execution-implementation.md `
    acceptance/2026-09-12_m4_bounded_execution_implementation.md
git diff --cached --check
git commit -m "feat: implement synthetic-only M4 bounded execution (M4-A.2E)"
git status --short --branch
git rev-parse HEAD origin/main refs/stash
```

After that the status shows only the branch line, `HEAD` is the single scoped delivery commit, and
the protected baseline (`origin/main`, `refs/stash`, M2 HEAD, database hash) is unchanged.  No
push, PR or merge follows, and none is authorized.

## What is NOT claimed

- No real-data, provider, database-content, holdout or M4-B execution; no push, PR, merge or
  next-stage start.
- No generic research executor exists: the executor accepts only the frozen five-object synthetic
  chain, and every entry fails closed on anything else.
- No statistical or economic finding, and no upgrade path from synthetic-source evidence to real
  research evidence.
