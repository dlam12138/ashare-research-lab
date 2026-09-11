# M4 合成分析矩阵验收场景 v1

状态：DESIGN_ONLY / ACCEPTANCE_CASES_NOT_IMPLEMENTED。本文是
[合成分析矩阵设计 v1](m4_analysis_matrix_design_v1.md) 的配套验收场景清单。

本文中的全部数值期望值，都是 2026-09-10 在本工作树用**既有真实实现**（A.1 合同编译器、
A.2I 计划编译器、synthetic dataset adapter）实测得到的；矩阵投影部分按设计第 3、6.5 节
规则独立重算。**矩阵产品实现尚不存在**，因此本文不声称任何矩阵实现测试已通过。
每个案例都写明：输入变化、预期矩阵或错误、验证入口。

## 0. 验证入口与前置条件

### 0.1 唯一来源验证入口

```text
validate_dataset(preparation, contract, plan, bound_inputs)      # 现有四参数 API
```

`validate_dataset` 的实现口径是**重新 materialize 并逐字节比较
`serialize_dataset`**（真实代码，`mechanism/datasets/synthetic.py`）：

```python
expected = materialize_analysis_dataset(contract, plan, bound_inputs)
if serialize_dataset(preparation) != serialize_dataset(expected):
    _fail("IDENTITY_CONFLICT")
```

任何"只比 `dataset_digest` 字符串"或"只跑 serializer"的变体都**不是**合格验证入口。

### 0.2 矩阵层的拟议入口（尚未实现）

```text
materialize_design_matrix(preparation, contract, plan, bound_inputs) -> MatrixPreparationV1
matrix_to_canonical_dict(matrix) -> dict
serialize_matrix(matrix) -> bytes
validate_design_matrix(matrix, preparation, contract, plan, bound_inputs) -> None
```

- 对外材料化入口**只有**四参数 `materialize_design_matrix`：它必须先执行
  `validate_dataset(preparation, contract, plan, bound_inputs)`，随后才做质量门与投影。
  **不存在**只吃 `preparation` 的公开入口。
- `validate_design_matrix` **必须**同时接收 `matrix` 与其声称的 `preparation` 及原始
  `contract`/`plan`/`bound_inputs`，因为它要重跑 `validate_dataset`（其第一个参数就是
  `preparation`）。签名里没有"省略 preparation"的版本。
- `_project_validated_matrix(preparation, plan)` 是私有实现细节，不是 API、不是验收入口；
  本清单的任何案例都不得以它作为验证入口，也不得用它论证"公开旁路可绕门禁"。
- 上游 `AdapterError` 原样传播；矩阵内容不一致才是 `MatrixError("IDENTITY_CONFLICT")`。

### 0.3 复现口径

本文所有 fixture 数值使用既有测试模块 `tests/test_m4_stage4a1_typed_contract.py` 的
`_document()` / `_compiled()`。复现时：

1. 解释器：`D:/量化分析-m4a2i/.venv/Scripts/python.exe`（规划核查已确认存在，不自动安装依赖）。
2. `PYTHONPATH` 需包含工作树的 `src` 与 `tests`。
3. 探针只读、不写文件、不开数据库、不调用 provider 或统计库。
4. 输出中出现的 `matrix_digest` 一律按设计第 6.5 节冻结载荷计算；载荷形状不同的
   摘要**不可比**。

基础 fixture 常量（后续案例默认继承）：

```text
dates            = ("2020-01-02", "2020-01-03", "2020-01-06")
condition        = {operator: "LTE", threshold: "-0.0100"}
controls         = ["SYNTH_CONTROL_1", "SYNTH_CONTROL_2"]
coverage_gate    = "0.9900"
missingness      = "FAIL_CLOSED"
role_order       = ("TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002")
series values    = TARGET_OUTCOME 0.01/0.02/0.03 ; FACTOR -0.02/-0.01/0 ;
                   CONTROL_0001 0.01/0.02/0.03 ; CONTROL_0002 0.01/0.02/0.03
```

基础身份（全部实测）：

```text
contract_digest = ee450d1f23cc68fb88718f3aa607cdda0c5e0d2b3fe951eddcb6e9b7b007f457
plan_digest     = 45a2461708863a8f4e9cb92f7774d2ffd1084558950c8f421838174059e21981
input_digest    = c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602
domain_digest   = b78882e43d745e2095b55688ac1ea68da25fdd1c971cea9c77f50924c0e100da
dataset_digest  = c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b
matrix_digest   = a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a
sha256(serialize_dataset(preparation)) = 32533abc2e9cefc7f0fe66923afc9a3f5d6ca5b0def7d1228c33ead8d071a060
sha256(serialize_matrix(matrix))       = 70d9926e0bec6e440b8c692384cd67f4c03727e7fd7ee602affc009000b187fa
validate_dataset(base) = 通过（无异常）
```

预期基础矩阵：

| trade_date | INTERCEPT | FACTOR_CONTINUOUS | CONTROL_0001 | CONTROL_0002 | CONDITION_INDICATOR |
| --- | --- | --- | --- | --- | --- |
| 2020-01-02 | `1` | `-0.02` | `0.01` | `0.01` | `1` |
| 2020-01-03 | `1` | `-0.01` | `0.02` | `0.02` | `1` |
| 2020-01-06 | `1` | `0` | `0.03` | `0.03` | `0` |

