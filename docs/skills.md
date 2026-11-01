# 32 个医学论文 Agent Skills：完整技能索引

[中文首页](../README.md) · [English](../README_EN.md) · [中文索引](skills.md) · [English catalog](skills.en.md)

按当前任务选择技能。每行给出最小输入、主要输出和合成教学示例；示例不是已发表研究或用户反馈。

完整技能目录可安装到 Claude Code、Codex 或其他支持 Agent Skills 的宿主。宿主验证范围见 [项目说明](readme-reference.md#status)。

## 起点与项目状态

| 技能 / Task | 用途 | 最小输入 | 主要输出 | 示例 |
|---|---|---|---|---|
| [医学科研选题](../dyz-med-ideate/SKILL.md)<br>Research questions | 从临床观察梳理可验证的研究问题 | 临床观察、兴趣与资源限制 | 候选问题与可行性路线 | [示例 / Example](../dyz-med-ideate/examples/示例-社区获得性肺炎选题推导.md) |
| [论文项目初始化](../dyz-med-init/SKILL.md)<br>Project setup | 为已明确的研究建立论文项目与结构 | 研究问题、设计与已有材料 | 项目骨架与材料缺口 | [示例 / Example](../dyz-med-init/examples/示例-老年髋部骨折队列研究立项.md) |
| [医学稿件诊断](../dyz-med-manuscript-diagnose/SKILL.md)<br>Manuscript diagnosis | 先评估已有稿件的问题与修改顺序 | 初稿、摘要或拒稿意见 | 诊断报告与修改优先级 | [示例 / Example](../dyz-med-manuscript-diagnose/examples/worked-example-rejected-manuscript.md) |
| [论文进度与下一步](../dyz-med-orchestrator/SKILL.md)<br>Workflow navigation | 根据现有材料判断下一步任务 | 论文文件夹与当前需求 | 进度地图与下一步建议 | [示例 / Example](../dyz-med-orchestrator/examples/虚构项目进度地图样例.md) |
| [项目状态记录](../dyz-med-passport/SKILL.md)<br>Project state | 内部维护已确认事实与产出版本 | 已确认事实、材料和批准记录 | 可追溯的项目状态 | [示例 / Example](../dyz-med-passport/examples/虚构项目状态文件样例.yaml) |

## 研究设计与文献证据

| 技能 / Task | 用途 | 最小输入 | 主要输出 | 示例 |
|---|---|---|---|---|
| [机制与因果逻辑](../dyz-med-mechanism/SKILL.md)<br>Mechanisms and causality | 检查机制假设、因果路径与证据层级 | 研究问题、设计与支持证据 | 机制链、假设缺口与验证路径 | [示例 / Example](../dyz-med-mechanism/examples/示例-炎症因子与术后认知功能障碍机制推导.md) |
| [数据充分性检查](../dyz-med-data-adequacy/SKILL.md)<br>Data adequacy | 判断数据能支持的问题和分析范围 | 数据字典、设计与获准数据 | 充分性报告与可分析范围 | [示例 / Example](../dyz-med-data-adequacy/examples/worked-example.md) |
| [研究注册核查](../dyz-med-registration/SKILL.md)<br>Study registration | 对照官方注册记录与方案、稿件 | 注册号、方案与稿件 | 注册对照表与待核实差异 | [示例 / Example](../dyz-med-registration/examples/示例-降压药物RCT注册核查.md) |
| [PubMed 与中文文献检索](../dyz-med-cnki/SKILL.md)<br>Medical literature search | 设计 PubMed 和中文医学来源检索并记录覆盖范围 | 研究问题、数据库与纳排范围 | 检索式、记录与候选文献池 | [示例 / Example](../dyz-med-cnki/examples/worked-example.md) |
| [关键文献精读](../dyz-med-key-literature/SKILL.md)<br>Critical literature reading | 对已有文献作结构化阅读与证据比较 | 候选文献与可访问全文 | 单篇简报与证据地图 | [示例 / Example](../dyz-med-key-literature/examples/worked-example.md) |
| [系统综述文献筛选](../dyz-med-screening-pipeline/SKILL.md)<br>Systematic review screening | 管理去重、筛选、纳排理由与 PRISMA 计数 | 检索记录、筛选协议与全文 | 筛选记录、提取表与计数 | [示例 / Example](../dyz-med-screening-pipeline/examples/worked-example.md) |
| [论断与引用核查](../dyz-med-evidence-audit/SKILL.md)<br>Claim–evidence audit | 检查文献和数据是否支持稿件论断 | 稿件、来源文献与研究结果 | 论断—证据矩阵与问题定位 | [示例 / Example](../dyz-med-evidence-audit/examples/worked-example.md) |

## 统计分析与图表

| 技能 / Task | 用途 | 最小输入 | 主要输出 | 示例 |
|---|---|---|---|---|
| [医学统计分析](../dyz-med-analyze/SKILL.md)<br>Biostatistical analysis | 先形成计划，再按批准范围执行统计 | 获准数据、数据字典与研究问题 | 分析计划、脚本与结果记录 | [示例 / Example](../dyz-med-analyze/examples/worked-example-cohort.md) |
| [统计结果与临床意义](../dyz-med-interpret/SKILL.md)<br>Clinical interpretation | 区分统计证据、效应大小与临床重要性 | 统计结果与有来源的临床阈值 | 逐结局解释与谨慎措辞 | [示例 / Example](../dyz-med-interpret/examples/worked-example.md) |
| [敏感性与稳健性分析](../dyz-med-sensitivity/SKILL.md)<br>Sensitivity analysis | 围绕明确的不确定性比较替代假设 | 主要结果、具体假设与批准范围 | 稳健性比较与局限说明 | [示例 / Example](../dyz-med-sensitivity/examples/worked-example.md) |
| [医学论文图表](../dyz-med-figures-tables/SKILL.md)<br>Manuscript tables and figures | 规划和核对 Table 1、森林图等图表 | 已执行分析输出与数据来源 | 图表、图注与一致性清单 | [示例 / Example](../dyz-med-figures-tables/examples/worked-example.md) |
| [研究流程图](../dyz-med-flowchart/SKILL.md)<br>Study flow diagrams | 由真实计数整理 PRISMA、CONSORT 等流程图 | 研究流程、筛选记录与计数 | 流程图、图注与计数核对 | [示例 / Example](../dyz-med-flowchart/examples/worked-example.md) |

## 论证与论文写作

| 技能 / Task | 用途 | 最小输入 | 主要输出 | 示例 |
|---|---|---|---|---|
| [论文论证与写作提纲](../dyz-med-writing-plan/SKILL.md)<br>Manuscript writing plan | 把研究问题、结果与证据组织成段落计划 | 研究问题、已核实结果与文献 | 论证地图与章节提纲 | [示例 / Example](../dyz-med-writing-plan/examples/示例-他汀类药物队列论证地图构建.md) |
| [医学论文引言](../dyz-med-introduction/SKILL.md)<br>Introduction writing | 围绕具体知识缺口组织引言 | 研究问题、写作提纲与核实文献 | 引言草稿与逻辑说明 | [示例 / Example](../dyz-med-introduction/examples/worked-example-knowledge-gap.md) |
| [医学论文方法部分](../dyz-med-methods/SKILL.md)<br>Methods writing | 将实际研究过程写成可复核方法 | 方案、执行记录与分析计划 | 方法正文与缺项清单 | [示例 / Example](../dyz-med-methods/examples/示例-队列研究方法部分撰写.md) |
| [医学论文结果部分](../dyz-med-results/SKILL.md)<br>Results writing | 把核实后的统计输出写成结果正文 | 已核实统计输出、表格和图 | 结果正文与数字对应关系 | [示例 / Example](../dyz-med-results/examples/worked-example-xelox-dfs.md) |
| [医学论文讨论](../dyz-med-discussion/SKILL.md)<br>Discussion writing | 组织主要发现、证据比较、意义与局限 | 已核实结果、研究设计与文献 | 讨论草稿与论断边界 | [示例 / Example](../dyz-med-discussion/examples/示例-他汀类药物与骨密度机制论断的证据分级.md) |
| [标题、摘要与关键词](../dyz-med-abstract/SKILL.md)<br>Titles and abstracts | 从已完成正文生成结构化摘要 | 完整正文、核实结果与期刊要求 | 标题、摘要与关键词 | [示例 / Example](../dyz-med-abstract/examples/worked-example-zhonghua-trimming.md) |
| [全文初稿与统稿](../dyz-med-write/SKILL.md)<br>Full manuscript drafting | 按明确请求整合材料或统一已有章节 | 已确认研究材料或完成的章节 | 完整初稿或统稿版本 | [示例 / Example](../dyz-med-write/examples/worked-example-final-coherence-check.md) |

## 翻译、修订与交付

| 技能 / Task | 用途 | 最小输入 | 主要输出 | 示例 |
|---|---|---|---|---|
| [医学论文中英翻译](../dyz-med-translate/SKILL.md)<br>Medical translation | 翻译正文与回复并保护数字、引用和术语 | 原文、术语表与目标语言 | 译文、术语表与保护检查 | [示例 / Example](../dyz-med-translate/examples/worked-example-cn2en.md) |
| [学术语言自然化](../dyz-med-deai/SKILL.md)<br>Academic style editing | 改善重复空泛表达并保留事实和作者语气 | 原稿与表达偏好 | 自然化稿件与修改说明 | [示例 / Example](../dyz-med-deai/examples/worked-example-before-after.md) |
| [医学研究报告规范](../dyz-med-guideline/SKILL.md)<br>Reporting guidelines | 核对 STROBE、CONSORT、PRISMA 等适用条目 | 稿件、研究类型与适用规范 | 条目覆盖表与定位建议 | [示例 / Example](../dyz-med-guideline/examples/worked-example-consort.md) |
| [投稿前模拟审稿](../dyz-med-review/SKILL.md)<br>Pre-submission review | 从证据、方法等视角评估稿件 | 接近完成的稿件与附件 | 模拟审稿报告与修改建议 | [示例 / Example](../dyz-med-review/examples/worked-example-review-council.md) |
| [改稿与审稿意见回复](../dyz-med-revision/SKILL.md)<br>Revision and reviewer responses | 逐条落实修改并记录正文位置 | 稿件、审稿意见与已完成改动 | 修订稿、逐条回复与修改定位 | [示例 / Example](../dyz-med-revision/examples/worked-example-reviewer-response.md) |
| [医学论文选刊](../dyz-med-journal-finder/SKILL.md)<br>Journal selection | 按主题、读者、预算与当前要求筛选期刊 | 稿件主题、文章类型、预算与时间 | 分层候选期刊与核实依据 | [示例 / Example](../dyz-med-journal-finder/examples/示例-2型糖尿病队列研究期刊推荐.md) |
| [Word 审阅稿导出](../dyz-med-export/SKILL.md)<br>Word review draft export | 整理章节、引用和图表生成基础 DOCX | 完成的章节、图表与文献 | 基础 DOCX 审阅稿与导出报告 | [示例 / Example](../dyz-med-export/examples/虚构稿件导出流程示例.md) |
| [投稿材料准备](../dyz-med-submit/SKILL.md)<br>Submission package | 准备投稿信、题名页与声明等本地文件 | 稿件、作者确认信息与期刊要求 | 投稿包与待确认清单 | [示例 / Example](../dyz-med-submit/examples/虚构课题投稿材料生成示例.md) |

`passport` 主要由其他技能内部使用；查进度用 `orchestrator`。正式统计、在线数据库检索及复杂排版需要相应软件、权限与材料。

<!-- Generated from docs/catalog.json by scripts/build_docs.py; edit the catalog, then use --sync-indexes. -->
