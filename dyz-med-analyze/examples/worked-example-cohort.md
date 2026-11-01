# 完整示例：从原始数据到结构化结果（虚构教学示例）

本示例为教学演示，涉及的研究课题、数据、数值均为虚构，不对应任何真实已发表研究，仅用于演示
dyz-med-analyze 的工作方式（计划先行、批准后执行、结果结构化）。

## 背景（虚构）

虚构课题："某虚构降压药X对老年高血压患者1年内心血管事件的影响（回顾性队列）"。

用户提供了一份虚构数据文件 `demo_cohort.csv`（500行×8列，全部为虚构生成的数值，不含任何真实
患者信息），列名如下：patient_id, age, sex, treatment_group, sbp_baseline, sbp_6month,
followup_days, cv_event_1year。

## 第1步：确认权限并做只读数据画像

- 用户确认数据可在本地处理；原文件保持只读，不向外部服务上传
- 探测到本地已安装 R 4.3.x 及计划所需 R 包
- 读取 demo_cohort.csv：500行，8列，无重复ID，缺失率 <2%
- 变量角色候选（仅用于与数据字典、方案逐项确认；模型置信度不构成确认）：

| 变量 | 类型 | 待确认角色候选 | 模型置信度 |
|------|------|------|--------|
| patient_id | 数值 | ID（排除分析） | 高 |
| age | 数值 | 协变量 | 高 |
| sex | 因子 | 协变量 | 高 |
| treatment_group | 因子(1/2) | 暴露/干预 | 高 |
| sbp_baseline | 数值 | 基线协变量 | 高 |
| sbp_6month | 数值 | 次要结局候选 | 中 |
| followup_days | 数值 | 时间-事件变量 | 高 |
| cv_event_1year | 二分类 | 主要结局 | 高 |

所有角色均先对照方案和数据字典核实，包括标为高置信度的主要结局与暴露；缺来源时保持待确认。
本例后续步骤假定主要结局、暴露编码、分析人群和时间起点已由方案确认，不能仅凭列名进入建模。

## 第2步：生成分析计划书（AI起草，等待用户确认）

基于研究设计（回顾性队列）与数据结构（独立样本、时间-事件主要结局），AI 自动生成如下计划要点，
并用 `templates/statistical-analysis-plan.md` 骨架呈现给用户：

- 主要结局分析：Cox比例风险回归，`Surv(followup_days, cv_event_1year) ~ treatment_group + age + sex + sbp_baseline`
- 效应量：HR + 95% CI
- 模型诊断：针对Cox模型评估比例风险，计划结合全局/相关协变量的cox.zph()输出与残差时间趋势图，
  在计划第4节或diagnostics.md记录实际观察、定位、适用条件与局限；资料不足或发现问题时报告并回到
  获批计划，不自动换模型
- 混杂因素：age、sex、sbp_baseline（虚构示例假定依据来自预设方案、临床知识和因果结构）
- 显著性水平：双侧 α=0.05
- 缺失数据：根据缺失发生在哪些变量、缺失机制和 estimand 预先规定；不因“缺失率<2%”自动选择完整病例
- 计划外分析声明区：暂无

**关键节点：AI 在此处暂停，明确告知用户"计划已生成，需要您确认后才会执行统计脚本"。**
本虚构示例中，假设用户明确回复"同意按当前展示的分析计划版本，在本地对指定数据执行上述分析，
不包含额外模型、数据外传或安装依赖"。实际执行前，须将这份人类批准绑定到当前统计分析计划的
稳定 `artifact_id`、`version` 和实际内容 `sha256`，记录确认人的角色/化名、带时区确认时间、
原始确认陈述，以及保存确认记录的路径、真实字节哈希和消息/段落定位；核实授权对象、动作与范围。
单独的 `analysis.plan_approved: true` 或“已确认”标签不能替代这些来源，也不是足够的执行许可。
本例不提供真实同意、身份或可验证哈希；以上只是教学说明，不代表已取得批准。计划内容变化后须重新
取得针对新版本的明确批准，不能沿用旧确认。在当前计划的批准来源与授权范围未核实前，AI 不会生成
或运行任何针对该数据文件的 R 脚本；不会因为数据“看起来很简单”而省略此步骤。

