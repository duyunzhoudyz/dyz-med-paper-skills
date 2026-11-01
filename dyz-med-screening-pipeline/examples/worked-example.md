# 系统综述筛选管线示例（虚构）

本示例的课题、记录和数字均为虚构，只演示口径与追溯方式。

## 场景

某虚构系统综述已经预设 PICO、纳排标准、主要结局、检索来源、双人筛选和冲突解决流程。

## 检索与导入

| 来源 | 记录数 | 来源类型 |
|---|---:|---|
| PubMed | 210 | database |
| Embase | 180 | database |
| 引文追踪与公开网页发现 | 15 | other_methods |

总识别记录为 405。公开网页发现没有被描述成 CNKI 等数据库的完整结构化检索。

## 去重与筛选

- 高置信重复组经人工确认后删除 93 条派生记录，原始导出仍保留。
- 进入标题摘要筛选：312 条。
- 标题摘要排除：260 条。
- 寻求获取全文报告：52 份。
- 未获取报告：3 份，单列为 `reports_not_retrieved`。
- 实际全文评估：49 份。
- 按方案的一个主要原因排除：30 份。
- 纳入报告：19 份。
- 其中两份报告属于同一项研究，因此纳入研究：18 项。

## PRISMA 计数

```yaml
identified:
  databases: 390
  registers: 0
  other_methods:
    - method: citation_searching_and_public_web_discovery
      unit: record
      count: 15
removed_before_screening:
  duplicates: 93
  automation: 0
  other: 0
screening:
  records_screened: 312
  records_excluded: 260
retrieval:
  reports_sought: 52
  reports_not_retrieved: 3
  reports_assessed: 49
eligibility:
  reports_excluded_total: 30
  reports_excluded_by_reason:
    wrong_population: 12
    wrong_intervention_or_exposure: 8
    wrong_outcome: 6
    wrong_design: 4
included:
  reports: 19
  studies: 18
```

所有数字由筛选表和研究—报告关联表复算；未获取全文没有再次算入全文排除原因。

## 数据提取

对 18 项研究建立研究层表，对 19 份报告建立来源关系，再按“研究—结局—时间点—分析人群”提取结局行。每个
数值记录报告、页码和表格位置，并由第二人核对。两份报告来自同一研究时，避免把重叠人群重复纳入 Meta。

## 交接

- 把上述计数交给 `dyz-med-flowchart` 生成 PRISMA 图。
- 把已验证、可比的结局数据交给 `dyz-med-analyze` 制定统计合成计划。
- 在合并模型实际执行成功之前，不写入合并效应、异质性或小研究效应结果。
