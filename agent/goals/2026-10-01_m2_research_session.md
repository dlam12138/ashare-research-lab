# Complete offline research session archive

Objective: one dated command assembles existing fixed value bundle, full PIT
facts and selected annual metric replay with retained source attachments,
navigation index and reproducibility verifier. This is existing M2 engineering,
not new data, methodology or a newly authorized research stage.
Verified base: origin/live main27ef45753fac5631badadc524c3b485c5c96e4a7;
owned clean worktree D:/量化分析-worktrees/量化分析-capsule-postmerge-acceptance,
branch codex/m2-research-session. Preserve primary feat/m2-value-assessment-mvp
HEAD3679b1bac7a1634c6452784a4d8f6d139966f222 and exact dirty/untracked state,
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, local main966206f and DB hash
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Allowed: new src/ashare_research/tools/research_session.py;
src/ashare_research/tools/research_entry.py; tests/test_research_session.py;
README.md; this Goal; agent/record/2026-10-01_09-m2-research-session.md;
acceptance/2026-10-01_m2_research_session.md. One bounded DSH task writes the
new module only. Parent owns entry integration, tests, docs, records and Git.
Forbidden: prior report implementations/engines/definitions/old tests, fixed
reports/config/events/evidence/mechanism/fixtures/DB/runtime modifications;
network/source acquisition/messages, new metrics/scores/ranks/claims, actual
backtests/holdout/registry admission, recursive delegation or fallback models.

Required API: build_session(request) -> dict[str,bytes] containing complete
canonical archive including manifest.json; export_session(request,output Path)
-> manifest dict; verify_session(directory Path) -> JSON-compatible result;
SessionError.code and main(argv) -> int. Use metric_replay.validate_request
and public build/export APIs only; facts uses full concepts/no period filter.
Retain original bundle12 files under value/, facts3 under facts/, metrics3 under
metrics/, four byte-exact pinned canonical files under snapshot/, index.md and
root manifest.json:24 files,23 managed. Compose in owned TemporaryDirectory,
read fixed public pin map/root; never patch global source roots. Render all
components/index/manifest before final root creation; exclusive mkdir and reject
existing file/dir/symlink before mutation. Late IO may leave owned partial output.
Deterministic bytes, no timestamps/absolute machine paths, all nested manifest
and source bytes unchanged. Index has relative links and explicitly separates
mixed-date value compilation from dated facts and metrics read model. Preserve
33facts/66missing parents, historical publication/version limits and proxy caveats.

CLI research session --as-of YYYY-MM-DD [--compare-with DATE] [--year repeated]
[--metric repeated] [--scope consolidated|parent_company] --output NEW_DIR;
alternative --verify DIR only, no selectors allowed in verification mode. Error2,
sanitized code on stderr, no partial stdout. No implicit current-date query.
Verification must reject malformed request/manifest, missing/extra files,
symlink files/directories, rehashed altered report/metadata/source. Read paths
from fixed expected layout, never trust arbitrary manifest paths. Regenerate
canonical archive from validated request and installed pinned baseline/definitions,
then compare every retained byte and complete manifest; not hash-only verification.
Explicitly requires installed compatible repository baseline/code, and proves
reproducibility/integrity, not historical availability or authenticity/signature.

Exact minimal local commands (owned worktree, PYTHONPATH=src, primary venv):
python -m pytest -q tests/test_research_session.py
python -m ruff check src/ashare_research/tools/research_session.py src/ashare_research/tools/research_entry.py tests/test_research_session.py
python -m ashare_research.cli research session --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-research-session
python -m ashare_research.cli research session --verify tmp/m2-research-session
git diff --check
Four meaningful cases: complete composition/exact child bytes and PIT semantics;
real export/relocation verification and selector identity; tampered/rehashed report,
source/manifest/extra/symlink denial; CLI/invalid selector/foreign-path/pre-render
source failure without output mutation. Parent one targeted run, repeat only
fixes; no full local regression. All mandatory hosted checks retained.

Acceptance: actual usable24file archive and verified relocated copy, four checks
and scoped lint pass, independent scope/diff/HEAD/protection review; clean branch
and local/origin synchronization. Commit/push task branch seven files only;
verify exact base/head, all hosted checks, clean mergeability then authorized merge
under standing tracked AGENTS rule. Never push main. Stop on CI/conflicts,
protection changes, source/methodology expansion, DSH failure/unavailability or
two failed repairs; report honestly, no silent model replacement. Final verdict
PASS/CHANGES_REQUIRED/BLOCKED with exact evidence packet. Further scoped
engineering allowed by continuation; new data or research stage not authorized.
