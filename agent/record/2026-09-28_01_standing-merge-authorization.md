# Standing PR merge authorization

User: remove repeated merge approval requirement; automatically merge.
Goal: agent/goals/2026-09-28_standing_merge_authorization.md.
Verified clean start at ae00efe7d5aa7cd592339b199c65281b9c1c441d.
PR #32 merged: 82110db539f8ff017e9db9894ace5c8815bca288 (head 91ef21a).
PR #33 merged: ae00efe7d5aa7cd592339b199c65281b9c1c441d (head 58f0bd0).
Each had 42 successful checks at pre-merge verification; exact head guards
used. Branches retained, no direct main push or deletion.

Replace only per-PR confirmation restriction in tracked AGENTS.md. Preserve
independent review, checks, stage/data/research restrictions and safety rules.
Older Goal stop points remain historical; the new user authorization supersedes
their per-PR merge confirmation requirement, not other restrictions.
Root M2 worktree has unrelated changes/untracked AGENTS.md and is not modified.
It will not automatically inherit this tracked rule until safely reconciled.
Validation: inspect exact diff; whitespace checks; Git/live remote and protected
database/stash checks. No product code changed; no claim of new test execution.
