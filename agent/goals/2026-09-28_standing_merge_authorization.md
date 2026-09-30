# Goal: persist standing PR merge authorization

User explicitly removed per-PR merge confirmation and authorized automatic
merging. Objective: persist that narrow change without expanding data/research
or destructive-operation authority. PR #32 and #33 checked green (42 checks
each) and merged at user direction, with exact expected head commits.
Verified base: origin/main ae00efe7d5aa7cd592339b199c65281b9c1c441d;
clean codex/standing-merge-authorization branch. Protected stash
cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f and M2 database SHA256
4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6.

Allowed: AGENTS.md merge rule, this Goal/record, branch commit/push/PR and
merge after review and passing required checks (or hosted auto-merge waiting
for them). No historical contract rewrite, dirty M2 worktree edit, data access,
research, force push or direct main push. Stage authorization remains separate.
Required behavior: standing authority covers scoped reviewed PRs, including
this governance change; stop on conflicts, failed checks or scope expansion.
Validation: git diff --check; git diff --cached --check; inspect exact textual
diff; verify PR heads/merge commits, clean tree, live main and protected hashes.
Acceptance: #32/#33 merged, governance rule committed/published, final report
distinguishes merged versus pending CI/auto-merge. No false completion claim.