## 第3步：R脚本生成与执行（仅在批准后进行）

用户确认后，AI 生成 `paper/analysis/analysis_20260706_103000.R`（虚构文件名），内容包括数据读取、
Cox模型拟合、假设检验和 Table 1 生成等。只有脚本真实执行成功并完成核对后，才写出可供稿件使用的结果：

- `paper/data/stats/analysis_output.txt`
- `paper/data/stats/structured_results.yaml`
- `paper/data/tables/table1.csv` / `table1.docx`

## 第4步：结构化结果示例（虚构数值）

以下是交接字段演示，假定模型执行完成但诊断证据尚缺；不是本仓库实跑结果。正式运行时，另在工件清单
登记 `analysis-results` 与 `analysis-output` 的实际 path、version、sha256；此处不编造可验证的哈希。
`source.locator` 也须改为真实输出定位。本片段缺少实际文件及绑定，不能直接作为已核实证据。

```yaml
schema_version: "1.0"
results:
  - analysis_id: cv-event-1year-cox-primary
    population: "方案规定的主要分析集；本教学例假定500人"
    outcome: cv_event_1year
    timepoint: "自方案确认的起点至365天"
    groups:
      comparison: "treatment_group=1（降压药X）"
      reference: "treatment_group=2（对照）"
    effect_scale: HR
    unit: ratio
    estimate: "0.71"
    ci:
      lower: "0.54"
      upper: "0.93"
      level: "0.95"
      adjustment: unadjusted
      method: "模型系数Wald区间（教学假设）"
    denominator:
      value: 500
      kind: count
      unit: participants
    events: 86
    p:
      value: "0.013"
      adjustment: unadjusted
      method: "双侧Wald检验（教学假设）"
    model: Cox proportional hazards regression
    adjustment_set: [age, sex, sbp_baseline]
    source:
      artifact_id: analysis-output
      locator: "教学定位：主要Cox模型treatment_group=1系数行，需替换为实际位置"
    execution_status: completed
assumption_checks:
  proportional_hazards:
    test: "cox.zph"
    p_value: 0.42
    assessment_scope: "未提供全局/协变量范围，待核实"
    observed_result: "仅提供检验P值；不足以证明比例风险假设成立"
    output_locator: null
    plot_locator: null
    assumptions_and_limits: "尚缺适用条件、实际检验输出及残差时间趋势评估记录"
    status: unverified
    response: "补充现有诊断证据；如需补跑或改模型，回到计划取得批准"
    response_approval: "尚未取得补充分析批准"
table1:
  n_group1: 250
  n_group2: 250
```

以上数值均为虚构，`completed`只演示模型执行状态，不证明诊断通过或医学正确性；`ci.adjustment`与
`p.adjustment`在此指多重性处理，协变量调整由`adjustment_set`另列。分组人数应由实际输出另行核对，
不能将教学假定的500人或250/250分组写入真实项目。

## 第5步：流转下游

本片段仅有比例风险检验P=0.42，诊断证据仍为 `unverified`，不能按诊断已通过交接，也不能据此判定
模型无效。先补齐已有输出、图形观察及适用性记录；证据相互冲突时保留冲突并提交统计人员确认，需要
新分析或变更模型时重新审批。完成适用诊断与分母核对后，结果才可供 `/dyz-med-interpret`、`/dyz-med-methods`、
`/dyz-med-results` 和 `/dyz-med-figures-tables` 正式使用；此前仅交付带缺项说明的审阅材料，不宣称已核实。

---
本示例演示的核心是："计划先行 + 明确批准 + 结果结构化"这条主线，实际使用中变量数量、研究设计、
统计方法会因真实课题而完全不同。
