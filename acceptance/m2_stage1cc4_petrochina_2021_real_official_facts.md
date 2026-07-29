# M2 Stage 1C-C.4 正式验收报告：中国石油 2021 年官方事实

## 结论

**Fail。**

在事实登记和 runner 执行前，`company_official` 文档合同已经失败：中国石油官网没有找到同时满足“2021 年、简体中文、A 股、完整年度报告”的正式文档。

## 已核验的中国石油官网文档

### 官网年度报告栏目中的完整报告

- 年度报告列表：<https://www.petrochina.com.cn/petrochina/ndbg/reportnd_list.shtml>
- 标题：`2021年年度报告`
- PDF：<https://www.petrochina.com.cn/petrochina/ndbg/202204/e5a5109dcf70405d8509e27040125ade/files/a2fdc43b19c547788f5149bf41840698.pdf>
- retrieved_at：`2026-07-29T22:25:37+08:00`
- SHA-256：`ea054145d5bcaf0f3fce9c3b0dab6927461cd231480e99b419bd646584244090`
- 大小：`4,582,111` bytes
- 页数：`276`
- 加密：否

通过 Poppler 分别渲染封面和 CAS 审计报告页并目视检查：

- 封面为 `中國石油天然氣股份有限公司 2021年度報告`；
- 封面同时列出香港、纽约和上海交易代码，不是明确的简体 A 股专版；
- 审计报告正文使用 `審計報告`、`中國`、`財務報表`、`準則`、`編製`、`為` 等繁体字。

该文档是完整年度报告，但属于本阶段明确禁止采用的繁体版本。

### 官网简体 A 股审计报告

- 公司公告栏目：<https://www.petrochina.com.cn/petrochina/gsgg/xwgg_list_42.shtml>
- 标题：`会计师审计报告（A股）`
- PDF：<https://www.petrochina.com.cn/petrochina/gsgg/202203/b39500c66f3b40f5b1a97c5b37f1f75f/files/f066f8223a454855ae08d97d1f3bf0cb.pdf>
- 公告日期：`2022-03-31`
- 页数：`95`

该文档是简体 A 股财务报表及审计报告，但不是完整年度报告，不能替代合同要求的公司官网简体 A 股完整年度报告。

## 上交所记录

- 601857 定期报告页：<https://www.sse.com.cn/disclosure/listedinfo/regular/index.shtml?productId=601857>
- 完整报告标题：`中国石油天然气股份有限公司2021 年度报告`
- 公告日期：`2022-04-01`
- 完整报告 PDF：<https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2022-04-01/601857_20220401_6_QNCbgaXu.pdf>
- 同日年度报告摘要：`601857_20220401_5_sJDm4LL5.pdf`，已排除

上交所存在完整 A 股年度报告记录，但不能据此补足缺失的合规 `company_official` 完整年报，也不能把同一交易所文档同时登记为两个来源。

## 未执行项目

按照“文档语言、版本或来源不符合合同即停止”的规则，本轮没有：

- 读取或登记 `revenue`、`net_profit_attributable_to_parent`、`operating_cash_flow`；
- 使用后续年报中的 2021 比较列；
- 创建 `acceptance/fixtures/official_facts/601857.SH/2021_annual.json`；
- 新增 2021 注册证据测试；
- 运行 `python -m ashare_research.tools.official_fact_acceptance`；
- 生成 reconciled facts、PIT、Audit 或 Lineage；
- 修改 runner、Fact Schema、Reconciliation、单位规则或容差；
- 修改 2022—2025 已验收证据或 `data/research.duckdb`。

因此成功计数不适用，不应伪造为 `3/3`、`9` 或 `0/3`。

Ruff、compileall、import、targeted/full pytest 也未运行：本阶段在创建 bundle、生产代码或测试变更前已经按来源合同立即停止。`git diff --check` 通过；默认 `data/research.duckdb` 结束 SHA-256 仍为 `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`。下载的 PDF、渲染 PNG、浏览器缓存和中间文件均已清理，未进入 Git。

## 阶段状态

```text
M2 Stage 1C-C.4: FAIL

blocker:
  company_official simplified-Chinese A-share full annual report not found

company full report:
  traditional Chinese -> excluded

company simplified A-share document:
  audited financial statements only -> not a full annual report

bundle created: false
runner executed: false
database written: false
Stage 1C-C.4 completed: false
multi-year integration allowed: false
```

若未来中国石油官网提供可核验的 2021 年简体 A 股完整年度报告正式路径，应从本阶段重新验收；在此之前不得用繁体版、审计报告、上交所副本或第三方转载绕过来源合同。
