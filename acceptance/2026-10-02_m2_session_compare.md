# Cross-session comparison acceptance

Goal: agent/goals/2026-10-02_m2_session_compare.md.
Base origin/main dd0f6583e8c58a16bafabcb48203dea3769fc42f;
task branch codex/m2-session-compare, own execution without DSH/delegation.
Commit/head/PR/hosted checks and final merge are independently inspected after
submission and reported in the final evidence packet; no prospective CI claim.

Seven files: this acceptance, Goal, agent/record/2026-10-02_02-m2-session-compare.md,
README.md, src/ashare_research/tools/session_compare.py,
src/ashare_research/tools/research_entry.py, tests/test_session_compare.py.
Complete input verification + canonical regeneration, explicit selected views,
full requests/dates/scopes/digests, added/removed selector keys, public original
common-key comparison and full byte-exact input records. Different scopes or
absent requested views reject; direction arbitrary; missing values remain null.
No financial arithmetic, data fetching, default DB changes or research admission.

Exact local commands (owned worktree; PYTHONPATH=src; python resolves explicitly
to D:/量化分析/.venv/Scripts/python.exe):

```powershell
python -m pytest -q tests/test_session_compare.py
python -m ruff check src/ashare_research/tools/session_compare.py src/ashare_research/tools/research_entry.py tests/test_session_compare.py
python -m ashare_research.cli research compare --left tmp/m2-research-session --right tmp/m2-research-session --right-view compare_with --output tmp/m2-session-compare
python -m ashare_research.cli research session --verify tmp/m2-session-compare/left
python -m ashare_research.cli research session --verify tmp/m2-session-compare/right
git diff --check
```

Scoped Ruff passed after one E501 line split before the test run. Four-case pytest
4passed in103.35s, no skips; one run, no full local suite or repeated tests.
Actual export exit0,50managed51total files; both nested verifiers exit0,
24verified files each, canonical root manifest and every byte compared.
Actual 2023 comparison2024-03-31→2025-03-31:7common keys,7value changes,
zero other states. Original cash FCF proxy17407700.000000000000→
17433900.000000000000万元; exact original engine results and inputs retained.

Artifact owned tmp/m2-session-compare (ignored, not committed):
- compare.md3371B SHA256f20ff2107ca98af28d4d9652f1721242bba14ada7f47cb397dc8580f2d68832f
- compare.json335572B SHA25607d2f801d782fd18abbf31193b7aa2c3364aab655e75e57439c70293e6ae136a
- manifest.json10555B SHA25697adfae6e950d98b40d04c2794f635ed3a8945f52faab5ca7e2858b6fa8de477

Known limits: full verification requires compatible installed pinned code/inputs;
outer manifest only inventory, not a new verifier/signature/authenticity proof.
Original common-comparison labels retained from existing engine; descriptive
categories do not infer causality. Missing source fields/66raw parents and
publication availability remain unresolved; no new financial research authorized.
Exclusive output safety, malformed/tampered inputs and portable evidence tested;
late filesystem errors may retain an owned partial output, never auto-delete.

Final review gates: expected branch/head and exact seven-file diff, clean worktree,
unchanged primary dirty/untracked snapshot/stash/DB/local main and protected hash
map; task origin0/0 and live main match; mandatory42checks success, clean merge
before standing-authorized merge. No automatic new data/research stage. Final
verdict pending actual targeted tests and hosted checks.
