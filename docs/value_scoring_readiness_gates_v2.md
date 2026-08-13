# 价值评分准入门禁（v2 复评）

版本：`value_dimension_scoring_readiness_gates_v2` / 1.0
日期：`2026-08-04`
状态：`frozen`

本文件取代 Stage 2 时代的 `docs/value_scoring_readiness_gates.md`（v1），对所有
十二项准入门禁依据当前仓库状态重新评估。每项门禁单独说明其是否阻塞**影子评分**
（shadow）或**生产评分**（production）。Stage 2K 只产出非生产影子，不产出生产评分。

## 结论概览

- 影子评分：**允许**（contract 可信、可追溯、缺失不等于零、PIT 安全、风险否决不可补偿）。
- 生产评分：**未授权**。enterprise_quality 的绝对阈值缺乏同行/统计校准，风险维度
  带边界不稳定，需有限的同行基准数据集。

## 十二项门禁复评

| # | 门禁 | v1 状态 | v2 状态 | 影子阻塞 | 生产阻塞 | 当前证据 / 凭据 |
|---|---|---|---|---|---|---|
| 1 | 每个评分维度有明确理论来源 | blocked | pass | 否 | 否 | `docs/value_dimension_scoring_methodology_v1.md`（四维契约，OECD/JRC/CFA 设计借用） |
| 2 | 每个分数可追溯至 Metric Result ID | blocked | pass | 否 | 否 | `config/value_dimension_scoring_registry_v1.json`：每个 component 绑定 metric_role/evidence_id |
| 3 | 缺失不等于零 | blocked | pass | 否 | 否 | `config/value_dimension_scoring_policy_v1.json`：missing_never_zero；ROIC 与股息收益率为 coverage gap |
| 4 | 周期企业有单独解释规则 | blocked | partial | 否 | 是 | 周期规则已写入 methodology；但无跨周期样本与行业基准，仅自述 |
| 5 | 至少有多年趋势 | partial | pass | 否 | 否 | ROE/ROA/margin/安全性/分红均有 2021–2025 序列；估值有 3y/5y/expanding PIT 分位 |
| 6 | 必要时有行业或历史基准 | blocked | partial | 否 | 是 | 自我历史 PIT 分位可用（估值）；绝对阈值无同行/统计校准；peer 未采集 |
| 7 | 阈值有经验或统计依据 | blocked | partial | 否 | 是 | 绝对阈值已冻结并有理论依据；无同行/统计校准 |
| 8 | 权重经过敏感性分析 | blocked | pass | 否 | 是 | `docs/value_dimension_scoring_weights_sensitivity.md` + `reports/petrochina_dimension_scoring_sensitivity_v1.json`：±25%、leave-one-out、coverage gate |
| 9 | 风险否决项不被其他高分抵消 | blocked | pass | 否 | 否 | 风险否决非补偿；任何触发即 block；缺失证据不视为无风险 |
| 10 | 事实、指标、评分版本化 | partial | pass | 否 | 否 | Fact Schema 2.1 / Metric Schema 1.0；评分 registry/policy/methodology 均 v1 |
| 11 | 不把评分写成买卖建议 | policy_ready | pass | 否 | 否 | 影子输出禁止 overall_score/rank/recommendation/target；`score_eligible=false` |
| 12 | 人工评审通过 | blocked | partial | 否 | 是 | 本阶段为受控研究方法测试；生产评分需另行授权与人工批准 |

## 复评说明

- 门禁 1、2、3、5、8、9、10、11：由当前 artifacts 支持，影子与生产均不阻塞。
- 门禁 4、6、7：部分通过（partial）。影子可用（以绝对阈值+自我历史分位做方法测试），
  但生产评分需要同行基准与统计校准，故阻塞生产。
- 门禁 12：partial。影子方法测试已建立；生产评分需要另行授权与人工批准。

生产评分未授权。任何通过门禁的现有证据都只支撑建立可解释的研究辅助，不自动生成
交易建议。缺失、不可比或分母失真必须显式呈现，不得以零代替。风险否决项与其他维度
分开表达，不能靠汇总抵消。