# Official archive discovery

Contract: agent/goals/2026-09-26_m4_eia_archive_discovery.md.
PR #30 merged, verified base 544be8011cf9d5b0abaecdb4c0b09683204dd2fb.
Plan: inspect official directory and issue landing pages only; record candidate
links without following price-table/PDF/XLS/CSV links or running research.

## Findings (2026-09-26)

Official archive index inspected:
https://www.eia.gov/petroleum/supply/weekly/archive/

The index maps the March 11 issue to week ending March 6, and the March 18
issue to week ending March 13. Both official issue landing pages were opened:

- https://www.eia.gov/petroleum/supply/weekly/archive/2015/2015_03_11/wpsr_2015_03_11.php
- https://www.eia.gov/petroleum/supply/weekly/archive/2015/2015_03_18/wpsr_2015_03_18.php

The March 18 landing header independently confirms its release date and week
ending date. Its table 11 links CSV/PDF spot-price material; figure 7 links daily
spot-price material. These links were NOT followed. No underlying artifact URL
was guessed, no price content downloaded, no API called and no backtest run.

Candidate decision: March 18 issue/table 11 deserves bounded content inspection
only after separate acquisition authorization. Its title does not establish
Brent RBRTE identity, daily granularity or coverage of all five target rows.
Figure 7 is a secondary candidate, not verified machine-readable data.
March 11 is a neighboring issue, not proof of full target-week coverage.

Important limit: a March 18 release cannot by itself prove availability during
March 9..13. The issue date is not a first-publication timestamp for each row.
Timezone/time-of-day, corrections, immutable vintage identity, exact row binding
and compatibility with the frozen signal cutoff remain unverified. Current
landing pages and dated paths do not prove unchanged historical file bytes.
No claim is made that archives are absent, or that this candidate clears PIT.

## Acceptance and handoff

Read-only discovery objective met: a specific official candidate and neighboring
issue have been located. Only three HTML directory/landing pages were opened
(plus a find within the index); no data-file link was followed.
No changes to implementation, frozen evidence, keys, database or research gates.
Validation commands: `python agent/tools/assess_eia_pit.py --check`;
`python agent/tools/validate_eia_artifacts.py`; `git diff --check`;
`git diff --cached --check`. Results recorded at final handoff.
Changes limited to this record and its Goal. Commit/push with draft PR; merging
that PR or acquiring candidate file contents requires separate authorization.
