# 工作记录：M4/M2 open PR 队列复核与合并

## 基本信息

- 日期：2026-10-08
- Agent：root（用户明确要求不使用 DSH、不委派）
- 当前分支：codex/m4-pr-queue-closeout（自 origin/main 8d0fb4d 新建）
- 开始提交：8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b
- 任务来源：用户“继续推进项目。不用dsh。你自己来干”；AGENTS.md 常设合并授权
- 对应模块：工程治理（复核与合并既有交付）

## 任务目标

按 2026-09-28 常设授权，独立复核并合并当前 24 个已交付 PR（#68–#91），
修复阻断其中 8 个 PR 的真实跨平台测试缺陷，并产出完整证据包。不启动新的研究阶段，
不获取真实数据，不使用 holdout。

## 范围

- 允许：复核/合并 #68–#91；在受影响 PR 分支上推送修复提交；本分支的 Goal、记录与验收文档。
- 禁止：force push、直接推 main、删除分支、重写历史；削弱/跳过测试；数据获取、数据库查询、
  统计执行、holdout、研究结论；修改保护基线、stash、数据库与无关工作树。

## 非目标

- 不启动 matrix 实现之后的新阶段、真实数据适配器或真实研究执行。
- 不清理主工作树既有未跟踪/修改文件，不处理 D:\量化分析 主树与 origin 的分支落后。

## 开始前状态

- origin/main 与实时 main：8d0fb4d0ba75726911ff6f7d7d9cbdc87a10db3b。
- 主工作树 D:\量化分析：feat/m2-value-assessment-mvp@3679b1b，脏树（用户文件）保留。
- 保护 stash：cb568efd7eaa6f0fca4b3bb5a1e2200b9341985f。
- 保护数据库 SHA256：4a71d3c7b88c0b16ae46ffb4f9bfbd006d91e0537e559235c9b5a1f919e2fce6。
- 24 个开放 PR：#68–#91；其中 #80–#87 的 ubuntu clean-clone 失败（测试调用 `cmd`），
  #90/#91 存在进行中的检查，其余检查全部成功。
- 依赖关系：#68→#69→#70→#71→#73→#74→…→#87 为线性堆叠链；#72、#88、#89、#90 独立；
  #91 依赖 #89。

## 实施计划

1. 落盘本 Goal 与本记录并提交（record-first）。
2. 建立保护快照（DB 哈希、stash、worktree、main 同步）。
3. 逐 PR 复核 head/diff/范围/检查，按依赖顺序合并全绿 PR（#68–#79、#88、#89、#90、#91、#72）。
4. 修复 #80 链上的 ubuntu 缺陷：POSIX 使用 os.symlink、Windows 保持 junction，
   意图与错误契约不变；本地先跑目标测试，再推送并等待 CI。
5. 将修复传播到 #81–#87 分支（合并 main，不 rebase），逐 PR 等 CI 变绿后顺序合并。
6. 处理 #90/#91 进行中的检查；全部完成后撰写验收文档，提交、推送、开 PR 并按授权合并。
7. 输出最终证据包（每条命令与结果、保护值、残留风险、未执行事项）。

## 决策记录

- 决策：只合并全部检查成功的 PR，不用 UNSTABLE/失败状态强行合并。
  原因：常设授权要求 “successful required checks”；仓库无分支保护，需自律执行。
  替代方案：开启 auto-merge 忽略部分失败——不采用，会绕过失败检查。
  风险：CI 等待时间较长（ubuntu clean-clone 约 14–18 分钟/轮）。
- 决策：修复 #80 链的 ubuntu 失败而不是跳过或放宽测试。
  原因：测试意图是“链接目录被拒绝”，POSIX 对应物是 symlink，可在不改变契约的前提下修复。
  替代方案：`pytest.mark.skipif` 跳过非 Windows——不采用，等于削弱验证。
- 决策：用合并 main 的方式更新 #81–#87 分支头，而非 rebase。
  原因：不重写已发布历史、不需要 force push。

## 实际操作

（执行过程中逐步更新本节：合并结果、CI 摘要、修复提交与验证。）

1. 检查主工作树、worktree 注册表、stash、数据库哈希、实时远端：无漂移（见上）。
2. 从 origin/main 新建本工作树与分支，落盘 Goal 与记录。
3. 逐 PR 复核：head、changed-files 范围、Goal/Acceptance 存在性、全部 42 项检查；
   确认所有新增源码集中在 src/ashare_research/tools/ 且不引入 socket/duckdb/url/requests/
   provider 等真实数据或网络调用（逐分支 grep 复核）。
