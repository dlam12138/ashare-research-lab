# Verified delivered-package byte comparison

Objective: compare two verified packages as ZIPs/directories without caller
restoration; identify added/removed/changed/unchanged canonical files. Latest
continuation authorizes this engineering stage; root own execution, no DSH/agents.
Verified base live/origin main0aa7bf4f15d13a0dc7e49c18a3f64f9b53e24841;
clean owned worktree D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance,
branchcodex/m2-package-byte-diff. PrimaryHEAD3679b1b/localmain966206f/stashcb568efd,
original dirty/untracked files and database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6 preserved.
Physical primary snapshot/protected427path-hash map saved tmp before implementation.

Allowed eight files: this Goal;
agent/record/2026-10-03_05-m2-package-byte-diff.md;
acceptance/2026-10-03_m2_package_byte_diff.md; README.md;
src/ashare_research/tools/package_byte_diff.py;
src/ashare_research/tools/package_archive.py;
src/ashare_research/tools/research_entry.py; tests/test_package_byte_diff.py.
Forbidden: existing tests/builders/package verifier/calculations/scoring/admission,
fixed inputs, new data or messages, persistent database/cache/holdout/real research,
foreign worktrees/runtime/ignored artifacts, main/force push/destructive cleanup.

Required: research diff (--left DIR | --left-archive ZIP)
(--right DIR | --right-archive ZIP) [--json]. Public compare_packages with explicit
side source types. Both inputs fully verified with fresh public loaders before
comparison. Add public load_verified_archive returning unchanged existing verified
receipt and fresh canonical byte map; verify_archive metadata wrapper compatible;
restore and all byte limits/errors unchanged. No cache or retained source reread
after canonical handoff; owned temporary decoding allowed, no caller destination.
All six kinds supported, unlike verified kinds rejected. Compare exact bytes,
not merely ZIP CRC/manifests/digests. Sorted union of relative paths; added/removed/
changed/unchanged states, counts, same_content, before/after SHA256 and byte sizes.
Archive encoding/compression differences do not count as package content changes.
Sides include complete existing verification metadata and optional ZIP digest,
no machine path/time. Schema m2_verified_package_byte_comparison_v1; readable
summary and deterministic JSON; changed rows indicate file bytes only, not new
financial facts, revision provenance or economic conclusions. Reuse original
baseline/authenticity/history/admission boundaries. Existing financial compare
command unchanged. Argument/source/layout/limit/content failures sanitized2/no
partial success; no output/export option, source or foreign path modification,
network/legacy config/log/default database initialization.

Required meaningful tests: six actual kinds directory/ZIP equivalence, bytewise
131vs80 workflow diff and reverse direction against independently read file maps;
ZIP_STORED vs DEFLATED same content; actual subprocess and readable CLI; fresh
map/receipt compatibility and source mutation after handoff not reread. Invalid
argument combinations before input reading, unlike kinds, directory tampering,
unsafe/corrupt/rehashed archive rejection/no caller mutation. Two bounded cases,
one targeted run, repeat only fixes; no local full suite. Exact commands with
PYTHONPATH=src, D:/量化分析/.venv/Scripts/python.exe in owned worktree:
python -m pytest -q tests/test_package_byte_diff.py
python -m ruff check src/ashare_research/tools/package_byte_diff.py src/ashare_research/tools/package_archive.py src/ashare_research/tools/research_entry.py tests/test_package_byte_diff.py
python -m ashare_research.cli research diff --left-archive tmp/m2-offline-workflow.zip --right-archive tmp/m2-direct-delivery.zip --json
git diff --check
git diff --exit-code 0aa7bf4f15d13a0dc7e49c18a3f64f9b53e24841 -- reports config events evidence src/ashare_research/mechanism tests/fixtures

Acceptance: six-kind exact equivalence, independent detailed diff/encoding
independence/error evidence, no source/caller changes, targeted/lint/diff checks
pass; actual retained131file ZIPs report all unchanged; eight-file scope and
primary/database/stash/protected427hashes unchanged. Commit/push scoped branch,
create PR. Actual independent commit/diff/Goal/acceptance review, exact base/head/
CLEAN mergeability and42successful required hosted checks across seven workflows
before standing-authorized merge. Final evidence actual commands/results, Git/
merge/refs/worktree/stash/protection/limitations. Stop on failure/conflict/protected
drift/scope expansion; no bypass. FinalPASS/CHANGES_REQUIRED/BLOCKED. Another stage
requires user authorization; no automatic next stage or real data/research/
backtest/holdout/production admission.
