# M3 Stage 3D-B-R2 Goal Contract

status: STOP_FOR_NORTH_STAR_REVIEW

## Objective

Recover Shanghai Stock Exchange security-level identities from the same official
delist metadata source used by the prior AKShare wrapper, reconcile those
identities only to the frozen `sh_delist.csv` compressed-row multiset, and—only
after all metadata gates pass—resume the already-consumed frozen OOS execution.

## Verified baseline

- Canonical worktree: `D:/量化分析-m3-stage3b`
- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Canonical starting HEAD: `188d255c6a827e2f8724ef83677ad0995cb51503`
- Canonical HEAD equals origin and is clean at task start.
- Holdout was consumed; accepted primary execution count is `0`.
- No primary statistic was observed; market proxy, FRED, CNI, Crash, OLS,
  bootstrap, and gamma were not executed.

## Frozen inputs and scope

- Frozen delist row universe: `D:/m3_stage3db_holdout_retry/akshare/sh_delist.csv`
- Frozen delist SHA-256:
  `72bf23f2bf0c5edc6bd585ad1434a6da010a22a1122af967e2f5d47c3ad4b0d0`
- SSE endpoint: `https://query.sse.com.cn/commonQuery.do`
- SQL ID: `COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L`
- Separate `STOCK_TYPE` requests: `1`, `2`, `8`; `COMPANY_STATUS=3`.
- SSE is the same-official-source raw-field preservation path, not a new
  research source.

## Forbidden scope

- No new research source, proxy, threshold, control, hypothesis, or robustness.
- No replacement or expansion of the frozen delist row universe.
- No modification of Stage 3D-B, Stage 3D-A, Stage 3D-B-R1, or research-core
  computation implementation.
- No price parsing, market proxy, FRED/CNI, regression, bootstrap, or gamma before
  the metadata and CI gates pass.
- No manual web lookup or company-code-to-security-code inference.

## Required behavior

- Type 1/8 resolve `A_STOCK_CODE` and must classify as `A_SHARE_COMMON`.
- Type 2 resolves `B_STOCK_CODE` and must classify as `B_SHARE`.
- Missing raw fields, invalid JSON, unproven pagination, invalid security class,
  security-level date conflicts, unresolved frozen rows, and ambiguous multiset
  matches fail closed.
- Frozen dates remain authoritative; SSE supplies identity only.
- Company-to-security one-to-many rows are retained as distinct occurrences.
- Extra current SSE rows are reported and ignored.

## Final observed state

- SSE recovery passed: 159/159 frozen compressed rows resolved; 146 A rows and
  13 B rows; zero unresolved, extra, security-level conflict, or
  company-code-as-security-id rows.
- Corrected Gate A passed: 2,514 master rows; 2,367 ever-eligible; 147
  never-eligible; zero metadata-insufficient rows. The original 148 failures
  classify as 57 ever-eligible, 91 never-eligible, and 0 metadata-insufficient.
- Exact retry of 57 true-required-missing series acquired 0; 2,310 base files
  were reused and 91 never-eligible symbols were not retried.
- Frozen market coverage remained below 0.99 (minimum
  `0.9736963544070143`), so no market proxy or primary statistic was
  materialized. FRED, CNI, Crash, OLS, bootstrap, and gamma remain
  unrequested/unexecuted.
- Final state:
  `M3_STAGE3DBR2_RECOVERY_COMPLETED_HOLDOUT_PRIMARY_INCONCLUSIVE`;
  `STOP_FOR_NORTH_STAR_REVIEW`.

## Required tests and validation

- Synthetic focused R2 parser/resolver/reconciliation tests.
- Stage 3D-B-R1, Stage 3D-B, Stage 3D-A, M3 boundary, full pytest, ruff,
  compileall, diff check, and frozen artifact SHA regression.
- Pre-metadata CI must pass before the first real SSE request.

## Acceptance and stop conditions

Acceptance requires zero unresolved frozen rows, zero security-level conflicts,
zero frozen-set expansion/loss, zero company-code-as-security-id rows, and all
six known R1 conflict companies resolved at security level. Any failure stops
with `STOP_FOR_NORTH_STAR_REVIEW`. A successful metadata-only recovery also
stops for North-Star review after evidence is recorded.

## Canonical identities

- Digest algorithm: `M3_REPOSITORY_RELATIVE_DIGEST_V2`
- Upstream inventory SHA-256:
  `f206780dcb6fd4c3b9d30a92025b75974284afd16eecd24770d2f812256f0031`
- Pipeline digest: `ab224492ff85f391a29048dfeec740f9bbffb376de3408a5645a4552b51b9d1b`
- Model digest: `4958351a5c79c0eb96bbfda9ebaaca5e71ab2b07236eaa808b0a92ebc6e9756d`