目标向量（行序，不进入矩阵列）：`["0.01","0.02","0.03"]`。

## 1. 案例索引

| ID | 案例 | 类型 | 验证入口 |
| --- | --- | --- | --- |
| AC-01 | 无 controls | 正常 | 四参数 + 矩阵入口 |
| AC-02 | 多 controls（3 个） | 正常 | 四参数 + 矩阵入口 |
| AC-03 | 控制注册顺序变化 | 正常/身份 | 四参数 + 矩阵入口 |
| AC-04 | 精确条件边界（四算子） | 正常 | 四参数 + 矩阵入口 |
| AC-05 | 缺行（各角色）与分母不变 | 负例/质量 | 四参数 + 矩阵入口 |
| AC-06 | PIT 不可见（PIT_UNPROVEN / PIT_NOT_AVAILABLE） | 负例/质量 | 四参数 + 矩阵入口 |
| AC-07 | `REJECTED_QUALITY` 不产出可用部分矩阵 | 负例/门禁 | 四参数 + 矩阵入口 |
| AC-08 | 重哈希篡改（preparation 自洽篡改） | 负例/安全 | 四参数 + 矩阵入口 |
| AC-08b | 矩阵内容不一致（来源合法、矩阵被伪造） | 负例/身份 | 矩阵入口 |
| AC-09 | 原始输入不匹配（重哈希输入篡改） | 负例/安全 | 四参数 + 矩阵入口 |
| AC-10 | 嵌套修改（合同内层字段） | 负例/身份 | 四参数 + 矩阵入口 |
| AC-11 | 输入排列不变性 | 等价性 | 四参数 + 矩阵入口 |
| AC-12 | 跨目录身份（键序 + 工作目录） | 等价性 | 四参数 + 矩阵入口 |
| AC-13 | 规范十进制边界与非法值 | 负例/结构 | ObservationV1 构造 |
| AC-14 | 上游错误码传播 | 负例/结构 | 四参数 + 矩阵入口 |
| AC-15 | 行序与列数不变量 | 结构 | 矩阵入口 |

## 2. 正常案例

### AC-01 无 controls

**输入变化**：`_document()` 的 `controls = []`，重新冻结与编译。

**预期 preparation**（实测）：

```text
contract_digest = 224d1dda42298ac8c1055fa8093ffbacfd43592364568777f365552df2e26f73
plan_digest     = 25d45eccedca0854f2ec5a6ccc08701f54822cf20d57a8764484a2016347f0d7
input_digest    = d002f398f45b820f9b1d14e43c9866a7a3a53e52f0c3b7b65245408772124952
dataset_digest  = e0e52d46f078be3993e759b27c8bb84e71c3a590001282ef63eb1d02aff6728f
status          = READY_SYNTHETIC ; n/N = 3/3
role_order      = ("TARGET_OUTCOME","FACTOR")
```

**预期矩阵**（实测 `matrix_digest = f6df25c471bc1a60f6f48c4863f30791388d26461b3210228a118975e5505db8`）：

| trade_date | INTERCEPT | FACTOR_CONTINUOUS | CONDITION_INDICATOR |
| --- | --- | --- | --- |
| 2020-01-02 | `1` | `-0.02` | `1` |
| 2020-01-03 | `1` | `-0.01` | `1` |
| 2020-01-06 | `1` | `0` | `0` |

列数必须为 3（`coefficient_role` 依次为 `alpha`、`beta_factor`、`gamma_condition`），
**不得**因为"基础 fixture 有 2 个 controls"而补出 5 列。

**验证入口**：`validate_dataset(preparation, contract, plan, bound_inputs)` 通过；
`materialize_design_matrix(preparation, contract, plan, bound_inputs)` 返回 3 列矩阵。

### AC-02 多 controls（3 个）

**输入变化**：`controls = ["SYNTH_CONTROL_1", "SYNTH_CONTROL_2", "SYNTH_CONTROL_3"]`，
并额外提供 `CONTROL_0003` 序列（`0.04/0.05/0.06`）。

**预期 preparation**（实测）：

```text
contract_digest = 284295d316f2af1dad947a126d51ef077f5582f0d34841614eec644592d5a284
plan_digest     = 1be6c91f6e14f31f8402d48efad3e8fdf76ee2149049d889334d66d7058e3e04
input_digest    = daad9c937c22a8883c1b0bb54ff6ed4f9780f7baaeccb49e06e399e929bbae88
dataset_digest  = 4c0603288b168b067b9a117744ffba38c3e6a81a0be9668511702140f31bec0f
role_order      = ("TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002","CONTROL_0003")
status          = READY_SYNTHETIC ; n/N = 3/3
```

**预期矩阵**（实测 `matrix_digest = 13c1830672434e1d6a56ae8a3548ab106b6baab86295b792a242e2f4b43f115e`）：

| trade_date | INTERCEPT | FACTOR_CONTINUOUS | C1 | C2 | C3 | CONDITION_INDICATOR |
| --- | --- | --- | --- | --- | --- | --- |
| 2020-01-02 | `1` | `-0.02` | `0.01` | `0.01` | `0.04` | `1` |
| 2020-01-03 | `1` | `-0.01` | `0.02` | `0.02` | `0.05` | `1` |
| 2020-01-06 | `1` | `0` | `0.03` | `0.03` | `0.06` | `0` |

