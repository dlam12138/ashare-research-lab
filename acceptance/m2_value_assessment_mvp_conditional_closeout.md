# M2 value-assessment MVP conditional closeout

Status: `CONDITIONAL PASS — PENDING FINAL CI EVIDENCE`

Milestone 2: CONDITIONALLY CLOSED WITH EXPLICIT EVIDENCE GAPS

## Decision and Git boundary

- Goal: `agent/goals/2026-08-04_m2_stage2j_post_roic_north_star_and_closeout.md`
- Branch: `feat/m2-value-assessment-mvp`
- Start HEAD: `ecc150449e83804fa6b91f5a5660387946e22b80`
- Final validated implementation HEAD: `8b1a58e13ed6c17217ec4c84c5c3285e37b0dc43`
- North-Star decision: `M2_CONDITIONAL_CLOSEOUT_ALLOWED`
- Permitted next gate: `M3_NORTH_STAR_PREFLIGHT_ALLOWED`
- Next-stage implementation: `NOT STARTED`

This is not a full-completion claim. The canonical current gaps remain visible,
traceable, score-ineligible, and non-zero-filled.

## Canonical closeout artifacts

- Review: `docs/post_roic_north_star_review.md`
- Completion matrix: `reports/m2_value_assessment_completion_matrix.json` and `.md`
- Gap ledger: `reports/m2_explicit_gap_ledger.json` and `.md`
- ROIC decision: `docs/decisions/ADR-ROIC-001-strict-evidence-non-computability.md`
- PetroChina profile: `reports/petrochina_value_profile.json`,
  `reports/petrochina_value_profile_2021_2026.md`, and
  `reports/petrochina_value_profile_one_page.md`
- Closeout summary: `reports/m2_stage2j_closeout_summary.md`
- Checksums: `reports/m2_stage2j_artifact_manifest.json`

## Module and evidence outcome

- Trusted existing profitability/cash-quality, ROE, ROA, financial-safety,
  valuation, profile, lineage, Identity and PIT contracts are preserved.
- Stage 2F remains complete with nine explicit exchange-payload gaps.
- Stage 2H remains complete with two `missing_evidence` risk slots.
- ROIC is `not_computable_under_strict_evidence_contract` with exact gaps
  `M2G-ROIC-001` through `M2G-ROIC-007`.
- ROIC decision code:
  `ROIC_NOT_COMPUTABLE_UNDER_STRICT_EVIDENCE_CONTRACT`.
- ROIC numeric value: `NOT PRODUCED`.
- ROIC shadow: `NOT RUN`.
- Production ROIC Metric/Result: `NOT CREATED`.
- Scoring: `SCORING_DEFERRED_BY_DESIGN`.
- Market mechanism: `NOT STARTED`.

## Current acceptance references

- Stage 2A: `acceptance/m2_stage2a_petrochina_minimal_transparent_metrics.md`
- Stage 2B-A/B: `acceptance/m2_stage2ba_petrochina_capex_cash_fact_coverage.md`,
  `acceptance/m2_stage2bb_petrochina_cashflow_metric_extension.md`
- Stage 2C: `acceptance/m2_stage2ca_value_evaluation_methodology_baseline.md`,
  `acceptance/m2_stage2cb_petrochina_2025_earnings_quality_fact_acceptance.md`,
  `acceptance/m2_stage2cc1_petrochina_2021_2025_earnings_quality_expansion.md`,
  `acceptance/m2_stage2cd_petrochina_earnings_quality_metric_extension.md`
- Stage 2D: `acceptance/m2_stage2db_petrochina_2020_2025_roe_roa_denominator_expansion.md`,
  `acceptance/m2_stage2dc_roe_roa_methodology_contract.md`,
  `acceptance/m2_stage2dd_petrochina_roe_metric_extension.md`,
  `acceptance/m2_stage2de_petrochina_net_profit_fact_coverage.md`,
  `acceptance/m2_stage2df_petrochina_roa_metric_extension.md`
