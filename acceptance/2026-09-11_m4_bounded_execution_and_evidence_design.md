# Acceptance: M4 bounded execution and evidence design

Revision: **R2** (current). R0 fixed the frozen design; R1 resolved Codex's first
`CHANGES_REQUIRED` review; R2 resolves Codex's second `CHANGES_REQUIRED` review (three consistency
findings) plus one additional measured defect found by the required consistency search, without
widening the whitelist. See "Revision R1" and "Revision R2" below for the defect-to-fix mappings;
each accepted fix is listed there with the exact documents and acceptance cases it changed.

Codex independent final verdict: **PASS**. Codex independently inspected the branch, HEAD,
working-tree diff, source interfaces, R2 corrections, acceptance-case index/body set, tests,
worktrees, stash, protected database hash and live GitHub state. Codex also reran both required
pytest groups outside the Harness ACL sandbox (`15 passed` and `255 passed`) plus ruff, so the
Harness-only three `tmp_path` setup errors do not block acceptance. Codex creates the single scoped
delivery commit after this document's final validation; its hash is reported in the external handoff.

Harness status before reviewer resolution: **BLOCKED** — the design-and-documentation content required by
`agent/goals/2026-09-11_m4_bounded_execution_and_evidence_design.md` is complete and validated in
the working tree, but the delivery commit cannot be created: this sandbox denies every write outside
the session workspace, and the R1 and R2 revision instructions explicitly forbid `git add`/`git
commit` because the parent repository is written by Codex (see "Blocking condition"). This is **not**
a self-acceptance: the contract and the revision instructions all make Codex's independent verdict
authoritative. The delivery contains no executor implementation, no statistical execution and no
authorization of any kind.

Verdict scope: content acceptance criteria (whitelist, frozen design, acceptance coverage, README
accuracy, targeted tests, protected state) are met as evidenced below; the **commit requirement is
unmet by design of the R1/R2 instructions**, and that single unmet requirement is the whole reason
for the `BLOCKED` verdict. One command sequence, quoted verbatim below, resolves it under Codex's
authority.

- Task contract (Codex-owned, already committed at the baseline):
  [Goal](../agent/goals/2026-09-11_m4_bounded_execution_and_evidence_design.md).
- Normative design: [specification](../docs/m4_bounded_execution_and_evidence_design_v1.md).
- Acceptance cases: [bounded execution scenarios](../docs/m4_bounded_execution_acceptance_cases_v1.md).
- Work record: [work log](../agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md).

## Scope and baseline

Deliver exactly whitelist paths 2-8 and nothing else. Verified base branch
`codex/m4-bounded-execution-design` at HEAD `82278f21c9fbe969a549cd7a07381794f3c5d4e7` (the Goal
contract commit), matching the required baseline with a clean worktree at task start. `main` and
`origin/main` are `f34adcb17c9995392690a1df6bb5a10ee102eb09`; live `main` re-read through the
GitHub API returns the same SHA, and there are no open PRs. PR #9, #11 and #12 are merged, which
is exactly what made the README capability and roadmap statements stale.

The delivery commit is created **after** this validation (the contract requires one scoped local
commit containing only paths 2-8). It could not be created in this sandbox: see "Blocking
condition" below. The validated content revision is therefore the baseline `82278f2…` plus the
seven whitelist paths as **working-tree** changes, with no other change anywhere in the repository.

## Revision R1 (answer to Codex `CHANGES_REQUIRED`)

Three findings, all in the whitelisted documents only. No `src/**`, statistics, database, provider,
holdout, commit or push was touched; no test was weakened.

| # | Finding | What R1 changes |
| --- | --- | --- |
| 1 | Doc 6.2 said float64 never enters identity, while 8.3/10.x put `float64_hex` and statistics into `artifact_digest` | Design 6.2 rewritten as an explicit **two-layer** identity: the upstream source-chain identity binds only canonical decimals/digests and float64 never enters it; the execution artifact identity **must** bind the normalized float64 outputs plus the numeric runtime. 6.1, 1.1(8), 8.3 and 10.4 aligned; AC-18 added. *(R2 note: the second layer is now split by artifact kind — the primary artifact binds the float64 outputs, the dispatch-only artifact binds no float statistic; see R2.1 below.)* |
| 2 | Doc 7.1 allowed plan `enabled=true` with actual `bootstrap.enabled=false`/`None`, creating an unauthorized runtime downgrade | 7.1/7.2/7.7/8.1/10.1 rewritten: the artifact's `enabled` is a **strict copy** of `plan.bootstrap_plan.enabled`; `enabled=true` must execute or the whole execution fails closed; only a plan declaring `enabled=false`/`DISABLED` takes the disabled path; `None` is no longer a legal value; AC-19 added |
| 3 | Doc 12.2 invented a closed `{"trim"}` parameter schema and made the current, valid registered entry (`{trim, window}`, arbitrary canonical JSON) fail | Section 12 rewritten as **true registered dispatch-only**: validate request IDs/order/method registration and forward the registered canonical parameters completely and immutably (including unknown nested keys), with no ignoring/rewriting/default filling, no auto-execution/expansion/selection, and no invented statistics. The entry is renamed `prepare_registered_robustness_dispatch`; schema, public API, states (`statistics_computed`/`outcome_read` = `False`), error codes (`UNSUPPORTED_ROBUSTNESS_PARAMETERS` and `INVALID_ROBUSTNESS_PARAMETER` removed), AC-12, records, acceptance and risks updated |