（C1/C2/C3 即 `CONTROL_0001`/`CONTROL_0002`/`CONTROL_0003`；`coefficient_role` 依次为
`beta_control_0001`…`beta_control_0003`。）

**验证入口**：列数必须为 6；控制列数量必须随注册控制数增长，不得固定。

### AC-03 控制注册顺序变化

**输入变化**：`controls = ["SYNTH_CONTROL_2", "SYNTH_CONTROL_1"]`（与基础 fixture 相反）。

**预期 preparation**（实测）：

```text
contract_digest = 91468509f54724eb61877baad116f1e67fa992eb22f6a5d4a2aea7b622145f1e
plan_digest     = 803eae6bdef67300792757170b238238786b77f314858cd34443c862f81c8143
input_digest    = 4a863864e3760a094a7d634c133aa3abe5badaf21f98d266372f08df992ae822
dataset_digest  = d4cddef0269825e3d040d3170aeab323c6c42c6c0e2e61c21c02f57bea8b1e94
role_order      = ("TARGET_OUTCOME","FACTOR","CONTROL_0001","CONTROL_0002")
```

**预期矩阵**（实测 `matrix_digest = 48f8a5b3930ecfad3abd29830d744ad8ec7cf368a130408d65f3fd90eab37f4f`）：

```text
rows = [("2020-01-02", ("1","-0.02","0.01","0.01","1")),
        ("2020-01-03", ("1","-0.01","0.02","0.02","1")),
        ("2020-01-06", ("1","0",    "0.03","0.03","0"))]
```

**关键断言**：本例的 `rows` 字面值与基础 fixture **完全相同**（两个控制 series 取值恰好
相同），但 `matrix_digest` 必须**不同**（`48f8a5b3…` vs `a3c40269…`）。角色名永远按注册
顺序重新编号为 `CONTROL_0001…`，不得按 series 名或字母序排回，也不得合并同名列。
因此"列名相同"不能作为身份判断依据。

**验证入口**：比较 `matrix_digest`；不得只比较矩阵字面内容。

### AC-04 精确条件边界（四算子）

**输入变化**：factor 序列固定 `(-0.02, -0.01, 0)`，阈值 `threshold = "0"`（合同写法），
只替换 `condition.operator` 并重新冻结、编译。计划中阈值规范化为 `"0"`。

**预期指示列**（实测）：

| 算子 | 2020-01-02 | 2020-01-03 | 2020-01-06 | `plan_digest` | `dataset_digest` | `matrix_digest` |
| --- | --- | --- | --- | --- | --- | --- |
| `LT` | `1` | `1` | `0` | `44207cc2…a8bab79` | `0246d5fb…96319d5` | `6b7687e3…417cbff7` |
| `LTE` | `1` | `1` | `1` | `798955e8…481bedf` | `4302b6f9…8a9c52` | `a862e23b…74a170ee` |
| `GT` | `0` | `0` | `0` | `f4030af6…88006f4` | `5a76f115…21d088d` | `7b170345…f5775183` |
| `GTE` | `0` | `0` | `1` | `f32b071c…f544b41` | `79e5fdd0…99f90f24` | `7fbfcf8f…c608d610` |

（完整 64 位值见设计文档第 7.3 节；本表省略号仅用于排版，验收时必须逐位比对。）

**阈值 `-0.01`（即合同 `"-0.0100"`）的边界对照**（实测）：

| 算子 | 指示列 (0102, 0103, 0106) | `matrix_digest` |
| --- | --- | --- |
| `LT` | (`1`,`0`,`0`) | `9d0c1f09…3fb7a49a` |
| `LTE` | (`1`,`1`,`0`) | `a3c40269…b2641e822a`（= 基础 fixture） |
| `GT` | (`0`,`0`,`1`) | `e228c48e…10ec77374` |
| `GTE` | (`0`,`1`,`1`) | `7a093d21…be271d1e0` |

**关键断言**：

1. 阈值相等处严格区分，不做浮点容差：`-0.01` 在 `LTE`/`GTE` 下为 1，在 `LT`/`GT` 下为 0。
2. 合同 `"-0.0100"` 在计划中规范化为 `"-0.01"`；`"0"` 规范化为 `"0"`。
3. 四个算子的 `plan_digest`、`dataset_digest`、`matrix_digest` 两两不同。

**验证入口**：逐算子构造合同并重编译；比对指示列与三个摘要。

## 3. 质量与拒绝案例

### AC-05 缺行（各角色）与分母不变

**输入变化**：`data_quality_gates = {coverage_gate: "0.66", missingness_policy:
"RETAIN_IN_DENOMINATOR"}`，删除单个 observation。

**预期**（实测）：

