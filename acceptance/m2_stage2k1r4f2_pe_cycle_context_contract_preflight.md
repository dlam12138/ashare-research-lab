# M2 Stage 2K.1R4F.2 — PE Cycle Context Contract Preflight and Normalized Earnings Method Review

## Verdict: PASS — LOCAL CANDIDATE

Status: completed

Decision: `PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED`

Remote CI: **PENDING** (local validation complete; not yet committed/pushed at closeout time)

PE numeric scoring: **BLOCKED_UNCHANGED**

Next-stage implementation: **NOT STARTED**

This stage is a **method preflight / evidence inventory**.  It freezes the
problem definition, inventories the real committed PIT facts, compares at
least five normalized-earnings methods, and freezes the prototype evidence
contract — while **not** restoring any PE numeric score and **not**
modifying any v2 scoring contract.

## 0. Final report card

```
M2 Stage 2K.1R4F.2:                                    PASS — LOCAL CANDIDATE
Status:                                                 completed
R4F.1 upstream:                                        TRUSTED
PE current percentile:                                 TRUSTED_DESCRIPTIVE_EVIDENCE
PE numeric scoring:                                    BLOCKED_UNCHANGED
Scoring registry/policy v2:                            UNCHANGED
Observed annual history:                               2020..2025 (facts), ROE 2021..2025
Consecutive annual ROE observations:                   5
Full-cycle coverage:                                   NOT_PROVEN
Historical-average EPS method:                         BLOCKED_FULL_CYCLE_NOT_PROVEN
Average-ROE x current-BVPS method:                     ELIGIBLE_FOR_PROTOTYPE
Normalized-margin method:                              DIAGNOSTIC_READY
Normalized commodity-price method:                     DEFERRED_NOT_PRIMARY
Peer/sector normalization:                             DEFERRED_NOT_AUTHORIZED
PIT:                                                   PASS
Restatement handling:                                  PASS
Share-scope consistency:                               PASS
Normalized earnings diagnostics:                       TRUSTED_NON_SCORING
PE score produced:                                     NO
Valuation dimension score:                             NO
Production scoring:                                    NOT AUTHORIZED
Overall score:                                         PROHIBITED
Historical manifest debt:                              KNOWN_NON_BLOCKING_R4B_R4C
Decision:                                              PE_CYCLE_CONTEXT_NORMALIZED_EARNINGS_PROTOTYPE_ALLOWED
Next-stage implementation:                             NOT STARTED
Remote CI:                                              PENDING
```

## 1. What was frozen

- Formal problem (Section 二): a deterministic, PIT-safe normalized-earnings
  contract that prevents current low PE from mechanically scoring high when
  current earnings exceed sustainable/mid-cycle earnings.
- Reference review with explicit borrowing and cuts (CFA normalized EPS /
  average-ROE; Damodaran scale-distortion and margin diagnostics; MADR
  decision shape only).
- Method option matrix A–F (Section 六) with frozen conclusions.
- Prototype evidence contract `pe_normalized_earnings_average_roe_v1`
  (Section 七) — Decimal-only, no trim/winsorize/exclude, no arbitrary
  thresholds, no "5y = full cycle" claim.
- Observed history: `2020..2025`; ROE eligible `2021..2025` (2020 blocked —
  no 2019 opening equity); `full_cycle_proven = false`.
- Decision gate with derived evidence gates (PIT / restatement / share
  scope / history / BVPS / reproducibility / method review / no-score).

## 2. Boundary preserved

- `pe_numeric_scoring_authorized = false` — PE stays
  `coverage_gap_cycle_context_required`.
- `valuation_attractiveness` stays `insufficient_evidence_cycle_context`.
- registry v2 / policy v2 / shadow inputs v2 / capsule v5 / shadow v6 /
  sensitivity v8 — **unchanged**; no registry v3 / policy v3 / shadow v7 /
  sensitivity v9.
- No production score / overall score / recommendation / target price /
  peer / M3; no network access; no default-DB write.
- R4B / R4C historical manifest debt: recorded as
  `KNOWN_NON_BLOCKING_FOR_R4F2`, left for the final milestone-wide
  integrity closeout.

## 2a. Manifest sweep (Section 二, option B — debt confirmed)

Full verifier sweep of all 18 committed artifact manifests:

- **6 PASS**: R4C1 (17), R4E1 (1), R4E3 (4), R4E4 (22), R4E5 (15), R4F1 (13).
- **12 FAIL — all pre-existing, none caused by R4F2** (R4F2 modified zero
  tracked files):
  - content staleness (5–7 mismatches each): **R4A, R4B, R4C** — files
    changed after their manifests were pinned (R4B/R4C known since R4F1;
    R4A is the same class, also pre-existing);
  - legacy/unsupported manifest schema (verifier registers schemas only
    from R4C1 onward): Stage2J, R2K1R2, R2K1R3, R2K1R4D, R2K1R4E, R2K1R,
    R2K, ROIC i2, ROIC i2r — older manifest formats never registered in
    the current verifier.

R4F2 neither created nor modified any artifact manifest and did not register
any new verifier schema.  The debt statement
`historical_manifest_debt = KNOWN_NON_BLOCKING_R4B_R4C` is retained
(option B); no claim is made that "all existing manifests pass".

## 3. Key computed values (diagnostic, non-scoring)

- Average ROE (2021–2025, arithmetic mean): `0.1029179088085938346085963897`
- Current BVPS (MRQ parent equity 1,624,532,000,000 ÷ 183,020,977,818):
  `8.876206538550294436827638346`
- normalized_EPS_ROE: `0.9135206151007635380066173292`
- Current TTM parent NP / EPS: `158,184,000,000` / `0.8642943660660668889225593242`
  (TTM NP cross-validated against the R4E.4 PE_A_TTM 2026-03-31 state)
- Current EPS / ROE-normalized EPS: `0.9461136965920940114716739512` (pure
  math relation; **no** peak label, no arbitrary threshold)
- Historical-window average EPS (basic): `0.792`
  (labelled `HISTORICAL_WINDOW_AVERAGE_EPS`, never full-cycle)
- Average parent-NP margin: `0.04914241455740617927483288526`;
  normalized EPS via margin: `0.7646531740535774286590419341`
- TTM revenue: `2,847,796,000,000` (cross-validated against R4E.4
  PS_A_TTM 2026-03-31 state)

## 4. Validation performed

- R4F.2 static/regression tests: **35 passed**.
- CLI `build` then `verify`: all four artifacts **byte-identical**.
- R4F.1 protected tests / R4F protected tests / full suite: see work record.
- ruff / compileall / git diff --check / secret-path scan: clean.
- Scoring files exact-diff check: registry v2 / policy v2 / shadow v6
  untouched.
- Default DB SHA unchanged; stash preserved; protected files untouched.

## 5. Next stage (NOT STARTED)

`NORMALIZED_EARNINGS_PROTOTYPE` — to be separately authorized.  It must
verify PIT historical reconstruction, normalized-earnings identity, the
normalized-PE definition, current-vs-historical behavior, deterministic
A/B, sensitivity, and whether the peak/low-PE inversion is actually
removed.  **METHOD READY ≠ SCORING READY.**
