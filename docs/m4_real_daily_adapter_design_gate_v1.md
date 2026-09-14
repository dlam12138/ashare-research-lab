# M4 真实日频适配器：设计准入评审 v1

日期：2026-09-14。决策：**DESIGN_CONTRACT_STAGE_ELIGIBLE**。此结论只说明可以另立一项纯文档设计任务；不实现适配器，不获取或读取真实数据，不运行真实假设。任务契约见[本轮 Goal](../agent/goals/2026-09-14_m4_real_daily_adapter_design_gate.md)。

## 证据边界

[北极星 v2](../A股个股研究与市场机制验证平台-项目北极星.md) 的 M4-A 验收要求不同合法假设可配置、缺数据或方法时拒绝、配置与结果可追溯、合成 capsule 可跨系统复现，且不得放宽 M3 的 PIT、coverage、identity、holdout 规则。其历史 `NOT STARTED` 标题反映冻结时点，不覆盖当前主线的合成实现状态。[Stage4P 架构决策](../reports/m4_stage4p_architecture_decision_v1.json)选择在 M3 已验证核心之上建立薄通用层，同时把真实假设执行标为 `NOT_AUTHORIZED`。

主线 `dec8a29730ec26cd1396c530e7bc6cbc6fef1a05` 已有合成合同、计划、数据集、矩阵、有界执行和端到端入口。两条结构不同的合成假设在[PR #20](https://github.com/dlam12138/ashare-research-lab/pull/20) 的 `d593f40ee6cc17147164c67d31f84ce34da6785a` 上通过 Ubuntu、Windows 全量测试；PR 仍开放，未进入主线。该证据只涉及合成输入。现有[配置枚举](../src/ashare_research/mechanism/hypothesis_config.py)、[合成适配器](../src/ashare_research/mechanism/datasets/synthetic.py)和[有界执行器](../src/ashare_research/mechanism/execution/bounded.py)分别锁定合成身份/成员/因子、`SYNTHETIC` 模式与合成证据类型、以及合成数据执行门。当前没有把真实来源交给该管线的合法入口。

## 下一项纯设计必须回答的问题

| 边界 | 必须冻结的证据和拒绝规则 | 可借鉴而不能直接冒充通用证明的既有约束 |
| --- | --- | --- |
| 来源及版本 | 每个角色给出 provider、endpoint/方法、数据集/证券 ID、请求参数、原始内容哈希、抓取批次、来源发布时间及 revision/vintage；历史修订须产生新身份并说明选择规则。缺来源、版本或原始内容证明即拒绝，不自动换源。 | [M3 来源登记](../reports/m3_stage3b_source_registry_v1.json)与 `source_manifest.py` 的相对路径和内容哈希原则；M3 的具体 provider 与原始文件不是通用默认。 |
| 交易日历与时区 | 明确交易所范围、交易日和非交易日、停牌与半日处理、`Asia/Shanghai` 收盘/信号截止时刻，区分日期、时间戳和时区。预期日期必须来自经验证的日历，缺日历或冲突即拒绝，不能从已有行情行反推。 | M3 的交易日历来源与[日频时点合同](../reports/m3_stage3b_return_and_timing_contract_v1.json)提供约束；固定 M3 开发期及 2023 起 holdout 截止不能当作新假设窗口。 |
| 证券与成员 | 按证券级 ID 而非公司代码冻结上市/退市、证券类别、板块、特殊状态及规则版本；逐日成员按信号时点可知信息判定，市场代理等需要时使用 t−1 成员并显式排除目标。身份冲突、历史成员不完整、成员规则漂移即拒绝。 | [M3 主代理合同](../reports/m3_stage3br1_primary_proxy_contract_v2.json)及[证券身份恢复合同](../reports/m3_stage3dbr2_security_identity_recovery_contract_v1.json)记录 t−1、证券级身份与失败门；上证/601857/既有修复清单属于案例证据。 |
| PIT 与时序 | 区分 `observation_at`、`published_at`、`available_at`、`ingested_at` 和来源修订时点；对每个角色证明在合同规定的信号时刻已经可得。只给 `trade_date` 或同日海外日期不足以证明可得性；时间缺失、晚于截止、回填版本不明即拒绝。 | [M3 日频时点合同](../reports/m3_stage3b_return_and_timing_contract_v1.json)禁止用海外同日日期静默连接；合成适配器的 `available_on <= trade_date` 仅是日期级内部绑定，不是真实盘前或盘中 PIT。 |
| 数值与收益 | 冻结价格/收益类型、币种、单位、复权与公司行动、目标 outcome horizon、控制序列及角色顺序；禁止价格自动当收益、百分比点当小数、前复权与未复权混用。转换需要版本化公式及原始字段追溯。 | M3 目标研究收益与指数贡献收益在[时点合同](../reports/m3_stage3b_return_and_timing_contract_v1.json)中明确分离；该具体目标和行业/Brent 控制不得成为通用默认。 |
| 覆盖与缺口 | 用冻结的预期交易日域和角色清单作分母，报告每个角色及共同完整行的缺口、重复、无效值和 PIT 理由；缺项不得填零或缩小分母。门槛、warm-up、最小样本及失败处置必须预先声明；拒绝输出可供执行的部分矩阵。 | [合成适配器设计](m4_dataset_adapter_design_v1.md)的全域左连接、精确比率、`MISSING_OBSERVATION`/`PIT_UNPROVEN` 等思路可复用，合成证据本身不能升级。 |
| 谱系与注册 | 在读取真实 outcome 前冻结假设配置、窗口、源版本、角色、质量门与代码版本；绑定原始文件、规范化结果、合同/计划、数据集与代码的内容身份。绝对路径、当前时间、自报摘要均不足以替代内容验证；holdout 另设一次性授权和独立封存。 | [Stage4P M4-A 合同](../reports/m4_stage4p_m4a_generic_engine_contract_v1.json)禁止 outcome 后改合同；M4-B 只承载来源元数据，`NOT_TESTED` 不自动变成研究证据。M3 已解封且结论未定的 holdout 不能充当新鲜 OOS。 |

## 接口隔离与下一阶段交付

设计任务应首先决定一个**独立、版本化的真实来源合同与准备结果**如何同合成 v1 共存。当前 `IdentityPolicy`、`MembershipPolicy`、`FactorKind` 是封闭枚举，合成适配器的 calendar/membership evidence、`M4_DATASET_PREPARATION_V1` 验证器和执行器均锁定合成语义。不得只改 `mode`、重用合成 `evidence_digest`、把 `execution_authorized` 设为 true，或让真实对象通过 `run_synthetic_pipeline`。若设计需要扩展配置词汇或公共入口，必须提出**新的版本/独立接口和兼容性迁移方案**供另立 Goal 审查；本轮及下一项纯设计均不改冻结 v1。

建议下一项设计文档至少冻结：拟议公共类型与版本、逐字段来源证据、验证顺序及首错语义、规范摘要/序列化、M3 复用边界、正常与负例、合成回归保护、缺口及明确的实施门。负例须覆盖缺发布时点、修订版替换、非交易日/停牌、证券与公司 ID 混淆、t−1 成员漂移、复权混用、角色缺行、重复、阈值下覆盖、outcome 后改配置、holdout 输入和重哈希伪造。

**准入顺序**：用户单独授权纯设计 Goal → 设计与独立验收通过 → 再决定是否授权版本化合同/适配器实现 → 另行冻结真实来源和研究执行许可。任何设计 PASS 均不自动授权 provider 获取、数据库访问、真实候选、真实统计、holdout 或 PR 合并。

## 本轮保留风险

真实日历、成员历史、来源 revision/发布时间与目标收益约定尚未在 M4 通用合同中证明完整；M3 的案例修复和已消耗 holdout 不能补这个缺口。PR #20 的跨系统绿色 CI 通过全仓 `pytest -q` 收集合成测试，不能证明上述真实证据。若下一设计只能通过修改冻结 v1 或读取真实 outcome 才能完成，应停止并提交范围冲突，而非把缺口转成默认值。
