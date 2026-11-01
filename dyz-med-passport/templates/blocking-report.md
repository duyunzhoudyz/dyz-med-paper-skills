# 风险与待办提示（Heads-up Note）

> 本清单记录可核对的风险，不是科学通过或人工批准。开放项不自动阻塞无关任务；分析计划批准、
> 外部处理和提交授权等必要前置条件仍须满足，不能以“仅提示”为由跳过。

**生成日期**：<YYYY-MM-DD>
**项目**：<稿件标题或项目标识>
**当前阶段**：<project.current_stage>
**输入根目录与版本**：<--root；相关artifact_id / path / version / sha256>

## 尚未确认的事实
- [ ] <字段名，如 source_status.ethics> — <待核对事实、来源和影响范围>
- [ ] <字段名> — <说明>

## 尚未给出的人工确认
- [ ] <human_approvals中的键> — <目标artifact_id / version / sha256、动作、角色、确认时间、原始来源定位；缺项保持unverified>
- [ ] <需要的人类确认> — <不能由模型、单个布尔值或校验器补成批准>

## 检查有效性

| 检查ID及范围 | 输入绑定 | 执行状态 | 适用性 | 领域结论 | 当前有效性与证据 |
|---|---|---|---|---|---|
| <check_id / scope> | <artifact_id / version / sha256> | <execution_status> | <applicability> | <namespace / value或null> | <current / stale / unverified；report路径/哈希；问题定位> |

旧检查结论保留但不证明新版通过。纯排版变化默认stale；沿用科学判断须有内容等价证据和重核定位的新检查记录。

## 记录到的风险
- <OPEN-ID / severity / status / 风险描述> — <何时需处理、责任角色及关闭证据>
- <已回复数 / 已验证关闭数分别报告；verified_closed引用verification_check_id和evidence>

## 说明
以上事项源自当前工件与状态索引；校验器只报告结构和字节绑定问题，不判断医学正确性或人类同意真实性。
任务是否能继续取决于其实际范围、当前证据与必要授权；仅查询状态不执行分析、写作、修订或提交。
