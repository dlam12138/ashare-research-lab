# M4 真实日频来源合同验收用例 v1

日期：2026-09-14。状态：**DESIGN_ONLY / NOT_EXECUTED / NOT_AUTHORIZED**。配套设计见[真实日频来源合同与适配器设计 v1](m4_real_daily_source_contract_design_v1.md)，任务契约见[本轮 Goal](../agent/goals/2026-09-14_m4_real_daily_source_contract_design.md)。

本文件只定义未来实现必须满足的用例，**没有**被写成测试、**没有**执行、**没有**构造夹具或目录。用例中的日期、数值与占位摘要仅用于说明判定逻辑；`<sha256:...>` 均为占位符，本文未计算任何真实摘要。真实实现需要另立 Goal，并在新测试文件中实现这些用例；不得放宽或改写既有合成测试。

## 1. 基线与判定约定

`NORMAL-01` 为基线 bundle，其余用例只描述相对基线的增量。基线骨架（字段语义见设计文档第 3 节）：

```text
schema_version = "M4_REAL_SOURCE_BUNDLE_V1"
adapter_version = "M4_REAL_DAILY_ROLE_ADAPTER_V1"
bundle_id = "rdc-baseline-01"
study_id = "<frozen-study>"
contract_digest = "<sha256:contract>"      # outcome 前冻结
plan_digest = "<sha256:plan>"
code_identity = {git_commit: "<frozen>", source_tree_digest: "<sha256:tree>"}
window = {development_start: "2022-01-04", development_end: "2022-01-06",
          holdout_start: "2023-01-01", holdout_policy_id: "NO_HOLDOUT_AUTHORIZED"}
roles = ["TARGET_OUTCOME", "FACTOR"]       # 冻结顺序
source_runs = 每个角色一条，含 provider/endpoint/dataset_id/请求窗口、
              bounded_transport_proof、raw_locator、raw_sha256、published_at、revision_id、vintage_id
auxiliary_artifacts = 日历、停牌、成员的登记原始字节与来源版本；实际内容可复算
artifacts = 注入的离线只读 RawArtifactReaderV1，返回与 raw_sha256 一致的实际字节
contract/plan = 拟议 RealStudyContractV1 / RealAnalysisPlanV1
lock = 独立封存的 FrozenStudyLockV1（合同/计划/代码/来源版本摘要均匹配），在 bundle 外保存
calendar_evidence = 已验证日历，trading_dates = 2022-01-04/05/06，
              timezone = "Asia/Shanghai"，signal_cutoff_local = "20:00"
membership_evidence = as_of_rule = "T_MINUS_1_KNOWN_AT_SIGNAL"，target_exclusion = true
observations = 设计文档第 6 节的 6 个域内转换后观测；另有域外价格 warm-up 锚点
              （TARGET_OUTCOME 收益 0.02/0.00/0.01），全部 available_at <= 当日 20:00，
              available_at_basis = SOURCE_PUBLICATION_VERIFIED
domain = {expected_dates: 3 日, required_roles: 2, coverage_gate: "1/1", min_joint_dates: 2}
input_digest = "<sha256:recomputed>"
```

判定约定：阶段 0–6 为首错即拒绝（`RealSourceError(code, stage, locator)`），其中原始字节与证据摘要在质量聚合前复算；阶段 7 为聚合质量判定（先统计全部缺口，再以精确有理数比较 gate 和完整日期门槛）。任何拒绝都不得输出可执行矩阵。除单独注明外，校验入口传入 bundle、拟议 contract/plan、独立封存的 lock 和实际字节读取器。

## 2. 正常用例

