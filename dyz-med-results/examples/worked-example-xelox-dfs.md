# Worked Example：从结构化统计结果到结果部分正文

> **本示例为教学演示，涉及的研究课题、患者数据、具体数值均为虚构，不对应任何真实已发表研究、真实临床
> 试验或真实患者数据。** "XELOX""3年无病生存期（DFS）"等只是为了让示例具体可读而设定的虚构场景，
> 不构成任何医学建议或真实文献引用。

## 场景设定

虚构课题：一项虚构的回顾性队列研究，比较"XELOX方案"与"5-FU/LV方案"辅助化疗对II-III期结肠癌患者
3年无病生存期（DFS）的影响。`/dyz-med-analyze` 与 `/dyz-med-interpret` 已经跑完，`/dyz-med-results` 现在要把
结构化结果写成正文。

## 第一步：读取上游数据文件

### 1a. `paper/data/stats/structured_results.yaml`（片段，虚构数值）

```yaml
primary_outcome:
  variable: 3年无病生存期(DFS)
  analysis: coxph
  effect_size: HR
  point_estimate: 0.72
  ci_lower: 0.58
  ci_upper: 0.89
  p_value: 0.002
  n_events: 186
  n_total: 640
  adjustment_set: [年龄, 性别, BMI, 吸烟状态, Charlson合并症指数]

secondary_outcomes:
  - variable: 3年总生存期(OS)
    analysis: coxph
    effect_size: HR
    point_estimate: 0.81
    ci_lower: 0.64
    ci_upper: 1.03
    p_value: 0.087
    adjustment_set: [年龄, 性别, BMI, 吸烟状态, Charlson合并症指数]

subgroup:
  variable: 分期(II期 vs III期)
  interaction_p: 0.041

table1:
  per_group_N: {XELOX: 320, "5-FU/LV": 320}
  flagged_variables:
    - name: Charlson合并症指数
      p_value: 0.06

missing_data:
  pattern: 完全随机缺失(MCAR)，多重插补处理
  proportion: 0.03
```

### 1b. `paper/data/stats/mcid-classifications.yaml`（片段，虚构数值）

```yaml
3年无病生存期(DFS):
  statistical: significant
  clinical: uncertain
  mcid_threshold_HR: 0.80
  threshold_source: "虚构教学输入：假设方案为该结局、人群和3年时间窗预设HR 0.80的获益阈值，较低为获益方向；非真实临床依据"
  language_prescription: "The point estimate is beyond HR 0.80 in the benefit direction, but the CI crosses this threshold; clinical importance is uncertain. Report an association."

3年总生存期(OS):
  statistical: not_significant
  clinical: ci_includes_meaningful
  mcid_threshold_HR: 0.80
  threshold_source: "虚构教学输入：假设方案为该结局、人群和3年时间窗预设HR 0.80的获益阈值，较低为获益方向；非真实临床依据"
  language_prescription: "Report as INCONCLUSIVE. The CI includes the null and clinically important benefit; do not infer low power from the P value alone."
```

## 第二步：数值一致性核对（写作前的核对动作）

在动笔之前，先做一遍核对，而不是凭印象转述：

| 检查项 | structured_results.yaml | 计划写入正文的数字 | 核对结果 |
|---|---|---|---|
| 主要结局HR | 0.72 | 0.72 | 一致 |
| 主要结局95% CI | 0.58–0.89 | 0.58–0.89 | 一致 |
| 主要结局P值 | 0.002 | 0.002 | 一致 |
| 主要结局调整集 | 年龄/性别/BMI/吸烟/Charlson指数 | 同左，5项全部写入 | 一致，未遗漏 |
| 预设调整集 | 年龄/性别/BMI/吸烟/Charlson指数 | 按方法部分如实报告 | 一致；不是依据基线P值筛选 |
| DFS临床判断 | HR 0.72，CI 0.58–0.89，阈值0.80 | 点估计越阈值，但CI跨阈值 | uncertain；不沿用meaningful标签 |
| 研究设计与措辞 | 回顾性队列 | 关联及不确定性 | 不从调整后显著推断因果 |
| 亚组交互P值 | 0.041 | 仅转录已提供的交互检验 | 分层效应与CI未提供，待补充，不推断具体亚组获益 |

如果这一步发现正文草稿里的数字和 `structured_results.yaml` 对不上（比如草稿写成"HR 0.75"），建议
在这里就停下来核对，而不是先写完再改——数值不一致是审稿人最容易抓到的硬伤之一。