| 删除项 | n/N | `reason_counts` | `rejected_dates` | status | `dataset_digest` | `matrix_digest` |
| --- | --- | --- | --- | --- | --- | --- |
| `CONTROL_0002`@2020-01-03 | 2/3 | `{"MISSING_OBSERVATION": 1}` | `("2020-01-03",)` | `READY_SYNTHETIC` | `aff29dfd…40ae8d198` | `09a1af5f…4f1065812e` |
| `CONTROL_0002`@2020-01-02 | 2/3 | `{"MISSING_OBSERVATION": 1}` | `("2020-01-02",)` | `READY_SYNTHETIC` | `f85b4a37…ee245dec8` | `6e46e2a0…1d601addac` |
| `CONTROL_0001`@2020-01-03 | 2/3 | `{"MISSING_OBSERVATION": 1}` | `("2020-01-03",)` | `READY_SYNTHETIC` | `e684cab7…613701557` | `d995c832…27821d9d` |
| `TARGET_OUTCOME`@2020-01-03 | 2/3 | `{"MISSING_OBSERVATION": 1}` | `("2020-01-03",)` | `READY_SYNTHETIC` | `38b5d6cc…f2f6910` | `3c3b4158…10e05272` |
| `FACTOR`@2020-01-03 | 2/3 | `{"MISSING_OBSERVATION": 1}` | `("2020-01-03",)` | `READY_SYNTHETIC` | `8303d7e0…75932e27f` | `5734473d…474a5a245` |

**关键断言**：

1. `coverage_denominator` 恒为 3，缺口**不**缩小分母。
2. 上表第三列起各行 `n/N`、`rows` 行数与部分字面值相同，但 `dataset_digest` 与
   `matrix_digest` **两两不同** → 身份必须覆盖 `quality.reason_counts`、
   `quality.rejected_dates` 与 `dataset_digest`。
3. 矩阵行数必须是 2（保留的两个完整行），不得补齐被删日期，也不得把被删行的
   factor/control 值补零。

**验证入口**：`materialize_design_matrix(preparation, contract, plan, bound_inputs)`
返回 2 行矩阵；`quality.coverage_denominator == 3`。

**门槛精确性子案例**（实测）：

```text
gate "0.66" -> Decimal("0.66").as_integer_ratio() == (33, 50) -> 2*50 >= 3*33 -> True  -> READY_SYNTHETIC (2/3)
gate "0.67" -> Decimal("0.67").as_integer_ratio() == (67, 100) -> 2*100 >= 3*67 -> False -> REJECTED_QUALITY (2/3)
```

即 `2/3 ≈ 0.6667` 在 0.66 下通过、在 0.67 下拒绝。验收必须复算这一对，确认实现用的是
精确有理数比较而不是浮点或显示百分比。

**通过时的矩阵身份**（实测，gate 0.66 / RETAIN / 缺 `CONTROL_0002`@2020-01-03）：

```text
matrix_digest = 09a1af5f1dd323522e5b628f57245fb0287e551d19ff6d96f5a9214f1065812e
rows          = [("2020-01-02", ("1","-0.02","0.01","0.01","1")),
                 ("2020-01-06", ("1","0",    "0.03","0.03","0"))]
```

注意第二行是 `2020-01-06`（不是 `2020-01-03`）：被拒绝的日期整行从矩阵中消失，矩阵层
不得补行、不得补零、不得重排。

### AC-06 PIT 不可见

**输入变化**：在 gate 0.66 / `RETAIN_IN_DENOMINATOR` 下，令 `CONTROL_0002`@2020-01-03 的
`available_on = null`（PIT_UNPROVEN）或 `available_on = "2020-01-06"`（晚于交易日，
PIT_NOT_AVAILABLE），并重算 `input_digest` 与 `evidence_digest`。

**预期**（实测）：

| 场景 | n/N | `reason_counts` | `rejected_dates` | status | `dataset_digest` | `matrix_digest` |
| --- | --- | --- | --- | --- | --- | --- |
| `available_on = null` | 2/3 | `{"PIT_UNPROVEN": 1}` | `("2020-01-03",)` | `READY_SYNTHETIC` | `5cc29781…f80847c559` | `52298a8c…fcb6a0b7ef` |
| `available_on = "2020-01-06"` | 2/3 | `{"PIT_NOT_AVAILABLE": 1}` | `("2020-01-03",)` | `READY_SYNTHETIC` | `09dea69c…da35120337` | `fce3d11e…97ddcdc5b` |

**关键断言**：PIT 不可见与"缺行"在 `n/N` 上无法区分（都是 2/3），但在
`reason_counts`、`dataset_digest`、`matrix_digest` 上必须可区分。行被排除是**质量判定**
的结果，不是矩阵层自行过滤的结果——矩阵层只消费 `complete_rows`。

**验证入口**：比对 `reason_counts` 与 `matrix_digest`。

### AC-07 `REJECTED_QUALITY` 不产出可用部分矩阵

**输入变化**：

| 子案例 | gate | missingness | 缺口 | 预期 status | n/N | `complete_rows` |
| --- | --- | --- | --- | --- | --- | --- |
| 7a | 0.99 | `FAIL_CLOSED` | `CONTROL_0002`@2020-01-03 | `REJECTED_QUALITY` | 2/3 | `()` |
| 7b | 0.66 | `FAIL_CLOSED` | `CONTROL_0002`@2020-01-03 | `REJECTED_QUALITY` | 2/3 | `()` |
| 7c | 0.99 | `FAIL_CLOSED` | `CONTROL_0002`@2020-01-03 的 `value = null` | `REJECTED_QUALITY` | 2/3 | `()` |
| 7d | 0.67 | `RETAIN_IN_DENOMINATOR` | `CONTROL_0002`@2020-01-03 | `REJECTED_QUALITY` | 2/3 | `()` |

实测 `dataset_digest`：

