# CSV preflight acceptance

Goal: `agent/goals/2026-09-23_m4_csv_probe_preflight.md`.

Acquisition verdict: BLOCKED before network under
`REAL_LICENSE_EVIDENCE_MISSING`. User authorization remains valid; publisher
permission for software-development use and immutable retention is unresolved.
The previous licence clearance in commit `174d33a` must not be used for a CSV
request. The original transport successes and retained-byte identities remain
valid facts. No new dossier is created and the approved identity is unused.

Evidence: `evidence/m4/fred_csv_preflight_01.json`, corrected
`evidence/m4/provider_licence_artifacts_v2.json`, and the matching work record.
The retained legal source at lines 514, 571 and 778 contains the unresolved
restrictions and grant. This is an evidence sufficiency decision, not a legal
opinion about enforceability or a finding that API-specific terms necessarily
govern the graph CSV endpoint.

Reproduction: `python tmp/m4-provider-evidence-v2/validate_preflight.py` (local
ignored helper), `git diff --check`, `git diff --cached --check`, protected M2,
stash and database hash checks. Actual execution results belong to the record.
Raw data and the helper remain ignored; no observation values are tracked.

Next permissible work: offline planning; publisher clarification supplied by
the user, or a separately scoped and approved direct EIA source. Do not silently
substitute endpoints or treat another user approval as publisher permission.
