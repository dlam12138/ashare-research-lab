# Work record: M4 bounded execution and evidence design

Date: 2026-09-11. Executor: DeepSeek Harness (`deepseek-flash`). Reviewer: Codex.
Task contract: `agent/goals/2026-09-11_m4_bounded_execution_and_evidence_design.md` (Codex-owned,
committed at `82278f21c9fbe969a549cd7a07381794f3c5d4e7` before this execution).
Status: **completed; Codex verdict PASS** — the Harness completed and validated the design content
but could not write the linked worktree's parent Git metadata (section 12). Codex independently
reviewed the real diff, reran the required checks outside the Harness ACL sandbox, accepted the R2
corrections and creates the single scoped delivery commit after final document validation. No
implementation was performed.

Revision: **R2** (current; Codex's second review returned `CHANGES_REQUIRED` on R1 and raised three
consistency findings, all corrected here — see sections 18-21). R2 changes whitelisted documents
only; no `src/**`, statistics, database, provider, holdout, commit or push was touched.

Prior revisions, kept verbatim for audit below: **R1** resolved the three findings of Codex's first
review (two-layer identity, bootstrap `enabled` strictness, true registered robustness dispatch);
the **R0** sections remain as originally delivered so the revision history stays auditable.

R2 supersession note for readers of the R0/R1 sections below: wherever R0/R1 text still says the
robustness dispatch artifact's `artifact_digest` binds "float64 outputs" / the four statistic blocks,
the case list still contains `AC-09`, or `canonical_decimal` is called a "fixed 17 significant
digit" rendering, **R2 (sections 18-21) is authoritative**: the dispatch artifact binds no float
statistics at all, `AC-09` is deleted with all its references, and `canonical_decimal` is the
shortest round-trip companion rendering whose exact binary identity is carried by `float.hex`.

## 1. Objective, scope and non-goals

Objective: freeze an implementable, synthetic-only design for the remaining M4-A pipeline boundary
`Bounded Execution -> Reproducible Artifacts -> Evidence Disposition`, plus acceptance cases,
work record, acceptance document, a README correction for PR #9/#11/#12 staleness, and two
whitelist-limited test-assertion synchronizations.

Whitelist (Goal sections "Allowed scope" 2-8):

```text
2 docs/m4_bounded_execution_and_evidence_design_v1.md
3 docs/m4_bounded_execution_acceptance_cases_v1.md
4 agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md
5 acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md
6 README.md (current-capability and roadmap statements only)
7 tests/test_project_entry.py (current-capability text sync only)
8 tests/test_m4_stage4p_governance.py (canonical README-status assertion sync only)
```

Non-goals, explicitly honored: no `src/**` change, no dependency/workflow/configuration change,
no other test change, no call to `regression.py` / `bootstrap.py` / `robustness.py` / `evidence.py`,
no coefficient/interval/p-value/rank computation (not even on synthetic data), no database content
read, no provider, no real market input, no holdout, no M4-B, no delegation, no push/PR/merge,
no implementation.

## 2. Start state (verified, not inherited from a report)

```text
worktree            D:/量化分析-m4-executor-design
branch              codex/m4-bounded-execution-design
HEAD                82278f21c9fbe969a549cd7a07381794f3c5d4e7  = required baseline
git status          clean (0 porcelain lines); only a stderr warning about an unreadable
                    pytest-cache-files-x67a99h4/ directory left by an earlier session
origin/main         f34adcb17c9995392690a1df6bb5a10ee102eb09  = Goal-declared base
gh live main        f34adcb17c9995392690a1df6bb5a10ee102eb09  (GitHub API, task start)
gh open PRs         [] (none)
stash               cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f (pre-existing, preserved)
git worktree list   14 worktrees, all preserved, none switched or cleaned
protected M2 HEAD   3679b1bac7a1634c6452784a4d8f6d139966f222 (D:/量化分析, unchanged)
DB SHA256           4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6
                    (hash only; database contents never opened)
```

## 3. Files actually read (source of the frozen facts)

Read in full or in the relevant parts, directly from this worktree:

```text
D:/量化分析/AGENTS.md
agent/goals/2026-09-11_m4_bounded_execution_and_evidence_design.md
agent/record/README.md
README.md
src/ashare_research/mechanism/planning/matrix.py                (validate_design_matrix, invariants)
src/ashare_research/mechanism/planning/compiler.py               (plan sections, validate_analysis_plan)
src/ashare_research/mechanism/datasets/synthetic.py              (validate_dataset, quality semantics)
src/ashare_research/mechanism/hypothesis_config.py               (enums, canonical_decimal, strict fields)
src/ashare_research/mechanism/contracts.py, model_digest.py
src/ashare_research/mechanism/{bootstrap,regression,robustness,evidence}.py  (headers + real M3 bindings)
docs/m4_analysis_matrix_design_v1.md, docs/m4_analysis_matrix_acceptance_cases_v1.md
docs/m4_dataset_adapter_design_v1.md (referenced)
acceptance/2026-09-10_m4_analysis_matrix_design.md
tests/test_m4_stage4a1_typed_contract.py (fixture), tests/test_m4_synthetic_dataset_adapter.py (fixture)
tests/test_project_entry.py, tests/test_m4_stage4p_governance.py (assertions to synchronize)
```

No interface was inferred from a previous report: the plan sections, digests, matrix shape and
module behaviour above were re-measured in this session (section 4).

## 4. Measurement performed (read-only probes, no statistics)

### 4.1 Probe 1 — real plan / dataset / matrix facts

Standard-input probe, no file written, `PYTHONPATH = src; tests`:

```text
contract_digest = ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457
plan_digest     = 45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981
input_digest    = c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602
domain_digest   = b78882e43d745e2095b55688ac1ea68da25fdd1c971cea9c77f50924c0e100da
dataset_digest  = c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b
matrix_digest   = a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a
sha256(serialize_dataset(preparation)) = 32533abc2e9cefc7f0fe66923afc9a3f5d6ca5b0def7d1228c33ead8d071a060
sha256(serialize_matrix(matrix))       = 70d9926e0bec6e440b8c692384cd67f4c03727e7fd7ee602affc009000b187fa
matrix: 3 rows x 5 columns ; response_role = TARGET_OUTCOME
matrix.execution_authorized = False ; matrix.statistics_computed = False
plan.analysis_method_id = DAILY_CONDITIONAL_CONTROLLED_OLS_V1 ; plan.plan_state = DETERMINISTIC_PRE_EXECUTION_PLAN
bootstrap_plan  = {confidence_level "0.95", enabled true, method_id MOVING_BLOCK_BOOTSTRAP_V1,
                   replications 1000, seed 42, rng PCG64,
                   block_length_policy_id N_CUBERT_ROUNDED_CLAMP_1_20_V1}
robustness_plan = {automatic_expansion false, automatic_selection false, dispatch_only true,
                   entries[0] = {SYNTH_ROBUSTNESS_1, CONDITIONAL_DESCRIPTIVES_V1,
                                 parameters {trim "0.0100", window ["1","2","3"]}}}
evidence_plan   = {rule_id SYNTH_EVIDENCE_RULE_1, expected_direction POSITIVE,
                   confidence_requirement "0.95", data_quality_failure_disposition INCONCLUSIVE,
                   outcome_read false}
holdout_boundary = {policy_id NO_HOLDOUT_AUTHORIZED, execution_authorized false}
numpy version   = 2.5.3
```

Notable measured fact used in the design: the frozen A.1 robustness registry entry carries an
extra `window` parameter (a declarative annotation that no engine in this repository interprets),
which drove the closed-parameter-schema decision in design section 12.2.

### 4.2 Probe 2 — block-length policy agreement (pure arithmetic)

The design freezes the block-length policy as an exact integer rule
(`k` unique with `(2k-1)^3 <= 8n < (2k+1)^3`, clamped to `[1, 20]`) instead of a floating-point
`n ** (1/3)`, because libm `pow` is not guaranteed correctly rounded across platforms.

```text
n = 1..200000: exact-integer rule vs numpy.floor(float64(n) ** (1/3) + 0.5) clamped -> 0 mismatches
n = 1..200000: exact-integer rule vs math.floor(n ** (1.0/3.0) + 0.5) clamped        -> 0 mismatches
samples (n -> L): 1->1 2->1 3->1 4->2 5->2 6->2 8->2 10->2 20->3 27->3 64->4 125->5 216->6 1000->10 10000->20
```

### 4.3 Probe 3 — exact bootstrap endpoint indices and numeric boundaries (pure arithmetic)

```text
level=0.95 B=1000 -> alpha=0.025 k_lo=25  k_hi=974
level=0.95 B=8    -> alpha=0.025 k_lo=0   k_hi=7
level=0.95 B=3    -> alpha=0.025 k_lo=0   k_hi=2
level=0.5  B=8    -> alpha=0.25  k_lo=2   k_hi=5
level=0.99 B=1000 -> alpha=0.005 k_lo=5   k_hi=994
level=0.9  B=20   -> alpha=0.05  k_lo=1   k_hi=18
level=0.95 B=2    -> alpha=0.025 k_lo=0   k_hi=1
signed zero: (-0.0).hex() = -0x0.0p+0 ; (0.0).hex() = 0x0.0p+0 ; -0.0 > 0 False ; 0.0 > 0 False
range gate: abs(Decimal("1000000")) > Decimal("1000000") False (inclusive) ; "1000001" True
canonical plain form of 1e18 = 1000000000000000000  (a canonical, finite, out-of-range cell)
```

### 4.4 Deliberate non-measurement

No coefficient, interval, p-value, rank or disposition value was computed. In particular the
`rank(X) <= min(n, k) = 3 < 5` conclusion for the base fixture is a dimension argument, not a
computed rank. The acceptance cases therefore contain no numeric expectations for estimator
outputs; that is a deliberate consequence of the contract's forbidden scope, recorded in the
acceptance-cases document section 7.

## 5. Engineering decisions (and the alternatives rejected)

1. **Single source-bound entry per artifact kind.** Both public execution entries take the full
   five-tuple `(matrix, preparation, contract, plan, bound_inputs)` and call the existing
   five-argument `validate_design_matrix` first. Rejected: a matrix-only entry, a "validate the
   digest string" shortcut, and a `**kwargs` signature (which would allow an undeclared holdout
   parameter to be silently ignored).
2. **Dispatch by `term_role` / `coefficient_role` only.** Estimator columns come from
   `plan.design_plan.ordered_terms` position order and matrix cells by index; the response vector
   comes from `preparation.complete_rows` because the matrix deliberately has no response column.
   M3 column names, fixed development dates, alphabetical ordering and `source_series_role`
   keying are forbidden. Rejected: any reuse of `mechanism/regression.py`'s `DESIGN_COLUMNS` or
   `analysis_contracts` date constants.
3. **Rank gate before solving.** `matrix_rank(X) == k` is required, then `lstsq` with `rcond=None`
   and a second rank check. Rejected: minimum-norm solution, `pinv`, dropping controls, switching
   estimator, or silently ignoring rank deficiency.
4. **Bootstrap replicates are fail-closed on rank deficiency.** A rank-deficient resample raises
   `SINGULAR_RESAMPLE`; it is not skipped. Rejected alternative: count skipped replicates and
   require a minimum estimable share — rejected because it needs an invented threshold constant.
5. **Endpoints are exact order statistics.** `k_lo = floor(B*alpha)`, `k_hi = ceil(B*(1-alpha))-1`
   with `alpha = (1-level)/2` computed in `Decimal`. Rejected: any library quantile default
   (an implementation-detail choice that would leak into identity).
6. **Closed robustness parameter schema.** ~~`CONDITIONAL_DESCRIPTIVES_V1` accepts exactly
   `{"trim"}`, so the unmodified fixture entry (which also declares `window`) fails closed with
   `UNSUPPORTED_ROBUSTNESS_PARAMETERS`.~~ **Superseded in R1** — see section 15. The R0 reasoning
   ("match the project's strict-field idiom, reject unknown parameters") was wrong for this
   boundary: parameters here are *registered data to be forwarded*, not an executor-owned schema,
   and the closed schema made the current, valid registration non-dispatchable. R1 instead defines
   no robustness parameter schema at all and forwards the registered canonical parameters verbatim.