Design sections touched by R1: 1.1, 2.3 (clarification only), 4.1, 6.1, 6.2, 7.1, 7.2, 7.7, 8.1,
8.3, 9.1, 9.2, 10.1, 10.2, 10.4, 11.2, 11.3, 11.4, 12 (rewritten), 16. Cases sections touched: 0.2,
0.4, 1 (index), 2 (AC-01), AC-05, AC-12 (rewritten), AC-16 (nested mutation 16d added), new AC-18
and AC-19, and the section 7 implementation-ordering requirement. The two tests and the README are
unchanged by R1 (their R0 synchronization is unaffected by these design corrections).

R2 sections touched: design 1.1(8), 6.2, 8.3, 10.2, 10.4, 14.2 and 16; cases index (AC-09 removed,
AC-12 title synchronized), the numbering/mapping note, AC-08 and AC-18 (subcases 18f/18g) plus the
section 7 ordering lists; this document's revision header, frozen-decision items 3 and 8, coverage
rows, residual risks, blocking-condition wording and the R2 subsection. The two tests and the README
are unchanged by R1 and R2.

## Frozen design decisions (the ten required behavior areas)

1. **Source-bound entry, no matrix-only trust path.** The only public **statistical execution**
   entry is `execute_bounded_analysis(matrix, preparation, contract, plan, bound_inputs)`. The
   robustness entry is `prepare_registered_robustness_dispatch(matrix, preparation, contract, plan,
   bound_inputs, robustness_ids)` — deliberately *not* named "execute", because in this stage it
   runs no statistic at all. Both must call the existing five-argument `validate_design_matrix`
   first (structure + self digest -> four-argument `validate_dataset` byte comparison ->
   re-projection -> `serialize_matrix` byte comparison). No `**kwargs`, so an undeclared
   holdout/real-data/selection argument is a `TypeError` rather than a silently ignored parameter.
2. **Mechanical mapping from the plan.** Estimator columns are `matrix.rows[*].cells` by index and
   are named only by `plan.design_plan.ordered_terms[*].{position, term_role, coefficient_role}`;
   the response vector comes from `preparation.complete_rows` at
   `role_order.index(response_role)` with an enforced row-by-row alignment check. M3 column names
   (`DESIGN_COLUMNS`, `ANALYSIS_COLUMNS`, `market_ex_target_return`, `oil_return`,
   `industry_return`, `Crash_t`, `gamma`), fixed development dates and keying by
   `source_series_role` are forbidden; the primary effect is located by the unique
   `CONDITION_INDICATOR` term, never by parsing the evidence binding text.
3. **Canonical-decimal conversion and two-layer identity.** `Decimal(text)` -> exact range gate
   `abs(value) <= "1000000"` (inclusive) -> `float()` -> `math.isfinite`. Identity is explicitly
   **two layers** and the design no longer contradicts itself:
   - the **upstream source-chain identity** (`contract_digest`, `plan_digest`, `input_digest`,
     `domain_digest`, `dataset_digest`, `matrix_digest`) binds only canonical decimal strings,
     canonical ISO dates and digests — float64 never enters it and is never written back upstream;
   - the **primary artifact identity** (`ExecutionArtifactV1.artifact_digest`) **must** bind every
     float64 output of the estimator, bootstrap, conditional descriptives and evidence blocks
     through the normalized `Float64ValueV1{float64_hex, canonical_decimal}` rendering, plus
     `numeric_runtime`, code and schema versions and the full source chain; otherwise "change a
     coefficient without changing the digest" would pass validation;
   - the **robustness dispatch artifact identity** (`RobustnessArtifactV1.artifact_digest`) binds a
     *different* set, because that artifact computes nothing: the full source chain, the request
     order and the registry order, `method_id`, the **complete canonical parameters** (unknown
     nested keys included), `provenance`, code/schema versions and `numeric_runtime`. It has no
     `estimator` / `bootstrap` / `conditional_descriptives` / `evidence` block and
     `statistics_computed = False`, so it has **no float64 statistic output at all** — claiming
     that it binds float blocks would misreport "bound" as "computed". The frozen parameters must
     first be projected to their plain-JSON form (the existing `_thaw` semantics, equivalently
     `json.loads(parameters_canonical_json)`) before entering the digest payload, because
     `FrozenJSONObject` is not JSON-serializable and `canonical_digest` would raise `TypeError`
     (design 10.2, measured read-only in R2).

   The two layers are connected one-way (float64 is derived from the source-chain decimals by a
   single deterministic conversion), so the artifact stays recomputable. No
   epsilon/`isclose`/`allclose` anywhere; `-0.0` compares like `0.0` but differs in `float64_hex`,
   so the *disposition* is the same while the *artifact identity* differs. Outputs are
   `{float64_hex, canonical_decimal}` with a self-consistency check that verifies both come from the
   same float64 value (it does **not** require the two strings to be equal), and the frozen 16-step
   fail-closed order plus a closed error-code table make the first error reproducible.
4. **Allow-listed OLS contract.** Only `DAILY_CONDITIONAL_CONTROLLED_OLS_V1` with
   `model_family == "OLS"`, `numpy.linalg.lstsq` with an explicit `matrix_rank(X) == k` gate before
   solving and a second rank check after; unsupported method/model/RNG fail rather than downgrade.
   No `statsmodels`, no M3 modules, no column dropping, no minimum-norm fallback.
