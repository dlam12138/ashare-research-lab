# M2 离线研究资料交付指南

这条流程把已有的档案、指标速览、证据缺口台账和两时点对比放进一个 ZIP，
接收方复核后即可恢复浏览。示例使用仓库已有固定快照，不需要获取新数据。

## 准备环境

发送方与接收方都需要安装本仓库及其依赖，并保有兼容的代码和固定基线。
参照 [README 安装说明](../README.md#安装)，在仓库根目录、已激活的 Python
环境中运行以下 PowerShell 命令。ZIP 本身不包含完整运行环境。

建议随交付记录发送方的 `git rev-parse HEAD`，接收方核对自己的版本。
相同提交便于复现，但不替代下面的完整内容复核。

示例输出放在 `tmp/m2-handoff-walkthrough/`；`delivery.zip` 和 `received/`
必须尚不存在。再次操作请换一组新路径，保留上一份结果。

## 1. 发送方生成 ZIP

```powershell
python -m ashare_research.cli research deliver --as-of 2024-03-31 --compare-with 2025-03-31 --year 2023 --output tmp/m2-handoff-walkthrough/delivery.zip --json
if ($LASTEXITCODE -ne 0) { throw '生成失败，请先检查错误码' }
```

命令生成已完整复核的工作流 ZIP。这个示例包含 131 个文件；省略
`--compare-with` 时不生成两时点对比包，包含 80 个文件。
`--as-of` 是请求的查询时点，`--year` 是指标年度，不是下载或发布时间。
日期不会自动替换为今天；这里也没有刷新来源数据。

保存控制台回执中的 `archive_sha256`、`verified_file_count` 和
`verification.request`，连同代码提交号作为交付记录。交付文件是
`delivery.zip`；发送邮件或上传文件由使用者另行操作，命令不会自动发送。

## 2. 接收方先复核

将收到的文件放到示例 ZIP 路径，或者把后续命令中的路径换成实际位置。
若只是在同一台机器上演练，可直接使用第一步生成的文件。

```powershell
python -m ashare_research.cli research archive --verify tmp/m2-handoff-walkthrough/delivery.zip --json
if ($LASTEXITCODE -ne 0) { throw '复核失败，停止后续恢复和比较' }
```

成功回执的 `status` 是 `verified`，`package_kind` 是 `workflow`；
`verified_file_count` 应为本例的 131。核对 `archive_sha256` 与发送方记录
一致，并查看 `verification` 中的查询条件和复核说明。

这个命令不要求恢复目录，会在自有临时目录解码并逐字节复核完整包。
哈希一致可以核对文件是否相同；完整复核还检查内容能否由当前兼容基线重新生成。
二者都不证明发送者身份、数字签名或数据在历史某时刻已经公开。

## 3. 恢复并浏览

```powershell
python -m ashare_research.cli research archive --restore tmp/m2-handoff-walkthrough/delivery.zip --output tmp/m2-handoff-walkthrough/received --json
if ($LASTEXITCODE -ne 0) { throw '恢复失败，请保留现场并检查错误码' }
```

恢复会再次复核输入，成功回执的 `status` 是 `restored`。打开
`tmp/m2-handoff-walkthrough/received/index.md`，按导航浏览：

| 入口 | 用途 |
| --- | --- |
| `review/review.md` | 指标速览及请求的两时点变化 |
| `audit/audit.md` | 指标输入、缺失的原始证据及解释限制 |
| `session/index.md` | 完整档案、事实、指标和固定来源资料 |
| `compare/compare.md` | 本例两时点指标对比；未请求对比时没有此目录 |

先阅读速览和缺口台账，再深入档案。保留交付包原样；笔记放在包外，避免新增
文件或修改报告导致完整包复核失败。

## 4. 核对恢复内容，或比较两次交付

```powershell
python -m ashare_research.cli research diff --left tmp/m2-handoff-walkthrough/received --right-archive tmp/m2-handoff-walkthrough/delivery.zip --json
if ($LASTEXITCODE -ne 0) { throw '比较失败，请先解决输入复核错误' }
```

本例预期 `status: compared`、`same_content: true`、
`compared_file_count: 131`，以及：

```json
{"states": {"added": 0, "removed": 0, "changed": 0, "unchanged": 131}}
```

这是回执的字段摘录。完整 JSON 的 `entries` 按相对路径列出全部文件及前后
字节数和 SHA256；去掉 `--json` 则显示摘要及变化文件。

比较实际两次收到的 ZIP 时，改用以下命令，并将占位文件名换成实际文件：

```powershell
python -m ashare_research.cli research diff --left-archive old.zip --right-archive new.zip --json
if ($LASTEXITCODE -ne 0) { throw '两份交付包比较失败' }
```

左侧是旧包，右侧是新包；`added` 表示仅右侧有，`removed` 表示仅左侧有。
两边必须属于同一种包类型，且都能通过完整复核。ZIP 压缩方式或头部不同，
只要内部规范文件字节相同，仍会报告 `same_content: true`。

`diff` 成功退出码为 0，即使存在文件变化也是 0；自动化判断是否相同应读
`same_content`，不能只读退出码。文件变化不等于财务事实修订。
财务指标变化请查看本例的 `compare/compare.md`，或使用
[已有档案指标对比入口](../README.md#统一离线研究入口ashare-research-research)。

## 出错后如何继续

| 现象或错误码 | 处理 |
| --- | --- |
| `OUTPUT_PATH_EXISTS` | 使用新的输出文件或目录名，不覆盖旧交付 |
| `INVALID_ARGUMENTS` | 查看相应子命令的 `--help`；`archive --verify` 不接受 `--output` |
| `PACKAGE_KIND_MISMATCH` | 选择同类输入，例如工作流对工作流，档案对档案 |
| `VERIFY_*` | 检查代码及固定基线是否兼容、包内容是否被编辑；保留原件，解决原因后重试 |
| `ARCHIVE_*` | 核对实际收到的 ZIP；损坏、布局不安全或超限的包不能作为成功交付使用 |
| 写入失败 | 保留失败时的部分输出用于检查，解决磁盘或权限问题后换新路径重试 |

失败退出码为 2，不输出成功回执。生成和恢复不会覆盖或清理已有调用方路径；
迟到的写入失败可能留下部分输出，并不承诺原子发布。不要因文件已经出现就
认定成功，也不要通过修改清单或跳过复核来消除错误。

## 这份交付能支持什么

它支持浏览和复核既有固定来源资料。价值资料仍是混合日期汇编，事实和指标按
请求日期读取既有模型；两者不能互相替代。当前固定快照的 33 条事实、66 个
缺失原始父记录，以及历史发布和版本证据缺口保持不变。复核通过不会补齐这些
证据，也不会授予真实研究、回测、holdout 或生产使用资格。

本次实际演练结果见 [验收记录](../acceptance/2026-10-04_m2_handoff_guide.md)。
