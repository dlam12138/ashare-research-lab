# M4 数据适配器设计 v1

状态：DESIGN_ONLY / READY_FOR_IMPLEMENTATION_REVIEW。此文为本阶段规范；接口与
数据类型均为拟议接口，尚未实现。基线是 PR #9 合并提交
`bab24f981fef9336b84280544ce709702b9df116`。

## 目标与第一片范围

把已冻结的合同、分析计划和调用方显式提供的合成输入，转换为可追溯的日频角色表与
质量报告。既有计划只声明需要什么；适配器负责验证提供的数据是否满足声明。
第一片只支持一个目标时间序列、预先计算的 1D CLOSE_TO_CLOSE 收益和合成固定成员。
不支持面板、多证券逐行回归、价格转收益、跨时区对齐、财报因子或真实数据证明。
不调用 M3 的回归、bootstrap、稳健性或研究结果接口。

## 输入合同与计划必须一起验证

拟议纯函数：

```text
materialize_analysis_dataset(contract, plan, bound_inputs) -> DatasetPreparation
dataset_to_canonical_dict(preparation) -> independent dict
serialize_dataset(preparation) -> bytes
validate_dataset(preparation, contract, plan, bound_inputs) -> None
```

`contract` 是现有 FrozenMechanismContract，`plan` 是现有 DeterministicAnalysisPlan。
先用现有 build_analysis_plan(contract) 严格重编译，并要求与传入计划的规范序列化
逐字节相等。单独验证 plan_digest 或仅比较 source_contract_digest 不足以证明语义绑定。
计划没有投影 target.identity_policy、outcome.horizon/outcome_id 等全部合同字段，
因此不能仅从 plan 猜测这些值。本设计不改 A.1/A.2 的 schema、摘要或旧接口。

bound_inputs 必须显式传入；没有默认路径、数据库、当前时间、环境配置或 provider。
模式只接受 SYNTHETIC，且不是由模式字符串就能证明真实数据来源。该模式只允许
软件测试，无法升级为真实研究证据。真实数据适配必须另有来源验证设计和授权。

## 拟议 BoundDatasetInputsV1

公开构造器必须拒绝未知字段、错误运行时类型和可变嵌套容器；内部使用 frozen
dataclass 和 tuple。允许便捷构造器从调用方字典复制并规范化，不能持有调用方引用。
便捷构造器只复制容器、排序输入行及字典键；不得修复非法日期、数值或缺失证据。
以下表中所有字段必填，只有明确写 nullable 的字段允许 null。

| 字段 | 类型与约束 |
| --- | --- |
| schema_version | 固定 M4_BOUND_SYNTHETIC_DATASET_V1 |
| mode | 固定 SYNTHETIC |
| source_contract_digest / plan_digest | 与已验证合同及计划一致的 64 位小写 SHA256 |
| domain | ExpectedDomainV1 |
| bindings | RoleBindingV1 元组，按计划角色顺序 |
| observations | ObservationV1 元组；输入顺序不影响身份 |
| input_digest | 规范化完整输入的摘要，排除本字段 |

ExpectedDomainV1：domain_id、universe_id、membership_policy、pit_policy、
target_series_id、identity_policy、development_start、development_end、expected_dates、
calendar_evidence、membership_evidence。标识与策略逐项等于合同；日期窗口等于合同，
expected_dates 为非空、无重复、递增的交易日期元组，只能位于 development 闭区间。
calendar_evidence 为不可变对象，字段是 evidence_kind=SYNTHETIC_CALENDAR_V1、
domain_id、development_start、development_end、expected_dates、evidence_digest。
其重复字段必须与 domain 完全一致；摘要绑定除自身外全部字段。
membership_evidence 字段为 evidence_kind=SYNTHETIC_FIXED_MEMBERSHIP_V1、universe_id、
target_series_id、expected_dates、evidence_digest；固定目标覆盖每个预期日期。
不从已观测行推导交易日或成员，不用工作日规则猜测交易所日历。合成日历是显式测试
前提，不宣称证明交易所完整性。未来真实输入必须更换证据验证器，不能沿用该标签。

RoleBindingV1：role、series_id、value_semantics、unit、adjustment_policy、outcome_id、
horizon、observation_timing。角色为 TARGET_OUTCOME、FACTOR、CONTROL_0001…，
数量与顺序严格等于计划；series_id 逐项匹配计划。全部 unit=DECIMAL_RETURN、
adjustment_policy=SYNTHETIC_DECLARED_RETURN、horizon=1D、observation_timing=CLOSE_TO_CLOSE。
目标 outcome_id 等于合同，其余角色 outcome_id=null。全部 value_semantics=DAILY_RETURN；
第一片仅接受合同 factor.transform_semantics=RETURN，由明确白名单映射为 DAILY_RETURN。
目标的 OUTCOME_AS_DECLARED_BY_CONTRACT 必须通过原合同的 1D/CLOSE_TO_CLOSE 校验。
不将价格、百分比点或多日收益自动转换为目标单位。相同 series_id 可以绑定多个不同
角色，但必须有各自的 binding，值和来源必须一致；不擅自减少控制项或解除共线性。

