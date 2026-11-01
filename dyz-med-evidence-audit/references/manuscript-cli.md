# 正文与证据绑定检查

用于已有 Markdown 草稿与现有论断矩阵的机械对账。单技能可独立执行，Python 3.10+ 标准库，不联网，不修改输入。

```text
python "<技能目录>/scripts/audit_manuscript.py" --root "<论文项目>" --manifest audit-input.json --output checks/manuscript-v1.json
```

输入 manifest 的 schema_version 为字符串 1.0，manuscript 和 registry 均含项目相对 path 与原始字节 sha256。完整外层示例：

```json
{
  "schema_version": "1.0",
  "manuscript": {"path": "sections/manuscript.md", "sha256": "实际正文文件哈希"},
  "registry": {"path": "evidence/claims.json", "sha256": "实际矩阵文件哈希"}
}
```

registry 是现有矩阵的机器可读投影，不是另一套人工维护的事实源：

```json
{
  "schema_version": "1.0",
  "sources": [{"id": "E001", "path": "evidence/source.txt", "sha256": "实际文件哈希"}],
  "claims": [{
    "id": "C001", "text_sha256": "规范化段落UTF-8哈希",
    "evidence_ids": ["E001"], "source_locators": {"E001": "表2，第1行"},
    "support_status": "UNVERIFIABLE", "reason": "尚待核对支持关系",
    "action": "取得来源并人工核对人群、结局及措辞"
  }]
}
```

正文以空行分段，一段只放一个论断标记，例如：

```text
两组共纳入120名参与者。[claim:C001] [evidence:E001]
```

text_sha256：删除 claim/evidence 标记，Unicode NFC 规范化，把所有空白折叠为一个空格并去首尾空白，再对 UTF-8 字节取 SHA256。数字、标点及词语变化均不能静默归一化。新句哈希只能表示已登记的内容，不表示已验证；必须沿用实际六类支持裁定。

表格可作为一个完整的空行分隔块登记，把标记放在表格后紧邻一行（中间不空行）；哈希覆盖列名、分隔线和全部单元格。单独的表题/图注有数字时也要登记或明确留作人工复核。例如：

```text
| 组别 | 人数 |
|---|---|
| A | 60 |
| B | 60 |
[claim:C002] [evidence:E002]
```

此方式只能发现整表文本变更，不逐单元格验证统计含义；来源定位须包含表号、分析人群和相应结果版本。不要为消除提醒直接把表格登记成 SUPPORTED。

检查输入哈希、实际段落内容、重复/遗漏标记、来源引用、定位和未登记数字段落。未登记的非数字事实、表格复杂布局、支持关系与原始定位语义仍需人工核对。源码或纯排版变化不会自动获得科学通过。

退出0：所覆盖机械项目 consistent；退出1：discrepant 或 needs_review；退出2：输入/运行 blocked。报告的 scientific_acceptance 始终 not_assessed。observed_claims 提供新行号和实测文本哈希，不能把它直接用于自动“修复”旧裁定。报告含输入绑定，可由项目合同生成独立 check 记录；不把全局退出码当成投稿门禁。
