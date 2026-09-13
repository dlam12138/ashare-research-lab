# 工作记录：DSH 独立核查 M4 多假设合成验收

## 基本信息

- 日期：2026-09-13
- Agent：DeepSeek Harness 执行；Codex 独立验收
- 分支：`codex/m4-multi-hypothesis-acceptance`
- 开始提交：`1e3a514b61ece0f134011c4b84a60ca1931e31cc`
- 任务来源：用户指定改用 DSH 推进
- 对应模块：机制验证 / 工程治理

## 目标、范围和非目标

按[DSH 核查契约](../goals/2026-09-13_m4_multi_hypothesis_dsh_review.md)独立审查现有合成多假设验收，发现真实缺陷时只在白名单内修正。不修改产品源码、冻结研究合同、真实数据、其他工作树；不推送、建 PR 或合并。

## 开始前状态

当前工作树干净，本地分支 HEAD 为 `1e3a514b61ece0f134011c4b84a60ca1931e31cc`；local/origin/live main 为 `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05`。原 M2 HEAD、stash 和默认数据库 SHA256 分别为 `3679b1bac7a1634c6452784a4d8f6d139966f222`、`cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f`、`4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6`。

## 实施计划与决策

DSH 阅读真实接口、测试、契约和 CI，再运行聚焦验证。只有发现可复现缺陷才改验收测试；记录实际失败与修复。完整 envelope 包含数值运行时，不将其字节相等当作本阶段的跨系统结论。Codex 对 DSH 交付独立审查。

## 实际操作、验证、结果与遗留问题

待 DSH 实际执行后填写。不得预填通过结论。Ubuntu/Windows CI 在分支未推送前仍待验证。

## 最终文件变更与 Git 状态

待实际执行后填写。不推送、不建 PR、不合并。
