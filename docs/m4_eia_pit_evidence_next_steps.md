# EIA historical evidence: next steps

The successful five-day transport dossier remains valid. Offline assessment
`evidence/m4/eia_pit_readiness_01.json` establishes only that its verified row
schema lacks publication, availability, revision and vintage fields. It does
not assert that EIA has no archives, nor evaluate unseen supplemental evidence.

## Evidence still required

| Requirement | Acceptable evidence | Insufficient substitute |
| --- | --- | --- |
| Historical publication | First-party release artifact bound to the historical row/version | Observation date or current page date |
| Signal-time availability | Source evidence with timezone before the frozen signal cutoff | Local retrieval timestamp or assumed one-day lag |
| Historical version | Retained vintage/revision identity and pre-frozen selection rule | Current API response hash alone |

The [EIA API documentation](https://www.eia.gov/opendata/documentation.php)
describes date-range filtering of observations; this does not prove the time
they became public. The [current release schedule](https://www.eia.gov/reports/upcoming.php)
is discovery material, not row-bound 2015 publication proof. No current schedule
is extrapolated backward, and no archive was downloaded in this stage.

Next useful source work is first-party discovery of historical release/vintage
artifacts specifically covering 2015-03-09..13, followed by a bounded acquisition
contract naming the exact artifact paths and permitted content. Do not replay
the completed four-request probe or ingest broad archives containing later data.
If suitable historical evidence cannot be obtained, this transport cannot be
admitted to the existing strict-PIT research contract. Prospective collection or
a separately designed descriptive study are different tasks, not workarounds
that clear the existing gate. No automatic provider switch is authorized here.

Run `python agent/tools/assess_eia_pit.py --check` to reproduce the diagnostic.
It reads only tracked metadata, validates linked hashes, and cannot authorize
research even if a caller rehashes a readiness flag or adds a timestamp column.
An actual supplemental-evidence verifier requires separate review; this tool
does not pretend to implement one.