5. **Bootstrap contract.** `MOVING_BLOCK_BOOTSTRAP_V1` + `PCG64` + plan-declared seed and
   replications; block length frozen as the exact integer rule for
   `N_CUBERT_ROUNDED_CLAMP_1_20_V1` (measured to agree with the M3-era float expression for
   `n = 1..200000`, 0 mismatches); non-circular overlapping blocks over complete rows with a frozen
   draw order; endpoints are exact order statistics (`k_lo = floor(B*alpha)`,
   `k_hi = ceil(B*(1-alpha)) - 1`) with no library quantile default; rank-deficient resamples fail
   closed (`SINGULAR_RESAMPLE`) instead of being skipped. **Declaration and execution cannot
   fork**: the artifact's `bootstrap.enabled` is a strict copy of `plan.bootstrap_plan.enabled`,
   never re-derived. `enabled=True` means bootstrap must run or the **whole execution** fails
   closed — there is no path that emits a `enabled=false` artifact with `null` endpoints as a
   fallback; only a plan declaring `enabled=False` / `method_id="DISABLED"` takes the disabled
   path (`null` endpoints, no RNG, `INCONCLUSIVE`/`BOOTSTRAP_DISABLED`). When `enabled=True` every
   method-related field must be non-`None`; when `False`, all must be `None`.
6. **Registered robustness dispatch only — binding, not computing.** `robustness_ids` is an explicit
   ordered tuple; empty, duplicate and unregistered requests fail
   (`EMPTY_ROBUSTNESS_DISPATCH` / `DUPLICATE_ROBUSTNESS_ID` / `UNREGISTERED_ROBUSTNESS_ID`). The
   entry validates request order and registry membership and then **forwards the registered
   canonical parameters completely and immutably** — every key, nested object and array element,
   including keys this design never mentions (`window`), with no ignoring, rewriting, default
   filling or re-normalization. Parameters are bound by `artifact_digest`, so silently dropping or
   altering one is detectable. This stage defines **no robustness method allow-list and no
   parameter schema**, because the project has no existing robustness handler contract
   (`mechanism/robustness.py` is M3-bound and forbidden); inventing `trim`/`window` semantics would
   be inventing statistics. The artifact therefore has no `evidence` block, no statistic field, no
   ranking/selection field, `automatic_expansion`/`automatic_selection`/`parameters_interpreted`
   all `False`, and `statistics_computed = False` **and** `outcome_read = False`; the primary entry
   has no robustness parameter, so "pick the best robustness result" is not expressible.
7. **Complete disposition table.** A closed five-word disposition vocabulary and five-word reason
   vocabulary, with frozen precedence D1-D10 covering POSITIVE, NEGATIVE and TWO_SIDED,
   `level < requirement` -> `INCONCLUSIVE`, and exact strict comparisons at zero. D2 is keyed on the
   plan-declared `bootstrap_plan.enabled is False`, not on a runtime value. The declared
   `data_quality_failure_disposition` surfaces only on the `DATA_QUALITY_REJECTED` refusal (as
   `.disposition`), never as an artifact disposition word.
8. **Immutable artifacts with full-chain identity.** Frozen dataclasses with tuple containers; two
   separate artifact schemas; canonical JSON (sorted keys, compact, UTF-8, exactly one trailing
   newline) identical in form to the existing serializers; the **primary** artifact's
   `artifact_digest` covers the six-link source chain, provenance, the full method configuration
   (including method IDs, block-length policy, code/schema versions and the numeric runtime),
   sample facts, all estimator outputs, bootstrap facts, conditional descriptives and the evidence
   block — i.e. it binds the **float64 outputs** as normalized text, while the upstream chain keeps
   binding only canonical decimals. The **robustness dispatch** artifact's digest covers the source
   chain, provenance, method configuration (including `numeric_runtime`), sample facts, `dispatch`
   (`requested_ids` in request order, `registered_ids` in registry order, and the three
   strictly-`False` flags) and `entries[*]` (`robustness_id`, `request_ordinal`,
   `registration_ordinal`, `method_id`, the verbatim canonical `parameters`,
   `parameters_canonical_json`) — and no float statistic, because that schema has no statistic block.
   `provenance.synthetic_test_only` is explicit; serialization mechanically rejects
   host/path/session keys, absolute-path values and selection/aggregation key names.
9. **Authorization and transitions.** `execution_authorized` (real-research authorization) is
   `False` in every object this design can produce; `statistics_computed` is `True` **only** on the
   primary artifact and `False` on the robustness dispatch artifact (which computes nothing);
   `outcome_read` is `True` only on the synthetic primary artifact, scoped by
   `synthetic_test_only`. Synthetic execution authorization is a property of the source chain
   (`mode == "SYNTHETIC"`), not a flippable flag. No transition to real research or holdout exists;
   holdout is unreachable by signature, by plan-level `HOLDOUT_EXECUTION_NOT_AUTHORIZED`, and by a
   defense-in-depth row-window gate.
10. **Synthetic readiness is separated from real research authorization.** A frozen
    `interpretation_boundary` literal is part of every artifact and of the digest, so no artifact
    can be read as a research finding, an estimability/significance/economic-validity/tradability
    claim, an A-share mechanism result, or an authorization for real data, holdout or M4-B.

## Acceptance-case coverage (all 15 required classes present, plus 2 added by revision)

