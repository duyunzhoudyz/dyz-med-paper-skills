> 本示例为教学演示，涉及的研究课题、审稿意见、数据均为虚构，不对应任何真实已发表研究或真实审稿过程。
> 仅用于演示 `/dyz-med-revision` REVIEWER_RESPONSE 模式的工作方式。

# 示例：一次虚构审稿意见的回应流程

## 场景
虚构课题："阿XX类药物对老年高血压患者认知功能影响的前瞻性队列研究"（虚构）。用户收到"大修"（major
revision）决定，粘贴了两位审稿人的意见，说："帮我回复审稿意见。"

## Phase 0：审稿意见解析（节选）

```yaml
reviewers:
  - id: Reviewer_1
    comments:
      - id: 1
        type: METHODOLOGICAL
        severity: MAJOR
        original_text: "作者应说明为何调整模型未纳入基线认知评分（MMSE），并评估结果对该变量的敏感性。"
        required_action: "确认MMSE的时间点、缺失情况和因果角色；如方法学上合适，运行预先说明的敏感性模型"
        affects_sections: [Methods, Results]
      - id: 2
        type: INTERPRETIVE
        severity: MINOR
        original_text: "讨论部分'该药物可改善认知功能'的表述过于绝对。"
        required_action: "改为关联性表述，并在局限性中说明观察性设计限制"
        affects_sections: [Discussion, Abstract]
  - id: Reviewer_2
    comments:
      - id: 1
        type: FORMATTING
        severity: MINOR
        original_text: "参考文献格式请统一为期刊要求的Vancouver格式。"
        required_action: "重新格式化参考文献列表"
        affects_sections: [References]
```

## 分类汇总提示（呈现给用户）

```
审稿意见解析完成：共3条意见，来自2位审稿人
  METHODOLOGICAL: 1（1条MAJOR）— 需要用户确认是否有基线MMSE数据
  INTERPRETIVE:   1（1条MINOR）— 可自主修订
  FORMATTING:     1（1条MINOR）— 可自主修订

有1条意见需要您确认后才能继续：是否有基线MMSE评分数据可以补充到调整模型中？
```

## 用户确认后的点对点回应表（节选）

| 审稿人 | 意见编号 | 原始意见 | 类型 | 严重程度 | 回应策略 | 稿件改动位置 | 状态 |
|--------|----------|----------|------|----------|----------|--------------|------|
| Reviewer 1 | 1 | 说明MMSE未纳入原因并评估敏感性 | METHODOLOGICAL | MAJOR | 已确认存在基线MMSE数据且测量早于暴露；新增敏感性模型并更新Table 2，不声称仅凭调整即可排除反向因果 | Methods第3段、Table 2 | ACCEPT |
| Reviewer 1 | 2 | "可改善认知功能"表述过于绝对 | INTERPRETIVE | MINOR | 改为"与认知功能评分改善相关"，讨论新增一段说明观察性设计的因果推断局限 | Discussion第4段、Abstract结论句 | ACCEPT |
| Reviewer 2 | 1 | 参考文献格式需统一 | FORMATTING | MINOR | 已按期刊Vancouver格式重新排版全部28条参考文献 | 全文参考文献列表 | ACCEPT |

## 致编辑信节选（示例措辞）

> 感谢编辑和两位审稿人对我们稿件的细致意见。针对审稿人1提出的反向因果关切，我们确认了基线MMSE的
> 测量时点，并新增包含该变量的敏感性模型，结果详见更新后的Table 2；这一调整不能单独排除反向因果，
> 因此我们也在局限性中保留了相应说明。针对讨论部分表述过于
> 绝对的意见，我们已将结论调整为关联性表述，并在局限性中补充说明本研究的观察性设计无法完全排除
> 残余混杂。审稿人2提出的参考文献格式问题也已按期刊要求统一调整。

## 可追溯性矩阵（节选）

| Source | Comment ID | Issue | Decision | Manuscript Change | Location | Verification |
|---|---|---|---|---|---|---|
| Reviewer_1 | 1 | MMSE角色与敏感性 | ACCEPT | 确认时点并新增敏感性模型，更新HR估计值 | Methods §3, Table 2 | 用户确认字段与时点，实际模型输出可追溯 |
| Reviewer_1 | 2 | 因果语言过强 | ACCEPT | 改为关联性表述+局限性说明 | Discussion §4, Abstract | 纯文字修改，直接执行 |
| Reviewer_2 | 1 | 引用格式 | ACCEPT | 统一Vancouver格式 | References | 纯格式修改，直接执行 |
