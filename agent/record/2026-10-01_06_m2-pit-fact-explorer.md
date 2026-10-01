# M2 dated financial fact explorer

2026-10-01; parent Codex; user continuation and larger functional batches/fewer
tests. M2/value assessment engineering. Goal:
agent/goals/2026-10-01_m2_pit_fact_explorer.md.
Base main 9db39e8520f733966c0357b4367c696145d4c7e4;
branch codex/m2-pit-fact-explorer, initially clean.

Parent verified actual refs/worktree/remotes/stash/primary dirty state/DB and
protected files; read governance/routing/recent records and public snapshot/PIT
interfaces. Existing report bundle compiles mixed historical dates; new batch
offers explicit dated fact selection and version comparison using the retained
33-row canonical snapshot. Five existing concepts, one existing company, no new
source admission. Exact retained decimal values and unresolved parent evidence
must remain visible; historical snapshot metadata is not newly verified timing.

Plan: one bounded DSH implements module/four-to-five targeted tests/README;
parent independently reviews, runs minimal meaningful validation, exports usable
comparison, records results and handles task PR/required hosted gates. No full
local regression duplication. Public PIT engine reused rather than another gate;
temporary owned DB rather than user DB; missing source parents disclosed rather
than fetching or manufacturing source evidence. Status: local PASS; hosted gate
pending at this commit.

DSH wrote exactly the three implementation paths but its initial headless run
ended exit1 without final report; reason unknown. Parent stopped delegation and
used one bounded read-only completion audit retry (exit0, frozen). No fallback
model, recursive delegation, worker tests or helper files observed. Worker audit
did not inspect content sufficiently; it is not acceptance evidence.
Parent independently read actual implementation/tests/README, corrected missing
scope column adaptation (public engine filters context scope but returns f.*),
added tracing of both PIT dates with their own availability gates, preserved
original source fields and explicit missing references, and distinguished period
context metadata from restated fact dates. Exact finite Decimal comparison.

Initial five-case run: 4 failed/1 passed due missing scope column; scoped Ruff
found three long Markdown lines. Corrected adapter and formatting. Next run:
2 failed/3 passed: worker expected six numerical changes instead of five.
Independently read source rows: 2022 profit restatement already available at
2024-03-26, before requested 2024-03-31, so five 2023 values change, eleven
stay unchanged, five 2024 facts are added. Corrected fixture expectation without
weakening required behavior. Final same five cases: 5 passed in 25.55s; scoped
Ruff and diff check passed. No full local regression repeated; hosted retains it.
Actual CLI export: three files, two managed, 19844 managed bytes; 2023 profit
16114400.000000000000 -> 16141400.000000000000 万元 with both fact IDs/dates,
contexts/lineage and four unresolved parent references across the two views.
Primary exact dirty snapshot/protected hashes/DB/stash/local main preserved.
Acceptance file has exact commands, artifact digests, risks and delivery gates.
