# One-command verified ZIP delivery — acceptance checkpoint

Goal agent/goals/2026-10-03_m2_direct_zip_delivery.md; record
agent/record/2026-10-03_04-m2-direct-zip-delivery.md. Base live/origin main
a09e09c64d54fbe23350943962ab00eca05dc5af; branch codex/m2-direct-zip-delivery.
Own execution/no DSH/subagents. Checkpoint before commit/hosted gates; final
actual CI/merge/protection evidence retained in ignored tmp review packet.

Implemented research deliver --as-of DATE --output NEW_ZIP with comparison,
repeated year/metric and scope selectors plus JSON. Public deliver_workflow uses
only public export_workflow into owned temporary staging and public export_archive
for complete canonical verification before exclusive output creation. Early
existing-output/symlink ancestry rejection before build. Existing schema/receipt,
canonical handoff, deterministic archive bytes/errors/limits unchanged. No caller
intermediate path or additional files, default date, data acquisition, legacy
config/logging/default database initialization or changed research qualification.
Late output failure retains owned partial ZIP, sanitized error2/no success stdout;
never caller overwrite/cleanup or atomic publication claim.

Exact local validation, PYTHONPATH=src, owned worktree,
python executable D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_research_delivery.py
python -m ruff check src/ashare_research/tools/research_delivery.py src/ashare_research/tools/research_entry.py tests/test_research_delivery.py
python -m ashare_research.cli research deliver --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-direct-delivery.zip --json
git diff --check
git diff --exit-code a09e09c64d54fbe23350943962ab00eca05dc5af -- reports config events evidence src/ashare_research/mechanism tests/fixtures
```
Two targeted acceptance cases passed in48.56s on the first run. No corrections,
reruns, new skips, existing test changes or local full suite. Scoped Ruff and
diff/protected checks passed. Independent source/entry/README/Goal inspection
confirmed only public composition and unchanged earlier builders/verifiers.

Case1: real CLI131file ZIP with forbidden legacy config/logging, exact receipt
and ZIP bytes versus prior public workflow/export archive, source unchanged,
owned staging and all observed nested temporary roots removed, only caller ZIP
created. Actual subprocess80file delivery forwards explicit date, two years,
two existing metrics and scope; direct ZIP verifier returns exact receipt.
Full131file restoration equals every original relative path and byte.
Case2: existing foreign file/directory and symlink ancestor reject before any
builder; parser errors/bad date; propagated source build failure; staged manifest
tampering rejected by actual public archive verifier before caller output;
injected actual exclusive ZIP write failure retains exactly three own ZIP bytes,
sanitized OUTPUT_WRITE_FAILED/no success and foreign file/directory preserved.

Actual retained direct delivery ZIP tmp/m2-direct-delivery.zip created successfully:
131files/6,210,409ZIPbytes; status archived, original workflow ZIP SHA256
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561;
manifest SHA2567889bea763c849fcf194dd95c87b32802fe53b4e381af616e15398e15212d973.
Receipt tmp/m2-direct-zip-delivery-result.json. Previous artifacts preserved.
Primary original branch/status/diff/HEAD/localmain/stash/database tool snapshot
exactly unchanged; protected427paths/hashes and tracked baseline unchanged.

Compatible installed fixed baseline remains necessary; verification does not
prove authenticity, historical availability or research/production qualification.
Known33facts/66missingparents and provider historical evidence gaps unchanged.
No deviations or implementation blockers. Commit/push only seven allowed files;
all42hosted gates and exact base/head/CLEAN mergeability/independent review before
standing-authorized merge. Another stage requires user authorization; no automatic
next stage/new data/real research/backtests/holdout or production admission.
