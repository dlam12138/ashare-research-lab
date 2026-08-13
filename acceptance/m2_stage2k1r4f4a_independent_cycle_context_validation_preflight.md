# M2 Stage 2K.1R4F.4A acceptance

Status: completed

Closeout verdict: PASS — CI CONFIRMED

Remote CI: CONFIRMED

Decision: `PE_INDEPENDENT_CYCLE_VALIDATION_PROTOCOL_FROZEN_5Y_BACKFILL_REQUIRED`

3Y independent validation executable: NO

Reason: `LEFT_CENSORED_EPISODE_ONSET_NOT_OBSERVED`

PE scoring: `BLOCKED_UNCHANGED`

Next stage: R4F.4A1 — NOT STARTED

- Objective: freeze a PIT-safe, falsifiable, PE-algebra-independent cycle-context validation protocol and metadata-only readiness inventory.
- Verified baseline: `feat/m2-value-assessment-mvp` at `f1ef8ec`; R4F4 decision trusted; 728/728 series; one contiguous above-normalized regime; scoring blocked.
- Allowed scope: the R4F4A docs, contract, preflight reports, review module, thin offline CLI, tests, acceptance, and record listed by the task.
- Forbidden scope: protected registry/policy/shadow/capsule/sensitivity artifacts, R4F3/R4F3A/R4F4 committed artifacts, default DB, 5Y acquisition, Brent values, future outcomes, scoring, M3, force push, merge, PR, and tag.
- Required behavior: episode-only evidence, frozen onset anchor, exact 4Q/8Q targets, metadata-only readiness, separated future metadata, anti-leakage, and identification-based backfill justification.
- Required tests and validation: R4F4A and predecessor suites, full pytest, Ruff, compileall, diff check, secret/path scan, protected hashes, default DB, stash, branch/HEAD/remote checks.
- Acceptance criteria: deterministic artifacts verify; no future EPS value; protocol and interpretation frozen; correct decision gate; protected state unchanged.
- Stop conditions: stop after final-tip CI; do not start acquisition or outcome execution.
- Commit/push: scoped commits and normal pushes are authorized for closeout.

## Acceptance evidence

The preflight derives one 3Y left-censored candidate regime, zero observed onsets, and zero valid onset-anchored episodes. Candidate-reference target metadata exists at both 4Q and 8Q, but protocol-valid mature counts are zero and validation is not executable. The exact decision is `PE_INDEPENDENT_CYCLE_VALIDATION_PROTOCOL_FROZEN_5Y_BACKFILL_REQUIRED`, while scoring remains blocked.

The 5Y justification is onset recovery first and additional-episode opportunity second. Backfill guarantees no particular identification or outcome. The frozen 5Y stop rule prohibits automatic earlier-history expansion; fewer than two valid episodes after 5Y returns `INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY` to North-Star review.

Validation evidence: R4F4A 19/19; R4F1–R4F4 focused regressions 196/196; full suite 1905/1905; Ruff, compileall, artifact rebuild, diff check, boundary hashes, default DB hash, and secret/path scan passed. Two pre-existing pandas date parsing warnings remain non-blocking.

Implementation-tip CI evidence: GitHub Actions run [31250532941](https://github.com/dlam12138/ashare-research-lab/actions/runs/31250532941) completed successfully for `4d46dcc6ddd7a625058af8542ef3205d05960735`. The Ubuntu and Windows clean-clone jobs both passed their full offline suites and produced identity fingerprint envelopes; the provenance-gated cross-platform identity comparison also passed.
