# Compile-only plan ZIP delivery

Status: completed (local implementation and acceptance; hosted CI separate).

User continuation authorizes this bounded task; root implements directly without
DSH. Verified live base/main, isolated clean HEAD and primary/foreign status,
stash and protected hashes before implementation. Baseline captured in
tmp/archive-baseline.json; contract in
agent/goals/2026-10-08_m4_user_plan_archive.md.

Inspected actual package compiler/capture code, research dispatch, existing tests,
README, predecessor Goal and record guidance. Chosen deterministic stored ZIP:
direct captured-byte reproduction, bounded metadata parsing, no extraction.
Shared package helpers preserve existing directory verification receipts.
Stacked PR depends on open PR89; no merge authorized.

Implemented research plan-archive export/direct verification, shared captured
package verification, lazy entry dispatch and README examples. Only canonical
stored ZIP supported: bounded whole-file/EOCD/central metadata, four fixed
members, fixed metadata, captured-byte recompile and exact archive reproduction.
No extraction, data loading or execution. New outputs use exclusive creation,
managed path rechecks and readback; late failures retain owned partial files.

Validation with PYTHONPATH=src and D:/量化分析/.venv/Scripts/python.exe:

    python -m pytest -q tests/test_research_plan_archive.py tests/test_research_plan_package.py tests/test_research_plan.py tests/test_research_entry.py

Initial 45 passed in 44.42s; review added a late readback mutation case, then
archive-only 32 passed in 2.41s. Final exact combined command: 46 passed in
45.76s, retained in tmp/archive-pytest-final.txt.

    python -m ruff check src/ashare_research/tools/research_plan_archive.py src/ashare_research/tools/research_plan_package.py src/ashare_research/tools/research_entry.py tests/test_research_plan_archive.py
    git diff --check

Ruff initially found one overlong test line; corrected without changing existing
tests. Final Ruff and whitespace gates pass.

Public subprocess commands, all exit 0 with empty stderr:

    python -m ashare_research.cli research plan-package --hypothesis docs/examples/m4_hypothesis.json --output tmp/archive-demo/package --json
    python -m ashare_research.cli research plan-archive --package tmp/archive-demo/package --output tmp/archive-demo/plan.zip --json
    python -m ashare_research.cli research plan-archive --verify tmp/archive-demo/plan.zip --json

Actual demo used absolute output paths; full exact argv and three receipts are
retained in tmp/archive-demo/evidence.json. ZIP: 19741 bytes, SHA256
19310fbc1d4a866e4ec9e4abecd75f65b884a0c74aeda720d662105c7026099e.
Original source bytes preserved, manifests match, six execution/evidence boundary
flags false. Tests also cover source/archive mutation after capture, forged
reports with recomputed hashes, malformed EOCD/member metadata, collisions,
junctions, parent swaps and no network/database/executor/extraction access.

Independent review inspected actual source, diff, scoped file list, original
directory behavior, Goal and validation evidence. Fresh protection review:
1355 hashes, 56 foreign tree states, primary HEAD/dirt and stash all unchanged.
Local/origin/live main and PR89 base still match the verified baseline.
Final commit, synchronization, PR and hosted check snapshot are recorded after
push in ignored tmp/archive-final-review.json; inspect actual Git refs.

No scope deviation or unresolved local failure. PR89 is an unmerged dependency.
Compatible original compiler/renderer required; arbitrary third-party ZIPs
rejected. Path checks use existing package guards; they do not provide OS-level
isolation from concurrent hostile filesystem replacement. No merge or automatic
next stage authorized.