## 第三步：按推荐顺序生成初稿

### 初稿（第一版，包含需要被标记的解读性措辞）

> 共640例II-III期结肠癌患者纳入分析，XELOX组320例，5-FU/LV组320例。基线特征见表1。Charlson
> 合并症指数为统计分析计划预设的调整变量；其纳入不由基线组间P值决定。
>
> 主要结局方面，经年龄、性别、BMI、吸烟状态及Charlson合并症指数调整后，XELOX组相较于5-FU/LV组的
> 3年DFS风险比为0.72（95% CI 0.58–0.89，P=0.002），**提示XELOX方案可能通过更强的细胞毒性作用
> 延缓微转移灶进展**，这一发现**与既往部分回顾性研究结果一致**。次要结局方面，3年OS的HR为0.81
> （95% CI 0.64–1.03，P=0.087），置信区间包含无效值及预设阈值定义的临床重要获益。
> 分期亚组分析显示交互检验P值为0.041。

### Phase 6 检查：检测到解读性措辞

自查清单 D 项过一遍后，发现两处应当标记的表述：

1. **"提示XELOX方案可能通过更强的细胞毒性作用延缓微转移灶进展"**——这是对机制的推测性解读，不是
   对观察数据的陈述，按惯例属于讨论部分的内容。
2. **"这一发现与既往部分回顾性研究结果一致"**——这是把当前结果和文献比较，是典型的"consistent with
   previous studies"模式，同样按惯例属于讨论部分。

按建议性处理方式（标记 + 建议移动，而不是直接删除）：

> **[建议]** 检测到以下解读性表述，按写作惯例更适合放进讨论部分（Discussion），是否要移动，还是您
> 有意在这里保留，请您决定：
> - "提示XELOX方案可能通过更强的细胞毒性作用延缓微转移灶进展"
> - "这一发现与既往部分回顾性研究结果一致"
>
> 如果您同意，我可以把这两句原样搬到 `/dyz-med-discussion` 起草时使用的素材里，不会直接丢弃内容。

### 修订后的结果段落（解读性措辞移出后）

> 共640例II-III期结肠癌患者纳入分析，XELOX组320例，5-FU/LV组320例。基线特征见表1。Charlson
> 合并症指数为预设调整变量。
>
> 主要结局方面，经年龄、性别、BMI、吸烟状态及Charlson合并症指数调整后，相较于5-FU/LV方案，XELOX方案与
> 3年内DFS事件发生的较低瞬时风险相关（HR 0.72，95% CI 0.58–0.89，P=0.002）。点估计位于预设
> 临床重要获益阈值（HR 0.80）的获益侧，但置信区间跨过该阈值，临床重要性仍不确定。次要结局方面，
> 3年OS的HR为0.81（95% CI 0.64–1.03，P=0.087），置信区间包含无效值1及预设阈值定义的临床重要
> 获益，不能据此判定无效，也不能仅凭该P值推断检验效能不足。
>
> 按分期进行的亚组分析显示，分期与治疗方案之间的交互检验P值为0.041。

稿外待办：输入片段未提供分层效应、CI及亚组预设状态，需向统计输出和方案核对；不从单一交互P值
补写分层结论。输入未提供肿瘤分化程度分析结果，因此不加入该项事后分析。

## 第四步：图表标题示例（本节涉及的虚构Table 1 / Figure 1）

- 表题（表上方）："Table 1. Baseline characteristics of patients receiving XELOX versus 5-FU/LV
  adjuvant chemotherapy（虚构数据）。"
- 图题（图下方）："Figure 1. Kaplan-Meier curves for 3-year disease-free survival by treatment
  group（虚构数据）。"

## 小结：本例演示了什么

1. **数值一致性核对**：先列表核对正文数字与 `structured_results.yaml` 逐项是否一致，再动笔，而不是
   写完再核对。
2. **结果呈现顺序**：按"基线特征 → 主要结局 → 次要结局 → 亚组分析"排列；未提供的分层估计与CI
   列为待补，不补造事后探索性结果。
3. **解读性措辞检测与建议移动**：检测到"提示……""与既往研究一致"这类表述后，标记出来、建议移动到
   讨论部分，并且明确不是直接删除，而是先问作者。
4. **调整集透明度**：每条效应量都写清楚调整了哪些变量。
5. **结论反查**：DFS点估计位于获益阈值之外但CI跨阈值，判为临床重要性不确定；OS非显著不等于
   无效，也不单凭P值判断效能；观察性结果保持关联措辞。
