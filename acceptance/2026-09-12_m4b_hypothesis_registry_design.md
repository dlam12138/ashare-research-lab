# Acceptance: M4-B hypothesis registry design (design-only)

Harness verdict: **BLOCKED** — the design, acceptance cases, README synchronization and this document
are complete and independently validated in the working tree, but the Goal-mandated scoped local
delivery commit cannot be created because this sandbox denies every write to the linked git
directory (see "Blocking condition: scoped local commit"). This is **not** a self-acceptance: the
Goal and `AGENTS.md` make Codex's independent verdict authoritative, and the missing commit is the
single unmet Goal requirement. No push, PR, merge, implementation or next stage was attempted.

Verdict scope: this document accepts nothing beyond the frozen design and acceptance-case set for
the minimum M4-B `Theory / Hypothesis Registry` slice. No registry implementation exists, no real
candidate dataset was created, no literature was acquired, and no provider, database content, real
market input, holdout or statistical execution was accessed.

- Task contract: [Goal](../agent/goals/2026-09-12_m4b_hypothesis_registry_design.md).
- Normative design: [M4-B registry design v1](../docs/m4b_hypothesis_registry_design_v1.md).
- Acceptance cases: [M4-B registry acceptance cases v1](../docs/m4b_hypothesis_registry_acceptance_cases_v1.md).
- Work record: [work log](../agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md).
- Frozen preflight contract (unmodified): `reports/m4_stage4p_m4b_hypothesis_registry_contract_v1.json`.

## Baseline independently re-verified (this session, 2026-09-12)

