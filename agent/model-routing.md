# Astra/Luna 模型路由协议

本项目采用 Astra 规划、Luna 实施、Astra 独立验收的边界。Astra 先确定目标、保护边界、允许写入路径和验收证据，再默认委派一个 `gpt-5.6-luna`、`medium` 的 Luna worker；worker 只执行已分配范围，不递归派工。

委派应使用最小 fresh context，并显式传递 `model=gpt-5.6-luna`、`reasoning_effort=medium`、`fork_turns=none`（若命名 agent 接口不支持 `fork_turns`，仍须明确模型和推理强度参数）。不允许静默回退到更昂贵模型。连续两次修复失败，或发现语义/保护边界问题，立即交回 Astra。

Astra 根据实际 diff、命令输出和保护状态独立验收；不重复无关的全量测试，也不只信 worker 报告。交接和结果至少写明：基线、写入路径、实现行为、实际测试及结果、授权停止点、实际提交（如有）和证据。未经明确授权，不自动进入下一阶段、合并或推送。

可复制的交接/回报模板：

```text
基线：<分支>/<commit>
工作树：<绝对路径>
Goal：<本任务合同路径，含禁止范围和验收标准>
写入路径：<实际文件>
行为：<实现后的可观察行为>
验证：<相关命令与结果>；稳定后按 Goal 全量一次，后续仅因变更或失败重跑相关检查
授权停止点：<停止位置>
实际提交：<commit 或未提交>
证据：<diff、日志、保护状态>
```

项目配置只表达规则和默认路由，沿用原有用户授权、审批和运行时权限，不提供硬权限隔离，也不保证真实 token 节省。主任务须由用户在界面选择 Astra，配置不会热切当前任务；主线合并后，新工作树会继承配置，旧会话和工作树不会自动更新。运行时不支持 fresh fork 时，只使用实际支持的字段并传最小上下文，不虚构工具字段；模型不可用或额度受限时显式报告，禁止静默改模型。

官方 custom agent schema 与字段说明：[Agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)。
