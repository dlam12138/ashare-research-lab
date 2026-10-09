# Plan comparison section summary acceptance

Goal: agent/goals/2026-10-07_m4_plan_comparison_summary.md.
Verified base codex/m4-preparation-comparison-summary:
e427e5a1e3630063fc8abcdb4e7d2f47ff3aa8db. PR80 OPEN/MERGEABLE;
29SUCCESS/9pending at initial query, not a complete hosted gate.
Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly, no DSH/delegation.

Delivered plan-compare --summary [--section config|contract|plan (repeatable)]
[--json]. Both plans are still fully reproduced once per side through the
unchanged directory/ZIP verifiers before any projection; the summary is a pure
projection of the captured comparison report and adds no reads, extraction,
writes or diff recomputation. Section IDs validate before IO: --section without
--summary is INVALID_ARGUMENTS and an unknown or malformed section is
INVALID_SECTION, both before any plan file is touched; repeated sections dedupe
in canonical order.

Identity fields, equality flags, canonical_content_equal, change_count, the
global section change counts, boundary and notes are preserved exactly; filters
change only displayed change rows, and a selected section with no change yields
NO_MATCHING_CHANGES. Every change row must carry a known section and the
recomputed per-section counts and total must equal the captured globals or the
projection fails closed with COMPARISON_SUMMARY_MISMATCH; sanitized errors keep
code2 and empty stdout. New schema
m4_verified_compile_only_plan_comparison_summary_v1; Markdown is a compact
Chinese view; no plan-superiority, provenance, sealing, readiness or execution
claim. Without --summary original JSON and default Markdown are byte-equal to
the base CLI.

Actual exact commands use PYTHONPATH=src and
Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_research_plan_compare_summary.py tests/test_research_plan_compare.py tests/test_research_plan.py tests/test_research_plan_package.py tests/test_research_plan_archive.py tests/test_research_entry.py
python -m ruff check src/ashare_research/tools/research_plan_compare.py src/ashare_research/tools/research_entry.py tests/test_research_plan_compare_summary.py
git diff --check
python tmp/plan-comparison-summary/calculation_review.py
python tmp/plan-comparison-summary/demo.py
python tmp/plan-comparison-summary/verify_protections.py
```

Targeted21passed48.37s (six new cases plus fifteen unchanged existing cases).
Final Ruff/diff PASS; no pytest failure, existing test edit or full local-suite
claim. Cases cover the exact projection, legacy JSON/Markdown equality, all four
directory/ZIP transports, repeated/reordered sections, NO_MATCHING_CHANGES on a
canonically equal pair, global counts/identity/boundary preservation, one
verifier call per side with mutation-after-read handoff, invalid flags and
unknown sections before IO, doctored-report invariant guards with sanitized CLI
failure, offline/no-write guards and a real Windows junction rejection.

Actual subprocess demo: threshold change plus removed control yields10changes
(config2/contract2/plan6); the summary is identical across all four transports;
filtering to config+plan shows8rows while global counts and identities stay
unchanged; a format-only re-serialization is canonically equal and reports
NO_MATCHING_CHANGES with zero counts; --section without --summary and an unknown
section fail before IO; a real junction and a forged plan.json with rewritten
manifest fail closed;11source hashes unchanged and summary runs created no
files. JSON/Markdown/evidence retained in tmp/plan-comparison-summary/demo/.

Independent AST review (tmp/plan-comparison-summary/calculation-review.json):
every pre-existing function/class except cli main in research_plan_compare.py is
AST-identical to base; only the intended projection additions and cli main
changed. Before implementation captured47worktrees/46foreign states/27dirty
hashes/427protected hashes; protection review PASS:46foreign registrations/
HEAD/branches/statuses,27dirty hashes,427protected hashes, primary database/
stash/localmain unchanged and the compilers, plan/preparation verifiers and both
preparation comparison modules byte-equal to base. No comprehensive
ignored-runtime hash claim.

Seven-file scoped normal feature commit/push and stacked PR against80. Final
exact committed scope/head, clean owned tree, local/origin/live feature/
dependency/main refs, protections and exact-head hosted state independently
reviewed after publication, retained in
tmp/plan-comparison-summary/final-evidence.json.
Local acceptance PASS subject to final publication review. Hosted pending
checks remain pending; chain80->79->78->77->76->75->74->73->71->70->69->68 is
unmerged. No automatic merge or following stage. Real research/statistics/
holdout sealed.
