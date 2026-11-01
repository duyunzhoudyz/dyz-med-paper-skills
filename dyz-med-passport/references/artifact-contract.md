# 项目工件与版本绑定合同 v1.1

本合同用于项目状态索引，不是评测回执协议，也不是医学认证、电子签名或自动工作流。`schema_version: "1.1"` 扩展原有 passport；JSON 与 YAML 使用相同字段。单技能可使用显式文件和本合同的记录，不必创建 passport、导入兄弟技能脚本或连接数据库。

## 1. 身份、路径和字节

- `artifacts` 是当前工件列表。每项 `id` 为项目内稳定标识（例如 `analysis-results`、`screening-records`），不能根据文件名猜身份；同一工件更新时保留 ID。`path` 可保留用户既有的 `structured_results.yaml` 或其他文件名。
- 每项绑定 `version`（非空字符串，如 `v2`）与 `sha256`（原始文件字节的小写64位SHA256）。文件路径、版本、哈希均明确；不能以mtime、文件存在或版本标签代替字节核对。
- 当前列表中的ID唯一；检查运行使用新的唯一 `checks[].id`，不能覆盖旧检查。旧工件快照、已替代批准及变更原因追加到 `history`，未知扩展字段原样保留。检查器不修改、迁移或删除记录。
- 所有文件引用相对于 `--root`；未给 `--root` 时以 passport 所在目录为根，**不是**当前工作目录，也不自动推断 `paper/` 的父目录。CLI 的 passport 参数和 `--root` 参数本身相对于调用目录解析。
- 文件引用使用非空正斜杠相对路径；拒绝绝对路径、盘符、反斜杠、空段、`.`、`..`、URL及经符号链接逃出根目录的路径。外部文件应由用户选择合适根目录或显式整理到获准项目范围，不能偷偷复制。定位片段单独写 `locator`，不要拼进 `path`。验证器只读本地引用，不联网、不执行文件。
- 通用证据引用为 `{path: "paper/reports/check-v1.json", sha256: "<实际字节哈希>"}`；不接受占位哈希为有效证据。空文件可作为输入工件，但检查报告和人工来源证据必须非空。

## 2. 检查合同

```yaml
artifacts:
  - id: analysis-results
    path: paper/analysis/structured_results.yaml
    version: v2
    sha256: "<真实的64位字节哈希>"
    status: draft
checks:
  - id: result-consistency-run-002
    scope:
      domain: result_consistency
      description: "核对主结局结构化结果与Table 2报告清单；不验证模型或因果解释"
    inputs:
      - artifact_id: analysis-results
        version: v2
        sha256: "<运行时实际输入字节哈希>"
      - artifact_id: reported-values
        version: v1
        sha256: "<运行时实际输入字节哈希>"
    execution_status: completed
    applicability: applicable
    domain_result:
      namespace: result_consistency
      value: consistent
    report:
      path: paper/reports/result-consistency-run-002.json
      sha256: "<实际报告字节哈希>"
    checked_at: "2026-10-31T12:00:00+00:00"
```

示例中的 `reported-values` 也须在 artifacts 注册；以上片段展示形状，不是可直接通过的实测记录。

- `inputs` 是非空、无重复 `artifact_id` 的完整相关输入集合，每项精确绑定 `artifact_id/version/sha256`。相关稿件、数据、规则、分析计划、脚本或计数参数若会影响结论，都必须注册并纳入该次输入；校验器不能自行发现遗漏的科学依赖。
- `scope.domain/description` 均为非空字符串，说明覆盖域与具体范围。不能将局部检查当全文审查。
- `execution_status` 仅允许 `not_run / blocked / failed / completed`。`failed` 是执行失败，不是科学结论否定；正常运行后发现差异应为 `completed` 加领域差异结论。
- `applicability` 仅允许 `applicable / not_applicable / unknown`；后两者需非空 `applicability_reason`。不适用不是通过，也不能由未执行推定不适用。
- `domain_result` 在 completed 时为 `{namespace, value}` 两个非空字符串，按领域保留大小写和含义，例如 `mock_review: REJECT`、`prisma_counts: reconciled`。其他执行状态必须为 null。验证器不统一或解释各领域值，不把 completed、consistent 或 current 互相转换。
- completed/failed 必须有 `report:{path,sha256}` 与 `checked_at`（ISO日期或带时区时间）；not_run/blocked 可为 null，若提供仍核验。blocked/failed 需非空 `reason`。有错误的已执行报告仍应保存，不能伪装未运行。
- `freshness` **仅为验证输出**，不接受存储的 `freshness: current` 作为证据。输入集合、版本、字节或报告不可信时不得沿用旧检查作为当前依据。

## 3. 当前有效性、兼容与变更

验证器逐条输出 `current / stale / unverified`，与执行、适用性和领域结论分列：

- current：所声明范围内的绑定和现有文件可核对，且 completed 的报告完整；**不表示领域通过、同意真实或检查范围充分**。
- stale：已声明输入与当前工件版本/字节不一致，或检查报告字节变化；保留旧领域结论但不将其用于当前版本。仅依赖该工件的检查/批准失效，无关文件变化不影响它们。
- unverified：旧记录无绑定、缺文件/来源/输入、未知状态、执行未完成或适用性未知等；记录保留但不能升级。

无 schema_version 或 `"1.0"` 可读，整体保持 unverified。旧 artifacts 缺哈希、旧 checks 只有 status、旧 human_approvals 为字符串时均保留并提示未核实；即使搬到1.1，缺绑定的旧项也不会自动升级。未知 schema_version 或核心枚举值明确报错；额外字段不报错、不删除。`project`、`source_status` 等历史自由文本域不冒充新核心枚举。`history` 为不透明历史列表，不要求历史引用仍在当前列表；验证器只对当前工件及其检查/批准作上述判断，不认证历史。

