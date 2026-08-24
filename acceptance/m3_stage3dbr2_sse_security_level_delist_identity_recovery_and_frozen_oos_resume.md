# M3 Stage 3D-B-R2 — SSE Security-Level Delist Identity Recovery

## Scope and provenance

This is a post-unseal technical recovery. The holdout was already consumed,
accepted primary execution count was `0`, and no primary statistic had been
observed. The original Stage 3D-B Case-C acceptance and the Stage 3D-B-R1
`M3_STAGE3DBR1_SECURITY_MASTER_CONFLICT` blocker remain immutable historical
evidence.

R2 uses the same Shanghai Stock Exchange metadata endpoint underlying the prior
AKShare delist wrapper. It preserves the raw security-level fields lost by that
wrapper: separate requests for `STOCK_TYPE=1`, `2`, and `8`, with
`COMPANY_STATUS=3`. `COMPANY_CODE` is provenance only; it is never a security
master key.

## Frozen-row rule

The frozen `sh_delist.csv` snapshot remains the complete row universe. Its
compressed multiset is `(COMPANY_CODE, LIST_DATE, DELIST_DATE)`. SSE provides
identity enrichment only. Frozen dates remain authoritative, current SSE-only
rows are reported and ignored, and unresolved or ambiguous multiset matches
fail closed.

## Gates

The adapter fails closed on raw schema failure, unproven pagination, invalid
security type, security-level date conflict, unresolved frozen identity,
ambiguous multiplicity, or date drift. Success requires zero unresolved rows,
zero security-level conflicts, no frozen-set expansion or loss, and all six R1
conflict companies resolved at security level.

No price bytes, market proxy, FRED, CNI, Crash, OLS, bootstrap, gamma, or
robustness output is part of the metadata adapter. A later frozen OOS resume is
authorized only after the post-metadata CI gate and remains subject to the
original one-execution contract.

## Verdict

The final stage verdict is `STOP_FOR_NORTH_STAR_REVIEW`, whether the metadata
repair succeeds or encounters a blocker.
