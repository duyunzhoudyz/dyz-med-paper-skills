# 32技能离线路由声明与工件合同回归

此入口验证可机器执行的声明与合同，不需要模型账号、API Key、外部服务或患者数据。全部业务输入为合成数据，临时目录自动清理。需要 Python 3.10+ 和已安装的 PyYAML；缺依赖时报告 blocked，不自动安装。

## 执行

在仓库根目录运行：

```powershell
python -B scripts/run_offline_regression.py
```

默认在 `tests/results/offline-<UTC时间戳>/` 创建全新报告目录。也可显式命名：

```powershell
python -B scripts/run_offline_regression.py --output tests/results/offline-my-run
```

输出目录必须位于 `tests/results` 内且不存在；重复使用已有目录会退出2，不覆盖历史。退出0表示本次离线检查全部通过；退出1表示测试失败、跳过、缺少命名覆盖或其他检查失败；退出2表示输出路径或依赖等前置条件阻塞。此退出码不是科研结论或投稿门禁。

## 检查内容

| 层 | 执行内容 | 证据 |
|---|---|---|
| 32技能声明 | 名称、触发职责、排除边界、隐式调用开关、默认提示词身份；各技能有独立测试ID | `routing-coverage.json` |
| 38条语义规格 | 冻结20条与新增18条的ID、已知技能、正反集合、行为约束及全入口覆盖 | `routing-coverage.json` |
| 声明负向变体 | 每技能6种：改名、删触发、删边界、禁frontmatter调用、禁agent隐式调用、错误提示词身份 | `test-events.json` 中192个对应subtest |
| 规格负向变体 | 未知技能、正反冲突、空行为、跨文件重复ID、冒称已执行、空输入、缺入口覆盖、错误schema类型 | `test-events.json` |
| 工件交接 | results、PRISMA、references实际生成回执，交给passport；11种生产者状态组合与3组生命周期 | `test-events.json`、`unittest.log` |
| 关键失败分支 | 23组命名合同分支映射到实际执行的测试ID；缺失、失败或跳过不会算覆盖 | `failure-coverage.json` |
| 三类合成流程 | 观察队列、RCT、系统综述的正常/故障/待决定/版本失效；保留输入、报告与实际CLI回执 | `workflows/` |
| 新增写作交付工具 | 实际正文改数/移位、中文与英文数字和负号、引用/剂量/声明、四类文献导入与冲突、PubMed分页/缺页/查询绑定、DOCX内容与预检、评测包防答案混入 | `test_toolchain` 测试及 `test-events.json` |
| 工程检查 | 结构、链接、临时目录中Codex安装和字节自检；若本地工作区安装副本存在则另行只读核对；源文件与历史文件哈希前后比较 | `structure.json`、`installation.json`、`source-manifest.json` |

声明锚点由 `fixtures/routing-contract-v1.json` 独立维护，只忽略空白，不执行关键词分类。文案改变时应审阅其语义及职责边界，再更新合同锚点；不能直接从当前描述自动生成期望以消除失败。原语义fixture仍保持 `verification_status: not_run`，其必需/禁止行为文本是后续模型评测的判据，离线检查不声称已执行这些自然语言行为。

`fixtures/offline-coverage-v1.json` 是命名分支清单，不是源代码行覆盖率或穷尽证明。已有单工具测试仍由 unittest 自动发现；新增文件只要命名为 `test_*.py` 就进入统一回归。

## 离线约束

入口先运行护栏自检，再在父进程与所有获准子进程启用Python审计钩子。DNS、socket操作、系统shell和未获准进程启动被拒绝。仅接受当前Python执行四个既有业务脚本或其字节完全相同的临时副本；子进程使用 `-I -X utf8 -B`（隔离模式忽略环境编码设置，因此显式启用UTF-8），从校验过的字节执行，并禁止再创建进程。四脚本是 passport、结果对账、PRISMA计数、题录身份核对。模型CLI、`python -c` 和冒用脚本名均在启动前被拒绝。

护栏自检中的故意拒绝记录在自检结果中；业务测试若尝试越界，即使测试自行捕获异常，父/子进程的 `guard-events.jsonl` 仍会使总结果失败。正常运行没有该文件。报告分别记录允许的本地Python进程次数与意外阻断操作。

这是防止测试误联网或误启动外部模型的护栏，不是抵御恶意Python代码、原生扩展或系统级绕过的OS沙箱。题录测试中的模拟网络次数只代表mock transport，不代表真实HTTP；真实联网受上述护栏阻断。入口不读取认证文件或调用模型服务。

新工具测试在当前受护栏保护的 Python 进程内调用实际模块，PubMed 使用显式合成 transport；不会为新增脚本扩大子进程白名单。DOCX 测试检查文件包 XML、中文、数字、图表和引文，不冒充视觉检查。实际在线连通和 LibreOffice 渲染应另存证据，不加入离线入口。

`scripts/run_delivery_demo.py --output tests/results/<新目录>` 提供可重复的合成文献→正文→翻译→DOCX演示，产物及故障注入回执保存在新目录。它不替代三类原有合同流程、独立实际CLI试用或写作医学审阅。

## 结果解释

`summary.json` 汇总测试数、失败/错误/跳过、subtest数、各检查结论、离线护栏、版本与证据文件哈希；`test-events.json` 逐条保留测试及subtest状态。子项成功不替代父测试成功，命名覆盖按父测试最终pass计算。

passport退出0仅表示声明绑定有效且current。生产者返回差异或领域unverified时，其检查仍可能completed/current，报告原值必须保留。合同明确不解释领域结论能否支持关闭，消费方仍须审阅；回归专门验证这一限制。执行failed/blocked、输入或报告过期、不适用和缺关闭证据则不能冒充验证关闭。

本回归不能证明真实宿主加载、自然语言技能选择准确率、模型遵守边界、统计模型正确、全文证据正确或论文可投稿。JSON/YAML批准记录只检验结构与字节，合成人类来源不是真实批准。真实模型与医学验收均在报告中保持 `not_run`。