| ID | 输入 | 期望输出 | 校验入口 | 断言证据 |
| --- | --- | --- | --- | --- |
| RDC-N01 | 基线 bundle，全部字段齐备 | `M4_REAL_DATASET_PREPARATION_V1`；`execution_authorized=false`、`statistics_computed=false`、`research_outcome_consumed=false`、`outcome_bytes_examined=true`、`matrix=None`；`coverage = 6/6`、`gate_result=pass`、`joint_complete_dates=3` | `prepare_real_daily_dataset`（阶段 0–7 全通过） | outcome 前锁先通过；输出可复算 `dataset_digest`；无任何矩阵/统计字段 |
| RDC-N02 | 基线 bundle，`source_runs`、`observations`、`domain.expected_dates` 顺序打乱（集合不变、无重复） | 与 N01 完全相同的 `input_digest`、`dataset_digest` 与规范化字节 | `prepare_real_daily_dataset`、`real_dataset_to_canonical_dict`、`serialize_real_dataset`、带全部来源参数的 `validate_real_dataset` | 规范化排序键生效；重排不改变身份 |
| RDC-N03 | 基线 bundle 与同一原始字节复制到另一目录（宿主绝对路径不同，登记的相对 `raw_locator` 与 `raw_sha256` 不变） | 与 N01 相同的 `input_digest`、`dataset_digest`，通过 | `validate_real_source_bundle`（阶段 2） | 身份只由内容与相对身份决定，不含宿主路径 |
| RDC-N04 | 基线 bundle，`expected_dates` 由日历生成且与窗口一致，warm-up 锚点在域外显式声明 | 分母仍为 `3 × 2 = 6`，锚点不计入分母，`gate_result=pass` | `validate_real_source_bundle`（阶段 3、7） | 分母来源可追溯至日历与角色清单 |

## 3. 负例用例

