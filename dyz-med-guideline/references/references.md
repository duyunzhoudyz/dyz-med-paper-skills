# 医学报告规范版本与官方入口

核对日期：2026-07-31

使用前应通过 EQUATOR、规范官网或目标期刊作者指南再次确认版本和适用扩展。

## 主要规范

- **CONSORT 2025**：随机试验结果报告，已取代 CONSORT 2010。  
  https://www.bmj.com/content/389/bmj-2024-081123

- **SPIRIT 2025**：随机试验方案，更新 SPIRIT 2013。  
  https://www.bmj.com/content/389/bmj-2024-081477

- **STROBE**：队列、病例对照和横断面研究；按数据来源和领域检查 RECORD 等扩展。
- **PRISMA 2020**：系统综述和 meta 分析；范围综述使用 PRISMA-ScR，方案使用 PRISMA-P。
- **STARD**：诊断准确性研究；AI 场景检查适用扩展。
- **CARE**：病例报告。
- **TRIPOD+AI**：回归或机器学习预测模型；LLM 研究按适用范围检查 TRIPOD-LLM。  
  https://www.equator-network.org/reporting-guidelines/tripod-statement/
- **ARRIVE 2.0**：动物研究。
- **CHEERS 2022**：卫生经济评价。
- **SQUIRE 2.0**：质量改进研究。
- **COREQ / SRQR**：按定性研究方法选择。
- **MOOSE**：观察性研究的 meta 分析，可与当前 PRISMA 要求配合。

EQUATOR 指南库：https://www.equator-network.org/reporting-guidelines/

## 证据与偏倚工具

- GRADE 评价某结局的证据体确定性，不是单篇论文质量标签。
- RoB 2 用于随机试验偏倚风险评估。
- ROBINS-I 用于非随机干预研究偏倚风险评估。
- 具体工具和版本必须与研究设计匹配，不能因报告条目 `COVERED` 就假定偏倚评估已经完成。

## 本地文件边界

- `templates/checklists/consort-2010-legacy.md` 是历史快照，只供旧稿对照。
- `templates/data/cross-reference-map.yaml` 是结构示例，其中风险项 ID 不是已存在项目事实。
- 正式核查必须使用当前官方完整清单；本地摘要或模板不能替代原始规范。