```text
7a = d5e6511d420330e316c5b9ba26925294b7ecf2fcd77ec080f734e90bb32653cd  reasons={"MISSING_OBSERVATION": 1}
7b = 62352525a7724369ef7664233632f6a2a99571f64e7916e9a3cc3c0dd59984dd  reasons={"MISSING_OBSERVATION": 1}
7c = c75953b959b404a9f5a1c457578cc94400b97908afc6c097120ab850bf98a5f6  reasons={"MISSING_VALUE": 1}
7d = d1d287f7f0d657d8a36866e5392224c875cbcc5b647d43a8b31e38d48515487c  reasons={"MISSING_OBSERVATION": 1}
```

**预期矩阵层行为**（本设计的硬性门禁）：

1. 对外材料化入口按冻结顺序拒绝，**不返回任何对象**：
   - 步骤 A1：`validate_dataset(rejected_preparation, contract, plan, bound_inputs)` 先**通过**
     ——拒绝态 preparation 是适配器的合法产物，与原始输入逐字节一致，来源验证不应失败；
   - 步骤 A2：质量门随即拒绝，`materialize_design_matrix(rejected_preparation, contract, plan,
     bound_inputs)` 抛 `MatrixError("DATASET_NOT_READY")`，在任何投影之前终止。
2. 不存在 0 行的"空矩阵"对象，也不存在 2 行的"部分矩阵"对象。
3. 不允许任何"降级成功"路径：不能返回 `rows=()`、不能返回被截断的 rows、
   不能用其他错误码代替 `DATASET_NOT_READY`。
4. `validate_design_matrix` 在拒绝态下**没有可构造的验收输入**：合法矩阵对象不存在，因此
   本案例不构造伪造的"拒绝态矩阵"，也不把这种对象描述为必需输入。若调用方硬造一个对象并
   连同拒绝态 `preparation` 传入，流程会在 V3（重投影）同样以
   `MatrixError("DATASET_NOT_READY")` 终止——这是防御性行为，不是本案例的通过条件。
5. 7a 与 7b 证明：把 gate 从 0.99 降到 0.66 **不能**绕过 `FAIL_CLOSED` —— 两者都是
   `REJECTED_QUALITY`，因为 `FAIL_CLOSED` 下"存在任何缺口"即拒绝，与 gate 无关。

**验证入口**：对四个子案例的 `rejected_preparation` 断言
`materialize_design_matrix(preparation, contract, plan, bound_inputs)` 抛
`MatrixError("DATASET_NOT_READY")`；断言调用点没有任何可继续使用的返回值；并断言
`validate_dataset(...)` 本身**不**抛错（质量拒绝 ≠ 来源不一致）。

## 4. 安全与身份案例

### AC-08 重哈希篡改（preparation 自洽篡改）

**输入变化**：取基础 `preparation`，把 `complete_rows` 的三行 `condition_indicator`
全部取反（1→0、0→1），用 `dataset_to_canonical_dict` 去掉 `dataset_digest` 后重算并写回。

**预期**（实测）：

```text
tampered.dataset_digest = 721584843f0f10488b0e1aecc28cc30a52018844be4c5852923c0acdab57b79f
    （≠ 合法 c3410933652b992c798ec981d7a25da91ad7816b10d396468e87f34efc28879b）
serialize_dataset(tampered)                              -> ACCEPTED（内部自洽，无异常）
validate_dataset(tampered, contract, plan, bound_inputs) -> IDENTITY_CONFLICT
若被投影：matrix_digest = fdf644360661742ef18df1520cff830eba8dc629f97510b4bc84b9e951374d6a
    （≠ 合法 a3c40269f34d4414b177fd3ed512798934443aeeb6cae2a218d426b2641e822a）
    指示列由 (1,1,0) 变为 (0,0,1)
```

**关键断言**：篡改体自身摘要完全自洽、serializer 完全接受，**只有**四参数
`validate_dataset` 能拒绝。因此：

1. `serialize_dataset(tampered)` 通过**不能**作为矩阵入口的放行依据；
2. `tampered.dataset_digest` 形状合法**不能**作为放行依据；
3. 矩阵入口必须调用四参数 `validate_dataset`。

**验证入口**（拟议 API 的预期行为，尚未实现）：

1. `materialize_design_matrix(tampered, contract, plan, bound_inputs)` → 在 A1 步抛**上游**
   `AdapterError("IDENTITY_CONFLICT")`；投影从未执行，无矩阵对象返回。
2. `validate_design_matrix(forged_matrix, tampered, contract, plan, bound_inputs)` → 在 V2 步
   抛同一上游 `AdapterError("IDENTITY_CONFLICT")`；矩阵内容比较从未执行。
3. **不存在公开旁路**：没有任何只吃 `preparation` 的公开入口可以直接投影 `tampered`。私有
   `_project_validated_matrix` 不是 API、不是验收入口；它"不做来源验证"这一事实只说明来源
   验证必须由公开入口负责，不能反过来当作公开入口可绕过门禁的论据。
4. 来源合法但矩阵被伪造的情形，见 AC-08b。

### AC-08b 矩阵内容不一致（来源合法、矩阵被伪造）

**输入变化**：取基础 fixture 的**合法** preparation/contract/plan/bound_inputs，先按设计
口径得到合法矩阵 `M`，再伪造两个矩阵对象：

- `M1`：修改 `M.rows[0].cells` 的指示格（`1`→`0`）并**重算** `matrix_digest`，使对象自身
  自洽；
