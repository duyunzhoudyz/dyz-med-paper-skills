# 关键文献追踪表（骨架模板）

> 用途：以人类可读的表格形式追踪关键文献的精读进度和证据等级，作为 `paper/evidence/key-literature-map.yaml`
> 的辅助视图。复制本文件到项目里维护，逐行填写，不要预先编造文献标题或PMID。

| 文献（作者, 年份, 期刊简称） | PMID / DOI | 对本稿的贡献（背景/方法学借鉴/结论比较/矛盾证据） | 研究设计与个体质量评估 | DOI-PMID 是否已核实 | 全文获取状态 | 是否已写精读简报 |
|---|---|---|---|---|---|---|
| <示例：占位，填写实际文献> | <PMID:...或DOI:...> | <background / methods_borrow / discussion_compare / contradictory> | <研究设计；适用的偏倚风险或质量判断> | <yes/no> | <full_text_read/abstract_only/access_failure_recorded> | <yes/no，若yes填写 key-paper-briefs/文件名> |
| | | | | | | |
| | | | | | | |

## 填写说明

- **个体质量评估**：单篇研究记录研究设计、适用的偏倚风险工具和关键局限，不机械赋予 GRADE 等级。
  GRADE 用于某个结局的证据体确定性，应在多篇研究综合阶段单独完成。
- **对本稿的贡献**：一篇文献可能同时属于多个类别，用逗号分隔列出全部适用类别。
- **矛盾证据**：凡是与本稿拟定结论方向不一致的文献，务必在此列标注 `contradictory`，并在
  `frontier-literature-synthesis.md` 中单独讨论，不要遗漏或淡化。
- **全文获取状态**：与 `fulltext-ledger.yaml` 保持一致，`full_text_read` 需要能对应到本地实际存档的
  文件路径，不能仅凭摘要判断就标注为已精读全文。
