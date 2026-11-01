# 结构化摘要写作骨架（通用，中英双语）

这是一份可以直接照着填的结构化摘要骨架，覆盖大多数期刊都会用到的四大板块。具体投稿期刊的分节名称、
顺序、字数上限可能不同——落笔前请对照 `templates/journals/<journal>.json` 里的配置，或直接使用
`SKILL.md` Phase 1 的期刊格式对照表确认目标期刊的确切结构，这份骨架不替代该步骤。

## 使用方法

1. 先确定目标期刊（决定下面用哪一套分节名称、字数上限）。
2. 按下面每个板块的写作提示，从正文对应部分提取或改写关键句（不要凭空新写没有正文支撑的内容）。
3. 填完后核对字数/字符数（见下方"各期刊字数对照表"），超限时参考 `SKILL.md` Phase 3 的裁剪优先级。
4. 关键词部分请在 `data/term-store.yaml`（中文）或标准 MeSH（英文）中核对用词。

---

## 板块一：Background / 背景

**写作提示**：1-2句话说明为什么做这项研究——已知什么、还缺什么（知识缺口）、本研究要回答什么问题。
不要重复大段文献综述，只保留读者理解研究动机所必需的最少背景。

```
[English]
[Disease/condition] is associated with [known burden/consequence]. However, [specific knowledge gap
remains unclear / evidence is limited]. We aimed to [state the specific objective].

[中文]
[疾病/状况]与[已知负担/后果]相关。然而，[具体知识缺口尚不明确/证据有限]。本研究旨在
[陈述具体研究目的]。
```

## 板块二：Methods / 方法

**写作提示**：研究设计 + 研究场所与时间范围 + 研究对象（纳入/排除要点）+ 干预或暴露 + 主要结局定义
+ 关键统计方法。这是最容易超字数的板块，只保留能让读者判断研究可信度的最核心要素。

```
[English]
We conducted a [study design] of [population] at [setting] between [start date] and [end date].
Participants were [key inclusion/exclusion]. The primary outcome was [outcome definition]. We used
[key statistical method] to [analytic purpose].

[中文]
本研究为[研究设计]，纳入[年份区间]于[研究场所]的[研究对象]，关键纳入/排除标准为
[纳入排除要点]。主要结局指标为[结局定义]。采用[关键统计方法]进行[分析目的]。
```

## 板块三：Results / Findings / 结果

**写作提示**：样本量 + 主要结局的具体数值（效应量 + 置信区间或P值）+ 最多1-2个关键次要结局。
这是摘要中"不能被裁掉"的核心板块——`SKILL.md` Phase 3 明确要求：即使为了满足字数必须裁剪，也不能
静默删掉主要结局的数值结果。

```
[English]
A total of [N] participants were included. [Primary outcome result with effect size (e.g., mean
difference, OR, HR) and 95% CI or P value]. [Key secondary result, if space allows].

[中文]
共纳入[N]例研究对象。[主要结局结果，含效应量（如均数差、OR、HR）及95%置信区间或P值]。
[关键次要结局，视篇幅决定是否保留]。
```

## 板块四：Conclusions / Interpretation / 结论

**写作提示**：1-2句话直接回答研究问题，声称强度必须匹配实际证据强度（观察性研究避免因果语言）。
如果有 `manuscript_argument_map.yaml` 的 `claim_boundaries`，结论措辞需要落在
`allowed_claims`/`cautious_claims` 范围内，不要超出正文支持的结论边界。

```
[English]
[Intervention/exposure] was [associated with / shown to reduce/increase] [outcome] in [population].
[One sentence on clinical implication or need for further research, using appropriately cautious language
for the study design].

[中文]
在[人群]中，[干预/暴露]与[结局][升高/降低]有关（观察性研究请避免"导致""证实"等因果强语言）。
[一句话说明临床意义或对未来研究的提示，措辞强度与研究设计匹配]。
```

---

## 各期刊字数/结构对照表（摘自 SKILL.md Phase 1，此处仅作骨架填写时的速查）

| 期刊 | 分节结构 | 字数上限 |
|------|---------|---------|
| ICMJE default | Background, Methods, Results, Conclusions | 300词 |
| Lancet | Background, Methods, Findings, Interpretation, Funding | 300词 |
| NEJM | Background, Methods, Results, Conclusions | 250词 |
| JAMA | Importance, Objective, Design/Setting/Participants, Main Outcomes/Measures, Results, Conclusions/Relevance | 350词 |
| 中华系列 | 目的, 方法, 结果, 结论 | 中文300字符，英文300词 |

具体每个期刊的分节配置和裁剪优先级，参见 `templates/journals/<journal>.json`。中文期刊的字数计数
规则（按汉字计数、是否排除标点）和裁剪优先级，参见 `templates/journals/zhonghua-default.json` 里的
`abstract.counting_rules` 和 `abstract.trimming_priority_zh`。