| ID | 类别 | 输入增量（相对基线） | 期望结果 | 校验入口（阶段） | fail-closed 证据 |
| --- | --- | --- | --- | --- | --- |
| RDC-E01 | 缺发布时间 | 某观测 `published_at` 缺失或为 null | `REAL_PUBLISHED_AT_MISSING` | 阶段 5，`validate_real_source_bundle` | 抛出即拒绝，无准备结果 |
| RDC-E02 | 缺可得时间 | 某观测只有 `trade_date` 与 `ingested_at`，`available_at` 缺失 | `REAL_AVAILABLE_AT_MISSING` | 阶段 5 | 拒绝报告 `matrix=None` |
| RDC-E03 | 抓取时刻冒充 PIT | 某观测 `available_at_basis=INGESTION`，把早于截止的 `ingested_at` 赋给 `available_at` | `REAL_INGESTED_AT_AS_PIT` | 阶段 5 | 不得把 `ingested_at` 升级为可得性证明 |
| RDC-E04 | 晚于截止可得 | 2022-01-06 FACTOR 的 `available_at = 2022-01-07T09:00+08:00`（设计文档示例） | 该观测 `PIT_UNPROVEN`，且聚合后 `REAL_COVERAGE_BELOW_GATE`（`5/6 < 1/1`） | 阶段 5 记录，阶段 7 判定 | 拒绝报告含缺口明细，不得填零或顺延 |
| RDC-E05 | 修订版替换 | 同一 role+`trade_date` 用新抓取版本覆盖旧值，未给出新 `revision_id`/`vintage_id`，也未声明 `supersedes_raw_sha256` | `REAL_SOURCE_VERSION_MISSING` | 阶段 2 | 不得静默采用较新 revision |
| RDC-E06 | 修订身份冲突 | 声明了 `revision_id` 但 `raw_sha256` 与读取器返回的实际字节不符 | `REAL_RAW_HASH_MISMATCH` | 阶段 2 | 原始身份必须复算 |
| RDC-E07 | 非交易日输入 | 观测或日历域含 2022-01-08（周六）或法定休市日 | `REAL_NON_TRADING_DATE` | 阶段 3 | 不得回推日历、不得丢弃该行后继续 |
| RDC-E08 | 缺日历 | `calendar_evidence` 缺失或 `calendar_id` 未登记 | `REAL_CALENDAR_MISSING` | 阶段 3 | 无日历即无分母，直接拒绝 |
| RDC-E09 | 日历冲突 | 两个日历来源对 2022-01-05 是否交易日结论不同，或 `trading_dates_digest` 不符 | `REAL_CALENDAR_CONFLICT` | 阶段 3 | 冲突不取交集、不默认开市 |
| RDC-E10 | 停牌/身份歧义 | 2022-01-05 目标证券停牌且状态表与行情行冲突（既标停牌又有价格，或上市状态冲突） | `REAL_SECURITY_IDENTITY_CONFLICT`；若停牌状态表一致且显式声明，则记 `gap_reason=SUSPENSION` 并进入覆盖聚合 | 阶段 4、7 | 歧义即拒绝；显式停牌不得填零或换源 |
| RDC-E11 | 公司代码与证券 ID 混用 | `security_id` 填公司代码（无交易所限定），或 `company_id` 被当作主键参与连接 | `REAL_COMPANY_SECURITY_ID_CONFUSION` | 阶段 4 | 连接键必须是证券级身份 |
| RDC-E12 | t−1 成员漂移 | 某日成员按当日收盘后信息判定（`as_of_rule` 不符），或市场代理成员包含目标证券 | `REAL_MEMBERSHIP_DRIFT` | 阶段 4 | 不得用回填的当前成员替代历史成员 |
| RDC-E13 | 成员历史不完整 | 窗口内某交易日缺成员快照，或 `membership_rule_version` 中途变化未声明 | `REAL_MEMBERSHIP_INCOMPLETE` | 阶段 4 | 缺口不缩小 universe，也不默认沿用上一版本 |
| RDC-E14 | 复权混用 | 同一角色不同日期混用 `FORWARD_ADJUSTED` 与 `UNADJUSTED`，或转换公式版本未声明 | `REAL_ADJUSTMENT_MIX` | 阶段 6 | 不得自动统一复权 |
| RDC-E15 | 单位/收益语义错误 | 百分比点当小数（1.5 表示 1.5%）、价格直接当收益，或币种/单位与合同不一致 | `REAL_UNIT_MISMATCH` 或 `REAL_RETURN_KIND_MISMATCH` | 阶段 6 | 不做隐式换算 |
| RDC-E16 | 非法值 | 观测 `value` 为 NaN、空字符串或超出合同域 | `REAL_INVALID_VALUE` | 阶段 6 | 无效值不得当作缺口填充 |
| RDC-E17 | 缺角色来源 | bundle 缺 `FACTOR` 角色的 `source_runs`（角色仍在冻结清单） | `REAL_SOURCE_ROLE_MISSING` | 阶段 2 | 不得改用可选角色或缩减角色清单 |
| RDC-E17B | 有来源但缺角色观测 | `FACTOR` 的 `source_runs` 存在，但三个日期都缺其观测 | `REAL_COVERAGE_BELOW_GATE`，缺口明细为三个 `MISSING_OBSERVATION` | 阶段 7 | 来源存在不能掩盖角色观测缺行，也不缩分母 |
| RDC-E18 | 角色绑定不符 | 角色顺序、目标 outcome horizon 或控制序列集合与冻结合同/计划不一致 | `REAL_ROLE_BINDING_MISMATCH` | 阶段 1、6 | 合同与计划绑定必须逐项一致 |
| RDC-E19 | 重复行 | 同一 role+`trade_date`+`revision_id` 出现两条不同值的记录 | `REAL_DUPLICATE_OBSERVATION` | 阶段 6 | 不得取首条、末条或平均 |
| RDC-E20 | 覆盖低于门槛 | 同一日期的两个角色单元都缺，`coverage = 4/6 < 1/1`，其余两日完整 | `REAL_COVERAGE_BELOW_GATE` | 阶段 7（聚合） | 拒绝报告 `matrix=None`、`accepted_roles=()`，不得输出部分矩阵 |
| RDC-E21 | 覆盖边界（精确比较） | 同 E20，但在 outcome 前另行冻结 `coverage_gate = 2/3`；`joint_complete_dates=2` | 通过（`4 × 3 >= 2 × 6` 且 `2 >= min_joint_dates=2`），`gate_result=pass`，仍列出缺口明细；不授权执行 | 阶段 7 | 浮点近似不得导致误判，不能事后调门槛 |
| RDC-E21B | 完整日期不足 | `FACTOR` 在两个不同日期缺失，`coverage_gate` 预冻结为 `2/3`，单元覆盖为 `4/6`，完整日期仅 1 | `REAL_JOINT_DATES_BELOW_MIN` | 阶段 7 | 单元覆盖通过仍不得绕过完整日期门槛 |
| RDC-E22 | 伪造摘要 | `input_digest` 或某观测 `evidence_digest` 被替换为自报值；另对准备输出单独篡改 `dataset_digest` | `REAL_DIGEST_MISMATCH` | 阶段 2/6 后、或带全部来源参数的 `validate_real_dataset` | 内容复算不一致即拒绝，不得先做质量聚合 |
| RDC-E23 | 跨目录身份伪造 | 另一目录下相对路径相同但内容不同的原始文件被当作同一来源 | `REAL_RAW_HASH_MISMATCH` | 阶段 2 | 路径不作为身份，内容哈希决定身份 |
| RDC-E24 | outcome 后改合同 | 用离线夹具模拟 outcome 前独立封存的合同锁；bundle 或 contract 改写窗口、来源版本、角色、gate、horizon 任一字段，与锁不符（用例不读 outcome） | `REAL_POST_OUTCOME_MUTATION` | 阶段 1 | 合同在 outcome 前冻结，事后修改即拒绝 |
| RDC-E25 | holdout 注入 | bundle 含 `holdout_start` 及之后日期，或带 holdout 标记的数据 | `REAL_HOLDOUT_INJECTION` | 阶段 1 | 无一次性授权即拒绝，且不产生 holdout 输出 |
| RDC-E26 | 授权标志篡改 | `execution_authorized` 或 `statistics_computed` 被设为 true | `REAL_EXECUTION_NOT_AUTHORIZED` | 阶段 0 | 不变量强制为 false |
| RDC-E27 | 真实对象进入合成入口 | `M4_REAL_*` schema 对象传入 `run_synthetic_pipeline`、矩阵构建器或执行器 | 拒绝；断言实际冻结入口既有错误类型/码及无执行副作用，不要求拟议真实模块错误码 | 合成入口闸门 | 字段同名不得被当作合成证据接受 |
| RDC-E28 | 无界传输 | `bounded_transport_proof` 缺失，或响应日期超出请求窗口 | `REAL_ENDPOINT_UNBOUNDED` | 阶段 2 | 不得截断后继续使用 |