- `M2`：只改 `M.rows[0].cells` 而不重算 `matrix_digest`。

**预期**（拟议 API 的确定性语义，尚未实现）：

| 对象 | 调用 | 预期结果 |
| --- | --- | --- |
| `M1` | `validate_design_matrix(M1, base_preparation, contract, plan, bound_inputs)` | `MatrixError("IDENTITY_CONFLICT")`（V4 步：重投影字节 ≠ `M1` 字节） |
| `M2` | `validate_design_matrix(M2, base_preparation, contract, plan, bound_inputs)` | `MatrixError("MATRIX_DIGEST_MISMATCH")`（V1 步：自摘要与自身载荷不符） |
| `M` | `validate_design_matrix(M, base_preparation, contract, plan, bound_inputs)` | 通过（返回 `None`） |

**关键断言**：来源合法时矩阵层仍必须独立拒绝伪造矩阵；`MATRIX_DIGEST_MISMATCH`（V1）与
`IDENTITY_CONFLICT`（V4）分属两个不同阶段，不得混淆，也不得降级为"通过"。

### AC-09 原始输入不匹配（重哈希输入篡改）

**输入变化**：把基础 `bound_inputs` 中 `FACTOR`@2020-01-03 的值由 `"-0.01"` 改为
`"-0.05"`，同步重算该 observation 的 `evidence_digest` 与 `bound_inputs.input_digest`。

**预期**（实测）：

```text
base.input_digest      = c1f6c3d74066ee944dab4a56752da8b30ba8c647c3980a9051298c066409c602
rehashed.input_digest  = e877c147b58b53ee3283e87bcce49592470643c161e7a675af1e06a51943b464  （≠ base）
rehashed.dataset_digest = 2788e8ec06d370a3020b99fecbdcb4d7cb30d7568dbea33d0f22a63a063a7aea
rehashed.matrix_digest  = 95a7d95835ebd92f7f7cccfb890ba3bd2ad7cadab00c1e36f608a11a48b6fdf3
rehashed.rows           = [("2020-01-02",("1","-0.02","0.01","0.01","1")),
                           ("2020-01-03",("1","-0.05","0.02","0.02","1")),
                           ("2020-01-06",("1","0",    "0.03","0.03","0"))]
validate_dataset(rehashed_preparation, contract, plan, 原始 bound_inputs) -> IDENTITY_CONFLICT
```

**关键断言**：篡改后的输入自洽（`input_digest`、`evidence_digest` 全部重算正确），
因此"输入自报摘要"不能证明来源；只有拿**原始 `bound_inputs`** 重新 materialize 才能
发现不匹配。同时 `dataset_digest` 与 `matrix_digest` 都随数据改变——语义变化必须改变身份。

**验证入口**：`validate_dataset` 抛 `IDENTITY_CONFLICT`；
`materialize_design_matrix(rehashed_preparation, contract, plan, 原始 bound_inputs)`
同样在上游来源验证步骤拒绝（抛上游 `AdapterError("IDENTITY_CONFLICT")`）。

### AC-10 嵌套修改（合同内层字段）

**输入变化**：在 `_document()` 的内层
`robustness_registry[0].parameters.trim` 由 `"0.0100"` 改为 `"0.0200"`，重新冻结与编译。

**预期**（实测）：

```text
nested.contract_digest = f4c193cbbc9a32e9bc7d17bf9ba494c7702fc46acd3c723102d025e8084eed9f  （≠ 基础）
nested.plan_digest     = 8833ed844a7f50d9665945b7d18c07d2e1d72bde97b13cf8aeefcad24e2cc677  （≠ 基础）
nested.dataset_digest  = dfa395bb1dff0c694cad4d8cc3438d07c2896f92bdb72d20fdbcfe663eaf5c6d  （≠ 基础）
nested.matrix_digest   = b75877ee489f1a08bdcbbcc6fa0f0c57a9a1e1fcc940844ca04ea5ea7c2ddd5e  （≠ 基础）
plan.robustness_plan.entries[0].parameters.trim: 基础 "0.0100" -> 修改后 "0.0200"
materialize_analysis_dataset(nested_contract, base_plan, base_inputs) -> CONTRACT_PLAN_MISMATCH
```

**关键断言**：该内层字段**不影响矩阵任何单元格数值**（factor/control/target 与指示列
完全相同），但 `matrix_digest` 必须改变。身份绑定内容的全量，不绑定"看起来相关的字段"。
另外，把新合同与旧计划混用必须触发 `CONTRACT_PLAN_MISMATCH`。

**验证入口**：比对四个摘要；并在混用时断言 `CONTRACT_PLAN_MISMATCH`。

### AC-11 输入排列不变性

**输入变化**：把基础 `bound_inputs.observations` 整体逆序，其余不变。

**预期**（实测，全部为 `True`）：

```text
permutation.input_digest_equal      = True   （逆序后 input_digest 与原始相同）
permutation.dataset_digest_equal    = True
permutation.serialize_dataset_equal = True
permutation.matrix_digest_equal     = True
```

以及往返（`_input_payload` → JSON → `BoundDatasetInputsV1.from_dict`）后：

```text
roundtrip.dataset_digest_equal = True
roundtrip.matrix_digest_equal  = True
roundtrip.bytes_equal          = True
```

