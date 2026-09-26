# Goal: bounded native-browser FRED comparison

## Objective and verified baseline

User instructed continuation after proposed browser-versus-script comparison.
Verify whether a native Chromium main-document request receives the already
approved FRED terms page through the existing localhost proxy. Branch
`codex/m4-fred-transport-diagnosis`, initial HEAD `337a5e670ecfe416ad7c6207a07b8daf3c33c8a0`,
equals live origin branch; base main `9c9ced90d109437b937cfcaa069388689db636f5`.
Worktree clean, stash `cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`.
Protected M2 HEAD `3679b1bac7a1634c6452784a4d8f6d139966f222`; database SHA256
`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`.

## Scope and required behavior

Tracked: this Goal, `agent/record/2026-09-23_01_m4-fred-browser-comparison.md`,
`evidence/m4/fred_browser_comparison_01.json`. Temporary helper under ignored
tmp; browser profile/metrics under ignored output/playwright; successful raw
under existing SHA-addressed quarantine. Preserve all historical evidence.
CLI preflight found npx but no cached Playwright CLI. Use existing Chromium
via its local CDP endpoint; install no package and use no personal profile.

Exactly one allowed origin GET: https://fred.stlouisfed.org/docs/api/terms_of_use.html.
No cookies, credentials, retries, redirects, images, scripts, other origins,
legal/series/CSV or research operations. Intercept requests before navigation;
only this main-frame document may continue once. Browser certificate checks
remain enabled. Use existing 127.0.0.1:10808 upstream proxy through a loopback
budget relay: one permitted CONNECT to fred.stlouisfed.org:443, at most 15 s
from the allowed CONNECT, at most 1048576 upstream bytes (including encrypted
TLS overhead, stricter than body-only limit). Close tunnel at either limit.
Disable background networking and JS/service workers. No global config edit.

## Validation, acceptance and stops

Run `node --check tmp/m4-provider-evidence-v2/browser_probe.cjs`, review the
allowlist/budget/interception before `node tmp/m4-provider-evidence-v2/browser_probe.cjs`.
Verify attempt count, network/error metrics and any retained SHA256, check
`git diff --check`, protected Git refs/database hash and exact staged paths.
Stop after the single attempt, whether successful or not. Accurate diagnosis
is acceptance; a browser HTTP 200 alone is not licence-scope approval.
No successful response means acquisition remains BLOCKED. Disclose that
restricted headless navigation does not emulate a full interactive website.

## Delivery

Commit exactly the scoped tracked files, push topic branch to update PR #29.
No main push, force push, merge, source/CI/dependency change or next stage.

## Evidence representation clarification

CDP may decode response text, so its body is explicitly derivative evidence,
retained under ignored output/playwright, not certified original raw bytes.
Do not manufacture a licence artifact or dossier from this transport success.
The full evidence acquisition gate remains pending even if this comparison
meets its diagnostic acceptance criteria.
