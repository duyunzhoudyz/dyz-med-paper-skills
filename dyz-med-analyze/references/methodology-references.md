# dyz-med-analyze 相关规范与文献清单

以下均为真实存在的报告规范、指南或方法学文献，供撰写统计方法/结果部分、设计分析计划时参考。

## 统计方法与结果报告

- **SAMPL guidelines**（Statistical Analyses and Methods in the Published Literature）——医学期刊统计
  方法与结果报告的核心指南，规定效应量、置信区间、P值精确报告等要求。dyz-med-analyze 生成的
  methods-statistical-analysis.md / results-statistical-analysis.md 应遵循其报告习惯。
## 报告规范中的统计相关条目

- **CONSORT 2025**——现行随机试验报告规范，已取代 CONSORT 2010；统计方法、分析人群、结局估计和
  不确定性报告应按当前清单核对：
  https://www.bmj.com/content/389/bmj-2024-081123
- **STROBE**——观察性研究报告规范，第12项（统计方法，含混杂控制、缺失数据处理、亚组/交互分析说明）
  与本技能的"混杂因素处理"、"计划外分析声明区"直接呼应。
- **TRIPOD+AI**——预测模型开发与验证研究的现行报告框架；适用时从 EQUATOR 页面进入当前材料：
  https://www.equator-network.org/reporting-guidelines/tripod-statement/

## 因果推断与敏感性相关（与 dyz-med-sensitivity 衔接）

- VanderWeele TJ, Ding P. "Sensitivity Analysis in Observational Research: Introducing the E-Value."
  Annals of Internal Medicine, 2017. ——E-value方法的原始文献，dyz-med-sensitivity 中E-value计算的方法学
  依据；dyz-med-analyze 在观察性研究的分析计划中若涉及未测量混杂讨论，应与此一致。

## 临床研究行为规范

- **ICH E9 / E9(R1)**——临床试验统计原则及 estimand 与敏感性分析框架。用其指导分析目标、分析人群、
  缺失数据和敏感性分析的预先规定；不要把报告规范当成统计方法选择器。
- **赫尔辛基宣言**——人体研究伦理原则，涉及原始患者数据处理时的伦理背景。

## 期刊与出版伦理

- **ICMJE 建议**（Recommendations for the Conduct, Reporting, Editing, and Publication of Scholarly
  Work in Medical Journals）——涉及统计方法描述在稿件中的呈现要求。