4. 关键发现：#68–#91 是**堆叠 PR 链**，多数 PR 的 base 是上一条分支而非 main。
   #68 base=main；#69→#70→#71→#73→…→#79 的 base 依次为前一条分支。
   因此本轮把 #69–#79 合并进了各自声明的基础分支（GitHub 记录的合并即为该 PR 的
   实际语义），其内容将随链上后续 PR（#80 起）合并进 main。
5. 已合并（全部 head 与复核时一致、42/42 checks SUCCESS、mergeable CLEAN）：
   - #68 → main bc08bacbf7cc0db95082393138690a1f7285d758（head f9479c1）
   - #69 → c1c5f19e（head 1640ee5）/#70 → a9c5df82（head cf05289）/
     #71 → a08e8077（head 045d6b3）/#73 → 2f3ff8bb（head 748b782）/
     #74 → ccd112dd（head 7bdb6f0）/#75 → 50eacb52（head 3378090）/
     #76 → bc4981ab（head 4458142）/#77 → 4ef3cf3c（head f8cd69d）/
     #78 → 51542606（head 018624a）/#79 → a06cf3ce（head 34572a8）
6. #80 链修复：ubuntu clean-clone 因测试调用 `cmd` 建 junction 而失败（真实缺陷）。
   在 codex/m4-preparation-comparison-summary 上改为平台自适应（POSIX symlink /
   Windows junction），本地 9 passed，提交 1a81ffa 并推送；PR #80 base 改为 main，
   等待新 head 的 CI。
7. 复核发现（以 `git merge-tree --write-tree --name-only` 对当前 main 实测）：
   - #72（head 2164ff6）：与 main/链冲突于 README.md、research_entry.py、
     research_plan.py；其新增函数（_changes/build_comparison/render_comparison）
     与链上函数不重名，属可解冲突。
   - #88（head ec1749a）：仅 README.md 冲突（research_entry.py 可自动合并）；
     新增独立子命令 `research hypothesis-diff`，schema
     m4_compile_only_hypothesis_comparison_v1。
   - #90（head 980e31d）：仅 README.md 冲突；新增独立子命令 `research plan-batch`，
     schema m4_compile_only_hypothesis_inventory_v1，批次 1–16 份，只汇总声明需求。
   - **#89（head 83b2c99）与 #91（head 9b61d8f）：不可直接合并。**
     两者与已合并的 #68/#69 在同一路径 `src/ashare_research/tools/research_plan_package.py`
     / `research_plan_archive.py` 上 add/add 冲突，且 SCHEMA 同为
     `m4_compile_only_plan_package_v1` 却定义不同的包内文件名
     （#68: plan.json/plan.md；#89: report.json/report.md）。这是同一功能的两次
     独立实现（重复交付），需要设计层面的取舍/改造，超出“复核并合并”的授权范围，
     按 stop condition 不予合并并上报 CHANGES_REQUIRED。
   - 观察：#72 与 #88 都提供“两份假设配置对比”入口（一个挂在 research plan
     --compare-with，一个是独立 hypothesis-diff 子命令），功能相邻但不共享实现、
     不产生硬冲突；按项目既有小工具累积惯例可共存，但作为残留风险上报。
8. 运行器队列由合并推送产生的 56 个已合并分支冗余运行占满；这些运行不构成任何
   PR 的检查门禁，已 `gh run cancel` 取消以释放并发，保留所有 PR head 的相关运行。
9. #80 修复后 CI 42/42 SUCCESS、CLEAN，已合并进 main：merge commit 0818edff。
   至此链上 #68–#80 的全部内容（含修复）进入 main。
10. 波次二：把 origin/main（0818edff，含修复）合并进 #81–#87 各分支并推送；
   PR base 全部改为 main。新 head 与本地目标测试结果：
   - #81 b20e739e：10 passed（+entry）
   - #82 fbb1d061：13 passed
   - #83 42a94d6d：12 passed
   - #84 569ab436：12 passed
   - #85 9e9441dc：11 passed
   - #86 8a33a340：11 passed
   - #87 777b4118：12 passed
   注：首次 fetch 因本地代理 SSL 抖动失败，导致第一次本地合并合入的是旧 main
   （bc08bac）；随即重试 fetch 成功后再次合并 0818edff，各分支已确认包含修复
   提交 1a81ffa（每分支历史中多一个无内容的合并提交，未推送前已第二次合并修正，
   推送后的 head 均含修复）。

