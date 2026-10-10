<!-- AI provenance: action=created; model=GPT-5; agent=Codex; date=2026-10-10 -->

# First-party historical PIT evidence review (frozen EIA transport)

Contract: agent/goals/2026-10-10_m4_eia_pit_evidence_review.md. This record
doubles as acceptance evidence. Baseline: origin/main and live main
6b71979a5096e61ae2703e5d69a3cf5602e7d5ae; branch
codex/m4-eia-pit-review; frozen diagnostics passing before and after the
review (see Validation). Scope executed: bounded first-party discovery over
official EIA HTML documentation, schedule, guidelines, notice, FAQ and
archive landing pages. No value files fetched; no API call; no non-eia.gov
host; no price observation values transcribed anywhere in this record.

## Request ledger (9 of <= 12 budget; all HTTPS GET, www.eia.gov, HTML)

| # | UTC time | URL | HTTP | bytes | sha256 (retained in ignored tmp/eia-pit-review/) |
| --- | --- | --- | --- | --- | --- |
| R0a | preflight, time not recorded | /petroleum/supply/weekly/ | 200 | 86855 | not retained |
| R0b | preflight, time not recorded (via local proxy) | /petroleum/supply/weekly/ | 200 | 86855 | not retained |
| R1 | 2026-10-10T13:12:18.545Z | /petroleum/supply/weekly/ | 200 | 86855 | a3943b5c4cbcf23ab40242f5519e770ba2a5cfb72cc72401e788c437c1fc0736 |
| R2 | 2026-10-10T13:12:28.361Z | /petroleum/supply/weekly/schedule.php | 200 | 52129 | fe50afa140a44beb96a4ed957544d064faf721ac1d8cf6a3b72916fde63fa2f2 |
| R3 | 2026-10-10T13:12:29.094Z | /about/information_quality_guidelines.php | 200 | 77410 | 3eeb1bc7d980dba93055b3cbfcb0436e4f60af0f25c763709e25bb0c5feb4ff3 |
| R4 | 2026-10-10T13:12:30.863Z | /petroleum/supply/weekly/wpsr_notice_06102026.php | 200 | 49834 | 37d3b70e74af28f311978a26a7700390947c7f11c0e2948f3de89e88a6a13d14 |
| R5 | 2026-10-10T13:12:51.052Z | /tools/faqs/ | 200 | 74427 | 506f0a3683266f1f0ff6b1d2596ffa30483514497b327608c0e8c8fb01012f97 |
| R6 | 2026-10-10T13:12:51.665Z | /petroleum/supply/weekly/archive/2015/2015_03_11/wpsr_2015_03_11.php | 200 | 62007 | 63d86f109df2a179d4c8c99e18af591f65d01e3cd07de90265bf7c1e7bcabef6 |
| R7 | 2026-10-10T13:12:52.152Z | /petroleum/supply/weekly/archive/2015/2015_03_18/wpsr_2015_03_18.php | 200 | 62008 | 741afc99a48bf68bc69470405a6bf1b13eab027d59f6817c4012ce947ed7974c |

No redirects followed, no retry performed (single attempt each; --max-redirs 0,
no --retry). R0a/R0b were reachability probes made before the contract was
written, counted here for completeness (direct and via the machine's local
proxy; both 200 with identical byte count).

## Requirement 1 - Historical publication (row/version-bound release artifact)

NOT ESTABLISHED at row level; bounded path identified.

- R6 and R7 are first-party, release-dated archive landing pages: R6 states
  "Data for week ending March 6, 2015 | Release Date: March 11, 2015"; R7
  states "Data for week ending March 13, 2015 | Release Date: March 18,
  2015". They cover the frozen window's week and expose exact artifact
  inventories (CSV tables 1-14/5a and PDF tables/figures plus the full
  report `pdf/wpsrall.pdf`).
- Reused prior evidence (not re-executed): the 2026-09-26 archive-discovery
  record established the issue mapping; the 2026-09-26 Table 11 probe
  established that the linked 2015 CSV is monthly-layout material without
  the five daily rows (record 2026-09-26_03, sha256
  b988d279f159184302d046455bdbac392a2aca43442a5d57d4e3ea2f8fc21679 for its
  ledger; CSV raw sha256 552aafb7ddb97cd00c7f63af8a0f2ae07613d9fa1617035829123a6c7febb864
  as retained there).
- Not established: per-row first-publication. Issue release dates prove
  availability of the issue, not of each daily row on its own date; whether
  the daily RBRTE values were first public earlier (daily-updated pages/API)
  is not documentable from the page class.

