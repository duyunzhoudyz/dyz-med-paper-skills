# 审稿意见回应表（模板）

用途：对应 SKILL.md“写逐条回复”和“验证受影响内容”，可用于 `response-letter.md` 的点对点回应
及 `traceability-matrix.md`。回应立场与问题验证关闭分别记录，不把回复完成率当作解决率。

- 本轮输入/输出：[项目根目录、稳定 artifact_id/path/version/sha256]
- 原始意见来源与编号：[保留原文、来源、位置]
- 复核记录：[唯一 check ID、完整 inputs、scope、execution_status、applicability、domain_result、report、checked_at]
- 当前有效性：[逐条验证输出 current / stale / unverified；缺绑定或范围不足不当作通过]

## 致编辑信（骨架）

```
尊敬的编辑：

感谢您和审稿人对我们稿件（稿号：[稿号]，题目：[标题]）提出的宝贵意见。下表记录各条回应、实际修改
及尚待确认的事项。[仅在确实完成时说明修改标注方式；不得预填“全部修改/验证完成”。]

再次感谢您和审稿人的时间与建议。

此致
[作者姓名/通讯作者]
```

## 点对点回应表

| 来源/原始编号 | 稳定问题 ID | 原始意见 | 类型 | 严重度 | 作者回应与实际改动/理由 | 稿件位置 | response_stance | 问题 status | verification_check_id / evidence |
|---|---|---|---|---|---|---|---|---|---|
| [来源与编号] | [ID] | [原文] | [见下] | critical / major / minor | [据实填写] | [未修改则写不适用及理由] | [未回应留空] | open | [未验证留空] |

类型与正文一致：editorial / interpretive / methodological / data_or_analysis / ethics_or_authorship / journal_adaptation。
`evidence` 记录 path/sha256；每个字段须来自实际材料，不将模板占位符登记为证据。

## 回应策略撰写提示（对应“写逐条回复”）
- 语气尊重、体现感谢，不使用防御性或轻蔑语气。
- 具体说明"改了什么"，避免"we fixed this"这类笼统表述——应指出具体章节、段落、数字变化。
- 不同意时用已核实证据或方法学理由解释保留原方案的原因；不是把审稿结论 REJECT 当回应类型。
- 已修改事项提供真实位置；未修改则给理由，不能捏造改动或定位。

## 回应立场（response_stance）
- **ACCEPT**：采纳意见；实际修改进展与验证状态另记。
- **PARTIAL**：部分采纳，说明采纳/保留部分及理由。
- **DISAGREE_WITH_REASON**：不采纳，附已核实证据或方法学理由；不自动关闭。
- **NEEDS_AUTHOR_INPUT**：需作者补充数据、源事实或伦理/注册依据，明确未完成内容，不编造回应。

## 问题处理与验证关闭（status）
- **open**：未处理；**in_progress**：处理中；**awaiting_verification**：处理后待核验。
- **verified_closed**：关联 verification_check_id 与 evidence:{path,sha256}；检查须为 current、completed、
  applicable，且审阅实际领域结论足以支持该问题关闭。校验器退出码 0 不能代替此判断。
- 输入/报告变更使依赖检查 stale，旧关闭不计入当前有效关闭数；保留历史，列出需重核项。
- 统计分别填写：已回应 [R/N]；已实施 [M/N]；当前有效验证关闭 [C/N]；待作者输入 [A/N]。
  三条均回复但仅一条验证关闭时写“回复 3/3，已验证关闭 1/3”，不能总结为问题全部解决。
