# Verified package byte comparison — acceptance checkpoint

Goal agent/goals/2026-10-03_m2_package_byte_diff.md; record
agent/record/2026-10-03_05-m2-package-byte-diff.md. Base live/origin main
0aa7bf4f15d13a0dc7e49c18a3f64f9b53e24841; branchcodex/m2-package-byte-diff.
Own execution/no DSH/subagents. Precommit checkpoint; final actual hosted/merge/
protection review retained in ignored tmp evidence packet.

Implemented research diff with mutually exclusive directory/archive input per
side and JSON option; public compare_packages. Fresh public load_verified_archive
returns compatible verified receipt/canonical byte map, metadata-only wrapper
unchanged; restore unchanged. Both sides fully verified before comparison, same
kind required, sorted union/exact bytes classify added/removed/changed/unchanged,
counts/same_content and per-side length/SHA. ZIP encoding differences ignored for
content state but original ZIP digest shown. Existing full verifier metadata/
limitations retained. Read-only caller paths, owned temporary ZIP decoding, no
cache/second retained read or financial calculations/qualification changes.
Existing financial compare entry remains untouched.

Exact local commands with PYTHONPATH=src and
D:/量化分析/.venv/Scripts/python.exe in owned worktree:
```powershell
python -m pytest -q tests/test_package_byte_diff.py
python -m pytest -q tests/test_package_byte_diff.py::test_invalid_inputs_tampering_and_canonical_handoff_never_reread
python -m ruff check src/ashare_research/tools/package_byte_diff.py src/ashare_research/tools/package_archive.py src/ashare_research/tools/research_entry.py tests/test_package_byte_diff.py
python -m ashare_research.cli research diff --left-archive tmp/m2-offline-workflow.zip --right-archive tmp/m2-direct-delivery.zip --json
git diff --check
git diff --exit-code 0aa7bf4f15d13a0dc7e49c18a3f64f9b53e24841 -- reports config events evidence src/ashare_research/mechanism tests/fixtures
```
Initial two-case suite1failed/1passed133.70s. Exact final assertion in the new
failure case incorrectly expected INVALID for non-JSON manifest bytes; existing
public verifier correctly reports VERIFY_MANIFEST_UNREADABLE on JSON decoding
failure. Corrected exact expected code, no product change/guard weakening/old
test edit. Only affected failure/handoff case rerun:1passed40.63s.
Four E501 lines wrapped before first tests; scoped Ruff and diff/protection pass.
No local full suite, repeated whole targeted suite or introduced skip.

Case1 covers six actual package kinds with directory/ZIP exact equality and full
metadata; independent131vs80workflow relative paths/bytes/digests and51compare
file removals, reverse direction51additions, changed/unchanged counts, exact SHA/
sizes of every present before/after file. STOREDvsDEFLATED same content despite
different archive SHA. Fresh public loader receipt/map compatibility and returned
map isolation; readable CLI with forbidden legacy config/logging, actual JSON
subprocess equals API report; all source files unchanged, no caller output created.
Case2 covers invalid combinations before reads/no output option, unlike kinds,
malformed/CRC/traversal/invalid-manifest/rehashed forged-report ZIP rejection with
no success stdout and no foreign mutation; verified canonical handoff consumed
once per side despite post-handoff retained source mutation, fresh later call
rejects now-invalid source. No source cache, bypass, new financial interpretation.

Actual retained ZIP-to-ZIP diff exited0: workflow/131files; added0/removed0/
changed0/unchanged131/same_content true. Both original ZIP hashes unchanged:
4cf2b85032b1af9fab9a7e91a5a06f1cf033c03552d3f920a2b6a43c95ae9561.
Receipt tmp/m2-package-byte-diff-result.json. Primary raw branch/status/diff/refs/
database snapshot exactly unchanged; stashcb568efd/localmain966206f/HEAD3679b1b,
protected427hashes and tracked baseline unchanged. Prior artifacts preserved.

Compatible installed fixed baseline required. File difference is not financial
fact/revision provenance or economic meaning; authenticity/history/research and
production qualification not proved. Known33facts/66missingparents/provider gaps
unchanged. No scope expansion/implementation blocker. Eight-file commit/normal
push, all42hosted gates and independent exact base/head/CLEAN mergeability/
protection review before standing-authorized merge. Another stage needs user
authorization; no automatic next stage/new data/real research/backtests/holdout.
