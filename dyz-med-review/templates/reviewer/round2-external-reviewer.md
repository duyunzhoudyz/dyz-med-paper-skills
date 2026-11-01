# 外部/跨模型审稿 — 第二轮模板

用途：配合[首轮模板](round1-external-reviewer.md)，按 SKILL.md“版本绑定与交接”对照原始意见与修订证据。
可在同一线程或显式提供完整对照材料的新线程中续审，记录实际方式、上下文共享和缺失内容；线程连续性或
新开对话均不保证意见独立。单模型多视角仍标 single-model multi-lens review，不冒充独立专家。

再发送前复核内容类别、用途、服务/目的地、获准范围和当前人类授权及 R2 targets 版本/哈希；首轮授权
不自动覆盖新版稿件或新目的地。未知不发送，改用已确认本地路径/待审材料。患者发表同意与研究参与同意
分开，适用性不明交专业复核，不推定批准或豁免。

## 提示词骨架（供已授权的第二轮对照审阅使用）

```
以下是实际第一轮问题清单、作者回应与修订证据，不假定这些意见由当前模型提出：

[提供稳定问题 ID、critical/major/minor 严重度、原始意见、回应立场、实际改动或未采纳理由]
[提供新旧版本/哈希、定位和验证材料；缺失则注明]

请逐项评估：
1. 将回应立场 ACCEPT/PARTIAL/DISAGREE_WITH_REASON/NEEDS_AUTHOR_INPUT 与处理状态
   open/in_progress/awaiting_verification/verified_closed 分列，不因接受意见或解释不同意就关闭。
2. 只有当前版本验证检查及证据实际支持解决时才建议 verified_closed；列 verification_check_id 和证据定位。
   缺材料、未覆盖或检查 stale/unverified 列待重核，不捏造验证记录。
3. 是否有修订后新引入的问题？保留稳定 ID 并为新问题另分配 ID。
4. 分列回复 R/N 和当前有效验证关闭 C/N；三条已回应一条已验证时写回复 3/3、关闭 1/3。
5. 给出 PASS/REVISE/REJECT 建议、实际范围与限制，不用平均分覆盖重大问题。

[在此粘贴修订后的稿件正文]
```

## 使用说明
- 对照依赖可追溯材料，不依赖虚构审稿人身份；不强制任何线程或自动技能流水线。
- 建议保存至 `paper/review/external-review-round2.md`，新建 R2 检查 ID，完整绑定 inputs、scope、
  execution_status、applicability、domain_result、report、checked_at；逐条消费 freshness。
- 问题关闭还需 evidence:{path,sha256}，所引检查 current/completed/applicable 且领域结论支持关闭；
  旧检查、旧关闭历史保留。退出码 0、完成回复或补充审阅都不等于科学 PASS 或可直接投稿。
- 当前 REJECT、重大未结或有限/失效检查必须传入汇总报告；仍可按用户要求制作显著标记的本地内部审阅稿。
- 外部回执记录实际发送字段/工件绑定、目的地、时间、执行状态、返回证据及限制；未执行写未发送，不虚构结果。