7. **Two independent artifact schemas.** The robustness dispatch artifact has no `evidence` block,
   no statistic field, no ranking/selection field, `statistics_computed = False` (R1) and
   `outcome_read = False`; the primary entry's signature has no robustness parameter. Rejected: one
   combined artifact with an optional robustness section (which would make "use the best robustness
   result" expressible).
8. **Authorization is three separate booleans with frozen transitions.**
   `execution_authorized` (real-research authorization) is `False` in every object this design can
   produce; `statistics_computed` is `True` only on the **primary** artifact and `False` on the
   robustness dispatch artifact (R1: dispatch binds, it does not compute); `outcome_read` is `True`
   only on the synthetic primary artifact and is scoped by `provenance.synthetic_test_only`.
   Synthetic execution authorization is a property of the source chain (`mode == "SYNTHETIC"`), not
   of a flag that could be flipped. Rejected: reusing one flag for both synthetic readiness and real
   authorization.
9. **Content prohibition is mechanical.** Serialization rejects a forbidden key set (host/path/
   session keys plus `best`/`selected`/`winner`/`aggregate`/`ranking`) and any absolute-path string,
   so "no host identity" and "no best-result selection" are enforced by the artifact writer rather
   than by documentation.
10. **Scope discipline on the README and the two tests.** The README edits are limited to the
    intro paragraph, four capability rows (A.2 status plus new A.2D/A.2M/A.2E rows), the
    current-authorization bullet, the A.2I section's stale closing sentence and the Milestone 4
    roadmap cell. `tests/test_project_entry.py` keeps every protective assertion and only syncs the
    capability list and the stale "数据适配、执行尚未实现" string to the new README wording;
    `tests/test_m4_stage4p_governance.py` only replaces the stale roadmap assertion with the
    accurate one plus a negative assertion. No aggregate, north-star or production-surface gate was
    touched.

## 6. Deliverables written

```text
docs/m4_bounded_execution_and_evidence_design_v1.md      new (16 sections; 10 required behavior areas frozen;
                                                          R1: sections 6.2/7.1/7.2/7.7/8.1/9.1/10.2/10.4/11.2/11.3/11.4/12/16 revised)
docs/m4_bounded_execution_acceptance_cases_v1.md         new (R0: AC-01..AC-17; R1 adds AC-18 and AC-19,
                                                          incl. all 15 required case classes)
agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md   this file
acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md        new
README.md                                               capability + roadmap + authorization statements synced
tests/test_project_entry.py                             capability assertions synced, protective assertions kept
tests/test_m4_stage4p_governance.py                     single canonical README-status assertion synced
```

## 7. Actual validation (every command with its real exit code)

Run from `D:/量化分析-m4-executor-design`. The contract commands were executed with
`PYTHONPATH` set to the worktree `src` and the interpreter
`D:/量化分析-m4a2i/.venv/Scripts/python.exe`.

| # | Command | Exit | Real result |
| --- | --- | --- | --- |
| 1 | `pytest -q tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `15 passed, 1 warning` (the warning is the `pytest_cache` `WinError 5` note below) |
| 2 | `pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | **1** | `252 passed, 2 warnings, 3 errors` — the 3 errors are pre-existing environment setup denials, see section 8 |
| 3 | `ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `All checks passed!` |
| 4 | `git diff --check` | **0** | clean |
| 5 | `git diff --cached --check` | **0** | clean; the index is empty because staging was denied (section 13) |
| 6 | `git status --short --branch` | **0** | see section 9 |
| 7 | `git rev-parse HEAD origin/main refs/stash` | **0** | `82278f2…` / `f34adcb…` / `cb568ef…` |
| 8 | `git worktree list --porcelain` | **0** | 14 worktree entries, all preserved |
| 9 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 10 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | **0** | `f34adcb17c9995392690a1df6bb5a10ee102eb09` |
| 11 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | **0** | `[]` (no open PR) |
| 12 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only) |
| 13 | Markdown audit of the five changed/added Markdown files (UTF-8 decode, final newline, trailing whitespace, TAB, conflict markers, unbalanced fences) | **0** | see section 10 |
| 14 | Repository-relative Markdown link resolution over the same five files | **0** | see section 10 |
| 15 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222` = protected value |

Intermediate measurement, recorded honestly: the first run of command 1 (before the acceptance
document existed) was `1 failed, 14 passed`, exit **1**, failing
`test_entry_and_history_evidence_links_resolve` on the then-missing README link
`acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md`. The file was then created and
command 1 was re-run to the passing result in the table. No test was weakened to reach it.

## 8. Pre-existing environmental failure (reported verbatim, not hidden)

Command 2 exits 1 with three **setup-stage** errors; they are environment/sandbox denials, not
test-body failures, and they reproduce identically on the unmodified baseline of this worktree
(measured before any edit in this session: same `252 passed, 2 warnings, 3 errors`, exit 1):

```text
ERROR tests/test_m4_synthetic_dataset_adapter.py::test_cwd_and_from_dict_order_invariance
ERROR tests/test_m4_stage4a2i_analysis_plan.py::test_semantic_ab_equivalence_and_cwd_independence
ERROR tests/test_m4_stage4a1_typed_contract.py::test_yaml_loader_requires_mapping_and_rejects_object_tags

PermissionError: [WinError 5] access denied:
  C:\Users\111\AppData\Local\Temp\dsh-LXAvdH\pytest-of-dlam12138
at _pytest/pathlib.py find_prefixed -> os.scandir(root)
```

The same denial produces the `PytestCacheWarning`s for `.pytest_cache\v\cache\{nodeids,lastfailed}`
and the unreadable `pytest-cache-files-*` directory seen in `git status` stderr. All three errors
are the three `tmp_path` fixture cases; the remaining 252 tests pass. This is reported as-is and is
**not** counted as a pass. Attribution and the final judgement belong to Codex.

## 9. Worktree, index and protected state

```text
branch / HEAD      codex/m4-bounded-execution-design @ 82278f21c9fbe969a549cd7a07381794f3c5d4e7
                   (HEAD unchanged: the delivery commit was denied, see section 12)
index              empty — `git diff --cached --check` exits 0 with no staged path; the failed
                   `git add` could not even create `index.lock`, so the index was not modified
changed tracked    README.md, tests/test_project_entry.py, tests/test_m4_stage4p_governance.py
added untracked    docs/m4_bounded_execution_and_evidence_design_v1.md
                   docs/m4_bounded_execution_acceptance_cases_v1.md
                   agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md
                   acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md
src/**             no diff
protected M2 HEAD  3679b1bac7a1634c6452784a4d8f6d139966f222 = protected
stash              cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f = protected (not applied, not dropped)
DB SHA256          4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 = protected
worktrees          14, all preserved, none switched or cleaned
temporary files    none written in this session (all probes used standard input)
pytest cache dirs  13 `pytest-cache-files-*` directories exist in the worktree root; one
                   (`…-x67a99h4`) pre-existed at task start and the other 12 were created by this
                   session's pytest runs. They are unreadable in this sandbox (the same WinError 5
                   denial), so `git status` cannot scan them and they are invisible to the index;
                   they are NOT gitignored, contain no task content, and were deliberately left in
                   place rather than force-deleted. The intended delivery commit therefore names
                   explicit paths, never `git add -A`.
ignored preserved  `.ruff_cache/` and `__pycache__/` trees are ignored run artifacts, left as-is
```

## 10. Document audit detail

For `README.md`, `docs/m4_bounded_execution_and_evidence_design_v1.md`,
`docs/m4_bounded_execution_acceptance_cases_v1.md`, this record and the acceptance document:
UTF-8 decode without error, no BOM, no CR, no TAB, no trailing whitespace, exactly one final
newline, no conflict markers, balanced code fences. Every repository-relative Markdown link in the
five files resolves to an existing file (including the four new README links).

## 11. What was not done / residual risk

- No implementation and no implementation test: `execute_bounded_analysis` and the other seven
  entries exist only as proposed API in the design document.
- No statistical value of any kind was computed, and the acceptance cases deliberately contain no
  numeric expectations for estimator outputs; the implementing stage must produce the first real
  values under separate authorization and independent review.
- ~~The robustness parameter-schema decision (design section 12.2) makes the unmodified A.1 fixture
  robustness entry non-executable by design (fail-closed).~~ **R1 supersedes this**: the unmodified
  fixture entry is now dispatchable, and this stage defines no robustness parameter semantics at
  all. The remaining risk is the reverse one — `trim`/`window` are forwarded but not interpreted —
  which is a scope statement to be resolved with a real handler contract in a separate Goal.
- Byte reproducibility is claimed only for a fixed `numeric_runtime`; the artifact records
  `numpy.__version__` (`2.5.3` here) so cross-runtime drift is detectable rather than silent.
- The design freezes an interpretation-boundary literal, so "design complete" cannot be read as a
  research finding, estimability/significance statement, tradability claim, or any authorization
  for real data, holdout, M4-B, push, PR or merge.
- R1 risk: the dispatch artifact is intentionally thin (a bound, immutable dispatch plan), so its
  usefulness depends on a future handler stage. That is deliberate — inventing statistics now would
  be worse than shipping a boundary that computes nothing.

## 12. Blocking condition: the required local delivery commit was denied

The Goal requires "one scoped local design-delivery commit containing only paths 2-8 after
validation". The exact staging command was executed after validation and was **denied**:

```text
$ git add -- README.md tests/test_project_entry.py tests/test_m4_stage4p_governance.py \
    docs/m4_bounded_execution_and_evidence_design_v1.md \
    docs/m4_bounded_execution_acceptance_cases_v1.md \
    agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md \
    acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md
fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4-executor-design/index.lock': Permission denied
[exit code: 128]
```

This worktree is linked to the repository at `D:/量化分析/.git`, which is **outside** this session's
workspace root (`D:/量化分析-m4-executor-design`). Write probes measured in this session:

```text
D:/量化分析/.dsh_write_probe                                          -> DENIED  (UnauthorizedAccessException)
D:/量化分析/.git/worktrees/量化分析-m4-executor-design/.dsh_write_probe -> DENIED  (UnauthorizedAccessException)
D:/量化分析-m4-executor-design/.dsh_write_probe                        -> WRITABLE
index.lock after the failure                                           -> absent (nothing was left behind)
```

The one-shot escalation of the identical command to `danger-full-access` was refused because no
approval channel is available in this session ("sandbox escalation … requires approval, but no
approval channel is available"). Per the runtime rules a refusal with no approval channel is final,
so no workaround was attempted: no alternate index file, no alternate git directory, no repository
re-initialisation, no path aliasing, no `git add -A`. The index is therefore empty and HEAD is still
`82278f21c9fbe969a549cd7a07381794f3c5d4e7`.

Consequence: the seven whitelist paths exist as validated **working-tree** changes only. The single
command that completes the contract requirement, run in a shell that can write to
`D:/量化分析/.git`, is:

```powershell
cd D:/量化分析-m4-executor-design
git add -- README.md tests/test_project_entry.py tests/test_m4_stage4p_governance.py `
    docs/m4_bounded_execution_and_evidence_design_v1.md `
    docs/m4_bounded_execution_acceptance_cases_v1.md `
    agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md `
    acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md
git commit -m "docs: freeze M4 bounded execution and evidence design"
```

No push, PR or merge follows, and none is authorized.

## 13. Next step

The delivery is complete as validated working-tree content, but the mandatory local commit is
**BLOCKED** by the sandbox denial in section 12. The next step is therefore, in order:

1. run the staging + commit command from section 12 in a shell with write access to
   `D:/量化分析/.git` (or grant this session the required file access), then re-run
   `git diff --cached --check`, `git status --short --branch` and
   `git rev-parse HEAD origin/main refs/stash` to confirm the single scoped commit and the unchanged
   protected baseline;
2. let Codex independently verify the real branch/HEAD, the delivery commit and diff, all changed
   and untracked files, the test evidence above, worktrees/stash, the protected baseline, the live
   GitHub state and Goal compliance.

The verdict must be exactly `PASS`, `CHANGES_REQUIRED` or `BLOCKED`; this record's own verdict is
`BLOCKED` on the commit step alone. Implementation, push, PR, merge and any M4-B or statistical
execution stage each require separate explicit user authorization.

## 14. R1 revision: the three review findings and their fixes

Codex's independent review of R0 returned `CHANGES_REQUIRED` with three findings. R1 changes only
whitelisted documents (paths 2-8); `src/**`, statistics, database, provider, holdout, commits and
pushes were not touched, and no test was weakened.

### 14.1 Finding 1 — self-contradictory identity boundary

R0 design section 6.2 stated "float64 never enters identity", while 8.3/10.x made `float64_hex` and
the statistics blocks part of `artifact_digest`. Fixed by replacing 6.2 with an explicit **two-layer
identity**:

- layer 1 (existing, unchanged): the six upstream source-chain digests bind only canonical decimal
  strings, canonical ISO dates and digests; float64 never enters them and is never written back;
- layer 2 (new artifact identity): `artifact_digest` **must** bind every float64 output of
  `estimator` / `bootstrap` / `conditional_descriptives` / `evidence` through
  `Float64ValueV1{float64_hex, canonical_decimal}`, plus `numeric_runtime` and the code/schema
  versions. Otherwise "change a coefficient, keep the digest" would pass validation.

The layers are connected one-way: float64 is derived from the source-chain decimals by exactly one
deterministic conversion, so the artifact stays recomputable. Also clarified: the `Float64ValueV1`
self-consistency check verifies both renderings come from the same float64 value and does **not**
require the two strings to be equal (`"-0x0.0p+0"` + `"0"` is a legal pair, and it defines a
different artifact identity than `"0x0.0p+0"` + `"0"`). Section 6.1, 1.1(8), 8.3 and 10.4 aligned.
New acceptance case **AC-18** (18a-18e).

### 14.2 Finding 2 — unauthorized runtime downgrade of `enabled`

R0 design 7.1 allowed the plan to declare `enabled=true` while the artifact recorded
`enabled=false` or `None`. Fixed in 7.1/7.2/7.7/8.1/10.1:

```text
actual_enabled = plan.bootstrap_plan.enabled        # strict copy, never re-derived
artifact.bootstrap.enabled is actual_enabled        # else INVALID_INPUT_STRUCTURE
```

`enabled=True` -> bootstrap must run, and any failure (method / RNG / replications / block length /
resample rank / finiteness) fails the **whole execution closed**: no artifact, no
"fall back to a null-endpoint artifact" path. Only a plan declaring `enabled=False` with
`method_id="DISABLED"` takes the disabled path. `None` is no longer a legal value; when
`enabled=True` every method-related field must be non-`None`, and when `False` all must be `None`.
The plan layer already enforces the `enabled`/`method_id` pairing
(`hypothesis_config` `INVALID_BOOTSTRAP_POLICY`), and the executor may not widen it. Disposition
D2 is now keyed on the plan-declared value. New acceptance case **AC-19** (19a-19d; 19d is the
direct counter-example to the old downgrade path).

Measured evidence for the strict-copy rule (read-only probe of the real frozen plan, section 16):
the default fixture declares `enabled=True` with `MOVING_BLOCK_BOOTSTRAP_V1`, so R0's
"declaration and execution may differ" clause was already wrong for the actual baseline.

### 14.3 Finding 3 — invented closed robustness parameter schema

R0 design 12.2 invented an executor-owned closed schema accepting exactly `{"trim"}`, which made
the **current, valid** registered entry (`parameters = {trim, window}`) necessarily fail with
`UNSUPPORTED_ROBUSTNESS_PARAMETERS`. Fixed by rewriting section 12 as **true registered
dispatch-only**:

- validate request IDs (non-empty, no duplicates, all registered), request order and the registered
  `method_id` / JSON-object shape;
- forward the registered canonical `parameters` **completely and immutably** — every key, nested
  object and array element, including keys this design never mentions — with no ignoring, no
  rewriting, no default filling, no re-normalization;
- no auto-execution, no auto-expansion, no auto-selection, and **no invented statistics**: this
  stage defines no robustness method allow-list and no parameter schema, because the project has no
  existing handler contract (`mechanism/robustness.py` is M3-bound and forbidden). `trim`/`window`
  semantics must be frozen together with a real handler contract in a separately authorized Goal;
- entry renamed `execute_registered_robustness` -> **`prepare_registered_robustness_dispatch`**,
  because "execute" would imply statistical execution. Outcome schema renamed accordingly:
  `RobustnessEntryResultV1{trim, retained_*_count, statistics}` ->
  `RobustnessEntryDispatchV1{robustness_id, request_ordinal, registration_ordinal, method_id,
  parameters, parameters_canonical_json}`; `RobustnessDispatchV1` gains
  `parameters_interpreted: bool` (strictly `False`);
- states: `statistics_computed` and `outcome_read` are now **strictly `False`** on the dispatch
  artifact (R0 had `statistics_computed=True`, which would have misreported "bound" as "computed");
- error codes: `UNSUPPORTED_ROBUSTNESS_PARAMETERS` and `INVALID_ROBUSTNESS_PARAMETER` **removed**;
  `UNSUPPORTED_ROBUSTNESS_METHOD` narrowed to "not a legal identifier / not a JSON object";
- stage 11.2 R8 rewritten (binding, not schema matching); 11.3 V3 now re-runs
  `prepare_registered_robustness_dispatch` and explicitly does **not** recompute statistics;
- 9.1/9.2 state tables, the section 16 risk table, AC-12 (rewritten), AC-05 (5e/5g), AC-16 (new
  nested-parameter mutation 16d) and the acceptance document all updated.

The nested mutation 16d is what makes the "complete forwarding" claim falsifiable: dropping or
rewriting a nested `window` element must change `artifact_digest`.

## 15. R1 validation (every command, real exit code)

Same environment as R0: worktree `D:/量化分析-m4-executor-design`,
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`, interpreter
`D:/量化分析-m4a2i/.venv/Scripts/python.exe`.

| # | Command | Exit | Real result |
| --- | --- | --- | --- |
| 1 | `pytest -q tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `15 passed, 1 warning` (the warning is the `pytest_cache` `WinError 5` note) |
| 2 | `pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | **1** | `252 passed, 2 warnings, 3 errors` — byte-identical to the R0 baseline result; the 3 errors are the same pre-existing environment setup denials (section 8) |
| 3 | `ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `All checks passed!` |
| 4 | `git diff --check` | **0** | clean |
| 5 | `git diff --cached --check` | **0** | clean; index still empty (nothing staged) |
| 6 | `git status --short --branch` | **0** | exactly the seven whitelist paths (` M` x3, `??` x4) plus `## codex/m4-bounded-execution-design` |
| 7 | `git rev-parse HEAD origin/main refs/stash` | **0** | `82278f21c9fbe969a549cd7a07381794f3c5d4e7` / `f34adcb17c9995392690a1df6bb5a10ee102eb09` / `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` |
| 8 | `git worktree list --porcelain` | **0** | 14 worktree entries, all preserved |
| 9 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 10 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | **0** | `f34adcb17c9995392690a1df6bb5a10ee102eb09` (live) |
| 11 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | **0** | `[]` (live; no open PR) |
| 12 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only; contents never opened) |
| 13 | Markdown audit over the five changed/added Markdown files (UTF-8 decode, BOM, CR, TAB, trailing whitespace, final newline, conflict markers, fence balance) | **0** | all five `issues=NONE` (fences 30 / 96 / 30 / 28 / 16) |
| 14 | Repository-relative Markdown link resolution over the same five files | **0** | 32 links total, all resolve; 0 files with missing targets |
| 15 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222` = protected value |
| 16 | Read-only probe of the real frozen plan (see section 16) | **0** | confirms the AC-12 / AC-19 expected values below |

## 16. R1 read-only probe (no statistics computed)

One read-only probe was run in R1 to replace assumption with measurement for the two
fixture-dependent claims. It builds the plan from the existing test helpers and prints the frozen
plan's canonical values — it calls no regression / bootstrap / robustness / evidence code and
computes no coefficient, interval, p-value, rank or disposition:

```text
$env:PYTHONPATH = (Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) 'tests')
python -c "<build_analysis_plan(_compiled()) and print canonical plan fields>"     # exit 0

