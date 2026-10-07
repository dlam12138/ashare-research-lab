# Plan review summary acceptance

Goal: agent/goals/2026-10-07_m4_plan_review_summary.md.
Verified base codex/m4-plan-comparison-summary:
0b9c358ef2dea4b1d68da0a1b794795686238de8. PR81 OPEN/MERGEABLE with
36SUCCESS/4pending at initial query, not a complete hosted gate.
Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered plan --summary [--section ID (repeatable)] [--json] for the compile
mode and both verify modes. The compile mode compiles the hypothesis exactly
once and projects that captured report; --verify and --verify-archive fully
reproduce the delivered package or native ZIP exactly once through the
unchanged verifiers before any projection. The summary is a pure projection of
the captured report and adds no reads, extraction, writes, recompilation or
re-verification.

Section IDs are requirements/sample/condition/method/conditional/bootstrap/
robustness/evidence/holdout in that fixed canonical order; repeated sections
dedupe in canonical order and an omitted selector shows all nine. Section IDs
validate before IO: a bare --section is INVALID_ARGUMENTS, an unknown or
malformed section is INVALID_SECTION, and any selector combined with the
export modes (--output/--archive) is INVALID_ARGUMENTS, all before a path is
touched.

Identity (hypothesis_id, source_file_sha256, contract_state, plan_state,
contract_digest, plan_digest, source_config_digest, source_contract_digest),
shape counts (requirement roles, ordered term count, robustness entries,
bootstrap enabled, holdout authorized), boundary and notes are preserved
exactly; filters change only the projected section payloads. The projection
fails closed with PLAN_SUMMARY_MISMATCH when the captured report violates the
frozen invariants: schema/status, exact all-false boundary keys,
contract/plan hypothesis, digest and state consistency, unique requirement
roles, exactly one intercept and one condition-indicator term, response role a
requirement role, other term source roles exactly the other requirement roles,
and conditional summary source roles matching. Sanitized errors keep code2 and
empty stdout. New schema m4_compile_only_plan_review_summary_v1; Markdown is a
compact Chinese view with a per-mode source legend; no provenance, sealing,
readiness or execution claim. Without --summary the original JSON and default
Markdown stay byte-equal to the base CLI.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_research_plan_review_summary.py tests/test_research_plan.py tests/test_research_plan_package.py tests/test_research_plan_archive.py tests/test_research_plan_compare.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_plan.py src/ashare_research/tools/research_entry.py tests/test_research_plan_review_summary.py
git diff --check
python tmp/plan-review-summary/calculation_review.py
python tmp/plan-review-summary/demo.py
python tmp/plan-review-summary/verify_protections.py
```

Targeted24passed36.17s (nine new cases plus fifteen unchanged existing cases).
Final Ruff/diff PASS; no pytest failure, existing test edit or full local-suite
claim. Cases cover the exact projection across compile/directory/ZIP
transports, legacy JSON/Markdown byte-equality, repeated/reordered sections,
payload mapping, identity/shape/boundary preservation, one-read snapshot
handoff for compile plus both verify transports, invalid selectors and
export-mode rejection before IO, doctored-report invariant guards with
sanitized CLI failure, sanitized verifier failures (forged manifest-consistent
plan.json, corrupt ZIP, missing paths, monkeypatched reparse path) and
offline/no-write guards.

Actual subprocess demo: five legacy invocations are byte-equal to the base
worktree; the projected summary is identical across compile/directory/ZIP
modes except the mode source legend (COMPILED_ONCE /
VERIFIED_DIRECTORY_ONCE / VERIFIED_ARCHIVE_ONCE); filtering to method+holdout
shows exactly those payloads while identity, shape, boundary and notes stay
unchanged; repeated sections dedupe in canonical order; bare --section and an
unknown section reject before IO; a real Windows junction and a forged
plan.json with rewritten manifest both fail closed; six source hashes are
unchanged and summary runs created no files. JSON/Markdown/evidence retained
in tmp/plan-review-summary/demo/.

Independent AST review (tmp/plan-review-summary/calculation-review.json):
every pre-existing function/class except cli main in research_plan.py is
AST-identical to base; only the five projection helpers and cli main changed.
Before implementation captured48worktrees/47foreign states/27dirty hashes/
427protected hashes; protection review PASS:47foreign registrations/HEAD/
branches/statuses,27dirty hashes,427protected hashes, primary database/stash/
localmain unchanged and the preparation tools, plan comparison and plan
package/archive verifiers byte-equal to base. No comprehensive ignored-runtime
hash claim.

Seven-file scoped normal feature commit/push and stacked PR against81. Final
exact committed scope/head, clean owned tree, local/origin/live feature/
dependency/main refs, protections and exact-head hosted state independently
reviewed after publication, retained in
tmp/plan-review-summary/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending
checks remain pending; chain81->80->79->78->77->76->75->74->73->71->70->69->68
is unmerged. No automatic merge or following stage. Real research/statistics/
holdout sealed.
