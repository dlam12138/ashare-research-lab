# Goal: M4 provider-evidence contract v2 amendment

Date: 2026-09-21. The user explicitly authorized this design stage after
merging PR #25 and explicitly requires DSH in place of historical Luna routing.
The parent agent owns scope, Git operations and final acceptance. DSH performs
bounded contract review and final read-only review; it must not recurse,
contact providers, modify files or fall back to Luna/another worker.

## Objective and verified baseline

Create an additive, offline v2 amendment that makes a later provider-evidence
acquisition decision precise without selecting a provider or acquiring data.
The amendment must preserve every fail-closed v1 rule while defining the exact
authorization envelope a future bounded transport-proof probe would require.

- Worktree: `D:/量化分析-m4-provider-evidence-contract-v2`.
- Branch: `codex/m4-provider-evidence-contract-v2`.
- Base and initial HEAD: `origin/main@8ecc2e7e35b9bea1f11d4fe5caee6ce2088a2dd2`
  (PR #25 merge).
- Initial source tree: `ba13f31cff0c26f8438ac0398b0fdba5c439283f`.
- Protected M2 HEAD: `3679b1bac7a1634c6452784a4d8f6d139966f222`.
- This protects the local `D:/量化分析` worktree only. The pre-existing remote
  M2 ref is `origin/feat/m2-value-assessment-mvp@ecb74a4178afd7de49b12f39eb58e541fc6fc4dd`,
  one commit ahead. Local `main@966206f06262e43f40c1c7aadbfb8596839eac91`
  is 25 commits behind `origin/main`; neither stale local ref may be changed.
- Protected stash: `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
- Protected database SHA256:
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.
- Accepted v1 manifest digest:
  `26542836f7b015c32d938ce1989cceb5f55437c59e908c5c1ba4d477867cb24f`.
- Initial quarantine inventory in this fresh worktree is exactly the tracked
  `data/quarantine/.gitkeep`; the six ignored v1 raw files remain worktree-local
  to the completed v1 worktree and are not copied here.

## Allowed scope and artifacts

Read-only use of tracked repository evidence and local Git metadata is allowed.
Writing is limited exactly to:

- this Goal;
- `docs/m4_provider_evidence_acquisition_design_v2.md`;
- `evidence/m4/provider_evidence_contract_v2.json`;
- `agent/record/2026-09-21_01_m4-provider-evidence-contract-v2.md`;
- `acceptance/2026-09-21_m4_provider_evidence_contract_v2.md`.

The parent may stage exactly the five paths above, validate, commit, push only
this branch and open one PR. The branch was created with the unsafe inherited
upstream `origin/main`; a bare push is forbidden. Push only with
`git push origin HEAD:refs/heads/codex/m4-provider-evidence-contract-v2`, then
set the upstream to that same remote branch if desired.

## Forbidden scope

No network, browser, DNS, provider or API access. No dataset endpoint or
metadata HTTP call, observation acquisition, credential, account, login,
provider selection, adapter/source implementation, test/config/CI/dependency
change, database open/query/write, holdout access, statistics or execution.
Do not modify v1 design/report/manifest/record/acceptance, README, frozen
contracts, historical records or protected worktrees. Do not copy, move,
delete, create, stage or commit ignored raw response files. No bare `git push`,
`git push --all`, `git push --mirror`, direct main push, force-push, merge or
later acquisition phase.

## Required v2 behavior

The design and machine-readable contract must agree and define:

1. additive schema identity `M4_PROVIDER_EVIDENCE_CONTRACT_V2`, future dossier
   identity `M4_PROVIDER_EVIDENCE_DOSSIER_V2`, and explicit v1 compatibility;
   the v2 contract is new policy, does not mutate v1 dossier/manifest schemas,
   and no v1 state or digest changes;
2. a distinct `BOUNDED_TRANSPORT_PROBE` evidence class that is only a future
   authorization specification, never authorization from this stage;
3. the exact probe envelope: a future authorization supplies the HTTPS
   host/endpoint allowlist; no credentials; GET only; one dossier per request;
   at most four requests per run; zero pagination; integer timeout in
   milliseconds; zero or one retry; integer requests-per-minute ceiling;
   requested-window-only; minimal declared fields; and a probe window strictly
   earlier than `2015-03-16`. Any response date in the frozen development
   window `2015-03-16..2022-12-30` or on/after holdout start `2023-01-01`, any
   undeclared field, ambiguous/unparseable date token or out-of-window date
   fails closed. Holdout exposure maps to `REAL_HOLDOUT_INJECTION`; all other
   unbounded transport maps to `REAL_ENDPOINT_UNBOUNDED`;
4. probe raw bytes, if later authorized, live only below ignored
   `data/quarantine/m4_provider_evidence_v2/`, are immutable and SHA256-named,
   have repository-relative locators, are never staged/committed/quoted
   wholesale (at most 25 words per source), never enter a database, tracked
   artifact, statistic or research flow, and are retained only when the licence
   permits it. Otherwise reject with `REAL_REDACTION_UNPROVEN`; an in-memory
   hash or redacted derivative never replaces the original;
5. exact transport proof fields: request method/host/endpoint, requested start
   and end, requested field list, timeout/retry/rate ceilings,
   `requested_window_only`, response min/max dates, raw date-scan count,
   ambiguous-date count, out-of-window count, undeclared-field count, raw
   SHA256/length/locator and `proof_digest`. The proof digest is lowercase
   SHA256 of UTF-8 sorted-key compact JSON of those fields except
   `proof_digest`, with `ensure_ascii=False` and no trailing LF. This is a
   specification-only rule in this stage because no probe data exists;
6. first-class `licence_artifacts` with stable ID, publisher, canonical URL,
   artifact/version/effective date, content SHA256, permitted-use and
   redistribution scope, retention/display and credential constraints,
   raw locator/SHA256/retrieval time, reviewer/date, expiry/revocation and
   contradiction handling. Every future dossier reference must resolve by ID
   and matching SHA; first-party licence text outranks documentation and third
   parties never prove licence/identity. Any use outside the recorded
   permitted-use or redistribution scope fails closed with
   `REAL_LICENSE_SCOPE_FORBIDDEN`;
7. `REJECTED` remains terminal. Reconsideration uses a new dossier ID with
   `predecessor_dossier_ids` and `predecessor_dossier_digests`; entries must
   resolve exactly to immutable terminal predecessors. The four v1 dossier IDs
   and digests are frozen exact sets and cannot be reused, mutated or
   resubmitted. The same lineage rule applies to any later v2 reconsideration;
8. current-official-URL discovery, deterministic redirect/timeout/retry rules,
   no mirror or silent provider substitution, and fail-closed retention;
   these are future procedures only—this stage verifies no current provider
   URL, availability, licence or terms fact;
9. an explicit mapping from the three codes used by v1
   (`REAL_CALENDAR_VERSION_MISSING`, `REAL_ENDPOINT_UNBOUNDED`, and
   `REAL_LICENSE_EVIDENCE_MISSING`) to non-empty v2 provision arrays without
   changing historical meaning, plus adopted future probe codes
   `REAL_HOLDOUT_INJECTION`, `REAL_LICENSE_SCOPE_FORBIDDEN` and
   `REAL_REDACTION_UNPROVEN`;
10. an authorization decision record specifying what a user must explicitly
   approve before a future acquisition-v2 stage, including hosts/endpoints,
   dates/fields/rates, raw retention, and confirmation that returned values
   are evidence-only and cannot enter research, database or holdout flows;
11. deterministic contract JSON: the tracked file is UTF-8, sorted-key,
   compact-separator JSON plus one LF, with no BOM, duplicate keys, floats or
   host-absolute paths. `contract_digest` is lowercase SHA256 of
   `json.dumps(object_without_only_the_top_level_contract_digest,
   ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')`
   with no trailing LF. Nested digests have distinct names;
12. `source_tree_digest` is the pre-write `HEAD^{tree}`
   `ba13f31cff0c26f8438ac0398b0fdba5c439283f`; it is not the final commit tree
   and cannot be made self-referential; and
13. no default provider, automatic fallback or transition to adapter work.

The JSON contract must contain exact keys `schema_id`,
`future_dossier_schema_id`, `terminal_predecessors`, `evidence_classes`,
`adopted_probe_codes`, `v1_code_mapping`, `source_tree_digest` and
`contract_digest`, plus: schema/version, predecessor contract
and manifest identities/digests, evidence classes orthogonal to provider roles,
mandatory gates, probe envelope and proof-digest specification, licence
artifact schema/linkage, exact terminal predecessor IDs/digests,
terminal-state/reconsideration rules, `v1_code_mapping` keyed by the exact three
used codes with non-empty `v2_provisions`, adopted probe codes, authorization
requirements, forbidden actions, source-tree digest and contract digest. Every
ordered set is an array with frozen order. No current provider fact is asserted.

## Exact validation commands and acceptance gates

All commands run in PowerShell 7 from the worktree root. Run and record exact
results. Hashing the protected database as raw bytes is allowed; opening it
through DuckDB or any database engine is forbidden.

1. `python -c "import json,pathlib; fail=lambda m:(_ for _ in ()).throw(ValueError(m)); json.loads(pathlib.Path('evidence/m4/provider_evidence_contract_v2.json').read_text(encoding='utf-8'),parse_float=lambda _:fail('float'),object_pairs_hook=lambda p:(lambda d:d if len(d)==len(p) else fail('duplicate key'))(dict(p)))"`
2. `python -c "import hashlib,json,pathlib; p=pathlib.Path('evidence/m4/provider_evidence_contract_v2.json'); raw=p.read_bytes(); assert raw.endswith(b'\n') and b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'); x=json.loads(raw.decode('utf-8')); e=x.pop('contract_digest'); c=json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode(); assert raw==json.dumps({**x,'contract_digest':e},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()+b'\n'; assert e==hashlib.sha256(c).hexdigest()"`
3. `python -c "import hashlib,json,pathlib; x=json.loads(pathlib.Path('evidence/m4/provider_evidence_manifest_v1.json').read_text(encoding='utf-8')); e=x.pop('manifest_digest'); assert e=='26542836f7b015c32d938ce1989cceb5f55437c59e908c5c1ba4d477867cb24f'; assert e==hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()"`
4. `python -c "import json,pathlib; v1=json.loads(pathlib.Path('evidence/m4/provider_evidence_manifest_v1.json').read_text(encoding='utf-8')); v2=json.loads(pathlib.Path('evidence/m4/provider_evidence_contract_v2.json').read_text(encoding='utf-8')); p=v2['terminal_predecessors']; assert {(x['dossier_id'],x['dossier_digest'],x['state']) for x in p}=={(x['dossier_id'],x['dossier_digest'],'REJECTED') for x in v1['dossiers']}; codes={x['rejection_code'] for x in v1['dossiers']}; assert set(v2['v1_code_mapping'])==codes; assert all(v2['v1_code_mapping'][c]['v2_provisions'] for c in codes)"`
5. `python -c "import json,pathlib; x=json.loads(pathlib.Path('evidence/m4/provider_evidence_contract_v2.json').read_text(encoding='utf-8')); assert x['schema_id']=='M4_PROVIDER_EVIDENCE_CONTRACT_V2' and x['future_dossier_schema_id']=='M4_PROVIDER_EVIDENCE_DOSSIER_V2'; assert 'BOUNDED_TRANSPORT_PROBE' in x['evidence_classes']; required={'REAL_HOLDOUT_INJECTION','REAL_LICENSE_SCOPE_FORBIDDEN','REAL_REDACTION_UNPROVEN'}; assert required<=set(x['adopted_probe_codes']); assert all(x['adopted_probe_codes'][c]['v2_provisions'] for c in required); d=pathlib.Path('docs/m4_provider_evidence_acquisition_design_v2.md').read_text(encoding='utf-8'); tokens=[x['schema_id'],x['future_dossier_schema_id'],'BOUNDED_TRANSPORT_PROBE','REJECTED','ACQUISITION_V2_NOT_AUTHORIZED',x['source_tree_digest'],x['contract_digest']]; assert all(t in d for t in tokens)"`
6. `$paths = @('docs/m4_provider_evidence_acquisition_design_v2.md','evidence/m4/provider_evidence_contract_v2.json'); $paths | ForEach-Object { if (-not (Test-Path -LiteralPath $_)) { throw "missing $_" } }; if (-not (Get-Command rg -ErrorAction SilentlyContinue)) { throw 'rg unavailable' }; $LASTEXITCODE = 0; rg -n -i -e 'api[_-]?key' -e 'authorization:' -e 'bearer ' -e 'cookie:' -e 'set-cookie:' -e '(^|["''=[:space:]])[A-Za-z]:[\\/]' -e '/Users/' -e '/home/' -- $paths; $scanCode=$LASTEXITCODE; if ($scanCode -ne 1) { throw "secret/path scan exit $scanCode" }`
7. `python -c "import pathlib,re; ps=[pathlib.Path(x) for x in ['agent/goals/2026-09-21_m4_provider_evidence_contract_v2.md','docs/m4_provider_evidence_acquisition_design_v2.md','evidence/m4/provider_evidence_contract_v2.json','agent/record/2026-09-21_01_m4-provider-evidence-contract-v2.md','acceptance/2026-09-21_m4_provider_evidence_contract_v2.md']]; [p.read_text(encoding='utf-8',errors='strict') for p in ps]; assert all(p.read_bytes().endswith(b'\n') and b'\r' not in p.read_bytes() for p in ps); links=[]; [links.extend((p,m.group(1)) for m in re.finditer(r'\[[^]]+\]\((?!https?://|#)([^)]+)\)',p.read_text(encoding='utf-8'))) for p in ps if p.suffix=='.md']; assert all((p.parent/t).resolve().exists() for p,t in links)"`
8. `git diff --check` and `git diff --cached --check`;
9. `git status --short --branch`;
10. `git rev-parse HEAD origin/main refs/stash 'HEAD^{tree}'`;
11. `git worktree list --porcelain` and `git stash list`;
12. `git -C 'D:/量化分析' rev-parse HEAD`;
13. `Get-FileHash -Algorithm SHA256 -LiteralPath 'D:/量化分析/data/research.duckdb'`.
14. `git status --porcelain --ignored | Select-String 'data/quarantine/'`
    (expected: no output; this fresh worktree contains only tracked `.gitkeep`).
15. After staging exactly the five authorized paths, assert
    `git diff --cached --name-only` equals that exact set before running
    `git diff --cached --check`. The artifact commit must have parent
    `8ecc2e7e35b9bea1f11d4fe5caee6ce2088a2dd2`.
16. Push only with the explicit refspec above; afterward assert
    `origin/main` remains `8ecc2e7e35b9bea1f11d4fe5caee6ce2088a2dd2`
    and `origin/codex/m4-provider-evidence-contract-v2` equals `HEAD`.

Acceptance requires DSH and parent independent `PASS`, byte-identical tracked
v1 artifacts, only authorized paths changed, all validations recorded,
protected baselines unchanged, local remote-tracking synchronization reported,
and the exact state `ACQUISITION_V2_NOT_AUTHORIZED`. The acceptance file must
contain the complete AGENTS.md evidence packet: Goal path; base/final branch and
commit; changed files; implementation summary; exact commands/results;
acceptance evidence; worktree/stash/protected database state; synchronization;
deviations, blockers and risks; PR number/URL; and whether any next stage is
allowed. DSH does not independently fetch or query the remote.

## Stop conditions and Git boundary

Stop on any need for network/provider access, raw-file movement, observation
data, credentials, database/holdout, implementation, provider selection,
schema relaxation or changes outside the allowed paths. DSH or parent verdict
must be exactly `PASS`, `CHANGES_REQUIRED` or `BLOCKED`. Push only
`codex/m4-provider-evidence-contract-v2` and open at most one PR. One artifact
commit plus one documentation-only handoff commit updating only the record and
acceptance with commit/PR evidence are authorized; no other commit is allowed.
Do not merge or begin acquisition v2 without a new explicit user authorization.