entries_len        1
robustness_id      'SYNTH_ROBUSTNESS_1'
method_id          'CONDITIONAL_DESCRIPTIVES_V1'
parameters (thawed) {'trim': '0.0100', 'window': ['1', '2', '3']}
parameters_compact  {"trim":"0.0100","window":["1","2","3"]}
bootstrap_enabled  True
bootstrap_method   'MOVING_BLOCK_BOOTSTRAP_V1'
```

Consequences now frozen in the documents:

1. the unmodified fixture entry **is** dispatchable, and its verbatim canonical parameter text is
   exactly `{"trim":"0.0100","window":["1","2","3"]}` (AC-12a expectation);
2. the A.1 source document declares `window: [1, 2, 3]` as integers, while the *plan* canonicalizes
   them to decimal strings — so the executor must forward the frozen plan value verbatim and must
   not normalize a second time (design section 12.2);
3. the default fixture declares `enabled=True` with a real bootstrap method, so the strict-copy rule
   applies to the primary baseline path, not only to a hypothetical case.

## 17. R1 next step

Content review can proceed on this R1 working tree. The commit blocker of section 12 is unchanged
and is now also mandated: the R1 instruction forbids `git add`/`git commit` because the parent
repository is written by Codex. The next steps are therefore:

1. Codex independently inspects the real branch/HEAD, the working-tree diff of the seven whitelist
   paths, the test evidence of section 15, worktrees/stash, the protected baseline and database
   hash, the live GitHub state, and Goal compliance — including re-deriving the AC-12/AC-19 expected
   values from the real plan as in section 16;
2. Codex stages and commits the seven whitelist paths under its own authority (command quoted in
   section 12), then re-runs `git diff --cached --check`, `git status --short --branch` and
   `git rev-parse HEAD origin/main refs/stash`.

The verdict must be exactly `PASS`, `CHANGES_REQUIRED` or `BLOCKED`. Implementation, push, PR, merge
and any M4-B or statistical execution stage each require separate explicit user authorization.

## 22. Codex independent review resolution

Codex independently inspected the actual branch/HEAD, the seven-path whitelist diff, all new and
modified files, the real compiler/matrix/adapter interfaces, the R2 identity and dispatch fixes,
the AC index/body set, worktrees, stash, protected M2 HEAD, database hash and live GitHub state.
Outside the Harness ACL sandbox, Codex reran the required tests and obtained `15 passed` and
`255 passed`; ruff and diff checks also passed. The three Harness `tmp_path` errors therefore remain
environment attribution evidence rather than product failures.

Final verdict: **PASS**. Codex creates the contract-required single scoped delivery commit after
this record's final validation and reports its hash in the external handoff. This resolution does
not authorize implementation, push, PR, merge, M4-B, real data, holdout or statistical execution.

## 18. R2 revision: the three review findings, the fixes, and one additional measured defect

Codex's second review of R1 returned `CHANGES_REQUIRED` with three consistency findings. R2 again
changes only whitelisted documents (paths 2-8): `src/**`, statistics, the database, providers,
holdout, subagents/delegation, `git add`/`git commit` and push were not touched, and no test was
weakened. The user instruction for R2 explicitly forbids the delivery commit, so the section 12
blocker is unchanged and is now instruction-mandated rather than sandbox-only.

### 18.1 Fix 1 - artifact identity binding split by artifact kind

R1 had one table row stating that **both** artifacts' `artifact_digest` "**must** bind the float64
outputs of the estimator, bootstrap, conditional descriptives and evidence blocks". That is true for
the primary artifact and false for the robustness dispatch artifact, whose schema has no such blocks
and whose `statistics_computed` is strictly `False`: it claimed a binding over outputs that do not
exist. R2 separates the binding:

- `ExecutionArtifactV1.artifact_digest` **must** bind **all** normalized float64 statistic output of
  `estimator` / `bootstrap` / `conditional_descriptives` / `evidence` (via
  `Float64ValueV1{float64_hex, canonical_decimal}`), the complete source chain, provenance, the full
  method configuration (incl. `numeric_runtime`, code and schema versions), `sample` and the three
  status bits;
- `RobustnessArtifactV1.artifact_digest` **must** bind the complete source chain, the request order
  and the registry order (`dispatch.requested_ids` / `dispatch.registered_ids`), `method_id`, the
  **complete canonical parameters** (unknown nested keys included), provenance, code/schema versions
  and `numeric_runtime`, plus the three status bits - and **no float64 statistic output**, because
  `statistics_computed = False` means there is none. The three strictly-`False` flags
  (`automatic_expansion`, `automatic_selection`, `parameters_interpreted`) are part of that binding.

Files touched: design 1.1(8), 6.2 (table split into layer-2(a)/(b), boundary table split, 8.3
scoped to the primary artifact), 10.4 (two explicit coverage lists), 16 (two new rows);
acceptance-cases AC-18 (new subcases **18f** structural absence and **18g** binding list, key
assertions and authorization interpretation rewritten); acceptance document decisions 3 and 8, the
coverage rows for two-layer identity, the R2 probe subsection below and the residual-risk text.

### 18.2 Fix 2 - orphan `AC-09` removed, index `AC-12` title synchronized

The cases index and the work record referenced `AC-09 bootstrap 禁用路径`, but the cases document
had **no** `### AC-09` section: an orphan index row. Since AC-19 already covers enabled/disabled and
the no-downgrade requirement in full, R2 deletes the `AC-09` row rather than inventing a duplicate
section, and states the requirement-to-case mapping explicitly:

```text
bootstrap 禁用路径      -> AC-19b (enabled=false / method_id="DISABLED": null endpoints, no RNG,
                           INCONCLUSIVE / BOOTSTRAP_DISABLED)
bootstrap 启用路径      -> AC-08 (enabled execution with exact endpoint indices) and AC-19a
                           (strict copy of the plan declaration, non-None endpoints)
无运行时降级            -> AC-19c (plan-level INVALID_BOOTSTRAP_POLICY propagated) and AC-19d
                           (induced failure fails the whole execution closed)
```

Also in the cases document: AC-08 gained assertion 5 (it covers the enabled branch only, with a
pointer to AC-19b for the disabled branch), the section 7 ordering lists were updated, and the index
title for `AC-12` was synchronized with its body heading to
`注册稳健性派遣：请求、顺序与完整转发` (the old `未注册稳健性与参数 schema` title was stale: it named
a parameter schema this design deliberately does not have, and described one negative subcase as if
it were the whole case). No other case was renumbered and no empty number was left behind. Verified
by machine: the index ID set and the body `###` ID set are now **identical**, with no orphan on
either side (section 20).

### 18.3 Fix 3 - `canonical_decimal` wording corrected

Design 6.2 had called `canonical_decimal` a lossy rendering in which "decimal mantissa digits beyond
`repr`'s 17 significant digits are discarded". That is wrong: CPython's `float` `repr` emits the
**shortest round-trip decimal** (the fewest digits that uniquely determine the value), so the digit
count varies by value and there is no fixed 17-digit truncation. R2 rewrites 6.2 to say exactly that,
adds the R2 read-only measurement table (section 20, probe A) and states that the **exact binary
identity is carried by `float.hex`**, with both renderings entering the primary artifact identity in
parallel. The same wording was corrected in the cases document AC-18 key assertion 3, the acceptance
document, and the design risk table (section 16).

### 18.4 Additional defect found by this revision's own consistency search (not in the review list)

The R2 instruction required a full-text consistency search, and that search found a fourth,
implementation-critical defect in the same subject matter as Fix 1: design 10.2/10.4 claimed the
robustness dispatch artifact's `artifact_digest` binds `entries[*].parameters` because "`canonical_digest`
recursively serializes the `FrozenJSONObject`". That is impossible: `canonical_digest` is
`json.dumps(payload, sort_keys=True, separators=(",", ":"))`, and `FrozenJSONObject` /
`FrozenJSONList` / `FrozenJSONNumber` are frozen dataclasses, not JSON-serializable values - the call
raises `TypeError` instead of producing a digest (measured, section 20 probe B). Because this sits
inside the exact binding statement R2 was asked to correct, leaving it would have shipped an
unimplementable digest rule, so R2 fixed it inside the whitelist:

- design 10.2 now specifies the **digest extraction path**: the frozen form must first be projected to
  plain JSON (object->dict, array->list, `FrozenJSONNumber` -> its canonical decimal string) - either
  the existing `planning/compiler._thaw` semantics or `json.loads(parameters_canonical_json)` - and
  only that projection enters the digest payload; the frozen form stays the verbatim, immutable
  storage and self-consistency check;
- the frozen form is neither copied into nor serialized inside `artifact_digest`, so no artifact
  identity depends on a dataclass `repr`;
- 10.4, 14.2 (reuse list) and 16 (new row) were aligned with it;
- the projection was measured to be deterministic, to bind the nested `window` element, and to equal
  `json.loads(parameters_canonical_json)` (section 20 probe B).

This is reported explicitly as a deviation from the literal R2 instruction ("fix these three
things"): a fourth, adjacent, measured defect was fixed within the same whitelist, and no other
content changed. Codex should treat it as reviewable scope, not as a silent edit.

## 19. R2 validation (every command, real exit code)

Same environment as R0/R1: worktree `D:/量化分析-m4-executor-design`,
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`, interpreter
`D:/量化分析-m4a2i/.venv/Scripts/python.exe`. Every command below was executed in this R2 session;
none is inherited from R0/R1.

| # | Command | Exit | Real result |
| --- | --- | --- | --- |
| 1 | `python -m pytest -q tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `15 passed, 1 warning` (the warning is the environment `pytest_cache` `WinError 5` note) |
| 2 | `python -m pytest -q tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | **1** | `252 passed, 2 warnings, 3 errors` - identical to the R0/R1 baseline; the 3 errors are the same pre-existing environment setup denials (section 8), reproduced again in this session with a new `dsh-aErK2R` temp directory name |
| 3 | `python -m ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | **0** | `All checks passed!` |
| 4 | `git diff --check` | **0** | clean |
| 5 | `git diff --cached --check` | **0** | clean; index still empty (R2 forbids staging, so nothing was staged) |
| 6 | `git status --short --branch` | **0** | exactly the seven whitelist paths (` M` x3, `??` x4) plus `## codex/m4-bounded-execution-design` |
| 7 | `git rev-parse HEAD origin/main refs/stash` | **0** | `82278f21c9fbe969a549cd7a07381794f3c5d4e7` / `f34adcb17c9995392690a1df6bb5a10ee102eb09` / `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` |
| 8 | `git worktree list --porcelain` (counted) | **0** | 14 worktree entries, all preserved |
| 9 | `git stash list` | **0** | only the pre-existing `stash@{0}` |
| 10 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | **0** | `f34adcb17c9995392690a1df6bb5a10ee102eb09` (live) |
| 11 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | **0** | `[]` (live; no open PR) |
| 12 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | **0** | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` = protected value (hash only; contents never opened) |
| 13 | `git diff --stat -- src` | **0** | empty output: no `src/**` diff |
| 14 | `git -C D:/量化分析 rev-parse HEAD` | **0** | `3679b1bac7a1634c6452784a4d8f6d139966f222` = protected value |
| 15 | Markdown audit over the five changed/added Markdown files (UTF-8 decode, BOM, CR, TAB, trailing whitespace, final newline, conflict markers, fence balance) | **0** | all five `issues=NONE` (fences 30 / 102 / 30 / 28 / 16; the design document grew from 96 to 102 with the two R2 measured blocks) |
| 16 | Repository-relative Markdown link resolution over the same five files | **0** | 32 links total, 0 missing (README 23, design 4, cases 3, record 0, acceptance 4) |
| 17 | AC index/body cross-check in the cases document (index rows `^\| AC-nn \|` vs body `^### AC-nn`) | **0** | both sets are exactly `AC-01..AC-08, AC-10..AC-19`; orphan index = none, orphan body = none |
| 18 | R2 read-only probe A: `canonical_decimal(repr(v))` over 9 float values | **0** | see section 20 |
| 19 | R2 read-only probe B: `canonical_digest` on `FrozenJSONObject` vs its plain-JSON projection | **1** (first form raises the expected `TypeError`) | see section 20 |

Honest note on command 19: the raw frozen form is *expected* to fail, and it did. The probe's overall
exit code is 1 only because that first statement raised; the projection form then produced the
deterministic digest and the nested-mutation digest. No probe wrote a file, opened the database,
called a provider, or computed a coefficient, interval, p-value, rank or disposition.

## 20. R2 read-only probes (no statistics, no file written)

Probe A - rendering semantics behind the corrected 6.2 wording:

```text
value                     repr                     float.hex                    canonical_decimal
0.0                       0.0                      0x0.0p+0                     0
-0.0                      -0.0                     -0x0.0p+0                    0
0.5                       0.5                      0x1.0000000000000p-1         0.5
0.1                       0.1                      0x1.999999999999ap-4         0.1
1.0/3.0                   0.3333333333333333       0x1.5555555555555p-2         0.3333333333333333
1e16                      1e+16                    0x1.1c37937e08000p+53        10000000000000000
1e-5                      1e-05                    0x1.4f8b588e368f1p-17        0.00001
123456789.123456789       123456789.12345679       0x1.d6f34547e6b75p+26        123456789.12345679
float("inf")              -                        -                            raises HypothesisConfigError
```

Conclusions actually used by the documents: the digit count varies (16 digits for `1.0/3.0`, 17 for
`123456789.12345679`), so **no fixed 17-digit rule exists**; `repr`'s exponent forms are folded by the
existing function; `0.0` and `-0.0` share `canonical_decimal == "0"` while their `float.hex` differ,
which is why the exact identity is carried by `float64_hex`; non-finite values fail closed as
`NON_FINITE_ESTIMATE`.

Probe B - digest extraction path behind the 10.2/10.4 correction:

```text
canonical_digest({"parameters": FrozenJSONObject(...)})
    -> TypeError: Object of type FrozenJSONObject is not JSON serializable
canonical_digest({"parameters": <plain-JSON projection>})
    -> b8a23abe4fdc6d6ed2e1d6045a49cfd89eae2b0c4b5ab3658f2b1bbe0f3a8375
same projection, nested window element "3" -> "999"
    -> 0b4f38cf2ce8436689c4e672be7768060ef8e7e00c3336eee4ab19a5161d4764
repeated evaluation of the same projection
    -> identical digest (deterministic)
plain-JSON projection == json.loads('{"trim":"0.0100","window":["1","2","3"]}')
    -> True, and re-dumping it compactly reproduces exactly that text
```

This keeps R1's nested-mutation claim (16d / 18g) true while replacing an impossible serialization
mechanism with a measured one. Only existing read-only functions were called:
`model_digest.canonical_digest`, `hypothesis_config._canonical_json_value`,
`hypothesis_config.canonical_decimal`.

## 21. R2 deliverables, scope and next step

Files changed by R2 (all inside whitelist paths 2-8):

```text
docs/m4_bounded_execution_and_evidence_design_v1.md        1.1(8), 6.2, 8.3, 10.2, 10.4, 14.2, 16
docs/m4_bounded_execution_acceptance_cases_v1.md           index (AC-09 removed, AC-12 retitled),
                                                           numbering note + mapping table, AC-08,
                                                           AC-18 (18f/18g), section 7 ordering
agent/record/2026-09-11_01_m4-bounded-execution-and-evidence-design.md   this file: header + 18-21
acceptance/2026-09-11_m4_bounded_execution_and_evidence_design.md        decisions 3 and 8,
                                                           coverage rows, R2 measurements, risks
README.md, tests/test_project_entry.py, tests/test_m4_stage4p_governance.py  unchanged by R2
                                                           (their R0 synchronization still holds)
```

Scope confirmation: no `src/**` diff, no dependency/workflow/configuration change, no other test
change, no statistical call, no coefficient/interval/p-value/rank/disposition computed, no database
content read, no provider, no real market input, no holdout, no M4-B, no delegation, no push, PR or
merge, and - per the R2 instruction - no `git add` and no `git commit`.

The section 12 blocker stands for the same single reason (the delivery commit must be made by Codex).
Sections 18-20 complete the R2 content correction; the next steps are:

1. Codex re-inspects the real branch/HEAD, the working-tree diff of the seven whitelist paths (with
   particular attention to the reviewable extra fix in 18.4), the R2 command evidence of section 19,
   worktrees/stash, the protected baseline and database hash, the live GitHub state and Goal
   compliance;
2. Codex stages and commits the seven whitelist paths under its own authority (command in section 12),
   then re-runs `git diff --cached --check`, `git status --short --branch` and
   `git rev-parse HEAD origin/main refs/stash`.

The verdict must be exactly `PASS`, `CHANGES_REQUIRED` or `BLOCKED`. Implementation, push, PR, merge
and any M4-B or statistical execution stage each require separate explicit user authorization.
