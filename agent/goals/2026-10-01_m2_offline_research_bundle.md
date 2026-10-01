# M2 offline research bundle

Objective: one complete usable batch: compile existing PetroChina value,
financial state/safety, valuation percentiles, shadow dimensions, PE disposition,
risk and explicit gaps into readable Markdown + JSON, export with portable
source attachments and checksum manifest, independently verify exported bundle.
User requested larger functional batches and minimal necessary testing.

Verified base origin/main/live main 73a462f8b6e118c9ab82c24934f2ef790a4f9ecf;
clean owned worktree, branch codex/m2-offline-research-bundle. Preserve primary
dirty worktree 3679b1b, stash cb568ef, local main 966206f and protected DB.

Scope: new src/ashare_research/tools/value_research_bundle.py,
new tests/test_value_research_bundle.py, narrow README; this Goal, one record,
one acceptance. Fixed nine baseline reports: petrochina_value_profile.json,
petrochina_dimension_scoring_shadow_v6.json, petrochina_risk_veto_report.json,
m2_explicit_gap_ledger.json, petrochina_pit_valuation_percentile_profile_v1.json,
petrochina_pit_financial_state_timeline_v2.json,
m2_stage2k1r4f4b_pe_disposition_decision_v1.json,
petrochina_value_profile_2021_2026.md, petrochina_financial_safety_2021_2025.md.
Pin their SHA256 from actual baseline, no old-source edits.

Behavior: default Markdown stdout; --json for canonical JSON; --output NEW_DIR
exports report.md, report.json, source attachments under sources/reports/ and
manifest.json; --verify DIR validates package using retained bytes, independent
of installed repository reports. CLI modes mutually exclusive; no input source
selection/acquisition. Deterministic output, original decimals/IDs/statuses and
source dates preserved; source hashes certify integrity only. Explicit mixed-date
historical compilation, never a unified as-of PIT query or refreshed research.
Display annual vs TTM valuation separately, shadows clearly nonproduction,
ROIC not computable, PE numeric scoring deferred, missing dividend/risk evidence
not zero/negative absence. No overall score/ranking/recommendation/new computation.
Existing output/symlink rejected; validate/render all bytes before creating output.
Never delete foreign artifacts. Late IO failure may leave only an owned partial
package; verifier rejects it. Failures sanitized with nonzero exit and no stdout.

Forbidden: existing implementations/tests/contracts/reports/events/config/DB
mutation, new data/literature acquisition, real backtests/M4/holdout, new scoring
or eligibility, new dependencies, unrelated cleanup/Git/main push or force push.

Minimal tests: four complete meaningful cases: readable/JSON coherent source
projection; actual CLI export+portable verification/determinism; corruption
rejected even with edited manifest; existing output rejected and unchanged.
No expanded test matrix or repeated full local suite. Parent runs once:
python -m pytest -q tests/test_value_research_bundle.py
& 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/tools/value_research_bundle.py tests/test_value_research_bundle.py
python -m ashare_research.tools.value_research_bundle --output tmp/m2-research-bundle
python -m ashare_research.tools.value_research_bundle --verify tmp/m2-research-bundle
git diff --check
Set PYTHONPATH to owned worktree src; hosted mandatory CI owns full regression.

Acceptance: four tests/static checks/real export/verify succeed, package source
and rendered bytes verified, six-file scoped diff and protected states unchanged.
Stop on scope expansion, unexpected protected changes, failed gates, worker
failure/two failed repairs. One bounded DSH edits only module/tests/README;
parent owns exact validation/Git/evidence. No worker tests or manual simulations.
Commit/push scoped codex branch, PR and independently gated merge under standing
authorization; verify expected head/base/all required checks. No next research
stage authorized by this reporting task.
