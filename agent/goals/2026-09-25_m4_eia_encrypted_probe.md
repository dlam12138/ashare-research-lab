# Goal: authorized EIA encrypted evidence probe

User explicitly authorized EIA_API_KEY use and encrypted original-response
retention under the existing five-day window and request limits. This new
contract supersedes the EIA plan's not-authorized decision for this run only;
frozen FRED/v2 contracts remain unchanged.

Baseline: clean codex/m4-fred-transport-diagnosis at
b90a63fec524fddc555f150e6b55df27ad001015, origin/live equal;
main 9c9ced90d109437b937cfcaa069388689db636f5.
M2 3679b1bac7a1634c6452784a4d8f6d139966f222;
stash cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f;
DB SHA256 4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Allowed: this Goal/record/acceptance, agent/tools/eia_probe.cjs and its synthetic
test, agent/tools/verify_eia_evidence.ps1 for independent offline verification,
agent/tools/validate_eia_artifacts.py for shareable artifact validation,
new EIA authorization/ledger/dossier JSON. AES-256-GCM ciphertext under
ignored data/quarantine/m4_eia_direct_01; random encryption key wrapped with
Windows DPAPI CurrentUser in that directory (OS master key is separate).
Read the authorized API key from Process or User environment privately; no key
in shell arguments, logs, tracked output or plaintext files. Exact original
bytes must be recovered from ciphertext and match SHA256 before acceptance.

Envelope: at most one unkeyed GET of www.eia.gov/opendata/register.php to retain
the already reviewed first-party terms, two keyed metadata GETs at
api.eia.gov/v2/petroleum/pri/spt/ and /v2/petroleum/pri/spt/facet/series/,
then one conditional GET /v2/petroleum/pri/spt/data/ for daily RBRTE,
value, 2015-03-09..2015-03-13 inclusive, ascending period, offset=0,length=5.
Maximum four requests total, zero retry/redirect/pagination, >=15 seconds
between starts, 15000 ms total per request including CONNECT/TLS/body, verified
TLS, identity encoding, cumulative response bodies <=1048576 bytes. Stop after
any error, missing/contradictory terms or identity, incomplete metadata or
retention failure. Ledger persists counts across offline review pauses.

New dossier eia_direct_brent_transport_probe_01 references the immutable v1
eia_brent_oil_transport predecessor digest; FRED identity remains unused.
Freeze allowed row keys before observation. Validate every date and identity,
units, exact five unique dates, total count and absence of undeclared columns;
never print/track numerical observations. No PIT/research-readiness claim.
No database access, holdout, product adapter, registration, merge or main push.

Validation: node --test agent/tools/eia_probe.test.cjs; node --check
agent/tools/eia_probe.cjs; scoped DSH preflight; encrypted roundtrip and
authentication-tamper tests; strict JSON/canonical digests, ledger bounds,
offline decryption/hash/metadata/date revalidation; git diff --check and
git diff --cached --check; protected state and secret-leak checks reporting
booleans only. Commit scoped artifacts, push explicit topic refspec, update
PR #29. A failed request is terminal for this run; no silent network retry.
