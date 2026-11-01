> 本示例为教学演示，涉及的研究课题、机构、数据、审稿意见均为虚构，不对应任何真实已发表研究或真实审稿
> 过程。仅用于演示 `/dyz-med-review` 的PASS/REVISE/REJECT呈现方式与"建议而非自动执行"的措辞。

# 示例：一次虚构稿件的多角度模拟审稿呈现

## 场景
虚构课题："社区获得性肺炎患者血清XX标志物与28天死亡率关联的回顾性队列研究"（虚构）。用户已完成
`/dyz-med-guideline`（STROBE核对）和 `/dyz-med-deai`，现在说："投稿前再帮我全面审一下。"

## 五视角汇总示例（单模型多视角，非独立专家）

```
# Quality Gate Aggregate Report

日期：2026-07-06
Review Mode: single-model multi-lens review
Study Type: retrospective_cohort
Review iteration: 1（是否续审由当前任务决定，无固定轮数要求）
Input binding: 教学片段未提供真实工件与哈希，freshness应为unverified
Execution note: 下列意见与结论均为虚构呈现，不是已执行检查回执

## Per-Gate Summary
| View | Verdict | Runtime note |
|------|---------|--------------|
| Evidence | REVISE | same model, separate rubric |
| Methods/Statistics | REVISE | same model, separate rubric |
| Ethics/Transparency | PASS | same model, separate rubric |
| Domain | PASS | same model, separate rubric |
| Journal Editor | REVISE | same model, separate rubric |

## Final Verdict（建议性判断，非自动阻断）: REVISE

**建议处理项（供用户参考决定优先级）：**
1. [方法统计视角] Discussion第2段出现"该标志物升高导致死亡率上升"的因果表述，但研究设计为回顾性队列，
   建议改为关联性表述（如"与死亡率升高相关"），并在局限性中说明无法排除混杂。
2. [证据核查视角] Table 3的效应量（HR 1.8）在正文引用为"HR 1.6"，两处数字不一致，建议核对原始统计
   输出并统一。
3. [期刊编辑视角] 摘要字数超出目标期刊限制约40字，建议精简Background部分。
```

## 呈现给用户的方式（示例措辞，体现"建议非阻断"）

> 五个模拟审稿视角中，伦理合规和领域专家视角给出PASS，方法统计、证据核查、期刊编辑视角给出REVISE。
> 这些视角由同一模型按不同量表完成，不代表五位独立专家。以上是参考意见，是否现在处理、分批处理、
> 还是先生成带问题的内部审阅稿，由您决定。HR 1.8与1.6的冲突尚未核实，因此本例不能给出无保留的
> 投稿就绪结论。材料齐全、科学审阅结果和外部提交授权应分别记录，当前请求不包含实际提交。

## 若修订后再次运行

使用稳定问题ID，回应立场和处理状态分列。以下仍是教学情景，不伪造关闭证据：

| 问题ID | 严重度 | 回应立场 | 处理状态 | 验证关闭所需证据 |
|---|---|---|---|---|
| REVIEW-001 因果措辞 | major | ACCEPT | awaiting_verification | 当前版本的句子、设计和支持证据重新核对 |
| REVIEW-002 HR冲突 | major | NEEDS_AUTHOR_INPUT | open | 统计原始输出与人群、模型口径，及修订后对账报告 |
| REVIEW-003 摘要篇幅 | minor | ACCEPT | awaiting_verification | 目标期刊当前字数规则与新摘要实测计数 |

本情景为已回应3/3、当前有效验证关闭0/3。只有`verification_check_id`指向current、completed、
applicable且领域结论支持关闭的检查，并有可定位的`evidence.path/sha256`，才能标为`verified_closed`。
检查报告先落盘，再由独立记录引用其实际哈希；输入改版后保留旧检查并重核，不直接替换旧哈希。
完整记录字段见`templates/mock-review-record.md`，缺少真实绑定时保持unverified。

## 仍有未解决问题时（Acknowledged Limitations 示例）

```
## Acknowledged Limitations
- [证据核查视角遗留] 部分历史病历数据缺失体重记录，无法在BMI校正模型中补全——数据本身不存在，
  非本轮修订能解决，已在局限性段落如实说明。
- [方法统计视角遗留] 用户认为当前的敏感性分析已充分，选择不再增加额外亚组分析——这是作者的范围
  取舍决定，已记录但不代表视角意见已完全采纳。
```
