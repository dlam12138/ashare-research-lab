# Acceptance: Astra/Luna routing

Status: LOCAL_PASS; final HEAD and remote CI are recorded in the delivery PR.
Goal: [task contract](../agent/goals/2026-09-07_astra_luna_model_routing.md).
Record: [work log](../agent/record/2026-09-07_02_astra-luna-model-routing.md).

## Baseline and files
- origin/main and GitHub main: 349101a1bae61dc4a11991e2420d21eedb69ff87.
- Independent branch codex/astra-luna-model-routing in D:/量化分析-model-routing.
- PR #9 remains OPEN at 13a441ffc0deedc6cc49001d3009e8aaa5442628, outside this diff.
- Seven new files: AGENTS.md, agent/model-routing.md, .codex/config.toml,
  .codex/agents/luna-worker.toml, this acceptance, linked Goal and work record.
- No product code, tests, README, workflow, dependencies or frozen artifact changed.

## Behavior and runtime evidence
Root governance is preserved verbatim as a text prefix from the original untracked
D:/量化分析/AGENTS.md; that original file was not modified. Entry links resolve.
Project settings select one child, gpt-5.6-luna, medium. The named worker pins the same
model/effort, reads the task/governance contracts and inherits existing permissions.
Protocol covers absolute worktree/Goal handoff, bounded writes, parent-owned acceptance,
minimal context, no recursive delegation, two-failure escalation, no silent model fallback,
and test reuse without weakening gates. The user's original authorization boundaries apply.

Actual delegation in this task used `model=gpt-5.6-luna`, `reasoning_effort=medium`,
`fork_turns=none`, task `/root/luna_routing_worker`. Luna wrote the four mechanism files;
Astra independently checked runtime configuration, protections and the final diff.
The first Luna turn ended at a usage limit after writing a draft. After the user's
"继续", the same Luna agent resumed and completed the draft plus focused review corrections.
No alternate model silently took over implementation, and the worker did not commit or push.

Installed codex-cli 0.153.4, normal app-server `config/read` with this worktree as cwd:
```json
{"enabled":true,"max_concurrent_threads_per_session":1,"default_subagent_model":"gpt-5.6-luna","default_subagent_reasoning_effort":"medium"}
```
The project layer reports disabledReason=null. Root routing instructions also appear in
`codex debug prompt-input`. Named custom-agent TOML is checked against the official schema;
the current collaboration tool does not expose named-agent selection, so the actual delegation
test used explicit parameters. Prompt-input renders messages, not a complete custom-agent
tool inventory; absence of the worker name there is not claimed as discovery evidence.

## Commands and outcomes
- `codex --version`: codex-cli 0.153.4.
- `codex features list`: multi_agent stable true; no feature settings were changed globally.
- `python tmp/check-routing-files.py`: PASS; UTF-8 tomllib parsing, exact routing defaults,
  pinned worker model/effort, inherited permissions, root governance prefix and relative links.
- `python tmp/check-routing-config.py`: PASS via initialize + config/read, cwd=this worktree,
  includeLayers=true; effective routing values above. No model execution in this probe.
- `codex debug prompt-input`: rendered root entry successfully; no model inference.
- Focused tests with PYTHONPATH set to this checkout's src and the existing dependency runtime:
  `D:/量化分析-m4a2i/.venv/Scripts/python.exe -m pytest -q tests/test_m4_stage4p_governance.py tests/test_project_entry.py`
  → **15 passed in 0.13s**. Verified imported package path points to this checkout.
- `git diff --check`: PASS. Final staged diff checked separately before commit.
- Protected-path diff against origin/main: empty. Existing North-Star and 194 research-artifact /
  85 M3-artifact / 21 M3-source aggregate checks passed without hash updates.
- Local full pytest intentionally not repeated for this docs/config-only change; unchanged
  Windows/Linux CI runs the repository's complete existing gates on the PR.

## Limitations and preserved state
An initial strict app-server probe failed because the pre-existing user-global config has
unknown field mcp_servers.fetch.type. Normal loading and effective project routing succeed;
the unrelated global file was not changed. An intermediate temporary probe edit had a shell
quoting error; it changed no tracked file. Probe helpers/schema output stay ignored under tmp/.
These are observed environment/probe limitations, not a claimed token-savings measurement.

Original M2 HEAD remains 3679b1bac7a1634c6452784a4d8f6d139966f222 with its previous dirty files.
Stash remains cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f, one entry. All eight prior worktrees
are retained. Original DB SHA256 remains
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.
The new tree has no default research DB. Local main ref remains untouched; origin/main and
GitHub main are the verified base. Final feature local/origin/remote equality is recorded in PR.

Main agent selection remains explicit in the client; settings do not hot-switch current tasks.
The tracked rules travel with the branch after checkout/merge, not to old worktrees automatically.
Stop before merging this PR or #9. No new research stage is authorized.