11. 2026-10-09 会话续作（用户再次指令"继续推进项目。不用dsh。你自己来干"）。
   开始时实测：origin/main 与实时 main 0818edff；#81–#87 head 与本记录第 10 步
   推送值一致（各分支 tip 均为同名"fix: build the … link fixture portably"
   提交，七个 patch-id 相同 27016）；#81/#82 为 CLEAN 且 42/42 检查成功，
   #83–#87 因 main 前移变为 DIRTY（GitHub 判定无法创建合并提交）。
12. 复核 #81、#82 精确 head 与 42/42 检查后依序合并：
   #81 → main 184baf28；#82 → main 5b30367e。合并后 #83–#87 仍 CONFLICTING。
13. 诊断：#83 与 main 之间存在两个 merge base（如 0818edff 与 cb5fbed），
   本地 git ort 递归合成虚拟基可干净合并（git merge 实测
   "Automatic merge went well"），GitHub 合并器拒绝；采用与波次二相同的
   处置：对 #83–#87 各分支把 origin/main（5b30367e）合并进分支并推送。
   五个合并提交均为内容空操作（合并前后 tree diff 为空），仅增加祖先历史；
   新 head：#83 fb6738c1、#84 c22f39a1、#85 42512f66、#86 64a4660b、
   #87 e3f87173。
14. 等待上述五个新 head 的托管检查全部完成后按依赖顺序合并。
15. #83 检查 42/42 成功且 CLEAN，已合并：main = 95fc18e（merge commit）。
   #81（main 184baf2）、#82（main 5b30367）为本会话更早完成。
16. #84–#87 在 #83 合并后再次变为 DIRTY（GitHub 合并器拒绝 criss-cross 多重
   merge base）。将新 main（95fc18e）再次合并进四个分支（均内容空操作，tree
   diff 为空）并推送：#84 bbc2942、#85 8a0fd4b、#86 8c206a5、#87 b3b1f3f。
17. 对 #88/#90/#72：本地将 b3b1f3f（#87 分支 tip；其树内容等于 #84–#87 全部
   合并完成后的 main）合并进各分支并解决冲突，使 GitHub 侧变为单基线合并，
   不再重演第 16 步的 criss-cross 拒绝：
   - #88：README（保留主线块 + 新增 hypothesis-diff 段）、research_entry.py
     （保留全部命令项并在元组首部加入 hypothesis-diff 行）；11 passed；ruff 通过。
   - #90：README（保留主线块 + 新增 plan-batch 段）、research_entry.py
     （保留全部命令项并在元组首部加入 plan-batch 行）；14 passed；ruff 通过。
   - #72：README（并存主线示例与 --compare-with 示例）、research_entry.py
     （plan 行并集，usage 首行含 [--compare-with JSON]）、research_plan.py
     （将 --compare-with 集成进扩展后的 main()：INVALID_ARGUMENTS 组合校验 +
     比较输出分支，保留 _changes/build_comparison/render_comparison）；8 passed；
     ruff 通过。
   三个新 head：#88 06d24ed、#90 59c80de、#72 f43aa29；推送后七个 PR 全部
   UNSTABLE（无冲突，等待检查完成）。
18. 观察：GitHub 合并器对分支与 main 之间存在两个及以上不可比 merge base 且
   虚拟基冲突的情形会拒绝（"the merge commit cannot be cleanly created"）。
   验证过的规避法是每次合并前令分支 head 包含当前 main（本地内容空操作合并 +
   推送 + 等检查变绿）；#81→#82 曾在该状态下直接合并成功。

19. 第二轮续作（用户中断后再次指令"继续推进项目。不用dsh。你自己来干"）。
    开始实测：origin/main=3346dbb6（#84 已在今日先合并），#85 随即 DIRTY（criss-cross
    再现）；#85-#87/#88/#90/#72 的 head 与检查状态与第 17 步一致（#84-#87 为 42/42 成功）。
