# Complete package verification acceptance checkpoint

Goal agent/goals/2026-10-02_m2_package_verification.md; record
agent/record/2026-10-02_04-m2-package-verification.md. Verified base origin/live
main7e72d2c4e029bf01ed4fe84b93d81af6be0961a5; task branch
codex/m2-package-verification. Own execution, no DSH/subagents.
Seven changed files: this acceptance; Goal; record; README.md;
src/ashare_research/tools/package_verification.py;
src/ashare_research/tools/research_entry.py; tests/test_package_verification.py.
Prior tools/engines/tests/fixed sources untouched.

One command recognizes value/session/review/audit/compare root schemas. Uses
public existing fixed builders/exports or fresh verified-session loader, only
fixed input subdirectories, temporary owned output roots. Checks links before
manifest read and again after regeneration; rejects missing/extra file/directory
layouts. Every file and complete root manifest compared byte-for-byte, never
trusting declared hashes or using recorded arbitrary paths for reads. No supplied
input mutations/cache/network/default DB. Original view inventories unchanged;
new command separately establishes reproducibility against installed baseline.

Exact local commands, owned worktree, PYTHONPATH=src, python explicitly
D:/量化分析/.venv/Scripts/python.exe:
```powershell
python -m pytest -q tests/test_package_verification.py
python -m ruff check src/ashare_research/tools/package_verification.py src/ashare_research/tools/research_entry.py tests/test_package_verification.py
python -m ashare_research.cli research verify --package tmp/m2-session-compare-reused --json
python -m ashare_research.cli research verify --package tmp/m2-research-review
python -m ashare_research.cli research verify --package tmp/m2-evidence-audit
git diff --check
```
One targeted run4passed55.35s/no skips; no repeated or full local suite. One I001
import ordering fixed before tests; final scoped Ruff and diff checks passed.
All five actual fixed package kinds verified in tests:12/24/27/27/51files, input
file bytes unchanged. Portable moved51file package verified with real root CLI;
no legacy config/logging initialization; failures sanitized/error2/no stdout.
Rehashed forged outer Markdown/JSON rejected despite nested session verification
success. Root metadata/view forgery, traversal inventory, missing/extra layout,
unknown schema and link guards exercised; foreign file bytes preserved. Actual
symlink where platform permits, reported-link path guard on hosts without link
privileges; no new skipped acceptance case.

Actual CLI exit0 for retained compare51files2619768totalbytes, review27files,
audit27files. Complete canonical manifest and every byte matched. Original hashes:
- compare97adfae6e950d98b40d04c2794f635ed3a8945f52faab5ca7e2858b6fa8de477
- review05dedead89e95f8d1c4518d2791b2a3463505b8b9c88515fa7306966794a70d2
- auditb20f9266004588f3abfa2d1ceacc6838c5d1a7b78e416e558af8bef397bfc21e
Actual compare JSON stdout retained as tmp/m2-package-verification-result.json
(ignored evidence artifact, not tracked). Publication/authenticity proof false;
installed pinned baseline required. No financial/source/research changes.

Final hosted outcomes/head/PR/merge and protection review pending in this
commit-time checkpoint; final packet records actual outcomes. Gates: exact
seven-file scope, expected base/head, clean task worktree and origin0/0, primary
status/diff/untracked/stash/localmain/DB and protected hash map unchanged,
42required checks successful/clean mergeability before standing-authorized merge.
Known historical gaps/33facts/66missing parents remain; no signature/authenticity
or admission judgment. Engineering continuation allowed, new data/research not.
