# Stage4P Work Record — North-Star v2 Adoption & Architecture Preflight

## Scope

Governance and architecture preflight only. No M4 production implementation, real outcome read, real data acquisition, literature acquisition, or alpha/trading research.

## Starting state

- Starting worktree: `D:\量化分析` (protected dirty M2 worktree; not mutated)
- Isolated worktree: `D:\量化分析-m4-preflight`
- Starting/base branch: `main` via `origin/main`
- Starting/base SHA: `a72b923256a483f2a8d5faefe657ae844dbace19`
- Origin verification: `origin/main == a72b923256a483f2a8d5faefe657ae844dbace19`
- Feature branch: `feat/m4-generic-research-preflight`
- Original worktree stash preserved; no stash pop performed.

## North-Star identity

- v1 path: `A股个股研究与市场机制验证平台-项目北极星.md`
- v1 SHA-256: `ad297e609b49bc6f76421ae6b50d213a003f6cec11c964d7da27f20127bd570f`
- v2 requested external path: `D:\量化分析-inputs\A股个股研究与市场机制验证平台-项目北极星-v2.md`
- Requested external path status: missing.
- Actual user-provided v2 source used: `D:\量化分析\A股个股研究与市场机制验证平台-项目北极星-v2.md`
- `NORTH_STAR_V2_INPUT_SHA256`: `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`
- v2 byte size: `38843`
- v2 line count: `1696`
- New canonical North-Star SHA-256: `f411235a94396443c6ffabdc6501c096d5d4163d6fb54b41678109fb3fc6a307`
- Temporary copied `-v2.md` was removed from the isolated worktree after exact adoption; only the canonical path remains.

## Protected baseline identities

- `reports/*` and `acceptance/*` stage 1–3 selected artifacts: 194 files, aggregate `7a147f62224732a31b35a545c5286c235e1702aff63d9baddcf17dcdd7b4e46a`.
- `reports/m3_*` and `acceptance/m3_*`: 85 files, aggregate `c4c9d52fc14a2dcb53efc7f59bc01824dbaf58c5ce3891ed5abe5f0c0768eb48`.
- `src/ashare_research/mechanism/*`: 21 files, aggregate `733f14bf7b060b6e1b1131f1219708b1ca7d6a0e46764fe9b763b6fb651dd625`.
- No M3 mechanism production code or frozen M3 artifact was intentionally changed.

## Audit and architecture

- v1 → v2 audit: `PASS`; no automatic trading, recommendation, large anomaly mining, or PnL optimization scope conflict.
- Reuse decision: `M3_PROVEN_CORE_REUSE_PREFERRED`.
- Architecture: `THIN_GENERIC_LAYER_OVER_PROVEN_M3_CORE`.
- M4-A: daily conditional/controlled mechanism research only; config → compiled frozen contract → bounded plan/execution → artifacts/evidence.
- M4-B: provenance-aware candidate metadata and state machine only; no literature full text and no real candidate dataset.
- PetroChina-specific identities, Brent/CNI/SH/601857 assumptions, -1% threshold, holdout dates, Stage3DB history, SSE repair artifacts, and 57 missing securities remain `CASE_EVIDENCE`.
- `knowledge/`, `engine.py`, DB schema change, and real data are not required in Stage4P.
- Future economic significance/tradability: `CURRENTLY_NOT_AUTHORIZED`.

## Changed files

- Canonical North-Star file (exact v2 replacement)
- `README.md`
- Stage4P reports under `reports/`
- Stage4P Goal under `agent/goals/`
- Stage4P acceptance under `acceptance/`
- Stage4P governance tests under `tests/`
- This work record

## Validation record

- focused Stage4P tests: `python -m pytest tests/test_m4_stage4p_governance.py -q` → `12 passed`
- North-Star consistency and M3 boundary tests: Stage4P plus all `tests/test_m3_*.py` → `325 passed, 1 skipped`
- full `pytest`: `python -m pytest -q` → `2258 passed, 4 skipped, 2 warnings`
- `ruff check .` → passed
- `python -m compileall -q src tests` → passed
- `git diff --check` → passed; canonical Markdown intentional hard-break whitespace is covered by a path-level `.gitattributes` exception without changing bytes
- JSON validation: all 7 `reports/m4_stage4p_*.json` parsed successfully
- frozen identity comparison: Stage4P governance test passed; protected aggregates remain byte-identical
- CI Windows/Ubuntu: pending remote CI result
- PR: pending; never merge automatically

Full-test warnings are the existing pandas `to_datetime` format-inference warnings in `tests/test_quality.py`; no test failure or new research execution occurred.

## Final stop

`STOP_FOR_NORTH_STAR_V2_MERGE_REVIEW`
