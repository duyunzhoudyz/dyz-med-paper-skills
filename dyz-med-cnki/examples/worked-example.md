# dyz-med-cnki 完整示例（教学演示）

> **本示例为教学演示，涉及的研究课题、检索结果、文献标题均为虚构，不对应任何真实已发表研究，仅用于
> 演示 dyz-med-cnki 的工作方式。**

## 场景

用户："我在写一篇关于二甲双胍对老年2型糖尿病患者认知功能影响的综述引言，帮我查一下相关文献，最好
中英文都覆盖一下。"

## Phase 1：检索优先级判断

研究涉及"老年2型糖尿病患者"，未明确要求国内人群特异性证据，因此默认路径：PubMed 为主，
Google Scholar 为补充，中文文献线索发现作为追加补充（用户提到"中英文都覆盖"）。

## Phase 2：PubMed 检索（虚构示例结果）

1. MeSH 扩展（使用 NLM MeSH 官方浏览器或当前可用检索能力；以下仅为示例）：
   - "二甲双胍" → `Metformin`
   - "认知功能" → `Cognition`, `Cognitive Dysfunction`
   - "老年2型糖尿病" → `Diabetes Mellitus, Type 2` + `Aged`

2. 布尔检索式（虚构示例，非真实执行结果）：
   ```
   ("Metformin"[Mesh]) AND ("Cognitive Dysfunction"[Mesh] OR "Cognition"[Mesh])
   AND ("Diabetes Mellitus, Type 2"[Mesh]) AND ("Aged"[Mesh])
   ```

3. 执行检索（虚构）：假设返回 128 条结果，按相关性排序取前 30 条。

4. 记录检索过程 → 写入 `paper/evidence/search-record.md`（示例条目，见下方"产出示例"）。

5. Semantic Scholar 补充核验（虚构）：对其中3条关键PMID查引用数，发现1条为高被引综述
   （虚构：引用数 210，`influentialCitationCount` 45），判断为关键背景文献。

## Phase 3：Google Scholar 补充检索

用网页搜索能力检索 Google Scholar，发现1篇疑似相关的学位论文（虚构标题：《二甲双胍对老年糖尿病患者
认知功能保护作用的队列研究》），标注为 `abstract_only`，引用前提示用户"该条目来自Google Scholar，
尚未通过PubMed/CrossRef核实DOI，建议核实后再引用"。

## Phase 4：中文文献线索发现（能力有限，如实告知）

用网页搜索（关键词"二甲双胍 认知功能 老年糖尿病 知网"）尝试发现候选中文文献线索，虚构结果：

- 发现1条疑似相关条目：标题《二甲双胍与老年2型糖尿病患者轻度认知障碍相关性分析》，作者、期刊、
  年份等信息来自网页搜索片段，**未核实真实性和完整性**，标注为 `discovery_only`。
- **如实告知用户**："这条中文文献是通过网页搜索找到的线索，我无法登录知网核实其摘要全文、无法确认
  是否为核心期刊、也无法自动下载全文。如果您需要这篇文献的全文，需要您自己登录知网或通过所在机构
  图书馆获取。"

## Phase 5：整合与去重（虚构示例产出）

| 来源 | 标题（虚构） | PMID/DOI | 获取状态 |
|---|---|---|---|
| PubMed | Metformin use and cognitive outcomes in older adults with T2DM: a systematic review（虚构） | PMID: 00000001（虚构占位） | abstract_only |
| Google Scholar | 二甲双胍对老年糖尿病患者认知功能保护作用的队列研究（虚构学位论文） | 无DOI，待核实 | abstract_only |
| 中文线索发现 | 二甲双胍与老年2型糖尿病患者轻度认知障碍相关性分析（虚构） | 无，仅网页搜索片段 | discovery_only |

## 产出示例：`paper/evidence/search-record.md` 片段

```
## 检索记录 SEARCH-001
- 检索日期：2026-07-06（示例日期）
- 数据库：PubMed
- 检索方式：结构化检索
- 精确检索式：("Metformin"[Mesh]) AND ("Cognitive Dysfunction"[Mesh] OR "Cognition"[Mesh])
  AND ("Diabetes Mellitus, Type 2"[Mesh]) AND ("Aged"[Mesh])
- 过滤条件：无日期限制（示例）；语种不限；人类研究
- 结果数量：128（虚构）
- 关键PMID：PMID:00000001（虚构占位）
- 获取状态：abstract_only
- 备注：本条为教学示例，非真实检索结果
```

## 小结

本示例展示了 dyz-med-cnki 的完整链路：PubMed为主的结构化检索 → Google Scholar补充 → 中文文献线索发现
（明确标注能力边界）→ 整合去重并标注每条文献的获取状态。所有具体文献标题、PMID、结果数均为虚构占位，
实际使用时必须替换为真实检索执行的结果。
