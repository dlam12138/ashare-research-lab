# M4 provider-evidence contract v2 acceptance

Verdict: pending final DSH and parent review.

Goal: `agent/goals/2026-09-21_m4_provider_evidence_contract_v2.md`.
Base: `origin/main@8ecc2e7e35b9bea1f11d4fe5caee6ce2088a2dd2`.
Branch: `codex/m4-provider-evidence-contract-v2`.

## Implementation

The stage adds an offline design and canonical machine contract. It defines a
future bounded transport-proof authorization envelope, first-class licence
evidence, terminal predecessor lineage and deterministic digest rules without
changing any v1 artifact or acquiring any provider data.

Changed files are limited to the five Goal-authorized paths. Acquisition v2,
provider selection, adapter implementation, observations, database/holdout
access, real-data validation and execution remain unauthorized.

## Validation evidence

Exact pre-commit commands, executed from the worktree root in PowerShell 7:

```powershell
python -c "import json,pathlib; fail=lambda m:(_ for _ in ()).throw(ValueError(m)); json.loads(pathlib.Path('evidence/m4/provider_evidence_contract_v2.json').read_text(encoding='utf-8'),parse_float=lambda _:fail('float'),object_pairs_hook=lambda p:(lambda d:d if len(d)==len(p) else fail('duplicate key'))(dict(p)))"
python -c "import hashlib,json,pathlib; p=pathlib.Path('evidence/m4/provider_evidence_contract_v2.json'); raw=p.read_bytes(); assert raw.endswith(b'\n') and b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'); x=json.loads(raw.decode('utf-8')); e=x.pop('contract_digest'); c=json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode(); assert raw==json.dumps({**x,'contract_digest':e},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()+b'\n'; assert e==hashlib.sha256(c).hexdigest()"
python -c "import hashlib,json,pathlib; x=json.loads(pathlib.Path('evidence/m4/provider_evidence_manifest_v1.json').read_text(encoding='utf-8')); e=x.pop('manifest_digest'); assert e=='26542836f7b015c32d938ce1989cceb5f55437c59e908c5c1ba4d477867cb24f'; assert e==hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()"
python -c "import json,pathlib; v1=json.loads(pathlib.Path('evidence/m4/provider_evidence_manifest_v1.json').read_text(encoding='utf-8')); v2=json.loads(pathlib.Path('evidence/m4/provider_evidence_contract_v2.json').read_text(encoding='utf-8')); p=v2['terminal_predecessors']; assert {(x['dossier_id'],x['dossier_digest'],x['state']) for x in p}=={(x['dossier_id'],x['dossier_digest'],'REJECTED') for x in v1['dossiers']}; codes={x['rejection_code'] for x in v1['dossiers']}; assert set(v2['v1_code_mapping'])==codes; assert all(v2['v1_code_mapping'][c]['v2_provisions'] for c in codes)"
python -c "import json,pathlib; x=json.loads(pathlib.Path('evidence/m4/provider_evidence_contract_v2.json').read_text(encoding='utf-8')); assert x['schema_id']=='M4_PROVIDER_EVIDENCE_CONTRACT_V2' and x['future_dossier_schema_id']=='M4_PROVIDER_EVIDENCE_DOSSIER_V2'; assert 'BOUNDED_TRANSPORT_PROBE' in x['evidence_classes']; required={'REAL_HOLDOUT_INJECTION','REAL_LICENSE_SCOPE_FORBIDDEN','REAL_REDACTION_UNPROVEN'}; assert required<=set(x['adopted_probe_codes']); assert all(x['adopted_probe_codes'][c]['v2_provisions'] for c in required); d=pathlib.Path('docs/m4_provider_evidence_acquisition_design_v2.md').read_text(encoding='utf-8'); tokens=[x['schema_id'],x['future_dossier_schema_id'],'BOUNDED_TRANSPORT_PROBE','REJECTED','ACQUISITION_V2_NOT_AUTHORIZED',x['source_tree_digest'],x['contract_digest']]; assert all(t in d for t in tokens)"
$paths = @('docs/m4_provider_evidence_acquisition_design_v2.md','evidence/m4/provider_evidence_contract_v2.json'); $paths | ForEach-Object { if (-not (Test-Path -LiteralPath $_)) { throw "missing $_" } }; if (-not (Get-Command rg -ErrorAction SilentlyContinue)) { throw 'rg unavailable' }; $LASTEXITCODE = 0; rg -n -i -e 'api[_-]?key' -e 'authorization:' -e 'bearer ' -e 'cookie:' -e 'set-cookie:' -e '(^|["''=[:space:]])[A-Za-z]:[\\/]' -e '/Users/' -e '/home/' -- $paths; $scanCode=$LASTEXITCODE; if ($scanCode -ne 1) { throw "secret/path scan exit $scanCode" }
python -c "import pathlib,re; ps=[pathlib.Path(x) for x in ['agent/goals/2026-09-21_m4_provider_evidence_contract_v2.md','docs/m4_provider_evidence_acquisition_design_v2.md','evidence/m4/provider_evidence_contract_v2.json','agent/record/2026-09-21_01_m4-provider-evidence-contract-v2.md','acceptance/2026-09-21_m4_provider_evidence_contract_v2.md']]; [p.read_text(encoding='utf-8',errors='strict') for p in ps]; assert all(p.read_bytes().endswith(b'\n') and b'\r' not in p.read_bytes() for p in ps); links=[]; [links.extend((p,m.group(1)) for m in re.finditer(r'\[[^]]+\]\((?!https?://|#)([^)]+)\)',p.read_text(encoding='utf-8'))) for p in ps if p.suffix=='.md']; assert all((p.parent/t).resolve().exists() for p,t in links)"
git diff --check
git diff --cached --check
git status --short --branch
git rev-parse HEAD origin/main refs/stash 'HEAD^{tree}'
git worktree list --porcelain
git stash list
git -C 'D:/量化分析' rev-parse HEAD
Get-FileHash -Algorithm SHA256 -LiteralPath 'D:/量化分析/data/research.duckdb'
git status --porcelain --ignored | Select-String 'data/quarantine/'
```