哈希是字节哈希，不能识别“科学内容没变”。包括纯排版在内的字节变化默认 stale。若专业人员决定沿用科学判断，必须另建当前输入绑定的检查记录，提供内容等价性证据、新旧版本对应关系及页码/表格/定位重核报告；旧记录仍 stale，不能直接改旧输入哈希。第一版验证器不自动裁定内容等价，不据标志位豁免失效。输入清单完整性与证据真实性仍需人审。

## 4. 人工批准和开放问题

保留 `human_approvals` 映射的既有键；新式对象：

```yaml
human_approvals:
  statistical_plan:
    state: confirmed
    targets:
      - artifact_id: analysis-plan
        version: v1
        sha256: "<计划实际哈希>"
    role: principal_investigator
    confirmed_at: "2026-10-31T12:30:00+00:00"
    source:
      kind: human
      actor_id: author-alias-01
      statement: "同意按该版本计划执行列明分析；不含额外模型或外传"
      reference:
        path: paper/approvals/plan-confirmation.txt
        sha256: "<保存确认记录的实际哈希>"
      locator: "message-id=synthetic-example"
```

- `state` 仅允许 `not_confirmed / confirmed / declined`；confirmed/declined 均需非空 targets、role、带时区 confirmed_at 和完整 source。not_confirmed 不证明任何授权；无来源的布尔值或状态字符串不能替代批准。
- actor_id 可为稳定化名，不强制真实姓名。source.kind 必须 human；reference 和 locator 可定位获准保留的原始人类确认，statement 明确对象、动作及限制。不得编造、由模型自评代替或把研究参与同意扩大为患者发表同意。
- 已有确认记录被更改、丢失或 targets 变更时，批准不再是当前可用依据。机器只核对结构与字节，输出 `recorded_not_authenticated`，**不能证明人类身份、权限、自由同意、法律有效性或科学适当性**。执行者仍须核对来源、角色、动作和当前用户请求；confirmed 不自动触发分析/上传/提交。
- `open_items` 保留 id/issue/needs/owner_role，severity 为 `critical / major / minor`；status 为 `open / in_progress / awaiting_verification / verified_closed`。回复、接受意见和完成改动不等于验证关闭。
- verified_closed 必须有 `verification_check_id` 指向当前 completed 且 applicable 的检查，及 `evidence:{path,sha256}` 定位关闭依据。验证器核对绑定、不解释该领域结论能否支持关闭；消费方仍需审阅。未知严重度或处理状态报错，旧记录缺字段仍标未核实。

## 5. 只读 CLI 与输出

Python 3.10+；JSON零第三方依赖；YAML仅使用已安装PyYAML，缺失明确 blocked，不自动安装。脚本自包含，不导入其他技能或仓库脚本。

在项目根运行（路径有空格时加引号）：

```powershell
python -B dyz-med-passport/scripts/validate_passport.py paper/project-passport.yaml --root .
python -B dyz-med-passport/scripts/validate_passport.py paper/project-passport.json --root .
python -B -m unittest discover -s tests -p test_passport_contract.py -v
```

Python API：`validate(passport_path: Path, root: Path | None = None) -> dict`；不修改传入数据/源文件，不创建输出文件。`exit_code(report) -> int` 与 CLI 规则一致。stdout 是JSON问题报告，含 `validator`、`status`（valid/invalid/blocked）、`freshness`、`errors`、`warnings`、`artifacts`、`checks`、`approvals`；问题为 `{code,location,message}`。checks 保留 execution_status/applicability/domain_result，增加 freshness；approvals 分列 state/freshness/provenance。`status: valid` 只表示合同结构与所引用文件核对无错误，不代表所有记录 current。检查器不写 passport，不批准、不运行科研分析。CLI参数错误由argparse写stderr。

| 退出码 | 精确定义 |
|---|---|
| 0 | 无合同错误且整体freshness=current；即使领域为REJECT也可能为0，禁止当作科学PASS或可投稿门禁 |
| 1 | 解析/结构/路径/文件缺失/哈希/重复ID/未知核心状态/人工来源字段等错误；输出可同时显示相关检查stale |
| 2 | CLI参数错误 |
| 3 | 无上述错误，但有stale或unverified记录（含legacy、not_run/blocked/failed、未知适用性、未确认批准、空状态） |
| 4 | YAML解析依赖PyYAML缺失；status=blocked |

整体freshness在记录中有stale时为stale，其次unverified，其余为current；解析/结构错误且未发现stale时为unverified。显式未确认批准会使整体未核实，但不应阻塞无关翻译、审阅版导出等任务；消费方按需要的artifact/check/approval逐条决策，不把总退出码当强制流水线门禁。

## 6. 下游生产者交接

计数和数值工具以本合同的 artifacts/inputs/scope/execution_status/applicability/domain_result/report/checked_at 为记录接口，可在自己的输出中附带记录供人审后更新索引；不擅自改 passport。运行前后核对输入字节，变化则报告无法形成稳定绑定，不把混合版本结果登记current。报告不能自哈希：先完成领域报告文件，再由独立检查记录引用它的字节哈希；不要把自身sha256嵌入自身文件。

PRISMA可用 `scope.domain` 与 domain_result.namespace=`prisma_counts`；统计对账可用 `result_consistency`，各自定义领域值及业务CSV/JSON字段，不需要导入此脚本。验证器的输入检查并不代替行级计数、单位/人群判断或数值核对。仅安装任一单技能时，可按同形字段交付独立记录并明确根路径，不强制安装dyz-med-passport。
