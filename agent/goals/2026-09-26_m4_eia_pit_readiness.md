# Goal: offline EIA PIT evidence readiness

User requested project continuation after PR #29 merged. Objective: identify
the precise evidence gap between the successful transport probe and historical
research admission; produce an executable offline assessment and tested report.

Baseline: origin/main/live main 487a8bf5aaccfa368b8e0aed822f710b15917903;
new branch codex/m4-eia-pit-readiness at that commit, initially clean.
Protected M2 HEAD 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f;
DB SHA256 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Allowed: this Goal/record, agent/tools/assess_eia_pit.py and synthetic unittest,
evidence/m4/eia_pit_readiness_01.json, and a concise next-evidence plan.
Official documentation discovery allowed; no API/observation requests, key
access, raw decryption, new prices, database, holdout research, source adapter,
contract relaxation, prior-artifact mutation, main push or merge.

Require strict JSON/dossier/proof and linked-file digest checks, recognition of
transport-only scope, field inventory for publication/availability/revision/
vintage, deterministic structural reasons, and a constant closed research gate.
The diagnostic must not accept a forged readiness flag or assert that absence
from this evidence proves that EIA offers no historical archive anywhere.

Tests: python -m unittest discover -s agent/tools -p test_assess_eia_pit.py;
python agent/tools/assess_eia_pit.py --check;
python agent/tools/validate_eia_artifacts.py; git diff --check;
git diff --cached --check; protected state and origin/live branch checks.
Scoped DSH review, parent verification, single commit/push and draft PR.
Acceptance is a correct tested readiness diagnostic; historical research
remains blocked until independent first-party PIT/version evidence is supplied.
