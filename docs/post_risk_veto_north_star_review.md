# M2 Stage 2I — Post-risk-veto North-Star Review

Date: 2026-08-02
Scope: selection of the next bounded value-assessment preflight after Stage 2H.1R
Decision: **ALLOWED**

This is a qualitative review. It does not assign numeric weights, scores, ranks,
targets, recommendations, or production metrics. The decision authorizes a
ROIC methodology and official-fact readiness preflight only; it does not
authorize a production ROIC calculation.

## Candidates compared

| Candidate | Direct value-assessment contribution | Current boundary |
|---|---|---|
| ROIC methodology and fact readiness | Tests whether operating capital, rather than only equity, assets, financing safety or market price, is earning a return | Allowed as a contract/readiness preflight; production computation remains gated on official facts and matching |
| Close remaining dividend/risk evidence gaps | Improves evidence completeness for value realization and risk-veto interpretation | Useful closeout work, but it does not answer the operating-capital return question |
| M2 value-profile closeout without ROIC | Consolidates the existing descriptive profile and keeps current gaps visible | Does not add the missing operating-capital lens |
| Market-mechanism MVP | Tests market-behaviour hypotheses and alternative explanations | Separate research module; it cannot substitute for accounting-capital evidence |

## Review answers

### 1. Which candidate most directly improves the answer to whether operating capital creates value?

The ROIC methodology/readiness preflight. The existing profile already contains
ROE/ROA, financial-safety, cash-flow, dividend, valuation and risk-veto layers.
ROE isolates parent equity, ROA uses total assets, and financial safety describes
funding constraints; none directly establishes whether the operating capital
supporting an integrated oil business earns an after-tax operating return.
ROIC is the most direct next lens, provided NOPAT and invested capital are
matched rather than assembled from attractive but incompatible proxies.

### 2. Would ROIC materially add information beyond the existing layers?

Yes. ROIC can connect operating earnings after tax to the capital base employed
to produce them, while ROE is affected by leverage, ROA does not isolate
financing/non-operating capital, and financial safety does not measure operating
return. It is therefore an incremental descriptive lens, not a replacement for
those layers and not a scoring input.

### 3. Can the required facts be obtained from audited statements and notes?

The annual reports and notes provide the relevant source boundary: operating or
pre-tax profit, tax expense, debt components, lease liabilities, cash and cash
equivalents, equity/NCI, investments, associates/JVs, goodwill, and operating
assets/liabilities are disclosed across the audited statements and notes. The
repository already proves official dual-source, CAS/consolidated, unit,
availability and restatement handling for several of these concepts. Coverage
is not assumed complete: exact concepts, comparative values, and PIT/version
chains must be audited year by year before a shadow calculation.

### 4. Which items are accounting facts and which are analytical policy choices?

Accounting facts are the reported statement/note values and their context:
period, consolidated scope, CAS, unit/currency, source document, filing date,
available-at date, restatement/version chain, debt and lease components, tax
expense/current-deferred tax, NCI, investments, associates/JVs and goodwill.

Analytical policy choices are the NOPAT bridge, operating-tax allocation and
fallback order, financing versus operating invested-capital view, cash and
excess-cash boundary, debt/lease matching, NCI treatment, associate/JV and
goodwill treatment, average-balance rule, loss-year and non-positive-denominator
handling, and whether an output is descriptive or eligible for any later gate.
The latter must never be labelled an official accounting rule.

### 5. Can a transparent contract be registered without pretending there is one universally official ROIC formula?

Yes. The contract will register one primary candidate only after comparing an
EBIT bridge, operating-profit bridge and directly adjusted operating-earnings
bridge against the evidence. It will retain rejected candidates and explain
why. It will explicitly distinguish reported facts from analytical choices,
require numerator/denominator scope matching, and set `score_eligible=false`.
No candidate will be selected because it produces the most attractive value.

### 6. Could remaining evidence gaps invalidate the work?

Yes, if the gaps force net profit or parent-attributable profit into NOPAT,
force ending invested capital to stand in for a missing opening balance, hide
all cash subtraction, mix consolidated and attributable scopes, or use manual
plugs for tax, leases, associates/JVs or NCI. The existing Stage 2F dividend
and Stage 2H risk gaps remain explicit profile limitations; they do not by
themselves invalidate this preflight. ROIC-specific missing facts will instead
lead to `ROIC_FACT_ACQUISITION_REQUIRED` or `ROIC_BLOCKED`, as defined by the
Stage 2I contract.

### 7. Why does market-mechanism research remain separate from value assessment?

Market-mechanism research asks statistical questions about prices, liquidity,
participants and conditional market behaviour. ROIC asks an audited-statement
question about operating earnings and capital employed. Combining them now
would blur accounting evidence with market hypotheses, expand the scope beyond
the current value profile, and weaken both PIT and reproducibility boundaries.

### 8. Why does scoring remain closed?

The current layers are descriptive and explicitly `score_eligible=false`; the
project has no approved weights, thresholds, rating semantics or scoring
readiness gate. A ROIC methodology contract must add evidence and explanation,
not silently turn a new ratio into a score or recommendation.

## Review evidence and repository-specific cuts

The review considered the existing Stage 2G.2R/Stage 2H.1R acceptance records,
the current ROE/ROA and financial-safety contracts, the canonical Fact/Context,
Identity, PIT, version-chain and Metric Engine code, and official PetroChina
annual-report bundles for FY2021–FY2025 plus the FY2020 opening denominator
evidence. External methodological review covered:

- CFA Institute, [Capital Investments and Capital Allocation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/capital-investments-and-capital-allocation).
- Damodaran, [Financial measures and ratios](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/definitions.html), including the distinction between after-tax operating income, invested capital and excess returns.
- FinanceToolkit, [transparent financial analysis repository](https://github.com/JerBouma/FinanceToolkit), for formula organization and explicit average invested-capital presentation.
- OpenBB, [standardization](https://docs.openbb.co/odp/python/developer/standardization) and [provider extensions](https://docs.openbb.co/odp/python/developer/extension_types/provider), for provider-to-standard-model separation.
- Ministry of Finance, [Enterprise Accounting Standards index](https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/index_2.htm), [Income Tax Standard 18](https://kjs.mof.gov.cn/zt/kjzzss/kuaijizhunzeshishi/200806/t20080618_46230.htm), and annual-report implementation guidance on borrowing costs, leases, deferred tax, consolidation and financial instruments.
- PetroChina, [2024 Annual Report](https://www.petrochina.com.cn/ptr/rdxx/202504/09bf572f6d2d45edbf2da8a055711480/files/388c17360377474ea5ebca247d8aeee1.pdf), with the repository's committed FY2021–FY2025 annual bundles as the auditable local evidence registry.

Borrowed designs are limited to the conceptual principles of operating-return
matching, standard-model separation, explicit formula organization and
input/output lineage. No external runtime dependency, formula library,
provider, XBRL processor or scoring model is copied. Repository-specific cuts
are Decimal 28 / `ROUND_HALF_EVEN`, canonical Fact IDs and contexts, explicit
PIT `available_at`, superseding version chains, no default-DB writes,
run-scoped non-production outputs, and fail-closed missing-fact semantics.

## Gate decision

**ALLOWED** — proceed to freeze ROIC methodology and audit official-fact
readiness. The expected Stage 2I outcome is a controlled preflight, not a
production ROIC computation. If the policy/evidence audit cannot support one
internally consistent formula, stop with `ROIC_BLOCKED`; if the formula is
frozen but facts are missing, stop with `ROIC_FACT_ACQUISITION_REQUIRED`.
