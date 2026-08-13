# Work record: M2 Stage 2H.1R historical risk completeness and profile canonicalization

## Basic information

- Date: 2026-08-02
- Agent: Codex
- Branch: `feat/m2-value-assessment-mvp`
- Starting commit: `401b96aa5284b237c77792d4991e6788c42dd20e`
- Task source: the authoritative attached Stage 2H.1R contract
- Module: value assessment / engineering governance

## Objective

Close the finite Stage 2H.1 correction by making the historical risk universe
complete as eight deterministic evaluation slots, preserving PIT and missing-
evidence semantics, canonicalizing the current PetroChina risk profile, and
separating deterministic input evidence from supplemental evidence.

## Scope and non-goals

In scope are the risk-veto contracts, runner, reports, profile integration,
tests, acceptance documents, and reused Stage 2G.2 reproducibility gates. The
default database, stash, protected Fact/Metric/definition baseline,
`agent/goals/`, and unrelated valuation layers are out of scope. ROIC, scoring,
Web, target price, recommendation, automatic trading, and market-mechanism
work are not started.

## Starting state and North-Star gate

- The verified branch and `origin` point to `401b96a`; there are no intervening
  commits after the expected starting head.
- The North-Star review in `docs/post_valuation_north_star_review.md` says
  `Stage 2H risk-veto evidence: ALLOWED`.
- The worktree contains only the pre-existing untracked `agent/goals/`
  directory. The pre-existing stash remains:
  `stash@{0}: On feat/m2-value-assessment-mvp: protect pre-existing Stage 1B.4
  record edit before Stage 1C`.
- Default database SHA-256 before edits:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Protected baseline required by the earlier acceptance is `354 Fact / 102
  Metric Result / 16 definitions`; it will be checked read-only before and
  after this task.
- Latest remote CI before edits is workflow run `30744466406`, commit
  `401b96a`, completed successfully with Ubuntu and Windows jobs.

## Known review points carried into this task

1. A historical query with no PIT-visible input can silently omit a risk ID.
2. The current 2025-04-01 historical run has seven observations.
3. The value profile contains old broad placeholders alongside Stage 2H detail.
4. Event `evidence_ids` do not distinguish deterministic input evidence from
   supplemental evidence.

These are defects to close, not conclusions to be hidden. No `available_at`,
observation, source type, content hash, or deterministic ID will be fabricated;
missing evidence remains `missing_evidence`.

## Planned implementation

1. Add versioned risk-universe and risk-slot contracts and a public evaluator;
   make the formal runner publish complete eight-slot results.
2. Upgrade event and observation evidence lineage to explicit input,
   supplemental, and all-evidence fields with fail-closed validation.
3. Make the value profile use one canonical current risk node and migrate old
   broad placeholders to explicitly legacy/superseded metadata.
4. Add focused regression tests, regenerate real/historical/synthetic outputs,
   update old-to-new documentation and acceptance, and run full local,
   clean-clone, Ubuntu, and Windows gates.

## Results

### Implementation

- Added `risk_universe_evaluation_v1` and `risk_evaluation_slot_v1` with a
  public `evaluate_risk_universe_as_of(...)` evaluator. Every PIT run now
  exposes exactly the eight frozen risk IDs; a slot with no PIT-visible input
  is explicit `missing_evidence` with no fabricated observation or conclusion.
- Upgraded event and observation lineage to v3. Input, supplemental, and
  ordered union evidence IDs are disjoint/validated; source types come from
  the evidence ledger; normalized values must reconstruct input lineage; and
  supplemental evidence cannot change `input_lineage_hash`.
- Canonicalized the value profile at
  `reports/petrochina_value_profile.json:current_risk_veto_profile` with eight
  current slots. The old broad governance/audit/related-party placeholders are
  retained only as explicitly legacy/superseded metadata.
- Reused the Stage 2G.2 cache resolver, verifier, artifact manifest, capsule,
  and CI contracts. Updated formal reports, profile reports, methodology,
  README, old-to-new mapping, acceptance, and focused tests.

