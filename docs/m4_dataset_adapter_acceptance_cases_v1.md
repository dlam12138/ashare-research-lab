# M4 数据适配器合成验收场景 v1

这是[设计规范](m4_dataset_adapter_design_v1.md)的未来实现验收矩阵，不是已运行的
适配器测试。当前没有 adapter API；下列输出为预期值。

基础 fixture：单目标、FACTOR、两个按合同顺序注册的控制；3 个合成预期日期
2020-01-02、2020-01-03、2020-01-06，全部属于合同 development。
目标收益 0.01/0.02/0.03，factor=-0.02/-0.01/0，两个控制各为 0.01/0.02/0.03。
全部 available_on 等于对应日期，来源 ID 唯一，证据完整，LT 阈值 -0.01，
门槛 0.66，missingness=RETAIN_IN_DENOMINATOR。输入标识完全使用 SYNTH_*，不
假借真实 ticker 或来源。构造器依规范计算所有证据摘要和上层摘要。

| 场景 | 唯一变更 | 必须结果 |
| --- | --- | --- |
| 完整基础输入 | 无 | READY_SYNTHETIC；n/N=3/3；indicator=1,0,0；执行授权 false |
| 控制单日缺行 | 删除 CONTROL_0002 的第二日 observation 并重算输入摘要 | n/N=2/3；全域仍 3 日；MISSING_OBSERVATION；2 完整行 |
| 更高门槛 | 上例 gate=0.67，重新冻结合同与计划 | REJECTED_QUALITY；n/N=2/3；complete_rows 空 |
| 严格缺失策略 | 缺行例改为 FAIL_CLOSED，重新冻结合同与计划 | REJECTED_QUALITY，即使 gate=0.66 |
| 显式空值 | CONTROL_0002 第二日 value=null | 保留 3 日分母；MISSING_VALUE；不填 0 |
| 未证明时点 | 第二日 control available_on=null | PIT_UNPROVEN，该行不能进入完整样本 |
| 未来可用 | 第二日 control available_on=2020-01-06 | PIT_NOT_AVAILABLE；n/N=2/3 |
| 非法身份 | 同 source_record_id 用于冲突 value | IDENTITY_CONFLICT，不降级为缺口 |
| 来源篡改 | 改 value 不重算 evidence_digest | EVIDENCE_DIGEST_MISMATCH |
| 输入篡改 | 改 input_digest | INPUT_DIGEST_MISMATCH |
| 角色缺失 | 删除整个 control binding | ROLE_BINDING_MISMATCH，不减少控制数 |
| 重复键 | 复制一个 observation，即使内容一致 | DUPLICATE_OBSERVATION |
| 非规范日期 | 用 20200102 或 2020-W01-4 替换日期 | INVALID_DATE |
| 非规范值 | bool、float、NaN、Infinity、字符串 0.0100 | INVALID_VALUE |
| 不明单位 | unit=PERCENT 或价格单位 | ROLE_BINDING_MISMATCH |
| 窗口越界 | 任意 role 增加非 domain 日期 | OUT_OF_DOMAIN，不静默过滤 |
| holdout 输入 | 增加合同 holdout 日期的 observation | OUT_OF_DOMAIN；任何统计调用计数为 0 |
| 空日历 | expected_dates 为空 | EMPTY_EXPECTED_DOMAIN |
| 全部缺行 | observations 为空，保留 bindings/domain；gate=0 | REJECTED_QUALITY；0/3；无完整行 |
| 整日被删除 | 删除所有角色第二日记录 | 分母仍 3；2/3；不能变为 2/2 |
| domain 被修改 | 删第二日但不改 calendar evidence | 证据不匹配失败 |
| 合法新 domain | 显式同步修改 domain 与证据并重算摘要 | 新 input/dataset identity，不能声称同一研究输入 |
| 计划被替换 | 换同结构、不同合同来源计划 | CONTRACT_PLAN_MISMATCH |
| 重哈希假计划 | 改计划阈值并重算 plan_digest | CONTRACT_PLAN_MISMATCH，与严格重编译不同 |
| 多日目标 | A.1 合法 horizon=5D | UNSUPPORTED_OUTCOME，不能当 1D |
| 未支持变换 | A.1 合法 factor.transform_semantics=STANDARDIZED | UNSUPPORTED_BINDING_POLICY |
| 未知策略 | 合同伪造非合成固定策略 | A.1 严格验证拒绝；不进入适配 |
| 弱质量开关 | pit_required=false，仍存在未来可用行 | 该行无效，不弱化计划的 PIT 要求 |
| 四条件算子 | 只变 LT/LTE/GT/GTE 并重冻 | 阈值相等处按算子精确区分，不用浮点容差 |
| 规范等价 | 反转 observation 输入及字典键顺序 | 规范输出字节、所有语义摘要不变 |
| 有序控制 | 交换合同 control 顺序并重冻/重绑 | 输出 roles 及 identity 改变，不排序回去 |
| 缺口身份 | 仅改缺口日期/原因，保持 n/N 不变 | dataset_digest 改变 |
| 防御复制 | 修改输入字典、导出 dict、嵌套列表 | 已构建对象和其序列化不变 |
| 环境独立 | 换 cwd、Windows/Linux、不同路径 | 相同输入固定 golden digest/bytes |
| 无外部行为 | 拦截文件、网络、DuckDB、回归及 bootstrap | 适配成功且这些调用均为 0 |

未来实现时应固化基础 fixture 的实际 contract/plan/input/dataset SHA256 和完整
序列化 bytes；本设计不虚构尚未实现的摘要。错误场景如改变字段需同步重算外层摘要
以命中被测试的内层错误；专测摘要失配的场景除外。质量场景断言完整审计行与缺口，
不能只断言状态字符串。不得为了通过测试修改 M3 源哈希或已有研究结果。