20. #84 以 head=bbc29429、42/42 成功、CLEAN 合并 → main 3346dbb6（merge commit）。
21. 采纳"链式预合并"（chain pre-merge）：不再逐 PR 等待，而为全部剩余 PR 一次性构造
    包含"模拟未来 main"的分支头，保证每次 GitHub 合并在其时刻都有唯一 merge base，
    消除 criss-cross 拒绝；各步均为本地合并 + 普通推送（非 force）：
    - #85：merge(origin/main=3346dbb6) → 3909db6c（tree 前后相同：内容空操作）
    - #86：merge(F1＝模拟 main@#85后) → b48cc47b（空操作）
    - #87：merge(F2) → 32f1dcfa（空操作）
    - #88：merge(F3) → 98011e78（空操作）
    - #90：merge(F4) → 42aae481（真实冲突解：README 同时保留 hypothesis-diff 与
      plan-batch 两段；research_entry.py 保留两个独立 ResearchCommand 条目，
      顺序 hypothesis-diff 在前。本地 pytest 19 passed；ruff 通过；git diff --check 干净）
    - #72：merge(F5) → acb1fd17（README/entry 自动合并；pytest 21 passed；
      ruff 通过；diff check 干净）
    其中 F1-F5 为本地 commit-tree 生成的"模拟 main"合并节点（不推送、不进入 main，
    仅作为分支祖先存在，保证 GitHub 合并时 base 唯一）。六个新头推送后 GitHub 全部
    显示 MERGEABLE（无冲突）；检查运行期为 UNSTABLE（等待完成）。
22. 六个新头托管检查全部完成：各 42/42 成功、0 失败。依序合并（各自合并时点 head 与
    42/42 检查、mergeStateStatus CLEAN；#86 检查时点 GitHub 正在重算显示 UNKNOWN，
    合并请求被 GitHub 接受并成功）：
    - #85 3909db6c → 91a31bdd
    - #86 b48cc47b → a9cae1fb
    - #87 32f1dcfa → fd55e12c
    - #88 98011e78 → 94b01231
    - #90 42aae481 → f087b18d
    - #72 acb1fd17 → 47dbb678
    合并后 main=47dbb678（GitHub 实测与本地 origin/main 一致）。
23. 网络：本轮本地代理反复抖动（api.github.com EOF、git schannel handshake 失败）。
    gh 以临时清空 HTTP(S)_PROXY 环境变量直连完成查询与合并；git 以
    `-c http.proxy= -c https.proxy=` 绕过配置的 SOCKS 代理完成 fetch。
    未修改任何 git/系统代理配置。
24. 复核保护基线（见"验证"）：主工作树 21 项脏/未跟踪不变、stash cb568efd 不变、
    数据库哈希不变；无 force push、无直接推 main、无分支删除。
25. 保持开放的 PR：#89、#91（重复实现，证据见第 7 步与验收文档）；设计取舍交由用户。
    至此 24 个 PR（#68-#91）中 22 个已合并，2 个停机上报。

## 验证

本任务两轮会话累计执行的关键验证（均在对应时点实测；本节为本轮 2026-10-09 续作）。

1. PR 头与检查（每 PR 在其合并时点重新读取）：
   - `gh pr view <N> --repo dlam12138/ashare-research-lab --json headRefOid,mergeStateStatus,mergeable`：
     head 与复核值一致；
   - `gh api repos/.../commits/<head>/check-runs?per_page=100 --paginate`：
     42 项检查全部 completed/success、0 失败；
   - 今日合并的 10 个 head（#81-#84、#85-#90、#72）均为 42/42。
2. 分支本地验证（`PYTHONPATH=src` + `D:/量化分析/.venv/Scripts/python.exe`）：
   - #88：`pytest -q tests/test_research_hypothesis_compare.py tests/test_research_plan.py tests/test_research_entry.py` → 11 passed；
   - #90：`pytest -q tests/test_research_hypothesis_compare.py tests/test_research_hypothesis_batch.py tests/test_research_plan.py tests/test_research_entry.py` → 19 passed；
   - #72：`pytest -q tests/test_research_plan.py tests/test_research_plan_comparison.py tests/test_research_entry.py tests/test_research_hypothesis_compare.py tests/test_research_hypothesis_batch.py` → 21 passed；
   - `ruff check <变更文件>` 全部通过；`git diff --check` 全部干净。
3. 合并确认：`gh pr merge <N> --merge` 后以 `gh pr view <N> --json state,mergeCommit`
   确认 state=MERGED 与 merge commit oid（见"结果"）。
4. main 同步：`gh api repos/.../commits/main`＝47dbb678…；本地
   `git -c http.proxy= -c https.proxy= fetch origin main` 后 `git rev-parse origin/main`
   ＝47dbb678…（一致）。
