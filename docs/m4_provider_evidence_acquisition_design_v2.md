# M4 provider-evidence contract v2 amendment

Status: `ACQUISITION_V2_NOT_AUTHORIZED`.

This offline amendment defines `M4_PROVIDER_EVIDENCE_CONTRACT_V2` and the
future dossier identity `M4_PROVIDER_EVIDENCE_DOSSIER_V2`. It does not alter
the v1 dossier or manifest schemas, reopen a terminal dossier, select a
provider, contact a provider, acquire observations or authorize an adapter.
No current provider URL, availability, licence or terms fact is asserted or
verified here.

The canonical machine contract is
`../evidence/m4/provider_evidence_contract_v2.json`, with contract digest
`b5f6b8d54f5fe733d41ed018a89b3065fc05a0e7130c072c66d19e469221bdca` and source-tree digest
`ba13f31cff0c26f8438ac0398b0fdba5c439283f`.

## Why v2 exists

The four v1 dossier identities are permanently `REJECTED`. Documentation-only
acquisition could not satisfy bounded transport, and licence evidence remained
unproven. v2 does not relax either gate. It separates future procedural
authorization from current evidence and makes the minimum proof envelope
mechanically reviewable.

The three historical v1 codes keep their meanings:
`REAL_CALENDAR_VERSION_MISSING`, `REAL_ENDPOINT_UNBOUNDED`, and
`REAL_LICENSE_EVIDENCE_MISSING`. Their exact mappings appear in
`v1_code_mapping`. Future probe failure may additionally use
`REAL_HOLDOUT_INJECTION`, `REAL_LICENSE_SCOPE_FORBIDDEN`, or
`REAL_REDACTION_UNPROVEN` under the frozen triggers in `adopted_probe_codes`.

## Evidence classes and gates

`DOCUMENTATION_ARTIFACT` and `LICENCE_ARTIFACT` remain non-observation
evidence. `BOUNDED_TRANSPORT_PROBE` is only a future request class. Its presence
in this contract is not permission to run it. Every mandatory gate must pass;
null, missing, expired, contradictory or unretainable evidence fails closed.

First-party licence or terms material has the highest authority. First-party
documentation cannot override licence scope. Third-party material is discovery
only and cannot prove publisher identity, licence or support. A licence record
must resolve by stable ID and matching retained-byte SHA256. Use outside its
permitted-use or redistribution scope is `REAL_LICENSE_SCOPE_FORBIDDEN`.

## Probe firewall

A future user authorization must name the allowed HTTPS hosts, endpoints, dossier
identities, dates, fields, response-size ceiling, timeout, retry count, request
rate and raw-retention decision. The envelope is HTTPS/GET-only, no credentials,
one dossier per request, no pagination, at most four total requests and at most
four requests per minute.

Before a probe, a future authorized stage must discover and verify the current
first-party URL. Mirrors and silent provider substitution are forbidden.
Redirects are forbidden unless every hop remains inside the explicit allowlist;
any off-allowlist or ambiguous redirect fails closed.

The requested end date must be earlier than `2015-03-16`. Any returned date in
the frozen development interval `2015-03-16..2022-12-30` or on/after the
holdout boundary `2023-01-01` fails closed. Holdout exposure is
`REAL_HOLDOUT_INJECTION`; ambiguous/unparseable or otherwise out-of-window
dates are `REAL_ENDPOINT_UNBOUNDED`.

Returned bytes are evidence-only. They may be date-scanned and hashed for the
declared proof fields, but values cannot enter a tracked artifact, database,
statistic, aggregate, study or holdout flow. If raw retention is not permitted
or fails, the probe must not run or the new dossier is rejected with
`REAL_REDACTION_UNPROVEN`.

The specification-only `proof_digest` is SHA256 of UTF-8 sorted-key compact
JSON containing every required proof field except `proof_digest`, serialized
with `ensure_ascii=False` and no trailing LF. This stage has no probe fixture
and therefore computes no proof digest.

## Terminal identity and reconsideration

The exact four `terminal_predecessors` in the machine contract bind the v1
dossier IDs, digests and `REJECTED` state. A later reconsideration requires a
new dossier ID plus matching predecessor IDs and digests. It cannot reuse,
mutate, relabel or resubmit a terminal v1 or v2 identity.
Future dossiers encode these links as `predecessor_dossier_ids` and
`predecessor_dossier_digests`.

## Raw retention

A future authorized response is retained only below
`data/quarantine/m4_provider_evidence_v2/`, named by SHA256 and referenced by a
repository-relative locator. It is immutable, worktree-local, ignored and
never staged or committed. An in-memory hash or redacted derivative never
substitutes for the original. No more than 25 words from a source may be quoted.

## Authorization decision

Before any acquisition-v2 work, the user must explicitly approve every field
listed in `authorization_requirements.required_explicit_fields` and change the
stage-level decision to `ACQUISITION_V2_EXPLICITLY_AUTHORIZED`. Until then:

`ACQUISITION_V2_NOT_AUTHORIZED`

No default provider, automatic fallback, adapter work, real-data validation or
research execution follows from this design.
