# M3 Stage 3D-B-R1 — Recovery Addendum

## Verdict

`M3_STAGE3DBR1_METADATA_REPAIR_BLOCKED`

`STOP_FOR_NORTH_STAR_REVIEW`

The original Stage 3D-B Case-C acceptance remains unchanged and is the
`INITIAL_TECHNICAL_BLOCK_HISTORY`. This addendum does not rewrite that history
as a successful or pristine execution.

## Gate A evidence

- Canonical starting HEAD: `6305168f5a445af2bfe579e06aec4402e9a53709`.
- Recovery class: `POST_UNSEAL_TECHNICAL_ADAPTER_RECOVERY`.
- Holdout was already consumed; accepted primary execution count before this
  recovery was `0`; no primary research statistic was observed before repair.
- The recovery contract, schema binding, universe audit, and adapter digest are
  in the new `m3_stage3dbr1_*` reports.
- The bound market metadata files match the original frozen SHA identities.
- Header binding used the actual CSV names. No positional column guessing was
  used.
- The raw current-plus-delist union contains 2,508 unique symbols; the
  historical failed request set contains 148 symbols, matching the original
  Case-C manifest.

## Fail-closed blocker

`sh_delist.csv` contains duplicate symbols with conflicting `listing_date`
values, including `600190`, `600555`, `600614`, `600625`, `600680`, and
`600695`. The recovery adapter therefore raised
`M3_STAGE3DBR1_SECURITY_MASTER_CONFLICT`. It did not choose current over
delisted metadata, earliest/latest dates, or silently drop those securities.

## Execution boundary

Because Gate A did not produce a valid unified security master:

- no new daily price bytes were parsed;
- no provider retry was made and no recovery overlay raw file was written;
- no market coverage or proxy return was computed;
- FRED and CNI were not requested;
- Crash, OLS, bootstrap, gamma, A/B, and any primary result were not run;
- accepted primary execution count remains `0`.

The original Case-C facts remain immutable: 897 target qfq rows, raw target SHA
`274f3be87992381db3a67a393b5357717d02dcbd6f11b3085b4617476c7a9bf6`, market
union 2,458, 2,310 daily files acquired, 148 failed, and no primary statistic
observed.

## Validation

- `python -m pytest -q tests/test_m3_stage3dbr1_recovery.py tests/test_m3_stage3db_preunseal.py tests/test_m3_stage3br1_primary_proxy.py` — PASS, 70 tests.
- Metadata-only real-capsule Gate A validator — PASS for detecting the required
  conflict and stopping before price parsing.
- M3 boundary suite — PASS, 275 passed, 1 skipped.
- Full `pytest -q` — PASS, 2,208 passed, 4 skipped, 2 warnings.
- `python -m ruff check src tests` — PASS.
- `python -m compileall -q src tests` — PASS.
- `git diff --check` — PASS.
- Immutable regression for the original Stage 3D-B adapter/input/proxy,
  original input manifest, and original acceptance — PASS.

No CI run or push was performed after this blocked Gate A.
