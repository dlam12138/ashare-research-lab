# EIA encrypted probe record

Goal: agent/goals/2026-09-25_m4_eia_encrypted_probe.md.
User authorized credential use and encrypted original retention. Baseline
b90a63f on codex/m4-fred-transport-diagnosis clean and synchronized. Protected
M2 HEAD/stash/default database hash matched Goal. User-scope EIA_API_KEY exists;
process-scope does not. Read the authorized user value privately at execution;
no restart or further user action is required.

Plan: implement bounded one-shot transport and AES-256-GCM retention with
DPAPI-wrapped key, test on synthetic bytes, DSH review, retain terms then
metadata, freeze schema, attempt one conditional observation request, offline
proof verification and scoped delivery. Outcome pending execution.

## Execution and result

DSH preflight PASS; five synthetic tests passed including ciphertext tampering,
wrong key, DPAPI roundtrip, date/holdout/schema/series/unit failures and metadata
completeness. The first-party EIA terms were retained encrypted before keyed
metadata. The metadata confirmed daily/value/series and one Brent RBRTE entry
among 11 complete series facets. The row-field allowlist was frozen in the
authorization before the observation request.

Four HTTP 200 responses, identity encoding, zero retries/redirects:

| Stage | UTC start | Body bytes | Elapsed ms |
| --- | --- | ---: | ---: |
| terms | 2026-09-25T02:03:52.344Z | 49715 | 798 |
| metadata | 2026-09-25T02:04:07.357Z | 895 | 1792 |
| series facets | 2026-09-25T02:04:22.359Z | 1378 | 1635 |
| five-day observations | 2026-09-25T02:04:41.917Z | 1799 | 1349 |

Total: 53787 bytes. Start intervals exceed 15 seconds; each request completed
within 15 seconds. Exactly five distinct daily dates 2015-03-09..2015-03-13,
RBRTE identity, Brent description, $/BBL units and frozen fields verified.
No prices are printed, tracked, statistically interpreted or used in research.

All four original bodies are AES-256-GCM encrypted in ignored quarantine.
The random encryption key is DPAPI CurrentUser wrapped; OS master keys remain
separate. Files are tied to this Windows user/profile and require preservation
of that profile for recovery. Protected key material and ciphertext were never
committed. Both Node and independent PowerShell/.NET decrypt/hash checks pass.

Independent verifier initially rejected a provider metadata echo represented
as an empty array rather than a dictionary. The verifier now permits an empty
echo container and checks any actual echoed key privately for equality; no
acquisition code, data, tests or ledger were altered to obtain a pass, and no
request was repeated. Diagnostic output was only a line number/type, not body
content or credential. The Goal now explicitly lists the independent verifier
as implementation of its original independent-validation requirement.

## Exact validation commands

- `node --check agent/tools/eia_probe.cjs`: PASS.
- `node --test agent/tools/eia_probe.test.cjs`: 5 PASS, 0 fail.
- `node agent/tools/eia_probe.cjs verify`: encrypted hashes and metadata/date
  checks PASS, entirely offline.
- `pwsh -NoProfile -File agent/tools/verify_eia_evidence.ps1`: independent
  .NET AES-GCM/DPAPI, 4 routes, 53787 bytes, five dates, secret absence PASS.
- `python agent/tools/validate_eia_artifacts.py`: strict and
  canonical JSON, proof/dossier/file digests, lineage, byte/route limits,
  ignored ciphertext and unchanged predecessor files PASS.
- `git diff --check`: PASS; staged equivalent required before commit.

Deliverable: `evidence/m4/eia_direct_dossier_01.json`, state
TRANSPORT_VERIFIED_EVIDENCE_ONLY. Frozen FRED/v2 artefacts remain unchanged.
This is not production-provider acceptance: historical publication/vintage
semantics remain unproven, so research and adapter admission remain closed.

Tracked scope: Goal, record, acceptance, four agent/tools files, authorization,
request ledger and dossier (ten files). Continue existing PR #29 without merge;
one scoped commit/push after final review. Final SHA/CI/synchronization reported
at handoff rather than recursively adding delivery-only commits.

Final DSH review verified evidence arithmetic, order, intervals, reference and
digest chains, lineage and evidence-only/PIT limits. It returned CHANGES_REQUIRED
because scoped artifacts were still untracked during review, and it could not
enumerate the tool directory or reproduce an ignored validator in a clean
clone. Parent enumerated all tools, promoted the artifact validator to the
tracked tools directory, and will resolve delivery by the scoped commit/push.
DSH did not independently decrypt private evidence; parent .NET validation is
the independent raw-byte check. No data-quality defect was reported.
