# Native preparation ZIP acceptance

Goal: agent/goals/2026-10-07_m4_preparation_archive.md.
Verified base codex/m4-preparation-package:
3378090ff895cea428c628deb0794cf4a74afedf, PR75 OPEN/MERGEABLE.
Live main remains8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b.
Root implemented and reviewed directly; no DSH/delegation.

Delivered research prepare-package --archive PREPARATION_DIR --output NEW_ZIP
and --verify-archive ZIP. Directory verification and archive verification share
the complete original plan recompilation, input preparation and exact ten-file
reproduction. Original directory receipts remain unchanged. Quality rejection
remains REJECTED_QUALITY with null matrix and unchanged execution boundaries.
Consistency is not provenance, independent sealing or research authorization.

ZIPs preserve original bytes with sorted ten regular members, stored encoding,
fixed1980 timestamp and0644 attributes. Verification reads the bounded ZIP once,
preflights raw length/EOCD/member count/central size/offset before member allocation,
checks inventory/type/flags/method/size/CRC, and requires canonical byte-for-byte
re-encoding. Only native layout is supported; compressed/encrypted/ZIP64/extra/
duplicate/traversal/prefix/trailing and noncanonical transport reject.
Content bounds remain1MiB/source,16MiB/artifact,64MiB/total plus fixed ZIP overhead.
No extraction, temporary reconstructed package, source writes or statistical runs.

All validation finishes before exclusive output creation. Existing, nested source
and linked/reparse destinations/ancestors reject. Partial owned writes remain
on failure with code2/sanitized stderr/no partial stdout. This is not atomic
publication or a hostile concurrent filesystem sandbox.

Actual commands use PYTHONPATH=src and Python D:/量化分析/.venv/Scripts/python.exe:

```powershell
python -m pytest -q tests/test_preparation_archive.py tests/test_preparation_package.py
python -m pytest -q tests/test_preparation_archive.py
python -m ruff check src/ashare_research/tools/preparation_archive.py src/ashare_research/tools/preparation_package.py src/ashare_research/tools/research_entry.py tests/test_preparation_archive.py
git diff --check
python tmp/preparation-archive/demo.py
python tmp/preparation-archive/verify_protections.py
```

Initial targeted8passed6.55s; review moved shared reproduction outside ZIP parser
exception translation so original stale-evidence error codes remain unchanged,
then affected4passed3.44s. Ruff/diff PASS; no failed pytest or modified existing
tests. No full local suite claim.

Four tests cover ready/rejected exact legacy receipts and original bytes;
deterministic ZIPs, offline/no-executor/no-extraction guards and once-read source/
ZIP mutation handoff; forged report/inventory, stale evidence, malformed layouts,
CRC/size/count limits before allocation; invalid flags before IO, existing/nested/
linked destinations and preserved partial write failures.

Actual CLI demonstration exports twice to identical59588-byte ZIPs, relocates
and directly reproduces the full directory receipt with REJECTED_QUALITY,
3/4 coverage and null matrix. SHA256:
80155ddadde8891a2ba37d23f99b948018c7e339363db76af2d48a2d3ee536aa.
Updated forged inventory fails PREPARATION_PACKAGE_MISMATCH. Actual Windows
junction read and output-parent paths fail LINKED_PREPARATION_PACKAGE_PATH.
Sources and valid ZIPs remain byte-identical; direct verification creates no files.
JSON/Markdown/evidence retained in tmp/preparation-archive/demo/.

Independent protection review PASS:41foreign registrations/HEAD/branches/statuses,
27dirty hashes,427protected hashes, stash/localmain/primary database unchanged.
Original synthetic preparation, diagnostics, plan directory/ZIP verifiers and
comparison modules remain byte-equal to base. No comprehensive ignored-runtime
hash claim. Eight-file implementation scope; final committed scope, clean owned
worktree, remote refs and exact-head PR/hosted checks are independently recorded
after publication in tmp/preparation-archive/final-evidence.json.

Local acceptance PASS subject to final publication review.
Pending hosted checks are not successful checks. Stacked dependency chain
75->74->73->71->70->69->68 remains unmerged. No automatic merge or next stage.