| Item | Command | Observed | Expected by Goal |
| --- | --- | --- | --- |
| Branch | `git rev-parse --abbrev-ref HEAD` | `codex/m4b-hypothesis-registry-design` | same |
| HEAD | `git rev-parse HEAD` | `0de39577f164c095c4bf4f9c3b742fbbee50745d` (Goal contract commit, ahead 1) | Goal contract committed |
| `origin/main` (ref) | `git rev-parse origin/main` | `1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd` | PR #13 merge point |
| live GitHub `main` | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | `1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd` (exit 0) | matches local ref |
| Open PRs | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | `[]` (exit 0) | none open |
| Worktrees | `git worktree list --porcelain` | **16** worktrees, all preserved, none pruned | preserved |
| Stash | `git stash list` / `git rev-parse refs/stash` | 1 entry (`On feat/m2-value-assessment-mvp: protect pre-existing Stage 1B.4 record edit before Stage 1C`) = `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f` | unchanged |
| Protected M2 HEAD | `git -C 'D:/量化分析' rev-parse HEAD` | `3679b1bac7a1634c6452784a4d8f6d139966f222` | unchanged |
| Protected database | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` (hash only; database never opened) | unchanged |
| Forbidden surfaces | `Test-Path src/ashare_research/m4` / `Test-Path knowledge` | `False` / `False` | both absent |
| Protected trees | `git diff --name-only HEAD -- src reports config data events` | empty (exit 0) | no diff |
| Existing mechanism layout | directory listing | `datasets/`, `execution/`, `planning/`; `registry/` absent; top-level `mechanism/*.py` unchanged | matches design §11.1 |

## Deliverables

| Path | Status | Content |
| --- | --- | --- |
| `docs/m4b_hypothesis_registry_design_v1.md` | new (untracked) | 16 sections freezing all ten required behavior areas; every interface explicitly marked **proposed** |
| `docs/m4b_hypothesis_registry_acceptance_cases_v1.md` | new (untracked) | AC-01..AC-22, each with input change, expected result/stable error code, validation stage and authorization interpretation; Goal coverage map |
| `README.md` | modified | capability table, historical/current authorization paragraph and Milestone 4 roadmap updated for the design freeze only |
| `agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md` | new (untracked) | work record, corrected to actual evidence from this session |
| `acceptance/2026-09-12_m4b_hypothesis_registry_design.md` | new (untracked) | this document |

`tests/test_project_entry.py` and `tests/test_m4_stage4p_governance.py` were **not** modified (Goal
paths 7–8 are conditional, and no assertion synchronization was required). Both pass unchanged.

## Exact validation commands and observed results

All commands were run independently from `D:/量化分析-m4b-registry-design` with
`$env:PYTHONPATH = (Join-Path (Get-Location) 'src')`, the shared verified interpreter
`D:/量化分析-m4a2i/.venv/Scripts/python.exe`, and `-p no:cacheprovider`.

| # | Command (Goal §"Required tests and exact validation commands") | Exit | Observed result |
| --- | --- | --- | --- |
| 1 | `python -m pytest -q -p no:cacheprovider tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | `0` | `15 passed in 0.12s` |
| 2 | `python -m pytest -q -p no:cacheprovider tests/test_m4_bounded_execution.py` | `0` | `49 passed in 62.51s (0:01:02)` |
| 3 | `python -m pytest -q -p no:cacheprovider tests/test_m4_analysis_matrix.py tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py` | `1` | `252 passed, 3 errors in 13.22s` — three `tmp_path` setup errors, attributed below; no assertion failed |
| 4 | `python -m ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py` | `0` | `All checks passed!` |
| 5 | `git diff --check` | `0` | no output (no whitespace errors) |
| 6 | `git diff --cached --check` | `0` | no output (empty index) |
| 7 | `git status --short --branch` | `0` | `## codex/m4b-hypothesis-registry-design...origin/main [ahead 1]`, ` M README.md`, three `??` whitelist files, plus the environment warning recorded under "Deviations" |
| 8 | `git rev-parse HEAD origin/main refs/stash` | `0` | `0de39577…45d`, `16842757…0fd`, `cb568efd…85f` |
| 9 | `git worktree list --porcelain` | `0` | 16 worktrees, all branches/detached HEADs preserved |
| 10 | `git stash list` | `0` | the single pre-existing `stash@{0}` |
| 11 | `gh api repos/dlam12138/ashare-research-lab/branches/main --jq '.commit.sha'` | `0` | `1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd` |
| 12 | `gh pr list --state open --json number,title,headRefOid,baseRefName,url` | `0` | `[]` |
| 13 | `Get-FileHash -Algorithm SHA256 'D:/量化分析/data/research.duckdb'` | n/a (cmdlet, no error) | `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6` |
| 14 | `git -C 'D:/量化分析' rev-parse HEAD` | `0` | `3679b1bac7a1634c6452784a4d8f6d139966f222` |
| 15 | `git diff --name-only HEAD -- src reports config data events` | `0` | empty |
| 16 | `Test-Path src/ashare_research/m4` | n/a | `False` |
| 17 | `Test-Path knowledge` | n/a | `False` |
| 18 | Markdown hygiene audit (UTF-8/BOM, CR, final newline, trailing whitespace, conflict markers, fence balance) on all changed Markdown | `0` | `issues= NONE` for design, acceptance cases, README, work record and this document |
| 19 | Repository-relative Markdown link resolution on all changed Markdown | `0` | every relative link resolves, including the design/cases → this document links |
| 20 | Acceptance-case index ↔ body consistency (`### AC-nn` headings vs index table) | `0` | 22 index IDs, 22 body sections, ID sets equal, no duplicates and no orphans; each section carries all four required labels |
| 21 | `git add -- README.md docs/m4b_hypothesis_registry_design_v1.md docs/m4b_hypothesis_registry_acceptance_cases_v1.md agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md` | `128` | `fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4b-registry-design/index.lock': Permission denied` |

### Final-state reproduction

After the record and this document were written, the four executable validation commands were run
once more against the final working tree (no `README.md`, `src/**`, `reports/**`, `config/**`,
`data/**`, `events/**` or test file changed in between; only whitelist documentation was added):

```text
pytest tests/test_project_entry.py tests/test_m4_stage4p_governance.py   -> 15 passed in 0.11s     (exit 0)
pytest tests/test_m4_bounded_execution.py                                -> 49 passed in 69.34s    (exit 0)
pytest <five upstream M4 files>                                          -> 252 passed, 3 errors in 18.94s (exit 1)
ruff check tests/test_project_entry.py tests/test_m4_stage4p_governance.py -> All checks passed! (exit 0)
```

The three errors are the identical `tmp_path` / `0o700` environment failures, i.e. the results
reproduce deterministically.

### Command 3 failure, recorded verbatim and independently attributed

All three errors are the same fixture setup failure, not test failures:

```text
E       PermissionError: [WinError 5] 拒绝访问。:
        'C:\\Users\\111\\AppData\\Local\\Temp\\dsh-WpZARg\\pytest-of-dlam12138'
D:\量化分析-m4a2i\.venv\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
ERROR tests/test_m4_synthetic_dataset_adapter.py::test_cwd_and_from_dict_order_invariance
ERROR tests/test_m4_stage4a2i_analysis_plan.py::test_semantic_ab_equivalence_and_cwd_independence
ERROR tests/test_m4_stage4a1_typed_contract.py::test_yaml_loader_requires_mapping_and_rejects_object_tags
```

Independent attribution probe run in this session (read-only apart from one temporary directory,
see "Deviations"):

1. `os.scandir('C:\\Users\\111\\AppData\\Local\\Temp\\dsh-WpZARg')` succeeds and lists
   `['pytest-of-dlam12138']` — the session temp root itself is readable.
2. A directory created with `tempfile.mkdtemp(dir=<worktree>/.dsh-probe)` and then `os.chmod(d, 0o700)`
   raises the same `PermissionError: [WinError 5]` on `os.scandir(d)` — inside the workspace.

Conclusion: this sandbox denies enumeration of `0o700` directories; pytest creates its `tmp_path`
basetemp with mode `0o700`, so only the three tests that request `tmp_path` fail at setup, while the
other `252` tests in the same run pass. The Goal requirement to record and attribute a genuine
environmental failure is met; no test was weakened, skipped or rewritten. The prior M4-A.2E work
record reports the same failure mode, and Codex previously reproduced that group on the host
(`255 passed`) — this document does not claim a host reproduction for this session.

## Independent design/acceptance-cases consistency audit

A read-only audit script parsed the two new documents and the real repository artifacts and checked:

| Check | Result |
| --- | --- |
| Design §2.1 quoted preflight contract vs the real JSON file (`json.loads` deep equality, 12 top-level keys) | equal |
| `minimum_fields` / source types / states / candidate classes / `MAX_REAL_DEMO_CANDIDATES` | 19 / 6 / 12 / 3 / 3, all matching the frozen file |
| §4.1 canonical key block vs §4.2 field table | 26 keys both sides, identical sets, rows numbered 1–26 |
| Identity-bearing field enumeration vs `26 − status − state_history − identity_digest − record_digest` | 22 = 22, sets identical |
| §7.1 `S1..S12` vs contract `state_machine.states` order | identical |
| §7.2 matrix expanded cell-by-cell vs the frozen grouped count | exactly **20** legal edges; grouped list equals matrix expansion; `S9/S10/S11` have no out-edges; `ESTABLISHED` single in-edge `S8→S10`; `DEFERRED` only `→S4` |
| §9.1 "existing frozen set" vs `mechanism/contracts.py::RESTRICTED_RESEARCH_OUTPUT_KEYS` | exact equality (12 members) |
| §9.1/§9.2 vs `RESTRICTED_RESEARCH_OUTPUT_KEYS` / `bounded.py::FORBIDDEN_KEYS` | superset (24 forbidden-environment members all present) |
| AC-09 statement of the frozen 12-member set | matches the source |
| `hypothesis_id` regex claim vs `hypothesis_config._IDENTIFIER_RE.pattern` | `^[A-Za-z0-9][A-Za-z0-9_.-]*$`, identical literal |
| §5.2 digest algorithm claim vs `mechanism/model_digest.py::canonical_digest` | identical (`sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())`) |
| §2.2 claim that the execution layer imports `canonical_digest` from `model_digest` | true (`bounded.py` line 61) |
| §2.2 serialization-convention claim vs `serialize_matrix` | true |
| §2.2 failure-convention claim (`MatrixError`/`AdapterError`/`ExecutionError` subclass `ValueError`) | true |
| §2.2 `expected_direction` word list vs `EvidenceDirection` | `POSITIVE`/`NEGATIVE`/`TWO_SIDED` — true |
| Error codes referenced by the acceptance cases vs the closed §8.2 table | every referenced code is defined |
| "13 public entries" claim | design §11.2 lists 13; acceptance §0.1 lists the same 13 |
| Goal "must at least cover" case list vs the acceptance-case set | all 16 classes mapped (AC-01..AC-22) |

### Corrections applied during this independent verification

The interrupted session left a documentation draft whose own internal claims had not been verified.
The following defects were found by the audit above and corrected inside whitelist paths 2–3:

| # | Defect found | Correction |
| --- | --- | --- |
| 1 | §2.1 quoted the preflight contract as verbatim but omitted the top-level `purpose` key | `purpose` restored; deep equality with the real file now holds |
| 2 | Identity-bearing count stated as 21 in four places while the enumeration (and `26 − 4`) is 22 | corrected to 22 in §4.3, §5.2 (twice) and the binding-scope rule |
| 3 | §1.1 said "19 minimum fields plus 3 provenance fields", contradicting §2.1/§4.2 | rewritten as 19 + 2 provenance + 3 record-level + 2 derived = 26 |
| 4 | §2.1/§4.2/AC §0.3 gave 19 + 5 → 26 without the two derived digests | arithmetic made explicit and consistent |
| 5 | §5.1 rule S8 pointed at §4.1 for the nullable positions, which §4.1 does not define | pointer corrected to §7.7 |
| 6 | §3 froze `HYPOTHESIS_ID_MAX_LEN`/`SHORT_TEXT_MAX_LEN`/… but the field table also uses 1000/200/100 while forbidding new constants | `CITATION_MAX_LEN=1000`, `SOURCE_VERSION_MAX_LEN=200`, `TARGET_HORIZON_MAX_LEN=100` added to the frozen list |
| 7 | AC-11(11b) and AC-17(17e) each offered two alternative error codes "to be frozen at implementation time" | single codes frozen: (11b) `PROVENANCE_REWRITE`, (17e) `ILLEGAL_STATE_TRANSITION`; §4.4, §7.7, §8.1 (V12 intra-order), §8.2 and T5 updated accordingly |

Corrections 1–6 are bookkeeping/consistency repairs; correction 7 removes an implementation-critical
choice that the Goal requires to be frozen in the design.

## Whitelist compliance

Added or changed paths, compared with Goal "Allowed scope" paths 1–8:

```text
docs/m4b_hypothesis_registry_design_v1.md                          new (path 2)
docs/m4b_hypothesis_registry_acceptance_cases_v1.md                new (path 3)
agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md       new (path 4)
acceptance/2026-09-12_m4b_hypothesis_registry_design.md            new (path 5)
README.md                                                          modified (path 6)
agent/goals/2026-09-12_m4b_hypothesis_registry_design.md           unchanged (path 1, Codex-owned)
tests/test_project_entry.py                                        unchanged (path 7, not required)
tests/test_m4_stage4p_governance.py                                unchanged (path 8, not required)
```

No diff exists under `src/**`, `reports/**`, `config/**`, `data/**`, `events/**`, dependencies,
workflows, north-star documents, other tests or fixtures. `src/ashare_research/m4` and `knowledge/`
remain absent, no top-level `src/ashare_research/mechanism/*.py` file was added, and the frozen
Stage4P preflight report is byte-identical (`git diff --name-only HEAD -- reports` is empty).

## Blocking condition: scoped local commit

The Goal requires one scoped local design-delivery commit after validation. The exact final command
sequence (all five whitelist paths, run after every other validation was complete) was denied by the
sandbox:

```text
$ git add -- README.md docs/m4b_hypothesis_registry_design_v1.md \
      docs/m4b_hypothesis_registry_acceptance_cases_v1.md \
      agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md \
      acceptance/2026-09-12_m4b_hypothesis_registry_design.md
fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4b-registry-design/index.lock': Permission denied
[exit code: 128]

$ git commit -m "docs: freeze M4-B hypothesis registry design and acceptance cases"
fatal: Unable to create 'D:/量化分析/.git/worktrees/量化分析-m4b-registry-design/index.lock': Permission denied
[exit code: 128]
```

Evidence that this is an environment boundary rather than a command error:

```text
write probe D:/量化分析/.git/worktrees/量化分析-m4b-registry-design/.dsh_write_probe
  -> DENIED (UnauthorizedAccessException: Access to the path ... is denied.)
index.lock after the failure                                              -> absent (no residue)
one-shot escalation retry of the same `git add` command with danger-full-access
  -> rejected: sandbox escalation to "danger-full-access" requires approval,
     but no approval channel is available
```

No workaround was attempted: no alternate `GIT_INDEX_FILE`, no alternate git dir, no repository
re-initialization, no `git add -A`, no history rewrite. All validated files are left **uncommitted**
in the working tree, exactly as instructed. `HEAD` remains
`0de39577f164c095c4bf4f9c3b742fbbee50745d`.

Host-side unblock command (must run where `D:/量化分析/.git` is writable, e.g. Codex's shell):

```powershell
cd D:/量化分析-m4b-registry-design
git add -- README.md `
    docs/m4b_hypothesis_registry_design_v1.md `
    docs/m4b_hypothesis_registry_acceptance_cases_v1.md `
    agent/record/2026-09-12_01_m4b-hypothesis-registry-design.md `
    acceptance/2026-09-12_m4b_hypothesis_registry_design.md
git diff --cached --check
git commit -m "docs: freeze M4-B hypothesis registry design and acceptance cases"
git status --short --branch
git rev-parse HEAD origin/main refs/stash
```

## Deviations and unresolved risks

1. **Scoped local commit missing** (the blocking condition above). Content validation is complete;
   the commit is the single unmet Goal requirement.
2. **Temporary probe directory left in the worktree.** To attribute command 3 independently, this
   session created `<worktree>/.dsh-probe/tmp39hvuzdy` (empty, untracked, non-ignored). The sandbox
   denies enumeration and deletion of that `0o700` directory, so it could not be removed
   (`Remove-Item` → access denied; `rd /s /q` → access denied; escalation → no approval channel).
   It contains no files, is not part of the staged/committed path set, and does not appear in
   `git status --porcelain -uall` output other than as
   `warning: could not open directory '.dsh-probe/tmp39hvuzdy/': Permission denied`. Cleanup command
   for a fully privileged shell: `Remove-Item -Recurse -Force 'D:/量化分析-m4b-registry-design/.dsh-probe'`.
   This is a deviation introduced by this session and is disclosed rather than hidden.
3. **Three `tmp_path` setup errors** in the upstream M4 regression group (command 3, exit 1),
   attributed above to the sandbox `0o700` restriction and not to any test or product defect. The
   exit code is recorded verbatim as `1`; the group is not claimed to be fully green in this sandbox.
4. **Interrupted prior session.** The design/acceptance drafts and the work record were left by an
   earlier DSH session that ended unexpectedly; several of its pre-written claims (including the
   claim that this acceptance document had been written and that the record was complete) were not
   supported by repository evidence. This document and the corrected work record supersede those
   claims; every statement here corresponds to a command run in this session.
5. **Design-stage residual risks R1–R8** remain as recorded in design §15 (unfrozen forbidden-source
   word list, free-text outcome statements, registry-level completeness gate not being a statistical
   verdict, matrix/edge verification obligations, regex-drift duty, scale-boundary interpretation,
   and the deliberately unfrozen persistence format). They are implementation-review items, not
   defects of this design freeze.

## Boundary statement

This is a design and acceptance-case freeze only. `M4-B NOT STARTED`; real hypothesis execution is
`NOT AUTHORIZED`; `real_registry_dataset_authorized = false`; `not_implementation = true`. No
registry implementation, real candidate dataset, literature acquisition, provider/database/holdout
access, statistical execution, push, PR, merge or next-stage authorization is granted by this
document. Codex's independent review and verdict remain authoritative.

## Codex host review addendum

Codex independently reviewed the actual worktree after the Harness handoff. The host shell can
access ordinary pytest temporary directories and reproduced the required suites against the same
tracked source and README state:

```text
tests/test_project_entry.py tests/test_m4_stage4p_governance.py          15 passed in 0.10s
tests/test_m4_bounded_execution.py                                      49 passed in 59.93s
five upstream M4 regression files                                     255 passed in 8.36s
ruff check                                                              All checks passed!
```

This converts the Harness-only `252 passed, 3 errors` result into a fully green independent host
result and confirms that the three Harness errors were environmental `tmp_path` setup failures,
not product or assertion failures. Codex also confirmed `git diff --check`, the exact five-path
delivery whitelist, zero diff under `src reports config data events tests`, unchanged protected DB
hash, unchanged original M2 HEAD and stash, and live `origin/main` at `1684275714b12d1e7d4c3c95f8a8adfcc4d5e0fd`.

The empty `.dsh-probe/tmp39hvuzdy` directory was independently verified as the only probe residue.
The app command policy rejected the exact recursive removal even after the target was verified, so
the empty, untracked directory remains outside Git's file set; no broader or cross-shell deletion
workaround was attempted.

Codex accepts the content as `PASS`. The scoped delivery commit is created by Codex in the host
shell after this addendum; its hash is necessarily reported in the external final evidence packet.
This stage still stops before push, PR, merge, registry implementation, real candidate collection,
literature acquisition, provider/database/holdout access, or real hypothesis execution.