**关键断言**：观测行排列不进入身份，因为 `_input_payload` 在计算 `input_digest` 前已按
`(trade_date, 角色序位)` 排序。矩阵行序只由 `domain.expected_dates` 决定，不由输入排列决定。

**验证入口**：逆序后重算四个摘要与序列化字节，必须全部相等。

### AC-12 跨目录身份（键序 + 工作目录）

**输入变化**：两件事分别测试：

1. 把矩阵规范字典的键顺序按 `sha256(键名)` 重排（值不变）；
2. 把当前工作目录从工作树根切换到 `src/ashare_research` 后重新 materialize。

**预期**（实测，全部相等）：

```text
keyshuffled.matrix_digest_equal      = True
input_payload.key_order_equal        = True
other_cwd.dataset_digest_equal       = True
other_cwd.serialize_dataset_equal    = True
other_cwd.matrix_digest_equal        = True
```

补充实测：`serialize_dataset(preparation)` 的字节中不包含工作树绝对路径，也不出现
`worktree`/`hostname`/`cwd` 之类的键。

**关键断言**：键顺序与工作目录都不进入身份；`canonical_digest` 内部固定
`sort_keys=True`，身份链只由内容摘要构成。因此"跨目录身份"是同一身份，不是新身份。

**验证入口**：换 cwd 重算三个摘要与字节；重排键后重算 `matrix_digest`。

## 5. 结构与错误传播案例

### AC-13 规范十进制边界与非法值

**输入变化**：直接用 `ObservationV1(role, trade_date, value, available_on, source_record_id,
evidence_digest)` 构造，`value` 取下列各值。

**预期**（实测）：

| `value` | 结果 |
| --- | --- |
| `"0"` | ACCEPTED（唯一的零表示） |
| `"0.01"` | ACCEPTED |
| `"1"` | ACCEPTED |
| `"-0.01"` | ACCEPTED |
| `"-0"` | `INVALID_VALUE` |
| `"0.0"` | `INVALID_VALUE` |
| `"0.0100"` | `INVALID_VALUE` |
| `"1E-2"` | `INVALID_VALUE` |

规范形式规则（与 `_dec` 实现一致）：

```python
canonical = "0" if d == 0 else format(d, "f")
if "." in canonical:
    canonical = canonical.rstrip("0").rstrip(".")
if canonical != value:
    _fail("INVALID_VALUE")
```

**关键断言**：

1. 矩阵单元格全部是规范十进制字符串；`INTERCEPT` 固定为 `"1"`；指示列为 `"0"`/`"1"`。
2. 矩阵层**不重新解析、不四舍五入、不格式化、不转 float**；一旦上游放行非法字符串，
   矩阵层必须抛错而非就地"修好"。
3. 指示值必须是严格 `int`；`True`/`False` 属结构错误 `INVALID_INPUT_STRUCTURE`。

**验证入口**：`ObservationV1` 构造结果；矩阵单元格逐格正则校验。

### AC-14 上游错误码传播

**输入变化**：分别构造下列非法输入。

**预期**（实测；`materialize_design_matrix` 行为为拟议语义）：

| 场景 | 预期错误族 | 预期错误码 |
| --- | --- | --- |
| `bound_inputs.mode = "REAL"` | `AdapterError` | `UNSUPPORTED_MODE` |
| `bound_inputs.input_digest` 置为 64 个 `0` | `AdapterError` | `INPUT_DIGEST_MISMATCH` |
| 追加一条重复 observation | `AdapterError` | `DUPLICATE_OBSERVATION` |
| 某 observation 的 `evidence_digest` 置为 64 个 `0` | `AdapterError` | `EVIDENCE_DIGEST_MISMATCH` |
| observation 的 `trade_date` 改为域外日期 `2023-01-03` | `AdapterError` | `OUT_OF_DOMAIN` |
| 用另一份合同（`threshold = "-0.02"`）+ 基础计划 | `AdapterError` | `CONTRACT_PLAN_MISMATCH` |
| 用另一份合同（`operator = "GT"`）+ 基础计划 | `AdapterError` | `CONTRACT_PLAN_MISMATCH` |
| `validate_dataset(base_preparation, other_contract, base_plan, base_inputs)` | `AdapterError` | `CONTRACT_PLAN_MISMATCH` |
| `materialize_design_matrix(base_preparation, other_contract, base_plan, base_inputs)` | `AdapterError`（A1 步原样传播） | `CONTRACT_PLAN_MISMATCH` |
| `materialize_design_matrix(tampered, contract, plan, bound_inputs)`（AC-08） | `AdapterError`（A1 步原样传播） | `IDENTITY_CONFLICT` |
| 拒绝态 preparation（AC-07） | `MatrixError`（A2 步） | `DATASET_NOT_READY` |
| 伪造矩阵 `M1` + 合法来源（AC-08b） | `MatrixError`（V4 步） | `IDENTITY_CONFLICT` |
| 伪造矩阵 `M2` + 合法来源（AC-08b） | `MatrixError`（V1 步） | `MATRIX_DIGEST_MISMATCH` |

**关键断言**：全部上游错误**原样传播**，不被包成矩阵错误、不被吞掉、不被替换成
"矩阵准备失败"之类的新码；矩阵层自有失败才抛 `MatrixError`。`IDENTITY_CONFLICT` 在两个
错误族中都存在：来源层（`AdapterError`）表示篡改的 preparation/输入，矩阵层（`MatrixError`）
表示来源合法但矩阵内容与重投影不符——验收必须同时断言错误**类型**与 `.code`，不能只看码名。