1. Strict JSON parse with duplicate-key and float rejection — PASS.
2. Canonical file/digest round trip — PASS; `contract_digest` is
   `b5f6b8d54f5fe733d41ed018a89b3065fc05a0e7130c072c66d19e469221bdca`.
3. v1 manifest recomputation — PASS;
   `26542836f7b015c32d938ce1989cceb5f55437c59e908c5c1ba4d477867cb24f`.
4. Terminal predecessor exact-set and v1-code mapping assertions — PASS; four
   predecessors and three distinct historical codes.
5. Design/JSON schema, evidence-class, adopted-code, authorization-state,
   source-tree and contract-digest agreement — PASS.
6. Secret/credential/host-absolute-path scan — PASS, no matches, rg exit 1.
7. Strict UTF-8, LF, final newline and relative-link checks — PASS.
8. `git diff --check` / `git diff --cached --check` — PASS before staging.
9. Initial status — exactly the five authorized new files, no upstream.
10. Initial refs — HEAD and `origin/main` both
    `8ecc2e7e35b9bea1f11d4fe5caee6ce2088a2dd2`; stash
    `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; source tree
    `ba13f31cff0c26f8438ac0398b0fdba5c439283f`.
11. Worktree/stash inspection — PASS; protected entries unchanged.
12. Protected M2 local HEAD — PASS,
    `3679b1bac7a1634c6452784a4d8f6d139966f222`.
13. Protected database raw-byte SHA256 — PASS,
    `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`;
    no database engine opened it.
14. Ignored quarantine inventory — PASS, no ignored entry; only tracked
    `data/quarantine/.gitkeep` exists in this fresh worktree.

The Goal received DSH `PASS` after two bounded review/fix cycles. Final artifact
review, staged-path equality, commit/push synchronization and PR evidence remain
to be recorded below.

## Final evidence packet

- Goal path: `agent/goals/2026-09-21_m4_provider_evidence_contract_v2.md`.
- Verified base: `origin/main@8ecc2e7e35b9bea1f11d4fe5caee6ce2088a2dd2`.
- Changed files: the five Goal-authorized files only.
- Protected worktree, stash and database: unchanged at the values above.
- Deviation: the unsafe inherited `origin/main` upstream was removed before
  implementation; explicit-refspec-only push is mandatory.
- Unresolved authorization: `ACQUISITION_V2_NOT_AUTHORIZED`.
- Artifact commit, handoff commit, remote synchronization and PR URL: pending
  the explicitly authorized two-commit parent Git handoff.
- Proceeding to acquisition v2 or any provider/adapter work: not allowed.
