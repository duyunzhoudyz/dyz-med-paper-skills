# PRISMA 规范化计数输入与跟踪表

本模板规定 `compute_prisma_counts.py` v1 的输入，不是手工维护第二套计数的表格。仅使用人工已确认的规范化
决定与关联；不接受原始题录格式，不代替方案、审查者台账或全文审阅。

## 1. 输入清单：绑定实际字节

命令在所选根目录运行（Python 3.10+，仅标准库）：

```powershell
python -B dyz-med-screening-pipeline/scripts/compute_prisma_counts.py paper/evidence/prisma-inputs-v1.json --root . --output paper/evidence/prisma-counts-run-001.json --check-output paper/evidence/prisma-check-run-001.json --run-id prisma-run-001
```

输入清单的形状如下；占位 SHA256 必须换成文件实际字节的小写64位哈希，不能原样运行：

```json
{
  "schema_version": "1.0",
  "id": "prisma-inputs",
  "version": "v1",
  "dataset_artifact_id": "screening-data",
  "tool_artifact_id": "prisma-counter",
  "artifacts": [
    {"id": "screening-data", "path": "paper/evidence/screening/normalized-screening-v1.json", "version": "v1", "sha256": "<实际数据文件哈希>"},
    {"id": "prisma-counter", "path": "dyz-med-screening-pipeline/scripts/compute_prisma_counts.py", "version": "v1", "sha256": "<实际执行脚本哈希>"}
  ]
}
```

- `id` 是稳定身份，不等于文件名；同一工件更新保留 ID，更改版本并重算哈希。清单自身的 id 不能与 artifacts
  重复，`prisma-counts` 保留给输出工件。脚本角色必须指向本次实际执行的文件，不能指向同字节的另一份副本。
- 决定台账、方案、规范化转换脚本等若影响本次计数，须作为 artifacts 的额外项加入；角色仅定位数据和计数脚本。
  工具验证全部声明项的字节，但不能自动发现遗漏的科学依赖，也不验证引用内容的真实性。
- 清单自身会以 id/version/实际哈希加入检查 inputs，不保存自哈希。两个输出是新文件，父目录须已存在；同一路径、
  已存在文件或覆盖输入一律拒绝。唯一运行 ID 由调用方分配，工具不读取全项目历史检查来保证全局唯一。
- manifest、artifact、output、check-output 均相对于显式 `--root`，使用正斜杠；拒绝绝对路径、盘符、反斜杠、空段、
  `.`、`..`、URL 和符号链接逃出根目录。CLI 脚本路径和 `--root` 参数本身按调用目录解释。

## 2. 规范化数据 JSON v1

顶层必须有 `schema_version: "1.0"`、非空 `protocol_version`、唯一非空原因代码数组 `exclusion_reasons`，以及下列
五个数组。没有行时显式写 `[]`，缺字段不等于零。未知扩展字段可保留，但不参与计数；核心字段不做同义词推断。
ID 和必填文本是非空字符串，不裁剪、改写或模糊匹配；JSON 重复键、重复实体 ID 和重复关联边均报错。

| 数组 | 每行必填字段 | 含义与约束 |
|---|---|---|
| records | record_id, source_id, source_record_id, source_type, pre_screen_decision, decision, decision_source | 一行一条检索记录。source_type=database/register/other_record；source_id 标识数据库、平台或方法，source_record_id 定位原始来源项。 |
| reports | report_id, source_id, source_report_id, branch, retrieval_status, decision, decision_source | 一行一份明确寻求获取的报告。branch=database_register/other_record/other_direct；source_report_id 是报告来源项标识。 |
| studies | study_id, basis | 一行一项人工识别的研究，basis 是研究身份认定依据或定位。 |
| record_reports | record_id, report_id, basis | 显式多对多关联。basis 定位人工核对依据。仅保留且未排除的记录能连到寻求获取报告。 |
| report_studies | report_id, study_id, basis | 显式多对多关联，不能把多份报告合并成一行。仅通过纳入报告关联的 distinct study_id 计入纳入研究。 |

`decision_source` 指向人工共识/裁决记录的稳定事件 ID 或定位。人工台账继续保留审查者、原始意见、时间、方案
及全文位置；脚本只校验其非空，不认证独立双审查者或裁决真实性。不一致的人工意见必须规范化为 conflict，不能
选取一人的 include 作为共识。缺来源不能用 AI 生成的文字替代。

### 记录状态

- pre_screen_decision=`retain/duplicate/automation/other`。工具只统计输入的既有决定，不执行任何去重或自动筛除。
- 被删除记录 decision 必须为 `not_applicable`；duplicate 另须 `duplicate_of`，指向现有 retain 记录，不允许自指、链式
  删除目标或缺失目标。其他记录不能设置 duplicate_of。不同研究报告不是自动重复项。
- retain 的 decision=`include/exclude/uncertain/pending/conflict`。include 意为人工已决定进入报告获取，不等于最终
  纳入；exclude 为标题摘要排除；pending 尚未完成标题摘要筛选；uncertain/conflict 已评估但尚未裁定。
- uncertain 不自动排除，也不由本工具擅自升级 include；人工决定寻求全文后再更新为 include，并保留其决定依据。

### 报告状态

- retrieval_status=`retrieved/not_retrieved/pending`。后两者 decision 必须为 `not_applicable`；pending 指获取尚未结束，
  不等于确定未获取。所有 reports 行都是已明确寻求获取的报告，不能用它代表尚未启动获取的候选报告池。
- retrieved 的 decision=`include/exclude/uncertain/conflict/pending`。pending 是已获取但尚未评估；其余为已评估，
  uncertain/conflict 仍未最终裁定。未经全文核对不能擅自填 include 或 exclude。