**验证入口**：断言错误**族**与错误码逐项相等（上游一律 `AdapterError`，矩阵层一律
`MatrixError`），不得只看 `.code` 字符串。

### AC-15 行序与列数不变量

**输入变化**：不改变输入，只检查输出结构不变量。

**预期**：

1. `len(rows) == len(preparation.complete_rows)`（基础 fixture 为 3）；矩阵层不得过滤、
   重排、去重或补齐行。
2. 行序严格等于 `preparation.complete_rows` 的顺序，即 `domain.expected_dates` 的字典序。
3. `len(columns) == len(plan.design_plan.ordered_terms)`（基础 fixture 为 5）。
4. `[c.term_role for c in columns]` 精确等于：
   `["INTERCEPT", "FACTOR_CONTINUOUS", *(role for role in role_order if role.startswith("CONTROL_")), "CONDITION_INDICATOR"]`。
5. 每行 `cells` 长度等于 `len(columns)`；`position` 为从 1 起的连续整数。
6. `columns[*].source_role` 精确等于
   `[null, "FACTOR", "CONTROL_0001", "CONTROL_0002", "CONDITION_INDICATOR"]`（真实计划的
   实测形状，与 `compiler.py::_terms` 及 `tests/test_m4_stage4a2i_analysis_plan.py` 一致）。
   其中 `FACTOR_CONTINUOUS` 绑定 `"FACTOR"`、`CONDITION_INDICATOR` 绑定其 transform 输出
   角色 `"CONDITION_INDICATOR"`，两者**不同**。分派只按 `term_role`：`source_series_role`
   只表达输入来源，无法单独说明该列取常量 `1`、取 `values` 还是取 `condition_indicator`
   （`INTERCEPT` 为 `null`；指示列来源角色不在 `role_order` 中，且指示值不在 `values` 里，
   而在 `condition_indicator` 独立元素里）。当前 `ordered_terms` 上 `term_role` 与
   `source_series_role` 的取值恰好一一对应，但该对应是当前角色命名的结果，不是投影契约，
   实现不得依赖它。
7. `execution_authorized is False` 且 `statistics_computed is False`，且都是严格 `bool`。
8. `response_role == plan.design_plan.response_role == "TARGET_OUTCOME"`，且必须是
   `role_order` 成员，并且**不出现**在 `columns` 中。
9. `quality.status` 显式继承 `preparation.status`（`QualityReportV1` 本身不含 `status`）；
   `quality` 的其余七个字段（`coverage_numerator`、`coverage_denominator`、`coverage_gate`、
   `missingness_policy`、`failure_disposition`、`reason_counts`、`rejected_dates`）逐字段
   等于 `preparation.quality` 的同名字段，不重判、不重算。

**验证入口**：逐条断言；`source_role` 是进入规范载荷与 `matrix_digest` 的审计/来源元数据
（必须与计划一致），但**不参与取值分派**；`source_role` 与 `term_role` 的上述对应关系必须
显式测试，因为"列语义"与"来源绑定"是两层信息，混用会取错列。

## 6. 文档阶段实际执行的验证（非矩阵实现测试）

本阶段**没有**矩阵产品实现，因此只运行既有 adapter / compiler / 保护门回归，外加只读探针。
实际命令、退出码与结果记录在
[工作记录](../agent/record/2026-09-10_01_m4-analysis-matrix-design.md) 与
[验收文档](../acceptance/2026-09-10_m4_analysis_matrix_design.md) 中。

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& 'D:/量化分析-m4a2i/.venv/Scripts/python.exe' -m pytest -q tests/test_m4_synthetic_dataset_adapter.py tests/test_m4_dataset_adapter_review.py tests/test_m4_stage4a2i_analysis_plan.py tests/test_m4_stage4a1_typed_contract.py tests/test_m4_stage4p_governance.py tests/test_project_entry.py
```

## 7. 实现阶段的验收顺序要求

实现（另立 Goal、另获授权）时必须：

1. **先复现全部负例**（AC-07、AC-08、AC-08b、AC-09、AC-10、AC-13、AC-14）确认门禁真的拒绝；
2. 再实现正例（AC-01 至 AC-04、AC-05、AC-06、AC-11、AC-12、AC-15）；
3. 负例必须在**未实现**状态下先确认"当前没有对应 API"或"当前实现会错误放行"，
   不允许为了让测试变绿而放宽门禁；
4. 不得新增镜像式测试来替代真实最小实现验证；
5. 本轮全部 `matrix_digest` 期望值都是**设计口径的重算值**，不是实现产物；
   实现落地后若摘要不一致，必须先判断是"实现偏离冻结载荷"还是"设计载荷需修订"，
   不得直接改期望值。

## 8. 边界声明

- 本清单**不构成**实现授权、统计有效性声明、满秩/可估计/可交易声明或执行授权。
- 矩阵准备成功只表示"来源已验证 + 列映射与数值投影就绪"，不表示任何统计性质。
- 本清单**不授权**访问真实数据、provider、数据库、holdout 或进入 M4-B。
- 合成来源证据不得升级为真实研究证据。
