# 流程图文字骨架

用途：先确认节点、计数与来源，再转换为 Mermaid 或投稿图稿。`<N>` 只能由真实记录生成；不适用、未记录和
真实为零必须分别标记。

## PRISMA 2020：数据库、注册平台及其他方法

按实际检索来源选择适用流程图。先登记唯一计数输入及回执，不在本模板手填数字：

```text
count_artifact_id: prisma-counts
count_artifact_version: <实际版本>
count_artifact_path: <相对于显式根目录的实际JSON路径>
count_artifact_sha256: <实际字节哈希>
check_id: <本次已核对输入绑定的检查ID>
root: <明确的项目根目录>
```

从该工件 `counts[metric].count` 代入每个节点；图源只保存 metric 和这份绑定作为数字来源。新工具为
`compute_prisma_counts.py`，其独立回执须为 completed/applicable/prisma_counts:reconciled，报告同时为
status=reconciled、finalizable=true，并确认所有 inputs、版本、实际字节仍匹配；不能仅凭状态字符串放行。
有差异、缺关联或旧绑定时，最多提供标明问题的审阅草图，绝不补数。模板占位符不是真实计数。

```text
[Identification: database/register records]
  Databases: counts["identified.database"].count
  Registers: counts["identified.register"].count

[Removed before screening: database_register]
  Duplicate records: counts["database_register.duplicates_removed"].count
  Automation removals: counts["database_register.automation_removed"].count
  Other removals: counts["database_register.other_removed"].count

[Screening: database_register]
  Records screened: counts["database_register.records_screened"].count
  Records excluded: counts["database_register.records_excluded"].count
  Advanced records: counts["database_register.records_advanced"].count
  Transition to reports: explicit record_reports edges, NOT count subtraction

[Retrieval / eligibility: database_register]
  Reports sought: counts["database_register.reports_sought"].count
  Reports not retrieved: counts["database_register.reports_not_retrieved"].count
  Reports assessed: counts["database_register.reports_assessed"].count
  Reports excluded: counts["database_register.reports_excluded"].count
  Reasons: exclusions_by_reason["database_register"][<actual reason code>]

[Other methods identifying records, if present]
  Records identified: counts["identified.other_record"].count
  Repeat record and report nodes using "other_record." metrics
  Preserve source_id and the corresponding member_ids for each method

[Other methods directly identifying reports, if present]
  Reports sought: counts["other_direct.reports_sought"].count
  Reports not retrieved: counts["other_direct.reports_not_retrieved"].count
  Reports assessed: counts["other_direct.reports_assessed"].count
  Reports excluded: counts["other_direct.reports_excluded"].count
  Reasons: exclusions_by_reason["other_direct"][<actual reason code>]
  NO title/abstract record-screening equation in this branch

[Included: union across all branches]
  Reports of included studies: counts["included.reports"].count
  Studies included in review: counts["included.studies"].count
```

逐数据库/方法拆框时，沿同一工件 source_rows 的 source_id 定位对应成员，保留查询条件和成员集合，不另存手填权威
计数。record/report 多对多转换只由 associations.record_reports 说明；一研究多报告通过 report_studies 关联，
跨分支纳入研究取全局集合，不能相加分支研究数。某份报告跨分支发现的矛盾交回人工归属确认，本版不自动裁定。

未获取全文属于 reports_not_retrieved，不放入全文排除原因。报告已获取但 pending 尚未评估；记录 pending 尚未筛选。
若在审阅草图呈现未完成流程，必须另外展示 records_awaiting_screening、records_unresolved、reports_retrieval_pending、
reports_awaiting_assessment 和 reports_unresolved 节点及问题定位；不能隐藏这些节点凑成完整的闭合图。

`equations` 仅连接同单位的分区集合。严禁“筛选记录−排除记录=寻求报告”，一研究两报告的最终节点应分别为1与2。
`differences` 记录旧汇总与复算值差异；在来源行修复后生成新运行工件，不能在图上改数。

## PRISMA-ScR

沿用与来源匹配的 PRISMA 2020 流程结构，并把纳入节点的术语改成范围综述实际使用的“证据来源”。保留
record、report 和 evidence source 的口径说明。

## CONSORT 2025：随机试验

```text
[Assessed for eligibility]: <N>
  Excluded: <N>
    Not meeting criteria: <N>
    Declined: <N>
    Other recorded reasons: <N>

[Randomized]: <N>

[Allocated to group A]: <N>          [Allocated to group B]: <N>
  Received intervention: <N>           Received intervention: <N>
  Did not receive: <N> + reasons       Did not receive: <N> + reasons

[Follow-up at <timepoint>]            [Follow-up at <timepoint>]
  Lost: <N> + reasons                   Lost: <N> + reasons
  Stopped intervention: <N> + reasons   Stopped intervention: <N> + reasons

[Included in <analysis set>]: <N>     [Included in <analysis set>]: <N>
  Excluded from this analysis: <N>      Excluded from this analysis: <N>
  Reasons: ...                          Reasons: ...
```

按具体试验设计和 CONSORT 扩展增删节点。不要默认失访者被排除分析，也不要把完成随访人群误标为 ITT。

## STROBE：观察性研究

```text
[Source population / records]: <N>
  Eligibility assessed: <N>
  Excluded: <N> + reasons

[Included]: <N>
  Grouping, matching or sampling appropriate to design

[Follow-up / data availability, when applicable]
  Lost or unavailable: <N> + reasons/timepoint

[Included in <analysis set>]: <N>
```

队列、病例对照、横断面和数据库研究使用不同节点；仅保留能帮助读者理解样本形成过程的内容。

## 对账记录

| 检查 | 左侧计数与来源 | 右侧计数与来源 | 状态 | 说明 |
|---|---|---|---|---|
| 待填写 | | | MATCH / MISMATCH / MISSING_SOURCE / NOT_APPLICABLE | |

所有图中数字都应能回到文件、字段、查询或记录集合。发现差异时保留两边原值并追查，不手工改图凑平。