- exclude 必须有且仅有一个 `primary_exclusion_reason` 字符串，且在 exclusion_reasons 内；其他决定不得带排除原因。
  `not_retrieved` 绝不纳入全文排除原因总和。
- database/register 记录映射到 database_register 报告，other_record 映射到 other_record；直接从其他方法获得的
  other_direct 报告不要求记录映射，也不能混入记录边。跨分支重复发现须先人工确定报告归属，本版拒绝冲突映射，
  不静默优先分配、不重复统计。同一 study 可以通过不同分支的不同报告纳入，研究集合仍取全局并集。
- include 记录缺报告关联、非 direct 报告缺记录关联、include 报告缺 study 关联均为 unverified。边引用不存在 ID
  为 invalid；不能补造实体。非纳入报告可以保留已知研究关联，但这些关联不计入纳入研究。

可选 `expected_counts` 为已报告汇总值清单，形如 `{"included.studies": 2}`。仅接受已定义 metric 和非负整数，
不是计数输入的替代品；差异在 differences 中保留 expected/computed/difference，不改写任一方。

## 3. 唯一计数工件与可复算集合

`--output` 写一个 JSON 领域报告。`counts` 使用平面 metric 键，每项都有：

```text
unit: record | report | study
count: 集合大小
member_ids: 排序后的唯一成员ID
filter: 明确字段条件或关联集合规则（描述文字，不是待执行代码）
source_artifact_id: 规范化数据稳定ID
```

`source_rows` 用实体 ID 定位输入 artifact、JSON pointer、来源 ID/来源项 ID；`associations` 保留记录—报告与报告—研究
全部边及 basis。同一研究两报告应为 `counts["included.studies"].count=1`、`counts["included.reports"].count=2`。
一记录两报告或两记录一报告均合法，禁止跨单位做减法。

| metric（b 为分支名） | 单位与过滤 |
|---|---|
| identified.database / identified.register / identified.other_record | record；按 source_type |
| b.records_identified / duplicates_removed / automation_removed / other_removed | record；分支全部记录/对应预筛删除决定 |
| b.records_awaiting_screening / records_screened | record；pending / include、exclude、uncertain、conflict |
| b.records_excluded / records_advanced / records_unresolved | record；exclude / include / uncertain、conflict |
| b.reports_sought / reports_not_retrieved / reports_retrieval_pending / reports_retrieved | report；全部报告/对应获取状态 |
| b.reports_awaiting_assessment / reports_assessed | report；pending / include、exclude、uncertain、conflict |
| b.reports_excluded / reports_included / reports_unresolved | report；exclude / include / uncertain、conflict |
| included.reports | report；所有分支 include 报告并集 |
| included.studies | study；纳入报告经 report_studies 关联的研究并集 |

b=`database_register/other_record/other_direct`；other_direct **没有**记录指标。要按具体数据库/方法列框时，用工件
source_rows 的 source_id 在对应 member_ids 中定位分组，并保留集合；不得另建手填数值来源。
`exclusions_by_reason[b][原因]` 保存排除报告集合、单位、数量和精确过滤字段，原因来自本次输入而非模板固定分类。

`equations` 仅按同单位分区核对：

- identified records = duplicates + automation + other removed + awaiting screening + screened records。
- screened records = excluded + advanced + unresolved records。
- sought reports = not retrieved + retrieval pending + retrieved reports。
- retrieved reports = awaiting assessment + assessed reports。
- assessed reports = excluded + included + unresolved reports。

**不建立 screened records − excluded records = sought reports。** record→report 必须沿显式关联边转换。
原因集合相加应为相同分支的 excluded reports；not_retrieved 不在原因集合内。

## 4. 状态、退出码与回执

| 状态 | 退出码 | 回执执行/领域结果 | 能否交付最终流程图 |
|---|---:|---|---|
| reconciled | 0 | completed / prisma_counts:reconciled | 仅在当前字节绑定有效且专业人员确认范围后可用 |
| discrepancy | 1 | completed / prisma_counts:discrepancy | 不能无保留使用；先追踪 differences |
| invalid | 1 | failed / null，reason 定位报告错误 | 不能；输入结构/绑定或矛盾使计数无效 |
| unverified | 3 | completed / prisma_counts:unverified | 不能；仅已知集合，count_scope=observed_only_not_final |
| CLI 参数不完整 | 2 | argparse 报错，无有效运行回执 | 不能 |

多个问题同时存在时，invalid 优先于 unverified，后者优先于 discrepancy；errors/unresolved/differences 分别保留。
finalizable 仅 reconciled 为 true，仍不是科学正确性或检索完整性认证。未决关系造成的研究数0只表示尚无已关联成员，
不能当作最终纳入0项研究。输入绑定/读取失败不输出猜测数字；路径或输出预检失败仅 stdout/stderr 报错，不强写文件。

`--check-output` 是独立 JSON v1.1 回执，含 artifacts 和 checks。inputs 完整绑定清单、数据、实际脚本与额外声明项；
输出工件固定 id=prisma-counts、version=run-id。检查 scope.domain 和 domain_result.namespace 均为 prisma_counts。
报告先写入，再由 check.report={path,sha256} 引用；checked_at 为带时区实时时间。失败但缺完整 inputs 的回执仅作
诊断，不能冒充有效合同或自动补全 passport。工具不改 passport、不安装兄弟技能；人工核对后可登记同形记录。

输入和脚本运行前后字节必须一致；有变化则 failed。重跑计数文件字节可重复；不同运行的回执 ID/日期可以不同。
任何已绑定输入版本/哈希或报告字节变化都使旧检查失效，必须重新执行并保留旧输出。0退出码只表示声明范围内闭合，
不证明全文真实获取、筛选合理、研究关联正确或具备合并分析资格。
