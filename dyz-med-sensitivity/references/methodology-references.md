# dyz-med-sensitivity 相关规范与文献清单

以下均为真实存在的方法学文献、报告规范或指南，供设计与报告敏感性分析时参考。

## 未测量混杂敏感性分析

- VanderWeele TJ, Ding P. "Sensitivity Analysis in Observational Research: Introducing the E-Value."
  Annals of Internal Medicine, 2017. ——E-value方法的原始文献，本技能E-value计算公式的直接依据。
- 原始论文与配套实现应优先于手工近似。使用计算器或软件时记录版本、效应尺度、转换和假设；不能把 OR/HR
  无说明地当作 RR。

## Meta分析敏感性与异质性

- **Cochrane Handbook for Systematic Reviews of Interventions，Chapter 13**——漏斗图不对称是小研究
  效应信号之一，不等于发表偏倚；不对称检验通常至少需要 10 项研究，并应按效应量选择方法：
  https://training.cochrane.org/handbook/current/chapter-13

## 观察性研究报告规范中的敏感性分析条目

- **STROBE**——虽未设专门的"敏感性分析"条目，但第12项（统计方法）鼓励报告任何敏感性分析；
  第9项（偏倚）要求描述解决偏倚的方法，敏感性分析常是回应偏倚关切的具体手段。
- **MOOSE**（观察性研究meta分析报告规范）——涉及meta分析情境下异质性来源探索与敏感性分析报告。

## 证据确定性分级

- **GRADE** 评估的是一组证据对结局的确定性；单个研究的敏感性结果不能自动映射成 GRADE 降级结论。

## 缺失数据处理假设

- Little RJA, Rubin DB. *Statistical Analysis with Missing Data*. ——MCAR/MAR/MNAR分类框架的经典
  参考，是本技能"缺失数据假设检验"部分的理论基础。
