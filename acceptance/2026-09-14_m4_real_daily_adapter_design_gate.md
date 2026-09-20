# M4 真实日频适配器设计准入验收

日期：2026-09-14。任务：[Goal](../agent/goals/2026-09-14_m4_real_daily_adapter_design_gate.md)；交付：[设计准入评审](../docs/m4_real_daily_adapter_design_gate_v1.md)。

## 核查与结论

DSH 对真实 Git、北极星、Stage4P、M3 来源/PIT、M4 合成接口及 PR #20 做只读挑战，退出码 0；它建议**仅允许另立纯设计阶段**，并指出合成 v1 的封闭枚举、模式和证据类型不能承载真实来源。DSH 没有编辑文件、运行 pytest、接触真实数据或提交。Codex 独立读取上述原始合同和源码，确认这一限制与下一设计所需的来源、日历、证券成员、时点、质量和前置注册证据。

本工作树从 `main@dec8a29730ec26cd1396c530e7bc6cbc6fef1a05` 建立；PR #20 保持 OPEN，head `d593f40ee6cc17147164c67d31f84ce34da6785a`，42/42 检查成功，未合并。PR 的合成可移植性证据未冒充本工作树的测试或真实研究证据。

从本工作树运行 `$env:PYTHONPATH = (Join-Path (Get-Location) 'src')` 后执行：

```powershell
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q -p no:cacheprovider tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4p_governance.py
```

实际结果：退出码 0，`114 passed in 2.90s`。该回归验证现有合成合同边界；没有真实数据测试，也没有把未运行的全量测试记作通过。文档 UTF-8、链接、Git 空白与保护状态的最终复核以本轮最终证据包为准。

## Verdict

**PASS** — 仅覆盖本轮设计准入评审。下一项纯设计可立项，但须另获用户指令并建立独立 Goal；真实数据获取、合同实现、统计运行、holdout、PR #20 合并和后续阶段均未授权。原 M2 工作树、stash 与默认数据库仅只读核查并保持保护。
