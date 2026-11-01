# 模拟审稿意见记录表（模板）

用途：整理证据、方法统计、伦理透明度、临床领域或期刊编辑视角的模拟审阅发现。配合 SKILL.md 的
“每个视角的报告格式”和“版本绑定与交接”，默认保存到 `paper/review/`，也可独立使用用户指定路径。
这是决策支持，不是真实独立专家评议，不是强制导出门禁。

## 基本信息
- 审稿角度：[证据核查 / 方法统计 / 伦理合规 / 领域专家 / 期刊编辑]
- 日期：[YYYY-MM-DD]
- 稿件版本：[版本号或修订轮次]
- 研究类型：[从实际材料或 passport 读取；未知则标未知]
- 实际运行方式：[single-model multi-lens review / 多上下文或多模型的实际配置]
- 模型及上下文共享/先前意见可见性：[据实际填写；新开会话不保证独立性]
- 项目根目录与输入工件：[稳定 artifact_id、path、version、sha256；缺绑定标 unverified]
- 检查 ID/范围：[唯一 checks[].id、scope.domain/description、完整 inputs]
- 执行状态：[not_run / blocked / failed / completed；blocked/failed 需 reason]
- 适用性：[applicable / not_applicable / unknown；后两者需理由]
- 领域结论：[completed 时 namespace=mock_review，value=PASS / REVISE / REJECT；否则 null]
- 报告与日期：[report.path、落盘后实际 sha256、checked_at；独立记录引用，不自哈希]
- 逐条 freshness：[验证输出 current / stale / unverified；不是手填 current 的认证]
- 外部处理预检：[内容类别、用途、服务/目的地、获准范围、当前人类来源及版本绑定；未知不发送]
- 实际处理回执：[发送字段/工件、目的地、时间、执行状态、证据及限制；未发送如实注明，不填假回执]

## 意见记录

| 问题 ID | 意见/证据 | 严重度 | 稿件位置 | 最小修复/待确认事实 | 回应立场 | 处理状态 | 验证检查与关闭证据 |
|---|---|---|---|---|---|---|---|
| [稳定 ID] | [实际观察] | critical / major / minor | [定位] | [内容] | [未回应则留空] | open | [verification_check_id；evidence.path/sha256] |

回应立场使用 ACCEPT / PARTIAL / DISAGREE_WITH_REASON / NEEDS_AUTHOR_INPUT；处理状态单独使用
open / in_progress / awaiting_verification / verified_closed。采纳或解释不同意不等于验证关闭。
verified_closed 须有 current、completed、applicable 的检查，且领域结论实际支持关闭及证据可定位。
统计：意见总数 [N]；已回应 [R/N]；当前有效验证关闭 [C/N]。例如回复 3/3 不等于关闭 3/3。
旧关闭检查变 stale 时列为需重核，不计入当前有效关闭数。建议性风格意见另作备注，不新造严重度。

## 维度打分（可选，供该视角自行定义评分维度）

| 维度 | 分数（0-10） | 权重 | 加权分 |
|------|-------------|------|--------|
| | | | |
| **合计** | | | **X.X / 10.0** |

## 本视角建议性判断
**PASS / REVISE / REJECT**（说明：这是本视角给出的参考意见，不是自动执行的决定）

- REVISE的具体条件（如适用）：[列出必须处理才可能改善判断的具体项]
- REJECT的理由（如适用）：[列出导致此判断的关键问题，避免笼统表述]
- 科学限制与下游用途：[当前 REJECT、重大未结、stale/unverified 或有限范围不支持无保留 ready；可按授权交内部审阅稿]
- 材料完整性、科学结论/freshness、外部授权分别记录；校验器退出码 0 和高平均分都不证明科学 PASS。
- 伦理记录：[研究参与同意；患者发表同意；适用性及有资质复核来源分别填写，未知不推定批准/豁免]

## 备注
- 本记录是否基于完整稿件文本，还是仅审阅了部分章节：[说明]
- 本视角是否发现与其他视角意见冲突的地方（如有，交由用户或汇总报告环节判断如何取舍）：[说明]