- Stage 2E: `acceptance/m2_stage2ea_financial_safety_methodology_contract.md`,
  `acceptance/m2_stage2eb_petrochina_financial_safety_vertical_slice.md`
- Stage 2F current correction: `acceptance/m2_stage2f1_dividend_evidence_correction.md`
- Stage 2G current lineage/reproducibility: `acceptance/m2_stage2g1_trusted_lineage_closeout.md`,
  `acceptance/m2_stage2g2_clean_clone_reproducibility_and_evidence_contract.md`
- Stage 2H current profile: `acceptance/m2_stage2h1r_historical_risk_completeness_and_profile_canonicalization.md`
- Stage 2I current extraction lineage: `acceptance/m2_stage2i2r_official_fact_extraction_and_lineage_closeout.md`

## Superseded/current mapping

- Stage 2F historical implementation remains preserved; Stage 2F.1 is the
  current source-identity correction.
- Stage 2G is preserved; Stage 2G.1 is the current trusted-lineage closeout and
  Stage 2G.2 is the current clean-clone contract.
- Stage 2H and 2H.1 remain historical; Stage 2H.1R is the canonical current
  eight-slot risk-profile contract.
- Stage 2I, 2I.1R, 2I.1R2, and 2I.2 remain audit history; Stage 2I.2R is the
  current extraction/search/lineage result. ADR-ROIC-001 governs the current
  non-computability decision without deleting that history.

## Protected baseline evidence

- Default DB SHA-256 at start:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected inventory: 354 Facts / 102 Metric Results / 16 definitions.
- Plan v3 SHA-256:
  `f33e5e8a2e24085e274e0ebf13d3b126092214bce916b87fd6259c26e7964782`.
- Stage 2I.2R formal artifact digest:
  `90632b11b4784a019f8765237fe0d4bafcf1b8a80ff5c681a57fba3798da2483`.
- Stage 2I.2R committed packet digest:
  `cb35113e81016ac9de2cd966b48174af425cfdb2aeb3fc5a0341afbe6cd1e57f`.
- Opening-head CI run `30863411552`: Ubuntu `91850026057` and Windows
  `91850026156` passed.

## Required validation evidence

Targeted Stage 2J, protected Stage 2F/2H/2I, Fact/Metric Identity/PIT, full
pytest, Ruff, compile/import, matrix, ledger, cross-format profile, manifest,
clean-clone, pollution, protected-state and final Ubuntu/Windows CI evidence is
recorded in the final section after execution. Conditional closeout is not
reportable until every required final gate passes.

## Non-goals and reopen conditions

No annual report was re-searched in Stage 2J; no new fact was downloaded or
extracted. No proxy tax, residual associate/JV allocation, unsupported
non-operating-asset deduction, plug, zero fill, score, ranking, threshold,
target, recommendation, target-excluded market proxy, statistical hypothesis,
oil/industry control, Web, trade, or M3 code was created.

ROIC may reopen only under the conditions in ADR-ROIC-001. Other M2 modules may
reopen through their own source-resolution or methodology governance; a current
gap cannot disappear solely because the milestone is conditionally closed.

## Final validation and CI

- Stage 2J focused: `13 passed`.
- Stage 2F protected: `22 passed`.
- Stage 2H protected: `15 passed`.
- Stage 2I/2I.1R/2I.1R2/2I.2/2I.2R protected: `76 passed`.
- Identity/PIT/Metric protected group: `112 passed` after the required
  append-only roadmap hash update; five directly affected blob-guard suites:
  `68 passed`.
- Full local pytest: `1056 passed, 2 warnings`; warnings are the existing
  pandas date-format warnings in `tests/test_quality.py`.
- Full Ruff, compileall/import, `git diff --check`, Stage 2J matrix/ledger/
  profile/decision validation, artifact verification, secret/absolute-path and
  DB/PDF/cache/raw-response pollution scans: passed.
- Trusted pre-Stage2J profile payload comparison: unchanged except for the new
  `capital_return` evidence-status node and the intended integrated ROIC status.
- Local clean-clone and final Ubuntu/Windows CI: pending.