## Requirement 2 - Signal-time availability (source evidence with timezone)

NOT ESTABLISHED. Only current-policy evidence exists.

- R2 (schedule page): "The standard release time and day of the week will
  be at 10:30 a.m. eastern time on Wednesday with the following
  exceptions." The exceptions table fetched today covers 2024-2026 only.
- No 2015-specific schedule/release-time artifact was discoverable in the
  page class. Per the frozen rule, a current schedule must not be
  extrapolated backward (docs/m4_eia_pit_evidence_next_steps.md).
- The requirement is additionally contingent on a future frozen research
  signal cutoff, which does not exist yet (research not authorized).
- R5 (FAQ index) yielded no spot-price publication-timing statement.

## Requirement 3 - Historical version (vintage/revision identity)

PARTIAL system-level evidence; NOT ESTABLISHED per row.

- R3 (EIA Information Quality Guidelines): "EIA's information may be
  revised after initial dissemination to reflect more complete information
  or other changes in the underlying data"; "If a substantive error is
  detected after a product is disseminated, EIA will make correction and
  issue an errata notice or other notification as appropriate";
  "Preliminary and revised data are noted."
- R4 shows EIA publishes dated WPSR notice pages (observed: "Improving data
  delivery for the Weekly Petroleum Status Report", Release Date: June 1,
  2026); the R1 home page links one current notice and the consolidated
  `WPSR_ErrataSheet.xlsx`.
- No per-row vintage mechanism for the daily spot series was found in the
  page class; the frozen transport dossier already establishes that the
  verified API response schema retains no availability/publication/
  revision/vintage identity (pit_semantics UNPROVEN).
- The WPSR Errata Sheet is the concrete first-party correction artifact;
  its content has not been inspected (file class) - bounded contract below.

## Disposition

Strict-PIT admission for the frozen transport remains NOT ESTABLISHED; the
research gate stays closed and the frozen diagnostic is unchanged
(next_task still applies). Discovery produced one bounded, specifically
enumerable next evidence step: a metadata-only inspection of four exact
first-party artifacts. If that inspection fails to bind the required
evidence, the honest terminal options remain prospective collection or a
separately designed study - neither authorized here; no provider switch is
authorized.

## Bounded acquisition contract (proposed; requires separate authorization)

Exact artifacts (URLs as discovered; no guessed paths), at most 4 GETs,
<= 25 MiB cumulative, no redirects, no retries, 20 s per request:

1. https://www.eia.gov/petroleum/supply/weekly/WPSR_ErrataSheet.xlsx -
   permitted inspection: worksheet structure and correction entries
   (entry dates, affected issue/table identifiers, description text);
   purpose: whether any correction touches WPSR spot-price material or the
   frozen window's issues.
2. https://www.eia.gov/petroleum/supply/weekly/archive/2015/2015_03_11/pdf/wpsrall.pdf
3. https://www.eia.gov/petroleum/supply/weekly/archive/2015/2015_03_18/pdf/wpsrall.pdf
   - permitted inspection (both): cover/release metadata, section
   inventory, spot-price section presence and identifiers, any errata or
   correction notices inside the issue; purpose: issue-level publication
   binding and revision notes for the frozen week.
4. (secondary, same rules)
   https://www.eia.gov/petroleum/supply/weekly/archive/2015/2015_03_18/pdf/figure7_8.pdf

Content rules: never transcribe price observation values anywhere; retain
original bytes encrypted under the existing AES-256-GCM + Windows-DPAPI
pattern; commit metadata-only findings with raw/ciphertext SHA-256; stop on
redirect, non-200, oversize or ambiguous content without retry; anything
beyond these four artifacts (other issues, dnav series pages, API calls)
requires a new scope. This contract does not admit the transport, does not
authorize provider selection, and does not authorize execution.

## Validation and acceptance

- python agent/tools/assess_eia_pit.py --check: PASS (before and after).
- python agent/tools/validate_eia_artifacts.py: PASS (before and after).
- python agent/tools/check_m4_progress.py: exit 0, research blocked,
  PIT_EVIDENCE_MISSING (before and after; checker file hash unchanged:
  990340862b6cc7c34eb366245ce5ec83e4ae2a7149052b77438c0d97334e8ce1).
- Frozen EIA evidence hashes re-verified equal to
  tmp/eia-pit-review/baseline-hashes.txt after the review.
- git diff --check / git diff --cached --check clean; exactly two tracked
  files added (goal + this record).
- Hosted CI on the PR must pass before merge; protection sweep re-run after
  merge.
- Deviations: none. Budget used 9/12 requests; no stop condition triggered.
