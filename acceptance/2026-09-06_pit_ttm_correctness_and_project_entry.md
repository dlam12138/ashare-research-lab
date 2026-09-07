# PIT/TTM correctness and project entry acceptance

Local implementation verdict: **PASS**. Remote delivery evidence is attached to
[PR #8](https://github.com/dlam12138/ashare-research-lab/pull/8) and its final-head checks.
This file records completed local validation; CI conclusions must be read from the
actual PR checks, not inferred from this verdict.

Goal: `agent/goals/2026-09-06_pit_ttm_correctness_and_project_entry.md`.
Base: `origin/main` at `a0a7c13ee47057abf5e40a96a616baf78451774e`.
Branch: `codex/pit-ttm-correctness-and-project-entry`.
Required: baseline-failing regressions, green full suite/lint/compile, unchanged frozen
artifacts and original DB/stash, scoped commits and an unmerged main-targeting PR.

## Implementation and interfaces

- A shared YYYY-MM-DD/calendar gate protects AsOfQuery and repository cutoffs.
  Noncanonical dates, whitespace and invalid types raise PointInTimeError;
  explicit empty strings no longer disable filtering. Repository None retains
  the existing optional audit semantics; normal PIT is inclusive of cutoff day.
- TTM latest-time candidates resolve by visible supersession ancestry. Conflicting
  IDs, cycles, backwards edges and ambiguous ties fail with ValueError, including
  identifying facts. Minimum period starts and one annual state per time make
  input order irrelevant. Missing inputs retain only visible lineage and transition
  at dependency availability within the existing report window.
- No public signature, database schema, formula, output field or unit changes.
- README is the main capability entry, with offline/real-input distinctions,
  evidence links and actual M4-A.1 Python interfaces. Repeated stage narrative is
  archived in docs/project-history.md. M4-A.2 design remains on its own branch.

## PIT_DATE_GATE_V2 protection amendment

The first full run exposed an overlooked legacy source freeze in six test files.
The user instructed "继续" after the narrow exception was presented. Only the
facts/as_of.py expected source blob was advanced:

- Historical: `d707ec3a9ee161d42f9951e52b946c6f2a569085`.
- Repaired: `8e50d151732e4e7eb2e63456f6ed990dc11d15a6`.
- Reason: alternate ISO date strings bypassed the VARCHAR PIT cutoff; shared
  strict validation fixes that error and the comparison-period validation.
- Affected tests: capital-return methodology, earnings-quality 2025 acceptance,
  net-profit foundation, ROE extension, ROE/ROA 2025 acceptance and foundation.
- Original hash remains documented in every changed map; exact equality assertions
  remain intact. An independent AST comparison against a0a7c13 confirmed unchanged
  map keys and exactly this one changed entry in each of the six maps.
- No frozen report, historical acceptance, research data, north-star, M3 source,
  M4 contract, CI workflow or other expected hash was changed.

This is a documented source-correctness amendment, not a relock of research results.

## Test evidence

Commands run in the new worktree using `.venv/Scripts/python.exe` (isolated Python 3.13.9,
dependencies installed with `-m pip install -e ".[dev]"`; no dependency declaration changes).

| Command / check | Actual result |
| --- | --- |
| `-m pytest -q tests/test_pit_date_boundaries.py tests/test_ttm_business_boundaries.py --tb=no` before product changes | 62 failed, 46 passed |
| Same two files after fixes | 108 passed |
| `-m pytest -q tests/test_m2_integration.py tests/test_m2_stage2k1r4e_financial_state.py tests/test_m2_stage2k1r4e_temporal_join.py tests/test_m4_stage4p_governance.py` | 60 passed |
| New boundaries, entry checks, valuation-series and six amended protection suites together | 208 passed, 54.89 s |
| First `-m pytest -q` | 7 failed, 2412 passed, 4 skipped, 2 warnings, 379.43 s |
| Final `-m pytest -q -rs` | 2419 passed, 4 skipped, 2 warnings, 327.59 s |
| `-m ruff check src/ tests/` | All checks passed |
| `-m compileall -q src tests` | Exit 0 |
| `git diff --check` | Exit 0 |
| `-m ashare_research.tools.stage2g_reproducibility verify-contracts` | pass_with_explicit_gaps; 33 facts; no network |

The initial 7 failures were six old source hashes plus one invalid negative-earnings
fixture. That fixture appended an unrelated same-time candidate and selected a Q1
with no prior inputs. It now replaces a computable annual input and additionally
requires nonempty negative observations, nonpositive_earnings and a null ratio.
All eight tests in that file passed after the correction. The first new-test attempt
also needed a NOT NULL context-fixture correction before the valid red run above.

Final skips are existing environment-dependent cases: three require unshipped real
Baostock snapshots; one requires symlink creation unavailable on this Windows session.
The two warnings are existing pandas date-inference warnings in test_quality.py.
No test was skipped or weakened by this change.

Existing PE and PS synthetic fixture outputs were compared by executing baseline
TTM source from `git show a0a7c13:src/ashare_research/pit_valuation/ttm.py` in memory:
all 25 states per metric are identical, including all payloads, IDs and lineage;
22 states per metric are computed. No fixture or expected research output changed.

`verify-clean-clone` was also attempted after local tests: it correctly rejected the
test-generated output directory and then-untracked acceptance file. It is a pre-test
clean-clone gate, not an in-place post-test gate. Leave runtime output intact and
verify it in the actual fresh CI checkout. No workaround or gate change was made.

## Git and protection evidence

- Implementation commits: `676c973` (dates), `34b6e3e` (TTM), `396a905` (entry),
  `e94f285` (scoped source protection and meaningful negative-earnings test).
- Original DB SHA256 remains
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- New worktree default DB is absent; original stash remains
  `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Original dirty worktree, other worktree HEADs and all pre-existing files are preserved.
- Stop before merge. This task does not authorize any next research stage.

## Remote delivery

- PR: https://github.com/dlam12138/ashare-research-lab/pull/8, OPEN, not draft,
  base main, head codex/pit-ttm-correctness-and-project-entry.
- First push and PR head: `af6ac41fbd758ca00043eef14b23e27fbe6f78ec`;
  local HEAD and origin tracking ref matched exactly at that handoff.
- Main remained `a0a7c13ee47057abf5e40a96a616baf78451774e`.
- Subsequent evidence-only commit records this handoff. Its final SHA and CI
  conclusions are recorded in the PR body/final response after the ordinary push,
  avoiding a self-referential commit hash in this file.
- All seven existing workflows are unchanged. Windows/Linux Stage2G clean-clone
  full tests and cross-platform identity, plus M3 lock/identity workflows, are
  required delivery evidence. No merge was requested or performed.
- Final changes are limited to four source files (as_of, dates, repository, ttm),
  three new test files, seven existing test files (six source-hash entries and one
  strengthened fixture), README/history/record index, and this task's Goal/record/acceptance.
