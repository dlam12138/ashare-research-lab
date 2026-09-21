# M4 provider-evidence acquisition record

Goal: `agent/goals/2026-09-20_m4_provider_evidence_acquisition.md`.

DSH first returned `CHANGES_REQUIRED` on the draft Goal for eleven contract
defects, including ambiguous raw retention, incomplete dossier identity and
state rules, missing exact validations, and insufficient licence/redaction
boundaries. After amendment, DSH found three residual issues: a superseded EIA
transport identity and two defects in the secret/path scan. Commit `6b5370a`
aligned oil evidence to EIA-underlying/FRED-transport R4 and fixed the scan;
DSH's bounded recheck returned `PASS` before acquisition began.

The worker completed the authorized documentation-only acquisition boundary.
The four frozen dossiers in
`evidence/m4/provider_evidence_manifest_v1.json` are all `REJECTED` with
deterministic dossier and manifest digests. The BaoStock first-party landing
page was retained while its older documentation URL returned 404; CNINFO and
AkShare documentation was retained with AkShare limited to third-party
transport metadata; EIA documentation was retained; FRED series retrieval
timed out. No observation endpoint or credentialed service was used.

Independent parent review found that the worker's original manifest timestamps
were later than the actual acquisition. They were replaced with the retained
files' local write times; the failed FRED request has no claimed retrieval
timestamp. Parent review also added the accessible BaoStock first-party landing
page, without calling either BaoStock dataset endpoint.

Private raw bytes are under ignored
`data/quarantine/m4_provider_evidence_v1/`, named by SHA256. The report records
the official URLs and the unresolved gates. No provider selection, adapter,
real-data validation, study binding or execution is authorized.

One discovery-only response is retained but is not provider evidence:
`data/quarantine/m4_provider_evidence_v1/8ce7d28762cbc2efec13f560c05f83be40d93b97f49a0f7968579a655ee77e65.bin`
is the 267207-byte SHA256-addressed HTTP 404 HTML response from
`https://github.com/baostock/baostock`, retrieved at
`2026-09-20T11:46:13+08:00`. It was used only to reject that discovery path,
is excluded from every dossier gate and digest, and remains ignored/untracked.

The parent agent must independently inspect branch, HEAD, diff, raw locators,
hashes, ignore status, protected baselines, worktree/stash and validation
results before deciding acceptance. This worker did not commit or push.

Final DSH read-only re-review returned `PASS` after independently reproducing
the manifest and dossier digests, raw inventory/hash/length/ignore checks,
timestamps, frozen rejection codes, protected M2 HEAD/stash/database hash and
all Goal validation commands. The reviewer confirmed that the discovery-only
GitHub 404 is fully accounted for and excluded from evidence gates.

Parent committed the four authorized tracked artifacts as
`c10e25af02d20b596bc44b43a654588c68f5b9c9`, pushed only
`codex/m4-provider-evidence-acquisition`, and opened PR #25. No merge or later
stage was initiated.