## 4. 覆盖核对

| 设计要求用例 | 对应用例 |
| --- | --- |
| 正常输入 | RDC-N01、RDC-N02、RDC-N03、RDC-N04 |
| 缺发布/可得时间戳 | RDC-E01、RDC-E02、RDC-E03 |
| 修订版替换 | RDC-E05、RDC-E06 |
| 非交易日 | RDC-E07、RDC-E08、RDC-E09 |
| 停牌/身份歧义 | RDC-E10、RDC-E11 |
| 公司对证券 ID | RDC-E11 |
| t−1 成员漂移 | RDC-E12、RDC-E13 |
| 复权混用 | RDC-E14 |
| 角色缺行 | RDC-E17、RDC-E17B、RDC-E18 |
| 重复行 | RDC-E19 |
| 覆盖低于门槛与完整日期 | RDC-E04、RDC-E20、RDC-E21、RDC-E21B |
| 伪造摘要 | RDC-E22、RDC-E23 |
| 输入重排不变性 | RDC-N02 |
| 跨目录身份 | RDC-N03、RDC-E23 |
| outcome 后变更 | RDC-E24 |
| holdout 注入 | RDC-E25 |
| 授权/入口隔离 | RDC-E26、RDC-E27、RDC-E28 |

## 5. 未覆盖与后续

未覆盖：真实 provider 的许可条款、限流与再分发；真实日历与成员来源的获取方式；真实 outcome horizon 的方法学选择；holdout 一次性授权的执行流程。以上均需真实数据或用户授权，超出本轮纯设计范围。

后续：实现这些用例需要另立 Goal，新增测试文件并对接第 1 节的基线骨架；在此之前不得声称真实来源合同已实现、已测试或已授权执行。