ObservationV1：role、trade_date、value、available_on、source_record_id、evidence_digest。
value 为 canonical_decimal 字符串或 null，禁止 bool、float、NaN、Infinity 和非规范字符串；
禁止用零填补 null。available_on 是规范 YYYY-MM-DD 或 null；source_record_id 是非空
稳定标识，evidence_digest 绑定该行前五个字段及对应完整 RoleBindingV1。
摘要由验证器重算，不能仅检查字符串存在。重复 source_record_id 只可跨角色复用同一
series_id/date/value/available_on；其他冲突报错。缺失行无须伪造来源 ID。

第一片不声称行哈希证明金融 PIT 或身份真实性；它证明合成输入内部绑定一致。
所有日期要求解析后 isoformat() 与原字符串一致，不接受紧凑日期、周日期、时间戳
或隐式时区转换。时间粒度仅限交易日：available_on <= trade_date 才可供当日收盘后
研究使用；当日数值不能解释为收盘前可交易信号。日内发布时点属于未来设计。

## 不支持策略必须显式失败

第一片仅支持实际 A.1 中的 SYNTHETIC_FIXED_IDENTITY、SYNTHETIC_FIXED_UNIVERSE、
EXPLICIT_PIT 策略组合，并要求 factor_kind=SYNTHETIC_REGISTERED。这是当前枚举
支持的策略；未来 A.1 新增策略不能自动开放本适配器。未知策略由 A.1 校验拒绝；
合同合法但本适配器未支持的 factor transform 返回 UNSUPPORTED_BINDING_POLICY；不能
把 A.1 校验通过解释成所有数据绑定均可执行。即使 pit_required 或 identity_required
为 false，计划的 PIT_AND_IDENTITY_AND_FINITE 也不允许弱化角色有效性。

## 验证顺序、覆盖率与保留缺口

1. 验证对象结构、合同、计划精确绑定、模式及支持的策略/频率。
2. 验证独立 domain 与证据摘要；空 domain 报 EMPTY_EXPECTED_DOMAIN。
3. 验证 bindings 完整性、身份、单位和顺序。缺一个控制绑定是结构错误；某天缺一个
   已绑定控制的 observation 是数据缺口，两者必须区分。
4. 验证全部 observation 的键、规范值和来源。相同 (role, trade_date) 重复，即使
   值完全相同也报 DUPLICATE_OBSERVATION，不选首条/末条，不做版本猜测。
5. 输入日期不在 domain 一律 OUT_OF_DOMAIN；包括 holdout 和其他窗口外日期。
   不先过滤再验证，从而掩盖错误输入。绝不读取文件以裁剪 holdout。
6. 按完整 expected_dates 左连接每个必需角色。不得 inner join 缩小分母。
   角色有效 iff 行存在、value 非 null、available_on 非 null 且 <= trade_date，且来源
   与身份验证通过。值 null 标 MISSING_VALUE，行不存在标 MISSING_OBSERVATION，
   时间缺失标 PIT_UNPROVEN，未来时间标 PIT_NOT_AVAILABLE。
7. 保留 N 个日期的全域审计行及各角色缺口。n 为全部必需角色共同有效的日期数，
   coverage=n/N，门槛比较采用整数与规范 Decimal 的精确运算，不采用显示百分比。
   输出 coverage_numerator 和 coverage_denominator；不以舍入小数作为身份输入。
8. FAIL_CLOSED missingness：任何数据缺口使状态 REJECTED_QUALITY，即使覆盖率已达标。
   RETAIN_IN_DENOMINATOR：保留缺口，n>0 且 n/N>=gate 才 READY_SYNTHETIC；否则
   REJECTED_QUALITY。缺 PIT 证据的行永远不进入完整样本。结构/身份/摘要错误总是
   直接抛稳定错误，不降级成可容忍缺口。n=0 即使 gate=0 也不就绪。

全域质量报告不产生 INCONCLUSIVE 的研究结论。evidence_rule 中的
data_quality_failure_disposition 原样保留为下游解释字段，适配器不执行证据处置。
此处 READY_SYNTHETIC 仅表示输入准备通过，execution_authorized 始终 false。

## 输出与条件生成

DatasetPreparationV1 字段：schema_version=M4_DATASET_PREPARATION_V1、adapter_version=
M4_SYNTHETIC_ROLE_ADAPTER_V1、source_contract_digest、plan_digest、input_digest、
domain_digest、role_order、status、execution_authorized=false、quality、audit_rows、
complete_rows、dataset_digest。所有嵌套结构不可变，公开 dict 转换返回独立副本。

