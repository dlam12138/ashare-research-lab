# Native reproducible preparation ZIP delivery

## Objective
Root directly adds prepare-package --archive PREPARATION_DIR --output NEW_ZIP
and --verify-archive ZIP, sharing original preparation reproduction without
extraction or statistics. No DSH/delegation; user continuation authorizes scope.

## Verified baseline
origin/live codex/m4-preparation-package:
3378090ff895cea428c628deb0794cf4a74afedf. PR75 OPEN/MERGEABLE;
22SUCCESS/13pending at latest check, not a complete successful hosted gate.
main8d0fb4d unchanged, unmerged chain75->74->73->71->70->69->68.
Fresh clean codex/m4-preparation-archive at3378090.
tmp/preparation-archive/baseline.json captured42worktrees/27dirty hashes/
427protected hashes, primary3679b1b/localmain966206f/stashcb568efd and DB SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

## Allowed scope
Eight files: this Goal, matching acceptance/record, README.md,
src/ashare_research/tools/{preparation_archive,preparation_package,research_entry}.py,
tests/test_preparation_archive.py. Ignored validation/demo artifacts allowed.

## Forbidden scope
Existing tests, schemas/compilers/adapter/matrix/executor/registry/quality gates,
source preparation/projector/plan verifiers, protected data and CI; source
acquisition, real research/holdout/statistics, input/digest repair, extraction,
temporary reconstructed packages, source writes, foreign worktrees/stash/DB,
main/force push/merges/destructive cleanup.

## Required behavior
Expose original directory-package snapshot reader and byte-file verification
as public helpers with unchanged reconstruction and exact legacy receipts.
Archive ten fixed flat regular members, sorted, uncompressed, fixed timestamp/
attributes; no extras/comments/ZIP64/encryption/data descriptors/prefix/trailing
content. Only the native format is supported, not arbitrary third-party ZIPs.
Bound raw archive by64MiB plus exact fixed transport overhead; source files1MiB,
other artifacts16MiB, total unpacked64MiB. Preflight EOCD/count/central size/
offset boundaries before ZipFile member allocation. Validate member inventory,
sizes/type/flags/method/CRC, then byte-equal re-encoding enforces canonical layout.
Always invoke shared complete plan recompilation/preparation reproduction and
every-file comparison before reporting success. Forged inner inventory cannot
validate changed reports. Reuse captured source files/archive bytes once, no
source rereads/extraction/path restoration. Quality rejection remains rejection.
Reject existing, linked/reparse paths/ancestors and output within source directory
including ..aliases. All validation before exclusive-create output. Failed owned
partial ZIP preserved, no overwrite/delete/success receipt. Not atomic publication
or a hostile concurrent filesystem sandbox.
Original identities/read boundaries and false execution/statistics/source-auth/
research-ready/holdout boundaries preserved. SHA/count receipt is consistency,
not provenance, authorship or independent sealing. No paths/timestamps in reports.
Directory commands unchanged; invalid flags/errors code2/sanitized/no partial stdout.

## Required tests and exact validation commands
PYTHONPATH=src, Python D:/量化分析/.venv/Scripts/python.exe:
python -m pytest -q tests/test_preparation_archive.py tests/test_preparation_package.py
python -m ruff check src/ashare_research/tools/preparation_archive.py src/ashare_research/tools/preparation_package.py src/ashare_research/tools/research_entry.py tests/test_preparation_archive.py
git diff --check
Actual CLI relocated ZIP reproduction/forgery and Windows junction rejection;
independent protection/scope/committed evidence review.
Cases: deterministic ZIP/unchanged bytes/ready versus rejected exact directory
receipt/once-read snapshots/offline guards; forged package, corrupt CRC/bytes,
wrong/duplicate/traversal names, compressed/link members, invalid/oversized/count/
prefix/trailing archives, preflight before allocation; invalid flags, existing/
linked/nested destinations and injected partial write failure preservation.

## Acceptance criteria
Eight-file scope, meaningful targeted tests/Ruff/diff/demo pass.
41foreign tree identities/statuses/27dirty hashes/427protected hashes, primary
database/localmain/stash unchanged; owned clean/local-origin-live synchronized.
No full local suite claim; final-head hosted state independently reported.

## Stop conditions
Stop failed gates, dependency/main/protection drift, unexpected edits or scope
expansion. No automatic merge or following stage.

## Commit and push requirements
Scoped normal commit/push, stacked PR against codex/m4-preparation-package.
Explicit chain75->74->73->71->70->69->68; no main/force push/automatic merge.
Final PASS/CHANGES_REQUIRED/BLOCKED packet distinguishes local versus hosted checks.
