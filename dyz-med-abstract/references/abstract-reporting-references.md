# 摘要与标题撰写相关规范与文献清单

以下均为真实存在的报告规范/方法学文献，按与"结构化摘要与标题撰写"的相关性简短标注。不是完整的
文献综述，只是这个技能在判断"摘要该写什么、该达到什么规范要求"时可以参考的清单。

- **ICMJE Recommendations for the Conduct, Reporting, Editing, and Publication of Scholarly Work in
  Medical Journals**（国际医学期刊编辑委员会，持续更新）——在"Preparing a Manuscript"部分对摘要
  提出通用建议：结构化摘要应包含背景、方法、结果、结论，且摘要中的数据必须与正文一致，不能包含
  正文中没有出现的信息。dyz-med-abstract Phase 3"摘要数值须与正文/结构化结果匹配"的要求与此对应。

- **CONSORT 2025 与其摘要报告要求**——当前随机对照试验报告规范已取代 CONSORT 2010；摘要仍应
  清楚报告试验设计、参与者、结局、分析人数、结果、结论以及适用的注册和资助信息。正式核对时使用
  当前官方清单，不依赖旧版条目号。早期的 CONSORT for Abstracts 是这一领域的重要历史扩展。

- **STROBE Statement**（观察性研究报告规范，队列/病例对照/横断面研究）——虽然 STROBE 主要条目
  针对全文，但官方说明与后续扩展讨论中明确建议摘要应提供研究设计的"均衡、翔实的总结"（informative
  and balanced summary），包括已完成的分析及主要定量结果，避免摘要中出现全文未支持的结论性语言。

- **PRISMA 2020 for Abstracts**（Page MJ, et al. PRISMA 2020 statement. *BMJ* 2021；PRISMA 2020
  官方清单包含专门的摘要条目 Item，对应 PRISMA 2009 时代已有的 PRISMA for Abstracts 扩展）——
  要求系统综述/meta分析摘要报告纳入研究数、研究人群/暴露/干预特征、综合方法、主要结果（效应量与
  可信区间）、局限性、结论和资助来源/注册信息。若研究类型为系统综述，摘要生成应参照该清单核对
  条目完整性，与 `/dyz-med-guideline` 核对的 PRISMA 版本保持一致。

- **STARD 2015**（诊断准确性研究报告规范）——摘要相关说明要求报告研究设计、参与者、诊断准确性
  的关键指标（如敏感度、特异度），适用于以诊断试验为主题的稿件摘要撰写。

- **TRIPOD+AI**（预测模型开发与验证报告规范）——摘要部分要求说明模型开发或验证的目的、
  数据来源、结局、预测因子、统计分析方法及关键区分度/校准度指标，适用于预测模型类摘要。

- **SAMPL Guidelines**（Statistical Analyses and Methods in the Published Literature；Lang TA,
  Altman DG）——对效应量、置信区间、P值等统计结果的报告方式提出具体建议，dyz-med-abstract 摘要结果
  板块中"效应量+置信区间"的呈现方式参照该指南的一般原则。

- **PubMed MeSH（Medical Subject Headings）**（美国国立医学图书馆维护）——英文关键词校验的权威
  来源；通过 NLM MeSH 官方浏览器或当前可用的检索工具核对，不假设某个固定工具一定存在。

如果稿件对应的具体研究设计还涉及 CARE 2013（病例报告）、ARRIVE 2.0（动物实验）、SPIRIT 2025
（试验方案）、MOOSE（观察性研究meta分析）等规范，摘要的结构和必报条目也应参照对应规范的摘要相关
要求，与 `dyz-med-guideline` 核对的版本保持一致，不引入不同的版本号/年份。

## 中文期刊摘要撰写参考

- **中华医学会系列期刊《稿约》**——各刊官网发布的投稿须知中通常包含结构化摘要的分节要求（目的/
  方法/结果/结论）与字数上限说明，是 `templates/journals/zhonghua-default.json` 配置的现实依据；
  具体数值以对应期刊当期《稿约》为准，本技能的默认配置仅供内部写作参考，不替代官方稿约核对。
- **CMeSH（中文医学主题词表）**——由中国医学科学院医学信息研究所等机构基于 MeSH 汉化维护，是
  `data/term-store.yaml` 骨架希望映射到的真实词表体系；本技能内置的骨架仅含少量示例词条，正式
  投稿前建议通过官方 CMeSH 检索工具核对完整关键词。
