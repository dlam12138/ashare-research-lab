# M2 Stage 2B-A 工作记录：资本开支现金事实覆盖

## 启动基线

- Branch：`feat/m2-value-assessment-mvp`
- HEAD：`5a3f9006b19781d1a42db6df09d5d718111f9c76`
- Worktree：clean
- `stash@{0}` 保持不动。
- Stage 1D-B：57 facts、最终 Fact PIT 15。
- Stage 2A：Metric Schema 1.0，26 个结果版本、20 个最终结果；全部
  Metric Result ID 作为冻结不变量。
- 默认数据库启动 SHA-256：
  `4A71D3C7B88C0B16AE46FFB4F9BFBD006D91E0537E559235C9B5A1F919E2FCE6`

## 官方 PDF 缓存策略

- 共享缓存：`D:\量化分析-cache\official-pdfs`。
- 每份文档先由已提交 annual bundle 取得 SHA-256、content_length 和
  URL，再验证缓存文件 `%PDF-` 文件头、大小和 SHA-256。
- 启动时共享缓存目录不存在。八个唯一 PDF 从任务开始前已存在且与
  bundle 完全匹配的 Git 忽略本地副本写入缓存；两组 byte-identical
  文档随后命中同一缓存对象。
- 正式统计：cache_hit 2、cache_miss 8、downloaded 0、
  hash_verified 10、populated_from_existing_local 8。
- 临时渲染和定位文件不进入 Git；共享 PDF 缓存不删除。

## 事实核验初步结果

- 经审计合并现金流量表的正式行标签为
  “购建固定资产、油气资产、无形资产和其他长期资产支付的现金”，与
  `cash_paid_for_fixed_assets` 语义一致；Concept ID、version、category、
  canonical unit 和 duration 语义不变，只补充正式中文 alias。
- 五个 original 合并列及后续比较列已完成两遍目视复核。当前确认
  2024 年报把 2023 比较值由 282,519 重列为 282,508（人民币百万元）；
  其余三个后续比较值不变，因此预期 `C = 1`。

后续实现、Fact ID、PIT、计数、门禁和提交证据将在真实离线验收后定稿。