### Formal results

| Run | As-of | Slots | Observations | Missing/un-emitted | Status | Artifact logical digest |
|---|---|---:|---:|---:|---|---|
| `petrochina_stage2h1r_real_final` | 2026-08-02 | 8 | 8 | 2 missing-evidence observations / 0 un-emitted | conditional_pass | `0d7536b41217ef0f3d091cc2ef67f7ab6cc8150dcb8793c1606ed96a329fbe5f` |
| `petrochina_stage2h1r_historical_20250401` | 2025-04-01 | 8 | 7 | 1 un-emitted | conditional_pass | `d2da8dc8bac94ae1f622aca63574ed9cdb62ff7ce0e90dcaa69a8e277b1b773b` |
| `petrochina_stage2h1r_early_20210101` | 2021-01-01 | 8 | 0 | 8 un-emitted | conditional_pass | `261460a6883a57d5a04ea408275a990e4ffc0d76135f933d24e97a0b76d5861e` |

The current published risk report and canonical value profile share universe
ID `risk_universe_6231c32047f90529316d931e`. The historical seven-observation
statement remains preserved as a historical result, not as universe cardinality.

### Reproducibility and tests

- Synthetic `stage2h1r_test_capsule` A/B artifact verification passed with no
  differences and shared digest
  `39aa6bd84490b541c1c5dc97e59d8bd796e3f145323d6af1238dc7a2ee73315a`.
- Independent real-cache A/B formal runs
  `petrochina_stage2h1r_real_ab` compared with no differences and shared
  digest
  `0d7536b41217ef0f3d091cc2ef67f7ab6cc8150dcb8793c1606ed96a329fbe5f`.
- Focused Stage 2H/2H.1R tests: `15 passed`.
- Protected official financial-safety vertical slice: `5 passed`, retaining
  the asserted `354 Fact / 102 Metric Result / 16 definitions` baseline.
- Full suite: `967 passed, 2 warnings`.
- Stage 2G.2 `verify-contracts`: `pass_with_explicit_gaps`; ruff, compileall,
  and `git diff --check` passed.
- Local clean-clone preflight returned the expected protected-state failure
  because the current worktree preserves the required stash, pre-existing
  local research inputs, `output`, `runs`, and untracked `agent/goals/`. No
  cleanup, stash mutation, default DB mutation, or destructive reset was used;
  the clean-checkout CI job remains authoritative.

### Protected state at verification point

- Branch remains `feat/m2-value-assessment-mvp`; starting HEAD was
  `401b96aa5284b237c77792d4991e6788c42dd20e`.
- Default DB SHA-256 remains
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Required stash remains
  `stash@{0}: On feat/m2-value-assessment-mvp: protect pre-existing Stage 1B.4
  record edit before Stage 1C`.
- `agent/goals/` remains untracked and preserved.

### Remote CI

Post-push workflows `30745949298` (implementation head) and `30746189865`
(closeout head) completed successfully. Both
`clean-clone (ubuntu-latest)` and `clean-clone (windows-latest)` passed the
clean-clone/offline-input preflight, static/import gates, Stage 2G.2 contract
gate, Stage 2H.1 risk-veto contract gate, independent capsule builds and
comparisons, artifact verification, synthetic risk capsule comparisons, and
the full offline test suite.

## Final status

M2 Stage 2H.1R: **CONDITIONAL PASS**.

Trusted: eight-risk PIT universe, slot contract, input/supplemental evidence
lineage, canonical current value-profile node, legacy placeholder migration,
artifact/cache reproducibility, and CI clean-clone gates.

PetroChina risk-veto profile: **UPDATED WITH EXPLICIT GAPS**. The two
bounded-search gaps remain `missing_evidence`; they are not negative
conclusions. The prior seven-observation historical statement is preserved as
historical evidence, while every evaluation now has eight explicit slots.

The default DB, stash, and untracked `agent/goals/` remain protected. ROIC,
scoring, Web, target price, recommendation, automatic trading, and
market-mechanism work remain not started. Stop after this final report.
