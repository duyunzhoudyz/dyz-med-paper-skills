> 本示例为教学演示，涉及的研究课题、机构、数据、数值均为虚构，不对应任何真实已发表研究，仅用于
> 演示 `dyz-med-write` 在"终稿连贯性检查"场景下的具体工作方式。

# Worked Example：终稿连贯性检查（dyz-med-write 的主要使用场景）

## 场景设定

虚构课题："腹腔镜远端胰腺切除术（LDP）与开腹远端胰腺切除术（ODP）术后30天并发症比较"（回顾性队列，
虚构数据）。用户已经用 `/dyz-med-introduction`、`/dyz-med-methods`、`/dyz-med-results`、`/dyz-med-discussion`、
`/dyz-med-abstract` 分别写完了五节草稿，现在说："各节都写完了，帮我一次性检查一下前后是不是一致"——这
是触发 `dyz-med-write` 终稿检查模式的典型说法。

`dyz-med-write` 在这个场景下的做法：把五节已有草稿当作**主要来源**，对照
`paper/data/stats/structured_results.yaml` 等上游数据文件，逐条走一遍
`templates/final-coherence-checklist.md`，只标记并建议修改不一致之处，不重写任何一节。

## 输入：五节草稿摘录（节选，含人为植入的不一致，全部为虚构数值）

**01-introduction.md（节选）**
> ...既往研究提示腹腔镜远端胰腺切除术（Laparoscopic Distal Pancreatectomy, LDP）相较开腹术式
> 可能降低术后并发症风险，但证据仍存在争议...

**02-methods.md（节选）**
> ...本研究纳入接受远端胰腺切除术患者共 214 例，其中 LDP 组 118 例，开腹组（ODP）96 例...

**03-results.md（节选）**
> ...LDP 组术后30天总体并发症率为 21.4%（25/118），显著低于开腹组的 34.4%（33/96）
> （OR 0.52, 95%CI 0.28–0.96, P=0.037）...主要结局的多因素分析显示，术式（LDP vs 开腹）经调整
> 肿瘤直径、BMI、手术时长后 OR 为 0.49（95%CI 0.26–0.93, P=0.029）...

**04-discussion.md（节选）**
> ...本研究中腹腔镜组并发症率为 21.4%，与既往报道的微创胰腺手术并发症率范围（15%–28%）大致相符...
> 值得注意的是，LR 组本身存在适应证选择偏倚（肿瘤较小者更倾向接受腹腔镜手术），本节将在下文详述...

**05-abstract.md（节选）**
> ...Results: LDP was associated with a lower 30-day complication rate compared with open surgery
> (19.8% vs 34.4%, adjusted OR 0.49, 95%CI 0.26–0.93, P=0.029)...
> ...Conclusion: Laparoscopic distal pancreatectomy may reduce short-term postoperative
> complications compared with open surgery...

## dyz-med-write 的检查过程（对照 `final-coherence-checklist.md`）

**一、术语一致性**
- 发现：Discussion 中出现"LR 组"，但 Methods/Results/Abstract 全部用"LDP 组"指代腹腔镜组，两者
  未做说明，读者无法确认是否为同一组。
  → 标记：术语不一致（LR vs LDP），建议 Discussion 统一改为"LDP 组"，或在首次使用"LR"时补充说明
  "LR（laparoscopic resection，即本文 LDP 组）"。

**二、数值一致性（与 `structured_results.yaml` 核对，此处为虚构示例数值）**
- Results 正文：LDP 组并发症率 21.4%（25/118）。
- Abstract：写成 19.8%。
- 示例假设 `structured_results.yaml` 也写成了 21.4%（25/118）；结构化文件与正文一致仍不能证明数值正确。
- 独立复算：25 ÷ 118 × 100 = 21.1864…%，保留一位小数应为 21.2%，因此 21.4% 与分子分母本身冲突；
  Abstract 的 19.8% 也不能由这组分子分母得到。
  → 标记：Results、Discussion、Abstract 与结构化来源存在需核实的数值冲突。先核实原始分析输出中的
  事件数、分母、分析人群及加权口径；若确认是未加权的 25/118，则三个章节应统一为 21.2%。若为调整或
  加权比例，应单列其估计方法，不能写成简单的 25/118。核实前不直接修改任何科学数值，不猜错误原因。
- 未调整 OR（0.52, 95%CI 0.28–0.96）与调整后 OR（0.49, 95%CI 0.26–0.93）在 Results 中都有报告，
  Discussion 与 Abstract 引用的均为调整后 OR 0.49——这一处数值一致，无需修改，仅在检查报告中注明
  "已核对一致"。

**三、缩写与定义**
- "LDP"在 Introduction 首次出现时给出了全称定义（Laparoscopic Distal Pancreatectomy），符合要求。
- "ODP"（开腹远端胰腺切除术）在 Methods 中首次出现但未给出英文全称/缩写定义，仅在 Methods 括号
  里写了"（ODP）"却没写全称。
  → 标记：缩写未完整定义，建议在 Methods 首次出现处补充"Open Distal Pancreatectomy, ODP"。

**四、图表编号核对**
- `display-items-manifest.yaml` 中列出图1（患者筛选流程）、图2（主要结局组间比较）、图3（并发症
  类型构成）、表1（基线特征）、表2（主要结局）、表3（多因素分析）。
- 核对五节正文：图1、图2、表1、表2、表3均被提及；图3（并发症类型构成）未在任何一节正文中被提及。
  → 标记：图3存在于 manifest 但未被正文引用，建议在 Results 的"并发症类型构成"段落中补充一句
  "并发症类型构成见图3"，或确认图3是否确实需要保留在本次投稿中。

**五、FORBIDDEN 内容自查**
- 五节正文通读未发现流程注释、QA清单式罗列或诚信声明混入正文，此项无需修改。

## 输出：检查报告（提交给用户，供其决定是否采纳）

| 类别 | 位置 | 问题 | 建议 |
|---|---|---|---|
| 术语不一致 | Discussion 第2段 | "LR 组"未与"LDP 组"统一 | 改为"LDP 组"，或首次使用时注明对应关系 |
| 数值冲突 | Results、Discussion、Abstract及结构化来源 | 21.4%与25/118不符，摘要19.8%也不同 | 核实原始事件数、分母与估计口径；若确为未加权25/118，应为21.2%，核实前不自动改数 |
| 缩写未定义 | Methods 首次出现处 | "ODP"未给出英文全称 | 补充"Open Distal Pancreatectomy, ODP" |
| 图表未提及 | Results | 图3（并发症类型构成）未被正文引用 | 在对应段落补充一句提及图3的编号 |

本例请求是检查，因此交付四项问题与建议。用户明确授权修订后，可按已核实事实修改；数值源冲突仍需先
核实，不把一个文件被称作“权威来源”当作免于算术核对的理由。输入中错误的21.4%与19.8%是故意保留的
反例，不能复制到最终稿。

## 简要提及：快速一次性初稿场景

如果用户在还没有任何分节草稿的情况下明确说"帮我一次性把全文合成一稿"，`dyz-med-write` 会改为直接从
`manuscript_argument_map.yaml`、`section_plans/*`、`structured_results.yaml` 等上游材料出发，
一次性写出 `paper/sections/manuscript.md`，写作过程中套用与 `/dyz-med-methods`、`/dyz-med-results`、
`/dyz-med-discussion`、`/dyz-med-abstract` 相同的写作纪律。这一场景的具体写作细节可参照各分节技能自身的
`examples/`；本示例的重点是更能体现 `dyz-med-write` 定位的"终稿连贯性检查"场景。