5. 保护基线（开始与结束两次实测）：
   - 主工作树 `D:\量化分析`：feat/m2-value-assessment-mvp @ 3679b1ba…，
     `git status --porcelain` 21 项（用户脏/未跟踪文件原样保留，未被本任务触碰）；
   - `git rev-parse stash@{0}`：cb568efd… 不变；
   - `Get-FileHash -Algorithm SHA256 data/research.duckdb`：4a71d3c7…fce6 不变；
   - 无 force push、无 main 直推、无分支删除。
6. 网络异常与规避（未改任何配置）：
   - `git -c http.proxy= -c https.proxy= fetch origin main`（绕过配置的 SOCKS 代理）成功；
   - gh 在临时清空 HTTP(S)_PROXY 的子进程中直连成功。
7. 未执行的检查（如实列出）：未运行任何研究执行、数据获取、数据库查询、holdout
   或统计命令；未跳过、删除或削弱任何测试（唯一测试改动为上一轮的跨平台可移植性
   修复 1a81ffa，已在 main 中并由托管 CI 复核）。

## 结果

- 本轮合并（2026-10-09 续作，全部为 GitHub merge commit）：
  #81→184baf28、#82→5b30367e、#83→95fc18e、#84→3346dbb6、#85→91a31bdd、
  #86→a9cae1fb、#87→fd55e12c、#88→94b01231、#90→f087b18d、#72→47dbb678。
- 上一轮（同 Goal）：#68→bc08bac、#69→c1c5f19、#70→a9c5df82、#71→a08e807、
  #73→2f3ff8b、#74→ccd112d、#75→50eacb5、#76→bc4981a、#77→4ef3cf3、
  #78→5154260、#79→a06cf3c、#80→0818edf（缺陷修复 1a81ffa 随之进入 main）。
- 合计 24 个 PR 中 22 个已合并；#89、#91 未合并（重复实现，上报待裁）。
- main 最终：47dbb6780933f8fb7abab922aa47027a1342de41。
- 合并标准：精确 head + 全量检查 42/42 成功 + GitHub 合并器接受（CLEAN，或重算中
  被接受）；criss-cross 情况以链式预合并保证唯一 merge base（第 16-21 步）。

## 遗留问题

- #89/#91 开放中，等待用户设计决策；#89 额外的 I/O 加固（open+fstat dev/ino 身份核验、
  `..` 拒绝、单文件大小限制、写前目录身份复核）暂无归宿，可另行裁决后移植。
- #72（`plan --compare-with`）与 #88（`hypothesis-diff`）提供相邻的两套"两份输入对比"
  入口，按仓库小工具累积惯例共存，作为残留风险上报。
- 本地 git 走 SOCKS 代理不稳定（EOF / schannel handshake 反复失败）；本轮以绕过/直连
  解决，未改配置，后续会话可能仍需相同绕行。
- GitHub 对 criss-cross（两个及以上不可比 merge base 且虚拟基冲突）的拒绝行为无公开
  文档；规避法（分支头包含当前 main 使 base 唯一）为经验验证，已在两轮会话一致应用。

## 下一步建议

1. 用户裁决 #89/#91：建议按"被 #68/#69 覆盖"关闭，或单独授权小任务移植 #89 的
   I/O 加固；不做未授权合并。
2. 本队列已清空至仅剩上述两个决策项；如用户认可，可另行授权规划下一阶段
   （本任务不自动开启新阶段）。

## 最终文件变更

- agent/record/2026-10-08_01-m4-pr-queue-review-and-merge.md（更新：步骤 11-25 与全部收尾节）
- acceptance/2026-10-08_m4_pr_queue_review_and_merge.md（新增：验收与证据）
- agent/goals/2026-10-08_m4_pr_queue_review_and_merge.md（已在 84f1ac1 提交）
- 本分支未改动任何生产代码；生产变化全部发生在被复核合并的 PR 分支上。

## 最终Git状态

- 本分支 codex/m4-pr-queue-closeout：本次收尾提交已推送 origin（非 force），
  将按常设授权在自身托管检查全绿后合并。
- main（本地 origin/main 与 GitHub 实测）：47dbb678。
- 开放 PR：#89、#91（保持不动）；已合并：22/24。
- 各 PR 工作树（registry×5、hypothesis×2、plan-comparison×1）均干净无未提交改动；
  主工作树/stash/数据库保护值不变；无 force push、无 main 直推、无分支删除。