| Required class | Case |
| --- | --- |
| Base success | AC-01 (full-rank synthetic fixture; structure + invariance only) |
| Source tamper / re-hash | AC-03 |
| Matrix tamper / re-hash | AC-04 |
| Wrong validation order | AC-05 |
| Unsupported method | AC-06 |
| Non-finite / conversion failure | AC-07 |
| Singular / rank-deficient disposition | AC-02 (base fixture, `rank <= 3 < 5`) |
| Bootstrap disabled / enabled | AC-08 (enabled, exact endpoints) + AC-19 (strict plan copy: 19a enabled executes, 19b disabled path, 19c plan-level pairing, 19d no downgrade fallback); the orphan R0 index row AC-09 was removed in R2 |
| Exact endpoints | AC-08 (seven `level`/`B` combinations with measured indices) |
| All evidence directions | AC-10 (POSITIVE, NEGATIVE, TWO_SIDED + zero-endpoint and confidence cases) |
| Quality rejection | AC-11 |
| Unregistered robustness / dispatch-only registered dispatch | AC-12 — *registered robustness dispatch: request, order and complete forwarding* (request order, registry binding, complete verbatim forwarding, nested `window` retained, unregistered request refused) |
| Holdout refusal | AC-13 |
| Input/key-order and CWD invariance | AC-14 |
| Artifact byte reproducibility | AC-15 |
| Nested mutation | AC-16 |
| Explicit synthetic-only provenance | AC-17 |
| Two-layer identity (upstream decimal vs per-artifact-kind binding) | AC-18 (18a–18e primary-artifact float64 binding, 18f robustness artifact has no statistic block, 18g robustness digest binds source chain, request/registration order, `method_id`, complete canonical parameters, provenance and runtime) |
| Bootstrap `enabled` strict plan copy (no runtime downgrade) | AC-19 |

Every case states its input change, expected output or error, validation stage (design section 11
numbering) and authorization interpretation. Because the contract forbids computing coefficients,
intervals, p-values or other outcomes even from synthetic data, the cases deliberately contain **no
numeric expectations for estimator outputs**; AC-01 and AC-15 assert structure, self-consistency and
byte-level reproducibility instead. That limitation is stated in the cases document (section 7).

## Actual validation (every command with its real exit code; re-run in full for R1)

Run from `D:/量化分析-m4-executor-design` with
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')` and interpreter
`D:/量化分析-m4a2i/.venv/Scripts/python.exe`. Every command below was executed again on the R1
working tree; the results are the R1 measurements, not the R0 ones.

| # | Command | Exit | Real result |
| --- | --- | --- | --- |
| 1 | `python -m pytest -q tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `15 passed, 1 warning` (the warning is the environment `pytest_cache` `WinError 5` note) |
| 2 | `python -m pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | **1** | `252 passed, 2 warnings, 3 errors` — identical to the pre-revision baseline; the 3 errors are pre-existing setup-stage environment denials (section "Pre-existing environmental failure") |
| 3 | `python -m ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `All checks passed!` |
| 4 | `git diff --check` | **0** | clean (no whitespace errors) |
| 5 | `git diff --cached --check` | **0** | clean; the index is empty (nothing was staged in R0 or R1 — see "Blocking condition") |
| 6 | `git status --short --branch` | **0** | exactly the seven whitelist paths (` M` ×3, `??` ×4) plus `## codex/m4-bounded-execution-design` |
| 7 | `git rev-parse HEAD origin/main refs/stash` | **0** | `82278f21c9fbe969a549cd7a07381794f3c5d4e7` / `f34adcb17c9995392690a1df6bb5a10ee102eb09` / `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` |
| 8 | `git worktree list --porcelain` | **0** | 14 worktree entries, all preserved |
| 9 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 10 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | **0** | `f34adcb17c9995392690a1df6bb5a10ee102eb09` (live) |
| 11 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | **0** | `[]` (live) |
| 12 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only; contents never opened) |
| 13 | Read-only Markdown audit over the five changed/added Markdown files (UTF-8 decode, BOM, CR, TAB, trailing whitespace, final newline, conflict markers, fence balance) | **0** | all five `issues=NONE` (fences 30 / 96 / 30 / 28 / 16) |
| 14 | Repository-relative Markdown link resolution over the same five files | **0** | all links resolve (README 23 links, design 4, cases 3, record 0, acceptance resolved) |
| 15 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222` = protected value |

Intermediate measurement kept for honesty: the first execution of command 1 (before the acceptance
document existed) was `1 failed, 14 passed`, exit **1**, failing
`test_entry_and_history_evidence_links_resolve` on the then-missing README link to this file. The
file was created and the command re-run to the passing result above. No assertion was weakened,
skipped or deleted to obtain it; `tests/test_project_entry.py` keeps every protective assertion
(`没有通用研究执行器`, `holdout 始终不授权执行`, the entrypoint/CLI assertions and the link
resolution test), and `tests/test_m4_stage4p_governance.py` keeps every aggregate, north-star and
production-surface gate.

### Pre-existing environmental failure (verbatim, not hidden)

Command 2 exits 1 because three `tmp_path` cases fail during pytest **setup**, before any test body
runs. This reproduces identically on the untouched baseline of this worktree (measured before any
edit in the R0 session: `252 passed, 2 warnings, 3 errors`, exit 1) and again identically on the R1
working tree, so it is not caused by this delivery:

```text
ERROR tests/test_m4_synthetic_dataset_adapter.py::test_cwd_and_from_dict_order_invariance
ERROR tests/test_m4_stage4a2i_analysis_plan.py::test_semantic_ab_equivalence_and_cwd_independence
ERROR tests/test_m4_stage4a1_typed_contract.py::test_yaml_loader_requires_mapping_and_rejects_object_tags

PermissionError: [WinError 5] access denied:
  C:\Users\111\AppData\Local\Temp\dsh-7tP7WA\pytest-of-dlam12138     (R1 measurement; R0 saw dsh-LXAvdH)
