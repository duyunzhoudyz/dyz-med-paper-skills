# 医学稿件的可执行交付流程

以下工具由助手在用户已授权的任务内串接。用户提供真实材料及用途，助手负责生成输入清单、哈希和执行命令。每个 skill 自带所需脚本与参考说明，单独安装也能使用。工具的“consistent”只描述机械检查，不能代替证据解读、医学审阅或投稿判断。

## 1. 检索与文献导入

已有文献管理器导出文件，先运行 [import_references.py](../dyz-med-cnki/scripts/import_references.py)，支持 RIS、字面值 BibTeX、NBIB 和 PubMed XML。输出 library.json 保留输入哈希、记录位置、原始字段和合并来源；identity-batch-XXX.json 可进入既有题录身份核验。相同题名不自动合并；冲突留给人工处理。

需要新增公开主题检索时，[search_pubmed.py](../dyz-med-cnki/scripts/search_pubmed.py) 保存原始分页、查询翻译和检索记录。用户已有明确授权即可据实记录，不重复索要确认；新增外传用途或敏感内容仍须另行处理。超过上限、缺页、重复 PMID 或网络失败均不算完整检索。它只实现 PubMed；系统综述仍需方案指定的其他数据库及独立筛选。

格式和命令见[文献工具说明](../dyz-med-cnki/references/literature-cli.md)。

## 2. 写作与正文证据绑定

根据已核实的结果和证据制作论证蓝图，再按[写作工艺说明](../dyz-med-writing-plan/references/writing-craft.md)检查段落功能与反向提纲。引言说明问题和缺口；讨论解释结果、比较证据并交代局限；不把语言流畅当成结论成立。

为需要追踪的实际段落分配 claim 与 evidence 标记，登记来源文件哈希、具体定位、支持状态和处理意见。运行 [audit_manuscript.py](../dyz-med-evidence-audit/scripts/audit_manuscript.py) 将注册内容与当前正文重新绑定。正文改变、证据变更、悬空标记或未登记的数字段落必须重新检查；不能只核对一份脱离正文的自填表。

支持状态仍来自审阅者判断；程序不自动证明来源支持论点。无数字且未标记的事实也可能漏检，需人工覆盖。输入合同见[正文校验说明](../dyz-med-evidence-audit/references/manuscript-cli.md)。

## 3. 翻译与语言修订

保留原稿，另存新稿；运行 [compare_protected.py](../dyz-med-translate/scripts/compare_protected.py) 检查数字、比较符号和引用出现次数。对剂量、单位、时间点、伦理/基金/AI 声明补充明确的原文—目标文保护短语。中文紧邻数字、负号和小数同样应检查。

该工具不能识别 A/B 两组数值互换、因果强度、否定词或语义等价性。检查通过后仍须逐句对齐并人工复核语义；不得据此自动认可翻译。详见[保护检查说明](../dyz-med-translate/references/protected-content-cli.md)。deai 内提供同一脚本的独立副本。

## 4. 报告规范与 Word 审阅稿

按[版本索引](../dyz-med-guideline/references/versioned-guidelines.md)取得适用的官方清单，记录实际读取的版本与来源；索引本身不等于清单核查完成。

用已核实的章节、PNG 图和引用显示文字创建导出清单，运行 [export_docx.py](../dyz-med-export/scripts/export_docx.py)。它生成包含中文、英文、表格、图片、行号和编号引用的基础 Word 审阅稿。源稿不变，占位符保留，内部证据标记只在审阅副本中隐藏。公式、复杂排版及原生修订应另用相应工具，不能默默丢失。详见[DOCX 说明](../dyz-med-export/references/local-docx-cli.md)。

用本地 LibreOffice 或 Word 渲染并逐页检查中文显示、换行、图注、表格、引文与分页，另存绑定该 DOCX 哈希的视觉回执。导出成功不关闭科学问题，也不自动提交期刊。

## 5. 新增确定性工具链与安全门禁

- **本地零联网 PHI 初筛与假名化**：[deidentify_check.py](../dyz-med-data-adequacy/scripts/deidentify_check.py) 检测中文身份证号（含校验码）、手机号、住院号/MRN、敏感表头和 >89 岁年龄；原文件只读，报告不回显原始标识符。
- **PubMed/Crossref 撤稿与勘误核查**：[verify_references.py](../dyz-med-cnki/scripts/verify_references.py) 在身份核验同时提取 `Retracted Publication`、`Expression of Concern` 与 `Erratum` 提示并汇总到 `retraction_alerts`。
- **可复现 Table 1 与可溯源 SVG 图**：[table1_summary.py](../dyz-med-analyze/scripts/table1_summary.py) 生成含 SMD 与输入哈希的基线表；[plot_clinical_svg.py](../dyz-med-figures-tables/scripts/plot_clinical_svg.py) 生成色盲友好森林图/KM/RoB2 矢量图及 `.provenance.json`，支持 `--check`。
- **结构化报告规范核查**：[audit_guideline.py](../dyz-med-guideline/scripts/audit_guideline.py) 配合 [structured-checklists.json](../dyz-med-guideline/data/structured-checklists.json) 校验 STROBE/PRISMA-2020/CONSORT-2025/STARD-2015/CARE/TRIPOD+AI 的证据定位、不适用理由、稿件哈希新鲜度与适用条目覆盖率。
- **量化临床风格检查与个人记忆**：[style_check.py](../dyz-med-deai/scripts/style_check.py) 扫描中英文 AI 套话、强因果过断言与句长分布，支持用户显式维护跨论文术语偏好文件。
- **目标期刊政策提取**：[fetch_journal_policy.py](../dyz-med-journal-finder/scripts/fetch_journal_policy.py) 默认从本地快照提取字数/摘要/文献限额、报告规范与 AI 披露政策（`--online --url` 需显式授权）。
- **Word 原生修订留痕稿**：[export_tracked_docx.py](../dyz-med-export/scripts/export_tracked_docx.py) 基于纯标准库 OOXML `<w:ins>`/`<w:del>` 生成真正的 Word 修订模式文件，服务导师改稿与审稿修回。
- **宿主安全与流程 Hooks**：[hooks/med_guard.py](../hooks/med_guard.py) 与 [hooks/hooks.json](../hooks/hooks.json) 提供 PHI 拦截、Plan-first 门禁与编辑后未绑定数值提醒（默认 `advisory`，设 `DYZ_MED_HOOK_MODE=strict` 启用退出码 2 硬阻断）。

## 6. 可重复验证

在仓库根目录运行：

```text
python -B scripts/build_demos.py
python -B scripts/run_delivery_demo.py --output tests/results/my-demo
python -B scripts/run_offline_regression.py
```

演示使用合成材料并植入一次正文数值错误。完整回归还检查原有32技能声明、交接合同、安装和三类研究流程。独立实际CLI试用与人工语义审阅另计，不以单元测试数量充当临床质量。

维护时用 `python -B scripts/sync_shared_resources.py` 检查翻译/deai 脚本及写作参考副本。修改声明的规范源后，显式加 `--apply` 同步；不改用户全局安装。新版本正式模型评测须重新冻结源码并遵守[评测协议](../tests/evaluation-protocol.md)。
