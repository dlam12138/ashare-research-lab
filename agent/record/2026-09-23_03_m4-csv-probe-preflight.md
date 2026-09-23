# M4 CSV probe preflight

Date: 2026-09-23. Parent: Codex; bounded reviewer: DSH. Module: M4 mechanism
verification / source evidence. Goal:
`agent/goals/2026-09-23_m4_csv_probe_preflight.md`.

Initial branch `codex/m4-fred-transport-diagnosis` at `174d33a594c496b106d163b1ffd5c376378bbb75`
was clean and matched origin and live remote. Main was `9c9ced9`.
The protected M2 worktree, stash and database byte hash matched the Goal.
Existing authorization covers one bounded historical CSV request; the user's
continuation is sufficient to progress this milestone without asking again.

Plan: independently review retained licence/identity material, run the bounded
probe only if all prerequisites pass, validate proof/dossier or record a
pre-network block, complete one scoped review and delivery.

## Finding under review

Retained FRED legal bytes (SHA256 `d69f84e9a2f8739fcaae5ce4d3bf50f6ab56c02fe904bf0dfeafc6f58bb8c3ac`)
contain a software-development/training restriction in their summary, in
addition to the personal-use grant and non-disruptive-access provisions.
The intended CSV request supports software-project development. Excluding model
training does not on its own resolve the broader wording. The parent therefore
withheld the CSV request and commissioned a bounded DSH review of the specific
clauses and existing NO_CONTRADICTION claim. This is a repository evidence-gate
decision, not a legal determination about enforceability.

No network request to a data provider has been made in this stage. No response
value, date, statistic, database content or holdout was accessed. Existing raw
licence pages are inspected only as permission evidence.

## Review and disposition

DSH returned CHANGES_REQUIRED on the earlier licence clearance. The parent
independently checked the retained personal-copy grant (line 571), summary
development restriction (514) and full-service archive/storage restriction
(778). Their applicability to a private transport-development probe is not
resolved by the retained evidence. The FRED licence and series artifacts now
state that uncertainty explicitly and supersede the review in `174d33a`.
Raw hashes, acquisition ledger and EIA evidence are unchanged.

Two DSH suggestions were not adopted: the original design's NOT_AUTHORIZED
label does not revoke the later explicit user authorization; and API-specific
terms cannot automatically be applied to graph CSV. DSH also encountered
one-line JSON truncation; the parent parsed the full files and recomputed their
digests. We classify this as REAL_LICENSE_EVIDENCE_MISSING, rather than a
definitive determination of forbidden use. Archive permission is unresolved
even for the prior retained FRED pages; no destructive removal was performed.

The dataset request count is zero. The CSV milestone is BLOCKED before network;
no proof or terminal dossier is fabricated. User authorization persists, and
repeating it would not resolve the publisher-evidence question.

## Validation and delivery

- `python tmp/m4-provider-evidence-v2/validate_preflight.py`: PASS; strict JSON,
  canonical serialization, authorization/contract digests, all licence fields,
  retained raw hashes/ignored locations, exact source clauses, zero-request
  disposition, unused dossier identity and unchanged protected tracked files.
- `git diff --check`: PASS.
- Protected default database SHA256 remains the Goal value; M2 HEAD and stash
  remain unchanged. No database connection was made.
- Changed files: this record, Goal, acceptance, preflight JSON and the corrected
  licence-artifact JSON. Ignored validation helper is local only.
- Commit/push the five paths together to the existing PR #29 branch. PR wording
  must report the licence block prominently. CI on `174d33a` is historical;
  it does not certify the new revision or publisher permission.

Next decision: obtain first-party clarification for FRED development/retention,
or authorize a direct EIA acquisition scope with exact endpoints and the same
historical evidence-only limits. EIA data ownership evidence alone is not a
FRED service permission. No new provider contact is part of this correction.
