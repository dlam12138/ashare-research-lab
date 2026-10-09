# M4 focused plan review summary

## Objective
Root directly adds a focused review summary to research plan:
--summary [--section ID] for the compile mode and both verify modes. The plan
is compiled or fully verified first; the summary is only a projection of that
captured report. User continuation authorizes this bounded engineering stage;
no DSH/delegation.

## Verified baseline
Origin/live codex/m4-plan-comparison-summary:
0b9c358ef2dea4b1d68da0a1b794795686238de8. PR81 OPEN/MERGEABLE;
36SUCCESS/4pending at initial query, not a complete hosted gate.
Main8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b unchanged.
Chain81->80->79->78->77->76->75->74->73->71->70->69->68 unmerged.
Fresh clean codex/m4-plan-review-summary at 0b9c358.
Before code tmp/plan-review-summary/baseline.json verified48worktrees/
47foreign states/27dirty hashes/427protected hashes against the previous
baseline, primary3679b1b/localmain966206f/stashcb568efd/database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Seven files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/{research_plan,research_entry}.py,
tests/test_research_plan_review_summary.py. Ignored demo/validation artifacts
allowed. Only cli main may change in research_plan.py; every pre-existing
function/class (compiler entry, decoding, markdown renderer, error handling) stays
AST unchanged; only new projection helpers are added.

## Forbidden scope
Existing tests, hypothesis config/contract compiler/analysis plan, plan
package/archive verifiers, all preparation tools and comparison modules,
schemas/CI/protected data/foreign worktrees/stash/DB/runtime. No acquisition,
real research/statistics/holdout, digest repair, extraction, writes, cleanup/
overwrite, main/force push, merges or automatic following stage.

## Required behavior
plan --hypothesis JSON --summary [--section ID], plan --verify DIR --summary
[--section ID] and plan --verify-archive ZIP --summary [--section ID] accept
--json. The compile mode compiles exactly once and projects that report; the
verify modes fully reproduce the delivered package or archive exactly once and
project the captured receipt report. No rereads, no extraction, no writes, no
new compilation or verification, no stored-diagnostic trust.
Selectors with export modes (--output/--archive) reject INVALID_ARGUMENTS before
IO; --section without --summary rejects INVALID_ARGUMENTS before IO; an unknown
or malformed section rejects INVALID_SECTION before IO; repeated sections
deduplicate in canonical order. Sections are
requirements/sample/condition/method/conditional/bootstrap/robustness/evidence/
holdout. Identity (hypothesis_id, source_file_sha256, contract_state, plan_state,
contract_digest, plan_digest, source_config_digest, source_contract_digest),
shape counts (requirement roles, ordered term count, robustness entries,
bootstrap enabled, holdout authorized), boundary and notes are always
preserved; filters change only the projected section payload.
The projection fails closed with PLAN_SUMMARY_MISMATCH when the captured report
violates frozen invariants: schema/status, exact boundary keys all false,
contract/plan hypothesis, digest and state consistency, unique requirement
roles, exactly one intercept and one condition-indicator term, response role a
requirement role, non-intercept/non-condition term source roles exactly the
other requirement roles, and conditional summary source roles matching.
New schema m4_compile_only_plan_review_summary_v1; Markdown is a compact Chinese
view with a per-mode source legend; no provenance, sealing, readiness or
execution claim. Without --summary original JSON/default Markdown stay
byte-identical. Sanitized errors/code2/no partial stdout. Offline, no database/
services/executor; sources immutable.

## Required tests and exact validation commands
PYTHONPATH=src; Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_research_plan_review_summary.py tests/test_research_plan.py tests/test_research_plan_package.py tests/test_research_plan_archive.py tests/test_research_plan_compare.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_entry.py tests/test_research_plan_review_summary.py
git diff --check
python tmp/plan-review-summary/calculation_review.py
python tmp/plan-review-summary/demo.py
python tmp/plan-review-summary/verify_protections.py
Cases: summary exact projection from compile/directory/ZIP modes, legacy JSON and
Markdown byte-equal, repeated/reordered sections, section payload mapping,
identity/shape/boundary preservation, once-read snapshot handoff,
invalid selectors and export-mode rejection before IO, doctored-report invariant
guards with sanitized CLI failure, offline/no-write guards, actual Windows
junction rejection.

## Acceptance criteria
Seven-file scope; meaningful tests/Ruff/diff/demo pass. 47foreign registrations/
HEAD/branches/statuses,27dirty hashes,427protected hashes, primary DB/stash/
localmain unchanged; untouched modules byte-equal to base and only cli main
changed in research_plan.py (AST review). Owned clean; feature/dependency
local/origin/live agree. No full local suite claim; exact-head hosted pending
state independently reported.

## Stop conditions
Stop failed gates, main/dependency/protection drift, unexpected changes or scope
expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push and stacked PR against codex/m4-plan-comparison-summary.
No main/force push or merge. Final PASS/CHANGES_REQUIRED/BLOCKED packet includes
actual Goal/base/head/files/tests/acceptance/protections/refs and hosted state.
