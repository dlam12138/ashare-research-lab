# Goal: M4 public provider-evidence acquisition v1

Date: 2026-09-20. The parent Codex/Astra agent owns planning, constraint
review, Git operations and final acceptance. One `gpt-5.6-luna` worker at
`medium`, with fresh context and no recursive delegation, performs bounded
research and drafts authorized deliverables. DSH performs additional read-only
contract analysis and final review; it must not write artifacts or contact
providers. Only a DSH `PASS` followed by the parent's independent `PASS`
accepts the stage; `CHANGES_REQUIRED` or `BLOCKED` stops it.

## Objective and verified baseline

Acquire citation-grade current public evidence for the provider candidates
already named in the accepted provider-evidence design. Produce a bounded,
fail-closed disposition for each dossier without selecting a provider,
implementing an adapter, downloading market observations, or running a study.

- Worktree: `D:/量化分析-m4-provider-evidence-acquisition`.
- Branch: `codex/m4-provider-evidence-acquisition`.
- Base: `origin/main@781f7fb035eb3fdebc3b2c03ed5f642f2094d29e`
  (PR #24 merge).
- Protected M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`;
  stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`; default database SHA256
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Frozen dossier set

Exactly four `M4_PROVIDER_EVIDENCE_DOSSIER_V1` records are in scope:

1. `baostock_trade_calendar`: BaoStock,
   `baostock.query_trade_dates`, tracked dataset `trade_calendar`, role
   `CALENDAR_EVIDENCE`;
2. `baostock_target_daily`: BaoStock,
   `baostock.query_history_k_data_plus`, tracked dataset `target_daily`, role
   `TARGET_OUTCOME`;
3. `cninfo_historical_issued_shares`: CNINFO publisher with AkShare-declared
   transport `stock_share_change_cninfo`, tracked endpoint
   `CNINFO p_stock2215 via akshare.stock_share_change_cninfo`, dataset
   `historical_issued_shares`, role `MEMBERSHIP_EVIDENCE`;
4. `eia_brent_oil`: U.S. EIA publisher, tracked endpoint
   `https://www.eia.gov/dnav/pet/hist/RBRTED.htm`, dataset `oil` / series
   `RBRTE`, role `FACTOR`.

Their identities come only from
`reports/m3_stage3b_source_registry_v1.json`. The EIA semantics may also cite
`reports/m3_stage3br2_oil_contract_v2.json`. No FRED, CNI, Shenwan, alternate
endpoint, dataset or role is in scope.

## Scope, artifacts and authority

Allowed: read-only HTTPS GET/HEAD retrieval of official provider/publisher
pages, official documentation, official terms/licence/privacy/access-policy
pages and official API metadata; browser/search for official-page discovery;
tracked repository evidence; response-metadata capture; bounded private raw
retention; writing the authorized paths; validation, commit, push and one PR.

For CNINFO, CNINFO first-party material alone can prove publisher facts.
AkShare project material is third-party-declared transport metadata only; it
cannot prove CNINFO identity, data semantics, PIT timing, rights or official
support. Search snippets and all other third-party summaries are discovery
only. BaoStock and EIA facts require their respective first-party sources.

Original HTTP response bytes may be written only below the already ignored
`data/quarantine/m4_provider_evidence_v1/` root in this worktree. Each file is
immutable after first write, addressed by SHA256, and referenced by a
repository-relative locator. These private raw files must never be staged,
committed, quoted wholesale or redistributed. A report may quote at most 25
words from any one source. If retention is forbidden or fails, the dossier is
`REJECTED` with `REAL_REDACTION_UNPROVEN`; an in-memory hash is insufficient.

Authorized tracked write paths are exactly:

- this Goal;
- `docs/m4_provider_evidence_acquisition_report_v1.md`;
- `evidence/m4/provider_evidence_manifest_v1.json`;
- `agent/record/2026-09-20_01_m4-provider-evidence-acquisition.md`;
- `acceptance/2026-09-20_m4_provider_evidence_acquisition.md`.

Forbidden: credentials, account creation, login, provider contact, form
submission, circumvention, bulk crawling, robots bypass, authenticated or
rate-limited API calls, market-price/factor/calendar/membership observation
downloads, database open/query/write, holdout access, provider selection,
adapter/source code, tests/config/CI/dependency changes, real-data validation,
statistics, study binding or execution.

## Required dossier behavior

The manifest contains exactly four dossier entries at the granularity above.
Every entry contains every mandatory field group from design section 1.
Unproven mandatory values are explicit JSON `null`, paired with a failed
`evidence_checks` item and a stable `rejection_code`; null never passes a gate.

`dossier_digest` is exactly the accepted design formula: SHA256 of UTF-8,
sorted-key, compact-separator canonical JSON for the dossier after removing
`dossier_digest`, reviewer notes and transient diagnostics. Host-absolute paths,
credentials, secrets and local-clock defaults are forbidden inputs.
`source_tree_digest` identifies `HEAD^{tree}`. The pretty-printed manifest has a
separate `manifest_digest`, computed over compact canonical JSON after removing
only `manifest_digest`; dossier exclusion rules are applied before their
embedded digests are calculated.

Original response evidence records retrieval time with explicit offset, final
URL, HTTP status, media type, response byte length, SHA256, redirect chain,
headers digest, `credential_class=NONE`, redacted request-shape digest and raw
relative locator. Cookies and volatile headers are excluded. Documentation,
terms and policy pages use `null` for dataset window/date-scan fields and cannot
satisfy a dataset transport gate. Dataset endpoints require all accepted
transport fields (`requested_window_only`, request/response min/max dates, raw
date scan, out-of-window count and `proof_digest`); this Goal forbids calling
them, so those gates cannot pass here.

The named licence artifact fields are mandatory: provider/publisher, artifact
identifier, version/effective date, content SHA256, permitted-use and
redistribution scope, retention/display constraints, credential constraints,
reviewer identity and review date. Absence, expiry or incompatible scope forces
`REJECTED` independently of data quality. A redacted derivative never replaces
the original; it requires its own locator/SHA, field-level manifest and
back-reference. Missing original retention forces `REAL_REDACTION_UNPROVEN`.

Binding state machine:

- creation -> `UNVERIFIED_CANDIDATE`;
- `UNVERIFIED_CANDIDATE` -> `EVIDENCE_COMPLETE` only if every design gate passes;
- `UNVERIFIED_CANDIDATE` -> `REJECTED` for any missing, contradictory, expired,
  forbidden or unretainable mandatory evidence;
- `EVIDENCE_COMPLETE` -> `REJECTED` on proven tamper, expiry, revocation or
  contradiction.

`REJECTED` is terminal; no transition reverses in place and reconsideration
requires a new dossier identity. Because dataset endpoints and observations are
forbidden in this stage, `EVIDENCE_COMPLETE` is not expected and must never be
inferred from documentation alone.

Rejection codes are limited to applicable accepted `REAL_*` codes and
`RDC-E01`–`RDC-E28` in
`docs/m4_real_daily_source_acceptance_cases_v1.md`, plus exactly
`REAL_LICENSE_EVIDENCE_MISSING`, `REAL_LICENSE_SCOPE_FORBIDDEN`,
`REAL_REDACTION_UNPROVEN` and `REAL_CALENDAR_VERSION_MISSING`. No new or renamed
code is allowed without a versioned amendment.

The report separates observed fact, inference and unresolved evidence. Every
current factual claim cites a manifest entry and an official URL. It states
that no dossier selection, adapter implementation, observation acquisition,
real-data validation or execution is authorized.

## Required tests and exact validation commands

No test suite applies and no test file may change. Run exactly:

1. `python -m json.tool evidence/m4/provider_evidence_manifest_v1.json > $null`
2. `python -c "import hashlib,json,pathlib; p=pathlib.Path('evidence/m4/provider_evidence_manifest_v1.json'); x=json.loads(p.read_text(encoding='utf-8')); e=x.pop('manifest_digest'); a=hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(); assert e==a,(e,a)"`
3. `python -c "import json,pathlib; x=json.loads(pathlib.Path('evidence/m4/provider_evidence_manifest_v1.json').read_text(encoding='utf-8')); ds=x['dossiers']; assert len(ds)==4; ids=[d['dossier_id'] for d in ds]; assert len(ids)==len(set(ids)); assert all(d['state'] in {'UNVERIFIED_CANDIDATE','EVIDENCE_COMPLETE','REJECTED'} for d in ds)"`
4. `python -c "import json,pathlib; x=json.loads(pathlib.Path('evidence/m4/provider_evidence_manifest_v1.json').read_text(encoding='utf-8')); r=pathlib.Path('docs/m4_provider_evidence_acquisition_report_v1.md').read_text(encoding='utf-8'); assert all(d['dossier_id'] in r for d in x['dossiers']); assert all(e['final_url'] in r for d in x['dossiers'] for e in d['retrieval_evidence'])"`
5. `rg -n -i "api[_-]?key|authorization:|bearer |cookie:|set-cookie:|[A-Za-z]:\\\\|/Users/|/home/" docs/m4_provider_evidence_acquisition_report_v1.md evidence/m4/provider_evidence_manifest_v1.json agent/record/2026-09-20_01_m4-provider-evidence-acquisition.md acceptance/2026-09-20_m4_provider_evidence_acquisition.md` (expected: no matches / exit 1)
6. `git diff --check`
7. `git diff --cached --check`
8. `git status --short --branch`
9. `git rev-parse HEAD origin/main refs/stash 'HEAD^{tree}'`
10. `git worktree list --porcelain`
11. `git stash list`
12. `git -C 'D:/量化分析' rev-parse HEAD`
13. `Get-FileHash -Algorithm SHA256 -LiteralPath 'D:/量化分析/data/research.duckdb'`

Additionally verify strict UTF-8, LF, final newlines, local Markdown links, raw
locator existence/hash/length, dossier digests, unique official URLs per
retrieval item, and that `git check-ignore` marks every retained raw file
ignored. Record the exact commands and results in the acceptance file.

## Acceptance, review and stop conditions

Acceptance requires four bounded dossier dispositions, first-party citations,
reproducible response metadata, retained ignored raw evidence, no unsupported
current fact, no committed response body, and all validations above. DSH and
the parent independently inspect branch/HEAD, commit/diff, changed/untracked
files, evidence, worktree/stash, protected M2/database baselines,
local/origin/remote synchronization, Goal compliance and acceptance evidence.

The final evidence packet must report the Goal path, verified base branch and
commit, final branch/commit, files changed, implementation summary, exact
commands/results, acceptance evidence, worktree/stash state, synchronization,
deviations/blockers/risks, PR number/URL and whether a later stage is allowed.

Stop immediately on any need for credentials, provider contact, observation
data, restricted content, database access, holdout, implementation or a broader
candidate search. Push only `codex/m4-provider-evidence-acquisition` and open
one PR. Direct main push, force-push, merge and every later phase are forbidden.