quality 字段：coverage_numerator、coverage_denominator、coverage_gate、missingness_policy、
failure_disposition、reason_counts、rejected_dates。reason_counts 按错误码排序，计数单位
为角色/日期单元；同一单元可有多个理由，不能将其总和当成缺失日期数。
rejected_dates 是至少一个角色无效的日期排序元组。
audit_rows 每行包含 trade_date 及按 role_order 的 cells 元组；cell 字段为 role、value
（缺行时 null）、available_on（缺行时 null）、source_record_id（缺行时 null）、
evidence_digest（缺行时 null）、valid、reasons。被拒绝的数据不被清零或改写。
reasons 按错误码排序去重；缺行仅记 MISSING_OBSERVATION，不额外重复计空值和时点
缺失。存在行则独立检查 value 与 available_on，可同时记录两种原因。结构错误校验
按上述阶段顺序执行；同一阶段按日期和角色序位处理，保证首个错误可复现。

仅 READY_SYNTHETIC 有 complete_rows；REJECTED_QUALITY 的 complete_rows 必须为空，
避免下游忽略质量门而误用部分样本。完整行字段为 trade_date、values（按 role_order
的规范数值元组）、condition_indicator。indicator 仅从同日有效 FACTOR 的 Decimal
和计划阈值执行 LT/LTE/GT/GTE 得到严格 int 0/1。不生成回归矩阵、拟合系数或 p 值。
下游显式数据框转换与执行器是后续阶段；本片不用 pandas 作为规范序列化边界。
validate_dataset 必须从原始合同、计划、完整 bound_inputs 重新准备并逐字节比较，
不能只验证一个重哈希输出的内部形状。serialize_dataset 的实现必须验证输出结构、
自身摘要、审计行到质量统计/完整行的一致性；完整来源验证仍需四参数验证入口。

## 确定性身份

使用现有 model_digest.canonical_digest（排序键、紧凑 UTF-8 JSON、SHA256，无换行）
计算各摘要；公开 envelope 序列化增加恰好一个 LF。摘要排除自身字段，数字始终
为规范字符串，计数与 indicator 为 int，布尔严格为 bool。输入 observations 按
trade_date、计划角色序位排序；重复键必须先拒绝。输出行按日期、cells 按角色序位。
domain_digest 是完整 domain 对象的摘要；input_digest 包含全部输入字段及完整
证据内容；dataset_digest 包含除自身外全部输出字段。所有 evidence_digest 的验证
先于上层 digest，禁止仅用自报 ID 或路径代替内容。

相同完整语义输入在不同目录/操作系统字节相同。日期域、角色顺序、任何值、缺口、
available_on、来源 ID、证据、合同或计划变化都必须影响身份。输入行排列和字典键
顺序不影响身份。绝对路径、主机名、运行时、UUID、下载 URL 不进入语义身份。
真实来源抓取时间等未来元数据的绑定另行设计，不将此次运行时间写成来源证据。

## 错误与 M3 复用

稳定错误至少包括 INVALID_INPUT_STRUCTURE、CONTRACT_PLAN_MISMATCH、UNSUPPORTED_MODE、
UNSUPPORTED_BINDING_POLICY、UNSUPPORTED_OUTCOME、EMPTY_EXPECTED_DOMAIN、
INVALID_DATE、ROLE_BINDING_MISMATCH、INVALID_VALUE、INPUT_DIGEST_MISMATCH、
EVIDENCE_DIGEST_MISMATCH、IDENTITY_CONFLICT、DUPLICATE_OBSERVATION、OUT_OF_DOMAIN。
报错可附 role/date，但不输出原始数据文件或隐私路径。上述枚举是拟议 API，不冒充
现有异常类已支持的错误码。

analysis_dataset.py 的防御复制、日期校验、重复拒绝、有限值和有效性原则可复用；
其 ANALYSIS_COLUMNS、全表非空要求、固定开发期及 target/tier1 筛选不适用新接口。
analysis_contracts.py 的 fail-closed 思路可复用，固定 M3 日期和 holdout 门不得调用。
model_digest.canonical_digest 可原样调用。regression/bootstrap/robustness/evidence
均不调用、不修改。适配器拟落在独立 mechanism/datasets 包，保持旧 M3 行为及哈希。

## 实施与验收边界

下一实施片仅含上述合成类型、纯适配器、规范序列化、验证器和
[合成验收场景](m4_dataset_adapter_acceptance_cases_v1.md)，不读取真实行情、不获取
provider、不构造真实 universe、不调用统计库、不开放 holdout，也不改 M4-B。
实现必须先复现负例，再验证固定输入跨平台身份、全部错误边界和原有保护门。
本设计验收不是实现授权；应在用户明确授权后建立单独 implementation Goal。