at _pytest/pathlib.py find_prefixed -> os.scandir(root)
```

Only the per-session sandbox temp directory name differs between runs; the failing node IDs, the
`WinError 5` denial, the setup stage and the counts are identical. The same denial produces the
`PytestCacheWarning`s for `.pytest_cache\v\cache\{nodeids,lastfailed}` and the unreadable
`pytest-cache-files-*` directory visible in `git status` stderr. `252 passed` is reported as
measured; the command is **not** claimed as green. Independent reproduction or attribution by Codex
is expected, per the contract.

## What the README and the two tests changed (and what did not)

```text
README.md
  - intro paragraph: PR #9/#11/#12 merged; design/compile/matrix preparation still do not mean
    statistical execution; bounded execution has a design only
  - capability table: M4-A.2 status corrected to "已在主线（冻结设计 + A.2I 计划编译实现）";
    new rows M4-A.2D 合成数据适配器 (PR #11), M4-A.2M 设计矩阵 (PR #12) and
    M4-A.2E 有界执行 (DESIGN ONLY；执行器尚未实现)
  - current-authorization bullet: A.2I + adapter + matrix merged; bounded execution has a frozen
    design only; executors, M4-B and real hypothesis execution remain separately unauthorized
  - A.2I section: the stale closing sentence "数据适配、执行尚未实现" replaced with the accurate
    statement plus links to the two new design documents
  - roadmap Milestone 4: A.2I COMPILE-ONLY IMPLEMENTED; A.2D SYNTHETIC DATASET ADAPTER
    IMPLEMENTED; A.2M ANALYSIS MATRIX IMPLEMENTED; A.2E BOUNDED EXECUTION DESIGN DELIVERED,
    DESIGN ONLY; bounded executor NOT STARTED; M4-B NOT STARTED; real hypothesis execution
    NOT AUTHORIZED

tests/test_project_entry.py
  - capability list extended with M4-A.2D / M4-A.2M / M4-A.2E (all rows present in the README)
  - stale "数据适配、执行尚未实现" replaced by "有界执行器尚未实现", plus "统计执行尚未实现" and
    "holdout 始终不授权执行"
  - every other protective assertion unchanged

tests/test_m4_stage4p_governance.py
  - exactly one stale assertion replaced: "dataset adapter / executor NOT STARTED" is now
    "bounded executor NOT STARTED", with positive assertions for A.2D/A.2M/A.2E and a negative
    assertion that the old stale string is gone
  - aggregate, north-star and production-surface gates untouched
```

`src/**`, dependencies, workflows, configuration, frozen reports, north-star documents, existing
M4 design/acceptance documents and every other test have **no diff**.

## Remote synchronization

- Local `origin/main` tracking ref and live GitHub `main` both read
  `f34adcb17c9995392690a1df6bb5a10ee102eb09`, so the Goal-declared base is confirmed against the
  live remote in this session.
- `gh pr list --state open` returned `[]`: no open PR.
- This branch was **not** pushed and has no remote counterpart; no PR was opened, nothing was
  merged, and no force-push or destructive git command was used.

## Protected state

```text
branch / HEAD      codex/m4-bounded-execution-design @ 82278f21c9fbe969a549cd7a07381794f3c5d4e7
                   (HEAD unchanged: the delivery commit was denied — see "Blocking condition")
index              empty; `git diff --cached --check` exits 0 with no staged path, and the denied
                   `git add` could not create `index.lock`, so the index was never modified
changed tracked    README.md, tests/test_project_entry.py, tests/test_m4_stage4p_governance.py
added untracked    docs/m4_bounded_execution_and_evidence_design_v1.md
                   docs/m4_bounded_execution_acceptance_cases_v1.md
                   agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md
                   acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md
src/**             no diff
original M2 HEAD   3679b1bac7a1634c6452784a4d8f6d139966f222 = protected
stash              cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f = protected (not applied, not dropped)
DB SHA256          4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 = protected
worktrees          14, all preserved, none switched or cleaned
temporary files    none written this session (all probes used standard input)
pytest cache dirs  13 `pytest-cache-files-*` directories in the worktree root (1 pre-existing,
                   12 created by this session's pytest runs); unreadable under this sandbox's
                   WinError 5 denial, therefore invisible to `git status` and to the index, not
                   gitignored, containing no task content; left in place, and the delivery commit
                   uses explicit paths rather than `git add -A`
ignored preserved  `.ruff_cache/` and `__pycache__/` run artifacts, left as-is
```

No database connection was opened; only a file SHA256 was computed. No provider, real market data,
holdout or statistical code was touched, and no coefficient, interval, p-value or rank was computed.

## Exact deliverables

```text
docs/m4_bounded_execution_and_evidence_design_v1.md                        new
docs/m4_bounded_execution_acceptance_cases_v1.md                           new
agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md      new
acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md          new (this document)
README.md                                                                  synced (capability + roadmap + authorization)
tests/test_project_entry.py                                                synced (capability assertions)
tests/test_m4_stage4p_governance.py                                        synced (one README-status assertion)
```

Plus the pre-existing, unmodified Goal contract
`agent/goals/2026-09-11_m4_bounded_execution_and_evidence_design.md`, which was committed by Codex
at the baseline and is not part of the delivery commit.

## Deviations, blockers and residual risks

- **No deviation** from the whitelist: no path outside items 2-8 was added, changed or deleted.
- **One blocker**: the contract-mandated local delivery commit could not be created, because the
  sandbox denies every write outside `D:/量化分析-m4-executor-design` (including
  `D:/量化分析/.git`) and the sanctioned escalation was refused for lack of an approval channel.
  No workaround was attempted. This is the sole reason for the `BLOCKED` verdict; the exact
  resolving command is quoted in "Blocking condition".
- **No Goal stop condition was triggered**: the baseline did not move during execution, no upstream
  schema change was needed, no new dependency/workflow/test outside the whitelist was required, no
  statistical or outcome computation was needed, and no database/provider/real-data/holdout/
  protected-artifact/M4-B access was needed.
- **Residual risk 1 (revision R1)** — the previous revision let the artifact record
  `bootstrap.enabled = false`/`None` while the plan declared `enabled = true`, which is an
  unauthorized runtime downgrade; and it let `artifact_digest` bind float64 outputs while doc
  section 6.2 claimed float64 never enters identity; and it invented a closed `{"trim"}` robustness
  parameter schema that made the *current, valid* registered entry fail. All three are fixed in
  this revision (design sections 6.2, 7.1, 7.2, 7.7, 8.1, 9.1, 10.2, 10.4, 11.2, 12, 16; cases
  AC-12, AC-16, AC-18, AC-19). The residual risk that remains is the *reverse* direction: this
  stage deliberately defines **no** robustness parameter semantics, so `trim` and `window` are
  forwarded but not interpreted. That is a scope statement, not a defect, and it must be resolved
  together with a real robustness handler contract in a separately authorized implementation Goal.
- **Residual risk 2 (revision R2)** — three consistency defects were corrected: the artifact-digest
  binding is now split by artifact kind (the dispatch artifact binds its source chain, request and
  registry order, `method_id`, complete canonical parameters, provenance and code/schema/runtime, and
  **no** float statistic, since it computes none); the orphan `AC-09` index row was deleted with all
  its references and the requirement is pinned to AC-08 + AC-19; and `canonical_decimal` is described
  as the shortest round-trip companion rendering with `float.hex` carrying the exact binary identity,
  instead of the incorrect fixed-17-digit wording. In addition, the required consistency search found
  and fixed a fourth *measured* defect inside the same whitelist (R2.4 above): the frozen
  `FrozenJSONObject` cannot be passed to `canonical_digest` (it raises `TypeError`), so the digest is
  now defined on its plain-JSON projection. That extra fix exceeds the literal R2 instruction and is
  deliberately flagged for Codex as reviewable scope rather than presented as requested work.
- **Residual risk 3** — byte reproducibility is claimed only for a fixed `numeric_runtime`
  (`numpy 2.5.3` here). Cross-version/BLAS drift is detectable in the artifact but not prevented.
- **Residual risk 4** — the acceptance cases contain no numeric expectations for estimator outputs
  because computing them is forbidden in this stage; the first real numbers must be produced under
  separate authorization and independently reviewed.
- **Residual risk 5** — the pre-existing three-case pytest setup failure is an environment
  limitation of this sandbox; it is reported verbatim and not hidden.
- **Residual risk 6 (R2 disclosure)** — the only content change outside the three review findings is
  the measured digest-extraction fix summarized in residual risk 2 and detailed in R2.4. Everything
  else in the R0/R1 delivery is unchanged.

## What is NOT claimed

- No executor implementation exists; no implementation test passed. All eight public entries are
  proposed API in a design document.
- No statistical validity, full rank, estimability, significance, economic validity or tradability
  is claimed or implied; no coefficient, interval, p-value or rank was computed.
- No real-data, provider, database, holdout or M4-B access; no push, PR, merge or next-stage start.
- Synthetic-source evidence is not real research evidence, and design completion is not
  implementation, statistical-execution, real-data, holdout, M4-B, push, PR or merge authorization.

## Blocking condition (the single unmet requirement)

The Goal's "Commit and push requirements" state: "DeepSeek Harness creates one scoped local
design-delivery commit containing only paths 2-8 after validation." The exact staging command was
executed after validation and was denied:

```text
$ git add -- README.md tests/test_project_entry.py tests/test_m4_stage4p_governance.py \
    docs/m4_bounded_execution_and_evidence_design_v1.md \
    docs/m4_bounded_execution_acceptance_cases_v1.md \
    agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md \
    acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md
fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4-executor-design/index.lock': Permission denied
[exit code: 128]
[stderr] warning: could not open directory 'pytest-cache-files-*': Permission denied   (13 dirs)
```

This worktree is linked to the repository at `D:/量化分析/.git`, outside this session's workspace
root `D:/量化分析-m4-executor-design`. Permission probes measured in this session:

```text
D:/量化分析/.dsh_write_probe                                           -> DENIED (UnauthorizedAccessException)
D:/量化分析/.git/worktrees/量化分析-m4-executor-design/.dsh_write_probe  -> DENIED (UnauthorizedAccessException)
D:/量化分析-m4-executor-design/.dsh_write_probe                         -> WRITABLE
index.lock after the failure                                            -> absent (nothing left behind)
```

The one-shot escalation of the identical command (the sanctioned retry after a real denial) was
refused: "sandbox escalation to \"danger-full-access\" requires approval, but no approval channel is
available". Per the runtime rules that refusal is final, so **no workaround was attempted** — no
alternate `GIT_INDEX_FILE`, no alternate git directory, no repository re-initialisation, no path
aliasing, no `git add -A`. The index is empty and HEAD is still the baseline commit.

Consequence: all seven whitelist paths exist as validated working-tree changes, and the contract's
commit requirement is unmet. In R1 and R2 this is also an **explicit instruction**, not only a
sandbox limitation: the revision tasks state that `git add`/`git commit` must not be attempted because
the parent repository is written by Codex, so no staging was attempted in R1 or R2 at all (the R0
denial is quoted above only to document why HEAD is still the baseline). The exact command that
resolves it, to be run under Codex's authority in a shell with write access to `D:/量化分析/.git`:

```powershell
cd D:/量化分析-m4-executor-design
git add -- README.md tests/test_project_entry.py tests/test_m4_stage4p_governance.py `
    docs/m4_bounded_execution_and_evidence_design_v1.md `
    docs/m4_bounded_execution_acceptance_cases_v1.md `
    agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md `
    acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md
git commit -m "docs: freeze M4 bounded execution and evidence design"
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash
```

After that, HEAD would be the single delivery commit and `git status --short --branch` would show
only the branch line (plus the pre-existing unreadable `pytest-cache-files-*` directories, which git
cannot scan). No push, PR or merge follows, and none is authorized.

## Stop conditions and next step

This delivery stops at design and at the blocked commit step. The next step is, in order: (1) Codex
independently verifies the real branch and HEAD, the working-tree diff of the seven whitelist paths,
all changed and untracked files, the test evidence above, all worktrees and the stash, the protected
baseline and database hash, the live GitHub state, and Goal compliance — comparing the design
documents against the real interfaces and recomputing the examples that do not require forbidden
computation, including the two fixture-dependent values below; (2) Codex runs the staging + commit
command in "Blocking condition" under its own repository write authority, then re-runs
`git diff --cached --check`, `git status --short --branch` and
`git rev-parse HEAD origin/main refs/stash` to confirm one scoped commit and an unchanged protected
baseline. The verdict must be exactly `PASS`, `CHANGES_REQUIRED` or `BLOCKED`.

### R1 fixture-dependent values, measured by read-only probe (not assumed)

One read-only probe built the plan from the existing test helpers and printed the frozen plan's
canonical values. It called no regression/bootstrap/robustness/evidence code and computed no
coefficient, interval, p-value, rank or disposition:

```text
entries_len        1
robustness_id      'SYNTH_ROBUSTNESS_1'
method_id          'CONDITIONAL_DESCRIPTIVES_V1'
parameters (thawed) {'trim': '0.0100', 'window': ['1', '2', '3']}
parameters_compact  {"trim":"0.0100","window":["1","2","3"]}
bootstrap_enabled  True
bootstrap_method   'MOVING_BLOCK_BOOTSTRAP_V1'
```

This is the measurement behind AC-12a (the unmodified fixture entry must dispatch successfully and
forward exactly `{"trim":"0.0100","window":["1","2","3"]}`) and behind AC-19a (the default fixture
declares `enabled=True` with a real bootstrap method, so the strict-copy rule governs the primary
baseline path). Note also that the A.1 source document declares `window: [1, 2, 3]` as integers
while the *plan* canonicalizes them to decimal strings — the executor forwards the frozen plan value
and must not normalize it a second time (design section 12.2).

Bounded-executor implementation, push, PR, merge and any M4-B or statistical execution stage each
require separate explicit user authorization.

## Revision R2 (answer to Codex's second `CHANGES_REQUIRED`)

Three consistency findings, all corrected in whitelisted documents only. No `src/**`, statistics,
database, provider, holdout, delegation, `git add`, `git commit` or push was touched, and no test was
weakened. R2 also fixed one additional *measured* defect found by the required full-text consistency
search (18.4 below); it is reported explicitly rather than slipped in.

### R2.1 Artifact identity binding is split by artifact kind (finding 1)

R1 described a single artifact identity that bound "the float64 outputs of the estimator, bootstrap,
conditional descriptives and evidence blocks". That statement is correct for the primary artifact and
**false** for the robustness dispatch artifact, whose schema contains none of those blocks and whose
`statistics_computed` is strictly `False`. R2 now separates them everywhere:

| Artifact | What its `artifact_digest` **must** bind | What it must **not** be claimed to bind |
| --- | --- | --- |
| `ExecutionArtifactV1` (primary, `statistics_computed = True`) | complete source chain, `provenance`, full `method_configuration` (incl. `numeric_runtime`, code/schema versions), `sample`, **all float64 statistic output** of `estimator` / `bootstrap` / `conditional_descriptives` / `evidence` via `Float64ValueV1`, and the three status bits | host / cwd / absolute path / session / environment identity |
| `RobustnessArtifactV1` (dispatch-only, `statistics_computed = False`) | complete source chain, request order and registry order (`dispatch.requested_ids` / `dispatch.registered_ids`), `method_id`, **complete canonical parameters** (unknown nested keys included), `provenance`, `artifact_schema_version`, `executor_version`, `numeric_runtime`, the three strictly-`False` dispatch flags and the three status bits | host/path/session identity, and **any float64 statistic output — it computes none and has no statistic block, so none exists to bind** |

Updated: design 1.1(8), 6.2 (layer-2 rows (a)/(b) plus the boundary table), 8.3 (scoped to the
primary artifact), 10.4 (two explicit digest-coverage lists), 16 (two new risk rows); cases AC-18
(new subcases 18f/18g, rewritten key assertions and authorization interpretation); this document's
frozen-decision items 3 and 8, the two-layer-identity coverage row and the residual-risk paragraph.

### R2.2 Orphan `AC-09` removed and the `AC-12` index title synchronized (finding 2)

The cases index (and this document) referenced `AC-09 bootstrap 禁用路径`, but the cases document had
**no** `### AC-09` section. Because AC-19 already covers the enabled path, the disabled path and the
no-downgrade requirement, R2 deletes the `AC-09` row and all references instead of duplicating it,
and pins the contract's disabled/enabled coverage to concrete cases:

```text
bootstrap 禁用路径   -> AC-19b   (enabled=false / DISABLED: null endpoints, no RNG, D2 INCONCLUSIVE)
bootstrap 启用路径   -> AC-08    (enabled execution, exact endpoint indices and interval_alpha)
                        AC-19a   (artifact enabled is the strict plan copy, endpoints non-None)
无运行时降级         -> AC-19c   (plan-level INVALID_BOOTSTRAP_POLICY propagated unchanged)
                        AC-19d   (induced failure fails the whole execution closed)
```

AC-08 gained assertion 5 (it covers the enabled branch only and points to AC-19b), the
implementation-ordering lists were updated, and the index title for `AC-12` was synchronized with its
body heading to *注册稳健性派遣：请求、顺序与完整转发* (the old title named a parameter schema this
design deliberately does not define). No case was renumbered, no empty number remains, and the
index/body cross-check is machine-verified in R2.5.

### R2.3 `canonical_decimal` wording corrected (finding 3)

The design had called `canonical_decimal` a rendering in which "decimal digits beyond `repr`'s 17
significant digits are discarded". R2 replaces that with the measured semantics: it is the
**shortest round-trip decimal companion** (the digit count varies by value; `1.0/3.0` renders 16
digits, `123456789.12345679` renders 17), and the **exact binary identity is carried by `float.hex`**.
Both renderings enter the primary artifact's identity in parallel. Corrected in design 6.2 (with the
measurement table and a new section-16 risk row) and in cases AC-18 assertion 3.

### R2.4 Additional measured defect fixed inside the same whitelist (18.1-adjacent)

The required full-text search found that design 10.2/10.4 justified the robustness artifact's digest
binding with "`canonical_digest` recursively serializes the `FrozenJSONObject`". That is impossible:
`canonical_digest` is `json.dumps(...)`, and the frozen JSON types are dataclasses, so the call raises
`TypeError` instead of producing a digest (R2 probe B, below). R2 therefore fixes the digest
extraction path: the frozen form is projected to plain JSON first (existing `_thaw` semantics,
equivalently `json.loads(parameters_canonical_json)`) and only that projection enters the digest
payload, while the frozen form remains the verbatim immutable storage. Design 10.2, 10.4, 14.2 and 16
were aligned. This is a deviation from the literal R2 instruction and is flagged for review as such.

### R2.5 R2 command evidence (each command re-run in this session)

| # | Command | Exit | Real result |
| --- | --- | --- | --- |
| 1 | `pytest -q tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `15 passed, 1 warning` |
| 2 | `pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | **1** | `252 passed, 2 warnings, 3 errors` — byte-identical to the R0/R1 baseline; same pre-existing setup-stage `WinError 5` denials |
| 3 | `ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `All checks passed!` |
| 4 | `git diff --check` / `git diff --cached --check` | **0** | both clean; index empty (R2 forbids staging) |
| 5 | `git status --short --branch` | **0** | exactly the seven whitelist paths (` M` ×3, `??` ×4) |
| 6 | `git rev-parse HEAD origin/main refs/stash` | **0** | `82278f2…` / `f34adcb…` / `cb568ef…` (unchanged) |
| 7 | `git worktree list --porcelain` (counted) | **0** | 14 worktrees, all preserved |
| 8 | `gh api …/branches/main --jq '.commit.sha'`, `gh pr list --state open` | **0** | `f34adcb17c9995392690a1df6bb5a10ee102eb09`; open PRs `[]` |
| 9 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7…E2FCE6` = protected value (hash only) |
| 10 | `git diff --stat -- src`, `git -C D:/量化分析 rev-parse HEAD` | **0** | no `src/**` diff; protected M2 HEAD `3679b1ba…` |
| 11 | Markdown audit over the five changed/added Markdown files | **0** | all five `issues=NONE` (fences 30 / 102 / 30 / 28 / 16) |
| 12 | Repository-relative link resolution over the same five files | **0** | 32 links, 0 missing |
| 13 | AC index/body cross-check in the cases document | **0** | index set == body set == `AC-01…AC-08, AC-10…AC-19`; no orphan index, no orphan body |
| 14 | R2 read-only probe A — `canonical_decimal(repr(v))` over 9 float values | **0** | no fixed 17-digit rule; `0.0`/`-0.0` share `"0"` with different `float.hex`; `inf` raises `HypothesisConfigError` |
| 15 | R2 read-only probe B — `canonical_digest` on the frozen form vs its plain-JSON projection | **1** (expected `TypeError` on the frozen form) | projection digest `b8a23abe…`; nested `window` mutation `0b4f38cf…`; deterministic; projection equals `json.loads('{"trim":"0.0100","window":["1","2","3"]}')` |

Neither probe wrote a file, opened the database, called a provider, or computed a coefficient,
interval, p-value, rank or disposition.

### R2.6 R2 result

The three review findings and the additional measured defect are resolved. The Harness could not
create the local delivery commit, but Codex independently reproduced the successful checks outside
the Harness ACL sandbox and accepted the content. Codex resolves the remaining mechanical commit
step after this final document validation. No implementation, push, PR, merge, M4-B work or
statistical execution is authorized by this PASS.
