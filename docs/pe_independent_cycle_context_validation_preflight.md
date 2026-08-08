# Independent cycle-context validation preflight

## Question and identification

Does the PIT-frozen normalized earnings proxy provide an economically meaningful earnings anchor, as judged by evidence independent of the raw/normalized PE algebra?

The raw-versus-normalized PE direction is rejected as empirical evidence because it is algebraically implied. The primary axis is future realized TTM earnings reversion to an episode-onset frozen normalized-EPS anchor. The primary falsification benchmark asks whether that frozen anchor predicts later realized earnings better than naive persistence of current TTM earnings.

## Reference review and repository cuts

CFA-style normalized earnings supplies the economic interpretation of normalized EPS as mid-cyclical capacity and recognizes average ROE × current BVPS as one method. Walk-forward validation supplies the rule that state `t` may use only information available by `t`, while later earnings is an ex-post outcome. EIA Europe Brent Spot Price FOB is only a feasible future context source. Analyst forecasts, consensus, peer PE, DCF, target price, stock returns, arbitrary peak thresholds, and an sklearn dependency are not adopted.

The repository-specific design uses independent contiguous episode regimes, exact fiscal-quarter horizons, a frozen anchor, separate anchor and outcome ledgers, and metadata-only readiness.

## Episode and anchor contract

`earnings_excess_t = current_ttm_eps_t - normalized_eps_t`. An episode onset is the first raw TTM state after the sign moves from non-positive to positive; it ends when the sign becomes non-positive. Daily market rows never create episodes. The 3Y window contains one contiguous candidate regime with 11 raw states, but it is active at the left boundary. It is therefore explicitly left-censored and is not mislabelled as an observed onset.

At a true observed onset, the raw and normalized state IDs, trade date, raw period end, current TTM EPS, normalized EPS, BVPS, ROE years, fact IDs, and PIT availability/effectivity identities are frozen. Future normalized EPS cannot replace the frozen value. A left-censored regime has `anchor_status = NOT_IDENTIFIABLE_LEFT_CENSORED`: its first observed date is not its onset, all formal anchor fields remain null, and `PROHIBIT_FIRST_OBSERVED_DATE_SUBSTITUTION` applies. Anchor error, naive-current error, and reversion outcomes are prohibited until a true onset anchor is identifiable.

## Outcomes and falsification

The primary horizon is exactly +4 fiscal quarters; +8 fiscal quarters is robustness only. `365/730`-day approximations, partial-quarter proxies, and forecasts are prohibited. Readiness may inspect state identity, period end, availability, effectivity, constituent IDs, existence, and maturity, but never a future EPS amount. Candidate-reference target metadata availability is reported separately from protocol-valid maturity. Metadata is available for the current left-censored regime at both horizons, but valid onset-anchored mature episode counts are zero.

For execution later, all arithmetic is Decimal. A distance ratio below/equal to/above one means moved toward/no change/moved away from the frozen anchor. Separately, absolute error to the frozen normalized anchor is compared with error to the original current TTM EPS. This allows the anchor claim to be contradicted.

Fewer than two mature independent episodes is not testable. Two is a governance recurrence minimum, not statistical significance. With three or more episodes, disagreement must be reported as mixed; no result-driven percentage threshold is permitted.

## Readiness and next boundary

Metadata shows one 3Y candidate regime, zero observed onsets, zero valid onset-anchored episodes, and one candidate-reference target metadata record at each horizon. Current 3Y validation is not executable. The remaining four 5Y facts are justified primarily to recover the left-censored onset if it lies inside the frozen 5Y window, and secondarily to expand the opportunity for additional independent episodes. They were not acquired here.

The 5Y backfill guarantees neither onset recovery, two episodes, executable validation, nor a favorable outcome. After rebuilding the frozen 5Y window, valid results include onset recovered with additional episodes, onset recovered but only one episode, continued left-censoring at the 5Y boundary, or no additional episodes. If fewer than two valid onset-anchored episodes remain, the result is `INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY` and returns to North-Star review. Automatic extension to earlier history is prohibited. The next authorized stage, if explicitly started, is R4F.4A1. No formal Brent data, future outcome evaluation, PE scoring, production result, or M3 work was performed.
