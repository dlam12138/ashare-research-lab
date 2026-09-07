# Goal: Astra planning and Luna implementation routing

## Objective and baseline
User approved landing the proposed repository routing mechanism as a separate small PR.
Verified origin/main and GitHub main: 349101a1bae61dc4a11991e2420d21eedb69ff87.
PR #9 remains OPEN at 13a441ffc0deedc6cc49001d3009e8aaa5442628; do not merge or modify it.
Branch: codex/astra-luna-model-routing; clean independent D:/量化分析-model-routing.
Original M2 HEAD: 3679b1bac7a1634c6452784a4d8f6d139966f222, dirty status retained.
Stash: cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f; original DB SHA256:
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
Installed codex-cli: 0.153.4. Original AGENTS.md is untracked and must stay untouched.

## Scope and behavior
Track root AGENTS.md preserving existing governance and linking agent/agent.md and
agent/model-routing.md. Add concise routing protocol and project-scoped Luna custom-agent
configuration; add project agent defaults only if supported by installed runtime.
Astra owns planning/invariants/independent acceptance, one Luna worker owns bounded execution.
Explicit gpt-5.6-luna / medium selection; minimal fresh context; no recursive delegation;
two unsuccessful fixes or semantic/protection conflicts escalate to parent. No silent model
fallback or savings guarantees. Existing approvals and runtime permissions still apply.
One task contract/record/acceptance; worker returns concise evidence and writes only assigned
files. Evidence from actual tools governs acceptance. No automatic next stage or merge.

## Forbidden scope
No application src/tests/research artifacts, frozen designs, North-Star, dependency/CI changes,
user-global configuration, other worktree changes, deletion, branch cleanup, real research,
new CLI executor or PR #9 integration. Preserve original AGENTS.md and all runtime data.

## Validation
Parse new TOML with Python tomllib and inspect pinned model/effort and permission inheritance.
Use codex --version / codex features list to check local configuration loading without an
API run. Verify instructions link correctly and original governance is preserved.
Actually delegate bounded document/config implementation to Luna while Astra validates
runtime compatibility and acceptance requirements. Record any runtime capability limitations.
Run existing focused entry/protection tests using explicit PYTHONPATH for this checkout:
python -m pytest -q tests/test_m4_stage4p_governance.py tests/test_project_entry.py
git diff --check
No new formatting tests or duplicate local full suite for docs/config only; existing CI stays.

## Acceptance and delivery
Protocol and project configuration agree; explicit Luna delegation succeeds; focused and
protection checks pass. Commit only scoped files, ordinary feature push and one PR to main.
Audit final HEAD/diff/status/stash/DB/remote. Final CI results and HEAD go in PR description.
Verdict PASS / CHANGES_REQUIRED / BLOCKED. STOP before merging this PR or #9.
