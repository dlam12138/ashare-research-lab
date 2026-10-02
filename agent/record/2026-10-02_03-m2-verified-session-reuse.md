# Verified canonical session reuse

Goal established before implementation; actual primary and owned branch/HEAD,
remote/live main, worktree/stash, governance/protocol/recent records and relevant
source/tests inspected. Fresh protection snapshot and tracked hash map captured.
Branched clean owned worktree from d2657d2, primary/foreign changes preserved.
Latest user expressly requires own work; no DSH/subagents.

Observed duplicate build_session calls after verify_session in review, audit and
comparison. Chosen change returns the canonical bytes already compared by the
same verification, retaining the existing public metadata-only API. Fresh loads
every call, no cache or source reopening. This reduces full builds by50% for
these consumers; it does not claim a measured50% wall-clock speedup.
Implemented public fresh verified-byte loader, preserved legacy metadata API,
switched all three consumers to same verified bytes. Verification body/order and
sanitized errors unchanged. Fresh owned dictionaries each call, no cache.
Four new acceptance cases passed33.95s in one run/no skips; scoped Ruff first-pass
success, diffcheck passed. Instrumented actual builds: review1/audit1/compare2,
formerly2/2/4; original retained JSON hashes matched for all three consumers.
Actual CLI exportexit0,51files compared byte-for-byte against pre-change retained
export, every file identical (including nested evidence and outer manifest).
No local full suite/repeated tests; exact commands and original hashes in matching
acceptance. Protected state comparisons and hosted CI/final review pending.
