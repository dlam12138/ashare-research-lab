# Offline workflow acceptance checkpoint

Goal agent/goals/2026-10-03_m2_offline_workflow.md; record
agent/record/2026-10-03_01-m2-offline-workflow.md. Verified origin/live main base
3a2abd2ec59929066fde2819a0331a26d67f1af1; task codex/m2-offline-workflow.
Own execution, no DSH/subagents; eight allowed files only.

One command assembles original session/review/audit packages and optional
as_of/compare_with comparison through existing public builders/exports. Original
nested bytes/formats preserved; 80/131 files, relative-link root index, canonical
manifest and normalized request. Whole-package verifier rebuilds the workflow
from selectors, compares exact layouts and every file including full root
manifest; arbitrary inventory paths never determine reads. No previous builders,
calculations, tests, sources, database/cache, research admission or data acquisition
changed. Prebuild complete bytes, reject existing output before build and before
exclusive creation; symlink ancestry rejected. Late writes retain owned partial
directory and return errors; directory publication is explicitly not atomic.

Exact commands: owned worktree, PYTHONPATH=src, python executable
D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_research_workflow.py
python -m ruff check src/ashare_research/tools/research_workflow.py src/ashare_research/tools/research_entry.py src/ashare_research/tools/package_verification.py tests/test_research_workflow.py
python -m ashare_research.cli research workflow --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-offline-workflow
python -m ashare_research.cli research verify --package tmp/m2-offline-workflow --json
git diff --check
git diff --exit-code 3a2abd2ec59929066fde2819a0331a26d67f1af1 -- reports config events evidence src/ashare_research/mechanism tests/fixtures
```

Four targeted cases passed95.71s, no skips, one run; no local full/repeated suite.
Scoped Ruff and diff checks passed; protected Git diff empty. One E501 wrapped
before testing. Tests independently verify all four nested package kinds, every
embedded session identical, deterministic rebuilt byte map,80/131file layouts,
valid navigation, moved actual root CLI, no legacy configuration/logging, sanitized
invalid args/errors2/no partial stdout. Rehashed index and nested report forgery,
root request tampering/traversal inventory rejected; foreign bytes preserved.
Output guard precedes build; invalid request/prebuild failure creates no output;
existing/symlink ancestor output preserved; injected late failure retains only
owned partial output and preserves foreign content. Actual links where privilege
permits, reported-link guard fallback otherwise, no new skipped test.

Actual 131-file two-date delivery and verification exit0;6,188,743totalbytes.
Complete manifest SHA256
7889bea763c849fcf194dd95c87b32802fe53b4e381af616e15398e15212d973.
JSON stdout retained tmp/m2-offline-workflow-verification.json; navigation at
tmp/m2-offline-workflow/index.md. All known historical gaps/33facts/66missing
parents preserved; installed compatible baseline required, authenticity and
historical availability proof false. No signature or new research conclusion.

Primary full status/diff/refs/stash/database snapshot unchanged. Database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Protected427file path/hash inventory unchanged; digest
0BBAB36862ECEE2F980069CB40D059C19A916727316C9B5487502338839FF476.
Primary branch3679b1b/stashcb568efd/localmain966206f and foreign artifacts preserved.

This checkpoint precedes commit. Actual PR/head/42hostedchecks/merge/protection
review outcomes go in the final ignored review packet. All required checks must
pass, expected base/head and clean mergeability required before standing-authorized
merge. Stop on gate failure/conflict/scope expansion. Engineering continuation
allowed; new data/real research stage unauthorized. No automatic next stage.
