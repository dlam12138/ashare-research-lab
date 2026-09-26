# EIA PIT readiness record

Goal: agent/goals/2026-09-26_m4_eia_pit_readiness.md.
Starting main 487a8bf, clean new branch codex/m4-eia-pit-readiness. Protected
M2, stash and database hashes match the Goal. PR #29 verified merged.

Read source contract and offline K1 kernel: publication/availability evidence
and revision/vintage identity are mandatory; ingestion time is not PIT evidence.
The existing K1 kernel remains synthetic-format-only; this task does not change it.

Documentation discovery reviewed EIA API documentation and release schedule.
API date filters address observation periods; the reviewed material does not
establish publication times or vintage identity for the five historical rows.
Search also returned current price-table snippets incidentally; those were not
opened as datasets, retained, parsed, quoted in artifacts or used in research.
No keyed request or new provider observation download was made.

Plan: implement a pure offline dossier/authorization assessment with strict
integrity checks, deterministic gaps, synthetic negative tests and a retained
report. Distinguish diagnostic completion from historical research readiness.

Implementation completed: metadata-only assessment validates dossier/proof and
allowlisted linked-file digests, retains a deterministic report, rejects forged
readiness claims and refuses to interpret added columns as historical evidence.
No raw values, decryption, credentials or provider requests are involved.

Validation: `python -m unittest discover -s agent/tools -p test_assess_eia_pit.py`
passed all 7 tests; `python agent/tools/assess_eia_pit.py --check` passed;
`python agent/tools/validate_eia_artifacts.py` passed; `git diff --check` passed.
Scoped read-only DSH review completed with no blocking defects reported.
Parent independently inspected implementation and reran the above checks.

Acceptance: the diagnostic is reproducible, preserves prior evidence and keeps
research admission closed. The missing publication/availability and historical
version evidence remains unresolved; this is not a historical backtest delivery.
Delivery is a single commit and draft PR; no merge or next-stage execution is
authorized by this record. Final commit/remote/PR status is reported at handoff.
