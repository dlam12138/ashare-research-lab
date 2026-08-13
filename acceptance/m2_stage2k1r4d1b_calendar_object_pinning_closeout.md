# M2 Stage 2K.1R4D.1b — Calendar Object Pinning Closeout

Status: `PASS`

## Verdict

```text
M2 Stage 2K.1R4D.1b: PASS
Calendar registry: TRUSTED
Explicit content-addressed selection: TRUSTED
No-scan/no-fallback contract: TRUSTED
Object SHA verification: TRUSTED
Calendar structural validation: TRUSTED
2020 PIT dates: UNCHANGED_AND_TRUSTED
R4D.1a status: PASS
Formal real-cache rerun: NOT_RUN_EXTERNAL_OFFICIAL_CACHE_UNAVAILABLE
PIT denominator gate: PIT_DENOMINATOR_FACTS_READY_FOR_SERIES_PREFLIGHT
Next-stage implementation: NOT STARTED
```

## Scope

R4D.1b is a micro-closeout on top of R4D.1a. It fixes the one not-trusted
contract from the reviewer: the calendar loader must read the single exact
content-addressed calendar object pinned by a committed registry, and must
never scan the cache directory or fall back to another parquet when the pinned
object is absent or corrupt. It does not redo R4D.1/R4D.1a and does not start
the PE/PB/PS series.

## The defect fixed

The R4D.1a loader selected a calendar object by filename prefix and silently
fell back to the first parquet in the directory when the prefixed object was
absent:

```python
matches = [p for p in parquet_files if p.name.startswith(prefix)]
path = matches[0] if matches else parquet_files[0]
```

It also recomputed the object's sha256 but never verified it against the
expected content address. This was fail-open: on a clean formal run with a
missing or wrongly-named file, or with only an older (but coverage-sufficient)
parquet present, the loader would keep running instead of failing closed.

## The fix

1. **Committed registry** `config/pit_valuation_market_calendar_registry_v1.json`
   pins the single object: `object_sha256`, `object_key` (named by that sha256),
   `row_count` (1597), `first_trading_day` (2020-01-02), `last_trading_day`
   (2026-08-05), `evidence_cutoff` (2026-08-02), and
   `resolver_contract = explicit_content_addressed_object_no_scan_no_fallback`.

2. `load_market_calendar` now reads `market_cache_root / registry.object_key`
   directly and verifies, in order, that:
   - the registry `object_key` stems from `object_sha256`;
   - the pinned file exists (missing file -> fail, never a fallback scan);
   - `sha256(file bytes) == object_sha256` (content address);
   - `row_count` matches;
   - `is_trading` and `trade_date` columns exist;
   - no null `trade_date`;
   - `trade_date` is unique and strictly increasing;
   - the first/last trading day match the registry;
   - the required coverage start/end are reached.

   Any mismatch raises `CalendarCoverageGapError`, which aborts the formal run
   (the loader is called once at the top of `_cmd_formal`, outside any
   try/except). No other parquet is ever substituted.

3. `contracts.validate_all_contracts()` now validates the calendar registry and
   reports a `market_calendar_registry_digest`; a registry whose
   `resolver_contract` would allow scanning/fallback is rejected.

## Facts unaffected

The calendar object, its trade dates, and every `effective_from` are unchanged
by R4D.1b (the same pinned object was already the one selected in the R4D.1a
run). The committed reported bundle already references the pinned object and
sha256 and resolves 2020-04-30 -> 2020-05-06 with `available_at` unchanged.
R4D.1b hardens the selection contract; it does not change any fact, fact id, or
readiness count.

## Tests

New `tests/test_m2_stage2k1r4d1b_calendar_object_pinning.py` (12 tests):

- pinned object present, content address correct -> PASS
- pinned object missing but an older parquet exists -> FAIL (no fallback)
- filename is the expected sha but content sha differs -> FAIL
- registry row_count mismatch -> FAIL
- duplicate trade_date -> FAIL
- non-increasing trade_date -> FAIL
- required coverage start not reached -> FAIL
- required coverage end not reached -> FAIL
- correct + older object coexist -> only the pinned object is used
- registry allowing scanning/fallback is rejected
- registry validates
- integration: committed registry pins the real local object (skipped when the
  gitignored baostock snapshot is absent)

## Verification

Executed 2026-08-06 (Windows local):

- New R4D.1b tests: **12 passed**.
- Related R4D tests (R4D.1a, fact identity, context/restatement/share
  continuity, restatement-and-readiness, true-upstream capsule): **95 passed**.
- Full offline test suite: **1433 passed, 2 warnings** (1421 R4D.1a baseline
  + 12 new R4D.1b tests).
- `ruff check src/ tests/`: All checks passed.
- `python -m compileall -q src tests`: pass.
- `git diff --check`: pass.
- `verify-contracts` (stage2g + R4D): pass, includes
  `market_calendar_registry_digest = 17f4480c…`.
- Real calendar loader check: reads `77021dce….parquet`, matches sha, 1597
  trading days, 2020-04-30 -> 2020-05-06; missing object with older parquet
  present fails; tampered content fails.
- Default DB `data/research.duckdb` SHA-256 unchanged (`4a71d3c7…`); stash and
  protected items untouched.

## CI (dual-platform)

Run `31066461569` on commit `4223aee` (Stage 2G reproducibility):

- clean-clone (ubuntu-latest, ubuntu): **success** — full offline suite
  **1430 passed, 3 skipped, 3 warnings** (0 failed; the 3 skips are
  clean-clone network/local-snapshot tests, consistent with the local 1433
  total); R4D contract gate outputs
  `market_calendar_registry_digest = 17f4480c…`.
- clean-clone (windows-latest, windows): **success**.
- identity-compare: **success** (cross-platform identity payloads identical).

## Conditional / pending

- End-to-end formal pipeline re-run: **NOT_RUN_EXTERNAL_OFFICIAL_CACHE_UNAVAILABLE**
  — the gitignored official R4D PDF cache is not present in the working tree
  (25 registered objects, none present). No network re-fetch and no substitute
  PDFs are used; the R4D.1b change is confined to the calendar loader, and the
  deterministic fact bundles are unchanged (verified against the committed
  reported bundle: 127 reported, 38 reconciled, 150 cells, 0 gaps). Formal PDF
  extraction is not claimed to have been re-executed.
- Dual-platform CI (Stage 2G reproducibility): **to run on push** — it runs
  `verify-contracts` (now including the calendar registry) and the full offline
  suite on ubuntu + windows clean clones plus cross-platform identity-compare.

## Git state

- Branch `feat/m2-value-assessment-mvp`.
- Implementation commit `4223aee` ("fix: pin PIT market calendar content
  object", pushed `878727e..4223aee`) — CI run `31066461569` succeeded on all
  three jobs.
- Docs close-out commit (this acceptance + work record CI evidence) follows.
- Protected user changes (`acceptance/m2_stage2i2r_*.md`, `AGENTS.md`,
  `agent/goals/`) left untouched and not staged.