# M4 offline synthetic demonstration entry

Objective: make the existing five-stage synthetic mechanism pipeline runnable
without caller Python code, independent of the Brent publication evidence wait.

Verified baseline: origin/main c1b68a4772f420ad9392e7d33de25be6fa71220a,
live remote equal; clean owned worktree; branch codex/m4-synthetic-demo-cli.
Earlier local email evidence branches are retained. Primary user worktree HEAD
3679b1b, stash cb568ef and protected research.duckdb remain untouched.

Allowed scope: new src/ashare_research/synthetic_demo.py,
tests/test_m4_synthetic_demo_cli.py, narrow README usage, this Goal, one record
and one acceptance file. Module command python -m ashare_research.synthetic_demo.

Required behavior: one fixed, clearly invented 24-row daily synthetic example;
construct request using public stage APIs and public identity/digest helpers;
run existing run_synthetic_pipeline and validate its result. No copied statistics,
no imports from tests or private upstream helpers. Default readable stdout gives
completed stages, row count, digest and the executor's verbatim interpretation
boundary. --json emits serialize_pipeline_result bytes verbatim, with final newline.
Arguments expose only help and --json: no input, config, seed, provider or output
path. No filesystem/network/database/environment access by the module. Bootstrap
is explicitly disabled for the bounded demonstration; no registry state binding.
Parser errors exit 2; known validation errors return sanitized failure, no result.

Forbidden: modifying frozen stage implementation/export/schema/design/fixtures or
existing tests, adding dependencies, real data acquisition/execution/holdout,
registry transitions, market conclusions, data/outputs/evidence mutations,
unrelated primary changes, stash or user worktrees. No credentials or email action.

Tests: genuine subprocess execution of text and JSON, deterministic bytes across
processes, valid canonical envelope and digest, all synthetic provenance and
boundary, unsupported input arguments fail before execution, failure sanitization,
public entry/no IO probes. Tests use ordinary pytest fixtures; no custom temp-root
or permissions bypass. Parent independently reviews implementation and runs tests.

Exact validation commands:
- python -m pytest -q tests/test_m4_synthetic_demo_cli.py tests/test_m4_synthetic_pipeline_orchestrator.py
- & 'D:/量化分析/.venv/Scripts/python.exe' -m ruff check src/ashare_research/synthetic_demo.py tests/test_m4_synthetic_demo_cli.py
- python -m ashare_research.synthetic_demo
- python -m ashare_research.synthetic_demo --json
- git diff --check
Hosted required checks cover full regression once; do not repeat locally.

Acceptance: above checks pass; serialized result verified through authoritative
validator; only six scoped files changed; frozen baselines and protected DB
unchanged; actual branch/HEAD/diff/status/stash/remote independently checked.
Record exact evidence and any worker deviations in acceptance.

Stop on broader scope, failing guards, worker failure or two unsuccessful fixes,
unexpected protected mutation or conflicts. DSH edits only the new module/new
tests/README; parent owns tests, records, Git and review. No recursive delegation.

Commit/push: commit scoped change on codex branch, push that branch, open PR;
standing authorization permits merge only after independent PASS, all required
checks, exact head/base and clean mergeability. Never push main or force push.
No subsequent research stage is authorized by this usability task.
