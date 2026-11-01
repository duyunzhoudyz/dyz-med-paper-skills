# 本地 Word 审阅稿导出

Python 3.10+，标准库生成 DOCX，无需 Pandoc、Word 自动化或网络。使用已核实工件创建新输出目录：

```text
python "<技能目录>/scripts/export_docx.py" --root "<论文项目>" --manifest export-input.json --output-dir submissions/v1
```

```json
{
  "schema_version": "1.0",
  "title": "研究标题",
  "sections": [{"path": "sections/manuscript.md", "sha256": "实际文件哈希"}],
  "figures": [{"path": "figures/flow.png", "sha256": "实际文件哈希"}],
  "references": {"R001": "作者已核实的参考文献显示文字"},
  "forbidden_identity_terms": []
}
```

Markdown 子集：1–3级标题、段落、粗体、1–8列表格、独立行 PNG 图片和单个 citekey。图片写作 `![图注](figures/flow.png)`，路径相对项目根；正文引用使用 `[@R001]`，按首次出现生成编号与文末清单，显示文字完全来自输入。

内部 `[claim:C001]`、`[evidence:E001]` 标记在审阅副本中隐藏，并写入导出警告；源 Markdown 保留。导出器不验证这些绑定，须先用 evidence-audit 完成正文核验并保留独立回执。

路径、文件哈希、图片缺失、悬空引用、表格列数与已列出的匿名敏感词均预检。外部图片、原始 HTML、代码块和块公式应走其他明确的本地导出路径，不能静默损坏或外传。unsupported 格式报错而不假装完整支持。

输出 manuscript-review.docx、export-check-report.json；默认持续行号、中文/英文字体、表格与图注。所有输出明确标记内部审阅版。占位符保留并警告，不为美观删除。默认格式不是任何期刊的官方要求；正式期刊版仍按当前作者指南调整并记录依据。forbidden_identity_terms 只能检查提供的字符串，不能证明完整匿名化。

本工具不支持 Word 原生修订，不设置投稿完成或科学通过。退出0仅表示生成审阅文件；视觉检查为 not_run，须实际渲染后另存回执。源文件不变，输出目录不能已存在。

预览优先使用已安装的本地 LibreOffice/Word 转为 PDF，再逐页检查。无预览工具时如实交付 DOCX 并说明未视觉核验，不上传到外部转换服务。返修对照稿沿用独立变更表；不要把彩色标记称为原生 tracked changes。
