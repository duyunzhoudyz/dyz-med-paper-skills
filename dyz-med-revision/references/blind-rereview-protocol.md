# 修回盲审自检与原生修订交付协议

在审稿修回阶段，容易出现“回复信写得很有说服力，但正文实际没改到位”的偏差。本协议提供两项可落地的工程防线。

## 1. 盲审自检模式（Response-Withheld Re-Review）

使用本技能随包标准库脚本 `scripts/blind_rereview_pack.py` 在物理上隔离作者回复信：

1. **打包盲审输入**（不含作者回复信，并剔除任何残余作者回应字段）：

```bash
python <skill_dir>/scripts/blind_rereview_pack.py pack \
  --comments paper/revisions/reviewer-comments.json \
  --manuscript paper/manuscript/v2.md \
  --out-dir paper/revisions/blind-check
```

2. **独立盲检**：仅凭生成的 `blind-rereview-packet.json`（原文意见 + 修改后正文）逐条核对，在 `blind-verdicts-template.json` 填写 `blind_check_status`（`resolved_in_text` / `partially_addressed` / `not_found_in_text` / `not_applicable_disagree`）与正文定位 `blind_check_locator`。
3. **交叉对账与阻断**：运行 `reconcile` 对照回复表，自动拦截“回复信写 `ACCEPT` 但正文未定位”或修改稿哈希已过期的问题：

```bash
python <skill_dir>/scripts/blind_rereview_pack.py reconcile \
  --verdicts paper/revisions/blind-check/blind-verdicts-template.json \
  --responses paper/revisions/response-table.json \
  --manuscript paper/manuscript/v2.md \
  --report paper/revisions/blind-check/reconcile-report.json
```

仅当盲检 `reconciled` 且相关科学/数值检查为 `current` 时，问题状态才可进入 `verified_closed`。

## 2. Word 原生修订稿（Tracked Changes）交付

向导师或期刊提交“修订留痕版（Marked-up Manuscript）”时，交由 `dyz-med-export` 的 `export_tracked_docx.py`（纯 Python 标准库生成启用 `<w:trackRevisions/>` 的原生 OOXML `<w:ins>` / `<w:del>` 修订文件，并默认剥离 `[claim:...]`/`[evidence:...]` 内部标记）或等效本地 Word 工具执行；本技能不强制假设兄弟技能目录存在。

交付规范：同时提供**清洁版**与**原生修订版**，并在 Word 或 LibreOffice 中打开核对修订标记显示，不把未核对的自动输出直接作为终版上传。
