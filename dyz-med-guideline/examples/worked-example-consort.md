> 本示例为教学演示，涉及的研究课题、机构、数据、数值均为虚构，不对应任何真实已发表研究。仅用于演示
> `/dyz-med-guideline` 的输入输出格式与工作方式。

# 历史教学示例：一篇虚构 RCT 稿件的 CONSORT 2010 核对

> CONSORT 2025 已取代 CONSORT 2010。本示例仅演示逐条核对和输出格式；当前 RCT 必须改用
> CONSORT 2025 官方清单及适用扩展，不能沿用本示例的 2010 条目作为现行检查结果。

## 场景
虚构课题："口服XX制剂对II型糖尿病患者HbA1c控制效果的随机对照试验"（虚构，非真实研究）。稿件已完成
全文初稿，用户说："帮我检查一下这篇RCT稿子符不符合CONSORT规范。"

## 输入
- 稿件全文（Introduction/Methods/Results/Discussion 均已写完）
- project.md 标注 study_type: RCT，双臂平行设计

## Phase 1：加载核对表
从 `templates/checklists/consort-2010-legacy.md` 加载历史版 CONSORT 2010 条目，仅用于演示。

## Phase 2：逐条核查（节选示例，非全部25条）

| 条目号 | 条目要求（摘要） | 稿件对应位置 | 状态 | 备注 |
|--------|------------------|--------------|------|------|
| 3a | 试验设计描述 | Methods 第1段："本研究为单中心、双臂平行、开放标签RCT" | COVERED | |
| 8a | 随机序列产生方法 | Methods 第2段提到"采用随机数字表" | COVERED | |
| 9 | 分配隐藏机制 | 全文未提及分配隐藏（如信封法/中心化随机） | MISSING | 建议在Methods补充分配隐藏步骤说明 |
| 11a | 盲法设置 | Methods 第1段已声明"开放标签" | NOT APPLICABLE | 开放标签设计下此条目不适用，但仍需在局限性中讨论盲法缺失的影响 |
| 13a | 受试者流程（建议附CONSORT流程图） | Results 提到入组200例，未见流程图 | PARTIAL | 建议用 `/dyz-med-flowchart` 生成标准CONSORT流程图 |
| 17a | 结局效应量及精度 | Results 表2报告HbA1c差异，仅有P值无95%CI | PARTIAL | 建议补充效应量的95%CI，参见 dyz-med-results 的效应量报告要求 |
| 23 | 试验注册号 | 未在稿件任何位置发现注册号 | MISSING | 建议核实是否已注册（ClinicalTrials.gov等），若确未注册应如实说明，不建议编造注册号 |

## Phase 3：合规报告汇总（示例，仅覆盖以上节选条目，非全部25条的真实统计）

- COVERED：2/7（28.6%）
- PARTIAL：2/7（28.6%）
- MISSING：2/7（28.6%）
- NOT APPLICABLE：1/7（14.3%）

## Phase 2.5：交叉核对示例

| Checklist Item | Status | Linked Item | Linked Status | Conflict |
|---|---|---|---|---|
| CONSORT-2010.item_17a | PARTIAL | RESULT-002（风险清单：效应量缺失） | 待处理 | 一致，无冲突——两处都标记了同一问题 |

## Phase 4：必需条目缺失提示（呈现给用户，非自动阻断）
- 条目9（分配隐藏机制）、条目23（试验注册号）目前是MISSING，通常建议在 `/dyz-med-review` 之前补充或如实
  说明缺失原因；是否现在处理、稍后处理，还是这两项本身就有正当理由缺失（例如确实是回顾性重新分析而非
  前瞻性注册试验），由用户判断。

## Phase 5：修改建议（节选）
- 条目9：在Methods的随机化小节补充"随机分配方案由未参与招募的统计人员通过中心化随机系统实施，研究者
  和招募人员在受试者入组前无法获知分组"这类具体机制描述（此处为示例措辞，需按实际情况填写）。
- 条目17a：在Results表2的HbA1c组间差异后补充95%CI，格式参照 `/dyz-med-translate` 或 `/dyz-med-results` 的
  统计表达规范。
