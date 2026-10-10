<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# Goal: first-party historical PIT evidence review for the frozen EIA transport

## Objective

Execute the separately scoped review that the frozen diagnostic names as its
next_task (`agent/tools/check_m4_progress.py`): bounded first-party discovery
over official EIA HTML documentation, index, landing and errata pages for
historical publication, signal-time availability and revision/vintage
evidence covering the frozen five daily rows 2015-03-09..13 (RBRTE Brent
spot). Output: a dispositioned evidence review record and, only if the
discovered artifacts justify it, a bounded acquisition contract naming exact
discovered artifact URLs and permitted content. The research gate stays
closed: no acquisition of value files, no provider selection, no execution,
no holdout.

## Verified baseline (2026-10-10, this session)

- origin/main and live main `6b71979a5096e61ae2703e5d69a3cf5602e7d5ae`
  (financial analysis line and M4/M2 queue closeout merged).
- Frozen EIA artifacts were hashed into ignored
  `tmp/eia-pit-review/baseline-hashes.txt` and the frozen diagnostics were
  re-run before any edit: `assess_eia_pit.py --check` PASS;
  `validate_eia_artifacts.py` PASS; `check_m4_progress.py` exit 0
  (research blocked, PIT_EVIDENCE_MISSING).
- Delivery worktree clean on the new branch; primary worktree, stash
  `cb568efd` and the database untouched (DB read only as a file hash).
- Preflight reachability probes (2 GETs, same URL, not retained) were made
  before this contract was written and are counted in the ledger.

## Allowed scope

- Branch `codex/m4-eia-pit-review` from origin/main.
- Two new tracked files: this Goal and its single work record (the record
  also serves as acceptance evidence); ignored `tmp/eia-pit-review/` logs
  and retained response bytes for bounds checks.
- Network: HTTPS GET only, host `www.eia.gov`, HTML pages only; total
  <= 12 requests including the two preflight probes; no redirects, no
  retries, per-request deadline 20 s, per-response cap 3 MiB; every request
  recorded in the record with UTC time, URL, HTTP status, byte count and
  SHA-256 of retained bytes.
- Page classes: documentation, about, methodology, index, archive, landing
  and errata pages; the two frozen-window issue landing pages may be
  re-opened to extract exact artifact hrefs for a bounded acquisition
  contract.
- Findings recorded factually with URL + SHA-256 references; no price
  observation values transcribed; only URLs discovered on already-fetched
  pages (no guessed artifact paths).

## Forbidden scope

- No API calls (`api.eia.gov` or any keyed endpoint); no CSV/XLS/PDF/ZIP or
  other file bodies; no value-bearing series/data pages; no non-eia.gov
  hosts (including web archives); no broad archives containing later data;
  no replay of the completed four-request transport probe.
- No changes to frozen evidence, tools, tests, checker, README gates,
  contracts, authorization, quarantine or any predecessor artifact; no
  acquisition, provider selection, execution, holdout, database access
  (file hash only), new dependencies, DSH, foreign worktrees, stash edits.
- No force push, no direct push to main, no branch deletion, no history
  rewrite, no scope expansion.

## Required behavior

- Review each frozen requirement (historical publication, signal-time
  availability, historical version) against the acceptable-evidence table
  in `docs/m4_eia_pit_evidence_next_steps.md`; classify each as ESTABLISHED /
  PARTIAL / NOT ESTABLISHABLE with URL + hash citations; keep unproven
  claims unproven (no extrapolation from current schedules or issue dates).
- If a viable bounded artifact path remains, define the bounded acquisition
  contract with exact discovered URLs only, permitted content, request and
  byte limits, and failure handling.
- If no obtainable first-party artifact can bind the required evidence,
  state that disposition and the honest options (prospective collection or
  separate design review) without authorizing either.

## Required checks and exact commands

```powershell
$env:PYTHONPATH='src'
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' agent/tools/assess_eia_pit.py --check
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' agent/tools/validate_eia_artifacts.py
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' agent/tools/check_m4_progress.py
git diff --check
git diff --cached --check
# re-hash frozen EIA files and compare against tmp/eia-pit-review/baseline-hashes.txt
```

Hosted CI on the PR (all checks) must succeed before merge; the protection
sweep is re-run after merge.

## Acceptance criteria

- Record contains a complete request ledger within budget; every finding
  cites a fetched URL and content SHA-256 or a pre-existing frozen artifact;
  frozen diagnostics still pass unchanged; frozen file hashes match the
  baseline; exactly the two new tracked files are added; one PR merged
  after green checks; protection sweep clean.

## Stop conditions

- A fetch would require following a non-HTML/file link, a redirect, a
  non-eia.gov host, or exceeds the budget; a frozen diagnostic fails;
  frozen hashes drift; unexpected concurrent edits; any scope expansion.
  Stop and report without merging.

## Commit and push requirements

- One commit (Goal + record) on `codex/m4-eia-pit-review`; push; one PR;
  merge after green checks under the standing authorization and the leaner
  delivery rules; no separate record PR, no automatic next stage.
