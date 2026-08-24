# Stage 3D-B-R2 Work Record

## Boundary and heads

- Start HEAD: `188d255c6a827e2f8724ef83677ad0995cb51503`
- Canonical branch: `feat/m3-mechanism-validation-mvp`
- Pre-metadata implementation HEAD / CI: `a2e93d685e0e9a839610c17c8381c89d7a038306` / PASS
- Post-metadata corrected-universe HEAD / CI: `c445028a0219e9d3e73f0f56371e43081913f434` / PASS
- Final HEAD: `FINAL_HEAD_RECORDED_BY_COMMIT`
- Holdout was `UNSEALED_CONSUMED`; accepted primary execution count remained `0`.
- No primary statistic was observed before or during identity recovery.

The M2 worktree at `D:/量化分析` was not touched. All R2 work used the clean
canonical worktree `D:/量化分析-m3-stage3b`.

## Frozen identity and adapter

- Frozen file: `D:/m3_stage3db_holdout_retry/raw/akshare/sh_delist.csv`
- Frozen SHA-256: `72bf23f2bf0c5edc6bd585ad1434a6da010a22a1122af967e2f5d47c3ad4b0d0`
- R1 adapter digest: `0875afa70a54e062b3ce6a0341d2c5387b3e0f32ff700204d2767dc71eff96d8`
- R2 adapter digest: `c2ec3a088563f23106d4869c0c5d66b5f722a71effdf57aa8f35c76c764bbf03`
- SSE endpoint: `https://query.sse.com.cn/commonQuery.do`
- SQL ID: `COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L`; `COMPANY_STATUS=3`
- Separate requests: `STOCK_TYPE=1`, `2`, `8`.
- Raw SHA-256 type 1/2/8: `30be9e33d772004c558e8de6ecd19508d067ba3897188eefae682cb386b9c611`, `48419b6fe22f65f12be8e4b6e902ae742db390e6a27311d8adc6759525707d3b`, `2df041793a2ba7369ce07d205b7ffd45357b0a77ffc4f64945da845d5971d6b1`.

## Reconciliation

- Raw result counts: type 1=`143`, type 2=`13`, type 8=`3`.
- Frozen compressed rows / unique keys: `159 / 159`.
- Resolved rows: `159`; unresolved: `0`; extra current SSE rows ignored: `0`.
- Standardized rows: `159`; A-share: `146`; B-share: `13`.
- Security-level conflicts: `0`; frozen expansion/loss: `0`/`0`;
  company-code-as-security-id: `0`.
- Normalized logical digest:
  `8a9bf3868d880ab50460e0be0633aef6d2aa48abdce81328d507d4f6a3d22153`.

The six R1 conflict companies were all resolved at security level, with no
same-security conflicting dates:

| company | security codes | types | listing dates | delisting date |
| --- | --- | --- | --- | --- |
| 600190 | 600190, 900952 | A, B | 1999-06-09; 1998-05-19 | 2025-07-28 |
| 600555 | 600555, 900955 | A, B | 2001-03-28; 1999-01-18 | 2022-07-14 |
| 600614 | 600614, 900907 | A, B | 1992-08-28; 1992-07-28 | 2021-07-22 |
| 600625 | 600625, 900931 | A, B | 1993-01-06; 1994-11-10 | 2001-04-25 |
| 600680 | 600680, 900930 | A, B | 1993-10-18; 1994-10-20 | 2019-05-24 |
| 600695 | 600695, 900919 | A, B | 1993-11-22; 1993-12-15 | 2022-06-15 |

## Corrected Gate A and Gate B

- Corrected security master: `2514` rows; A=`2459`, B=`54`, other=`1`.
- EVER_ELIGIBLE=`2367`; NEVER_ELIGIBLE=`147`; METADATA_INSUFFICIENT=`0`.
- Original 148 classification: ever=`57`, never=`91`, insufficient=`0`.
- Exact AKShare `stock_zh_a_daily` retry was limited to the 57 true-required-
  missing symbols. Acquired=`0`, still missing=`57`; 2,310 base files were
  reused immutably and NEVER_ELIGIBLE symbols were not retried.
- Provider missing data remained in the denominator.
- Frozen market coverage gate `>=0.99` failed: minimum holdout coverage was
  `0.9736963544070143` (2,167 eligible / 2,110 observable on the first gap
  date); 535 holdout rows were `PROXY_ROW_INVALID_DATA_GAP`.

## Computation boundary and final disposition

- Price bytes were parsed only after post-metadata CI, to evaluate the frozen
  coverage gate; no real market proxy was materialized.
- FRED: not requested. CNI: not requested. Crash: not computed. OLS:
  not executed. Bootstrap: not executed. Gamma: not computed.
- Final result: `M3_STAGE3DBR2_RECOVERY_COMPLETED_HOLDOUT_PRIMARY_INCONCLUSIVE`.
- Final decision: `M3_HOLDOUT_PRIMARY_INCONCLUSIVE_TECHNICAL_OR_COVERAGE_GAP`.
- Execution provenance: `POST_UNSEAL_TECHNICAL_RECOVERY_WITH_SECURITY_IDENTITY_REPAIR`.
- Final stop: `STOP_FOR_NORTH_STAR_REVIEW`.

## Validation

- Focused pre/post metadata suite: `175 passed`.
- Final full suite at the pre-record final HEAD: `2229 passed, 4 skipped, 2 warnings`.
- `python -m ruff check src tests`: PASS.
- `python -m compileall -q src tests`: PASS.
- `git diff --check`: PASS.
- Frozen artifact SHA and R2 adapter digest regression: PASS.
- R2 manifest and corrected Gate A validator: PASS.

No raw SSE JSON, retry price files, or external capsule bytes were committed
to Git.
