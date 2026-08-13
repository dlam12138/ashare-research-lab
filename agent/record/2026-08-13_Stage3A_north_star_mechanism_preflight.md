# Work Record: M3 Stage 3A — North-Star Mechanism Research Preflight

Status: LOCAL PASS — commit / push / remote CI pending

## Integration checkpoint

- Verified M2 feature tip `241c1804345fcbd8d91a9dd39cc8dfb4a1b3217d` in a clean isolated worktree.
- Created and pushed annotated tag `m2-value-assessment-conditional-closeout` at that tip.
- Created PR #2 from `feat/m2-value-assessment-mvp` to `main`.
- PR CI run `31706668191` passed Windows, Ubuntu, and identity comparison.
- Squash merged PR #2 as `7cc6a9bc51162ee3bac3748576070eb04d4904fb`.
- Kept the M2 tag and feature branch.
- Verified merged main in a clean worktree: R4F.4B verifier PASS and 10 focused tests passed.
- Created and pushed `feat/m3-mechanism-validation-mvp` from merged main.

## Stage 3A implementation

- Established the authoritative Goal contract before implementation.
- Read both project North-Star documents and relevant M2 closeout boundaries.
- Inspected existing provider interfaces without executing network calls.
- Froze the canonical question, directional abnormal-return hypothesis, ex-target primary proxy, threshold family, outcomes, tiered controls, PIT oil alignment, sample rules, four analysis layers, moving-block bootstrap, multiplicity policy, sealed holdout, extreme-date checks, contribution estimate, and evidence ceiling.
- Marked exact `SH_MARKET_EX_601857`, oil, industry, and historical index weights as acquisition-required rather than substituting a convenient index.
- Added a thin deterministic offline build/verify tool and focused contract tests.

## Scope proof

- No real market or control data acquisition/read.
- No holdout read.
- No fitted statistic, regression result, p-value, confidence interval, bootstrap output, index offset, or evidence grade.
- No PetroChina mechanism conclusion or funding-actor inference.
- No minute, Web, M4, trading, recommendation, or `mechanism/` implementation.
- No default DB or M2 artifact mutation.

## Validation

- A/B four-artifact SHA-256 maps: identical.
- Offline verifier: PASS.
- Focused Stage 3A tests: 10 passed.
- First full-suite attempt mixed the original checkout's editable install with this worktree and produced path-dependent legacy failures. Two manifest tests showed imports resolving to `D:\量化分析\src` while test roots resolved here. No old test was changed.
- Full suite rerun with `PYTHONPATH` explicitly bound to this clean worktree: 1943 passed, 3 skipped, 2 pre-existing pandas warnings.
- Final static/protected-state gates, commit, push, and remote CI remain pending.
