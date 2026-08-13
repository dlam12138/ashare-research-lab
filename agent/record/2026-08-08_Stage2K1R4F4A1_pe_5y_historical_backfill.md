# 工作记录：M2 Stage 2K.1R4F.4A1 — Frozen-5Y historical backfill

Status: PASS — LOCAL CANDIDATE; closeout authorized; remote CI pending

## 基线与范围

- 分支：`feat/m2-value-assessment-mvp`
- 基线/当前 HEAD：`284d3081e9ff9b58a740d1e63a61e0aace58c8c9`
- origin 同步：开始时 0 ahead / 0 behind
- R4F.4A final-tip CI：run `31250897525`, success
- 允许范围：四个 annual logical cells、官方证据与 PIT lineage、side-by-side
  calendar、isolated bundle/overlay、frozen-5Y readiness、episode/outcome
  metadata、窄兼容重构、测试与文档。
- 禁止范围：2014 或更早 economic facts、future EPS value、actual outcome、
  PE percentile/score、Brent、默认 DB、下一阶段、commit、push。

## 实施结果

- SSE official PDFs：2015/2016 新增 content-addressed external objects；
  2017/2018/2019/2020 复用既有 objects，其中 2017 SHA 为
  `c1a6fbffcc210020e672410400646e0c9fe2097f5de43047a24b950ae7930cea`。
- 实际公告日最早 2016-03-24，故新增 side-by-side calendar pin，范围
  2016-01-04..2026-08-07；与 R4F.3A overlap 2330/2330 exact match。
- 解析并验证四个 consolidated cells：2015 equity 1,179,968 million；
  2016 equity 1,189,319 million；2016 NP 7,900 million；2017 NP 22,793
  million。bounded comparative scan 未发现 restatement，Fact records=4。
- Decimal ROE：2016 = `0.006668672896107563161406786092`；2017 =
  `0.01913624531469271226661618072`，与 readiness resolver 逐值一致。
- frozen 5Y readiness = 1211/1211；candidate regimes=1；observed onsets=0；
  left-censored=1；valid onset anchors=0；mature +4Q/+8Q=0/0。
- final decision =
  `PE_5Y_BACKFILL_TRUSTED_INDEPENDENT_VALIDATION_NOT_TESTABLE_WITH_FROZEN_5Y_HISTORY`；
  action = `STOP_FOR_NORTH_STAR_REVIEW`。

## 确定性与验证

- External object SHA verification：6/6 PASS。
- Build A / Build B：11 deterministic artifacts byte-identical。
- R4F.4A1 targeted tests：21 passed。
- R4F.4A1→R4F.1 分阶段回归：236 passed。
- Full pytest：1926 passed，2 个既有 pandas date-parser warnings。
- Ruff、compileall、git diff check：PASS。
- secret/absolute-path scan：22 个 stage 文件 PASS。
- protected upstream artifacts：相对 HEAD 无 diff；scoring paths zero-diff。
- 默认 DB SHA-256：
  `4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`，
  与任务开始时一致。
- stash：唯一既有条目保持不变。
- branch/HEAD/local-origin：仍为任务开始状态，0 ahead / 0 behind。

## Git 状态

实现阶段本地验证完成；关闭授权允许分范围 commit、normal push 与 CI closeout。
当前尚未 commit/push，且不会开始 outcome-validation stage；machine-readable
next stage 已冻结为 `NONE_PENDING_NORTH_STAR_REVIEW`。
