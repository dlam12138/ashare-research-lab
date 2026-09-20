# M4 real-source chain integration acceptance

Date: 2026-09-20. [Goal](../agent/goals/2026-09-20_m4_real_source_chain_integration.md) · [record](../agent/record/2026-09-20_01_m4-real-source-chain-integration.md) · [design gate](../docs/m4_real_daily_adapter_design_gate_v1.md) · [source design](../docs/m4_real_daily_source_contract_design_v1.md) · [K1 acceptance](2026-09-14_m4_real_source_offline_kernel.md).

## Assessment

The separately authorized gate, design and offline K1 stages form a coherent linear chain and were replayed onto post-PR21 main without file conflict. Their historical evidence remains dated and intact. New reconciliation text records that PR #20 and PR #21 are merged but provide synthetic—not real-source—evidence.

The K1 proof remains deliberately non-authorizing: it reads only injected in-memory fixture bytes, declares calendar and real-source validation false, emits no matrix or statistics, and does not authorize execution or consume a research outcome. DSH's three reproducible findings were corrected inside the whitelisted kernel and test files: scale-preserving plain decimals now accept the design's zero/negative examples, every present value is validated before PIT classification, and holdout dates are forbidden in the calendar domain.

Focused validation passed **17/17**; the post-PR21 upstream regression passed **299/299**; Ruff check and format, Git whitespace and Markdown hygiene checks passed. Protected HEAD, stash and database hash are unchanged. No real provider, database contents, market observations or holdout were accessed.

Local pre-submit verdict: **PASS**, subject to final DSH diff recheck and remote PR/CI verification. This acceptance authorizes neither merge nor K2/provider/real-data work.
