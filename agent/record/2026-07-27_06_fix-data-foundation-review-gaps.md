# 工作记录：修复数据底座审查遗留问题

## 基本信息

- 日期：2026-07-27
- Agent：Claude Code (deepseek-v4-pro)
- 分支：fix/data-foundation-review-gaps
- 开始提交：f2ef7b3
- 任务来源：独立复审，修复上一轮 4 个遗留问题
- 对应模块：数据底座（修复）

## 审查发现

1. raw_file_path 语义错误：实际保存的是标准化 staging 数据
2. 质量门禁测试未覆盖"提供方成功但数据不合格"路径
3. 主流程使用 mode="replace" 绕过 append 分支的完整排序
4. 无"已有正式文件在失败时保持字节不变"的保护测试

## 范围

修改 src/、tests/、记录文件。不触及 Milestone 2。

## 实际操作

### Fix 1: raw/staging/quarantine 语义

**修改文件：**
- `src/ashare_research/providers/base.py` — 新增 `_save_raw_response()` 方法，在标准化前保存原始响应
- `src/ashare_research/providers/akshare_provider.py` — `get_stock_daily()` 和 `get_index_daily()` 中调用 `_save_raw_response()`
- `src/ashare_research/providers/baostock_provider.py` — 三个方法中调用 `_save_raw_response()`
- `src/ashare_research/cli.py` — `_create_service` 传递 `raw_dir` 给 Provider 构造函数
- `src/ashare_research/services/data_service.py` — `raw_path` 从 `provider.last_raw_path` 获取并传入 DuckDB

**结果：**
- raw/ 目录保存上游原始字段名（Baostock: date, code, preclose, turn, tradestatus）
- staging/ 目录保存标准化后数据
- quarantine/ 目录保存质量失败数据
- DuckDB `raw_file_path` 指向真实 raw 文件
- 真实验证：`data/raw/baostock/stock_daily/sh_601857_*.parquet` 存在且包含原始字段

### Fix 2: 质量失败路径测试

**修改文件：**
- `tests/test_data_service.py` — 新增 `BadDataProvider` 类（6 种坏数据类型）
- 新增 6 个质量失败测试：`test_quality_failure_quarantines_{nan,inf,neg_inf,duplicate_pk,ohlc_broken,missing_field}_batch`
- 重命名：`test_quality_failure_blocks_parquet_write` → `test_provider_failure_blocks_parquet_write`

**覆盖：** Provider 成功返回数据 + 数据被质量检查拒绝 + 正式 Parquet 未创建 + DuckDB 记录失败

### Fix 3: 完整主键排序

**修改文件：**
- `src/ashare_research/services/data_service.py` — `_merge_with_existing()` 中按完整主键排序

**新增测试：**
- `test_merge_sorts_by_full_pk_after_backfill` — 历史回补排序验证
- `test_duplicate_request_returns_same_count`（已有的去重测试）

### Fix 4: 正式文件字节级保护

**新增测试：**
- `test_quality_failure_preserves_existing_parquet_byte_for_byte` — SHA-256 验证正式文件在失败时完全不变

## 验证

| 检查项 | 状态 |
|--------|------|
| pytest (全部) | ✅ 76 passed |
| ruff | ✅ 仅非阻塞风格建议 |
| Baostock 真实数据 | ✅ adjustflag=3, 18 rows, raw file 存在 |
| 原始 raw 文件字段 | ✅ Baostock: date, code, preclose, turn, tradestatus |
| DuckDB raw_file_path | ✅ 指向真实 raw 文件 |

## raw/staging/quarantine 最终定义

| 目录 | 内容 | 保存时机 |
|------|------|---------|
| `data/raw/` | 上游原始响应（上游字段名、上游单位） | Provider 获取后、标准化前 |
| `data/staging/` | 标准化批次快照 | Provider 标准化后、质量检查前 |
| `data/quarantine/` | 质量失败数据 | 质量检查失败后 |
| `data/parquet/` | 通过质量门禁的正式数据 | 全流程通过后 |

## 结果

**状态：completed**

所有 4 个审查问题均已形成闭环。每个问题有对应的实现代码和测试。

### 是否建议进入 Milestone 2

是。数据底座修复已充分验证：
- 真实 Baostock 不复权正常
- AKShare 成交量单位正确
- 质量门禁阻止坏数据入库
- 正式文件在失败时完整保护
- 完整主键排序保证查询顺序
- raw/staging/quarantine 三目录语义清晰


