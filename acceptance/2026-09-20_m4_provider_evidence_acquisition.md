# M4 provider-evidence acquisition acceptance

Disposition: worker evidence packet only; parent/DSH review required.

Final independent DSH re-review verdict: `PASS`.

Goal: `agent/goals/2026-09-20_m4_provider_evidence_acquisition.md`.
Base branch was `codex/m4-provider-evidence-acquisition`, with HEAD initially
`6b5370a` and source tree `60f1cdc78911c550172e97bc92610526dfa29b89`.
Authorized tracked files written: the report, manifest, record and this
acceptance file. No commit or push was performed.

The manifest has exactly four unique dossier IDs and all four states are
`REJECTED`; each mandatory field group is present, unproven values are null,
and each failed gate has an accepted rejection code. Raw locator SHA256 and
length checks were performed against the ignored files. Official URLs and
retrieval metadata are recorded in the manifest and report.

Validation commands and results:

1. `python -m json.tool evidence/m4/provider_evidence_manifest_v1.json > $null` — PASS.
2. Manifest digest recomputation using sorted compact canonical JSON — PASS
   (`26542836f7b015c32d938ce1989cceb5f55437c59e908c5c1ba4d477867cb24f`).
3. Four unique dossier/state assertion — PASS.
4. Report contains every dossier ID and every manifest `final_url` — PASS.
5. Secret/path scan with the Goal's `rg` command — PASS (no matches; exit 1).
6. `git diff --check` and `git diff --cached --check` — PASS.
7. `git rev-parse HEAD origin/main refs/stash HEAD^{tree}` — PASS:
   `6b5370a194b78a7bc6fe1f9f7630ebc0283a7dd9`,
   `781f7fb035eb3fdebc3b2c03ed5f642f2094d29e`,
   `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`,
   `60f1cdc78911c550172e97bc92610526dfa29b89`.
8. `git worktree list --porcelain`, `git stash list` and protected parent
   worktree inspection — PASS; M2 HEAD is
   `3679b1bac7a1634c6452784a4d8f6d139966f222` and stash HEAD is the value above.
9. Dossier digests recomputed after removing only `dossier_digest` — PASS:
   `b8b36579a4261166c420a64e7e987fd933bcd269ff0c83e24a4adbc89a3c6175`,
   `f6ec233a63554fff9e6098355ae9ee2bb974c2015133114a393e471a1078f451`,
   `cd219c9a33e5251440568157806148a781abe951488e38cee8f96d6455f25c32`,
   `b748ac51d7bb3e22b8b42c444404183d3a1d7a1b44065f92b87870cbbc5cf9b2`.
10. Referenced raw locator existence/length/SHA256 — PASS: five referenced
    files match manifest lengths and hashes; `git check-ignore -v` reports
    `.gitignore:42:data/quarantine/*` for all six retained raw files.
11. Strict UTF-8, LF/final-newline, unique retrieval URL and local Markdown
    link checks — PASS.
12. `Get-FileHash ...research.duckdb -Algorithm SHA256` — PASS:
    `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`;
    the database was hashed only, not opened or queried.

Raw files remain ignored and untracked; no response body is staged. Deviations
are the legacy BaoStock documentation 404, the worker timestamp correction and
the bounded FRED timeout. The accessible BaoStock landing page was added during
parent review. These are fail-closed evidence results, not proof of provider
capability. Proceeding to provider selection,
adapter implementation, observation acquisition or real validation is not
allowed without a new authorized stage.

The sixth retained raw file is a discovery-only GitHub 404 recorded in the work
record by repository-relative locator, SHA256, length, URL and timestamp. It is
not cited as provider evidence and is excluded from dossier and manifest digests.

Parent Git handoff:

- Evidence commit: `c10e25af02d20b596bc44b43a654588c68f5b9c9`.
- Remote branch: `origin/codex/m4-provider-evidence-acquisition`.
- Pull request: <https://github.com/dlam12138/ashare-research-lab/pull/25>.
- `origin/main` remained `781f7fb035eb3fdebc3b2c03ed5f642f2094d29e`
  at push time; no direct main push or merge occurred.
- Later-stage work remains unauthorized pending explicit review/approval.
