# M4 provider-evidence contract v2 work record

Goal: `agent/goals/2026-09-21_m4_provider_evidence_contract_v2.md`.

Objective: create an offline, additive evidence-contract amendment that makes
a future authorization decision precise without acquiring data.

Scope: the Goal, design, canonical JSON contract, this record and acceptance
packet only. Non-goals: network/provider access, provider selection, adapter or
test implementation, observations, database, holdout, statistics and execution.

Start state: clean isolated branch at PR #25 merge `8ecc2e7`, source tree
`ba13f31c`; v1 manifest digest `26542836…724f`; protected M2 HEAD, stash and
database hash recorded in the Goal. The initial branch upstream inherited
`origin/main`; it was removed before work began, and explicit-refspec-only push
is required.

DSH's initial Goal review returned `CHANGES_REQUIRED`. The Goal was amended to
freeze the probe window firewall, canonical digest formulas, terminal lineage,
raw/licence retention, exact commands, changed-path gates and safe push rule.
A focused DSH re-review returned `PASS` before artifacts were drafted.

Implemented `M4_PROVIDER_EVIDENCE_CONTRACT_V2` and its design narrative. The
contract preserves all terminal v1 dispositions, defines future evidence
classes and failure codes, and keeps acquisition v2 unauthorized.

Local validation recomputed contract digest
`b5f6b8d54f5fe733d41ed018a89b3065fc05a0e7130c072c66d19e469221bdca`,
recomputed the frozen v1 digest, matched every terminal predecessor and code,
and passed encoding, link, secret/path, quarantine-inventory and protected
baseline checks.

Validation results and final Git/PR state are recorded in the acceptance file.
Remaining authorization boundary: no acquisition-v2 probe may run without a
new explicit user decision containing every frozen authorization field.

Parent Git handoff created artifact commit
`546c6cfaa3cf11ae78a705213be7d1c0996dde52`, pushed only the v2 feature branch,
and opened PR #26. `origin/main` remained at the verified PR #25 merge commit.
This record and the acceptance file are the only paths authorized for the
second and final documentation-only handoff commit.

Final DSH handoff recheck returned `PASS` after the full artifact commit SHA
was corrected and independently matched against HEAD, its parent and the local
remote-tracking ref.
