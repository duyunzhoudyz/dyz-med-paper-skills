# 医学期刊量化风格卡与个人术语库

本参考用于 `dyz-med-deai` 及各分节写作技能：目标是让初稿和修订稿接近主流临床医学期刊的克制、精确语域，而不是模仿聊天机器人腔调，也**绝不用于规避 AI 检测**。

## 1. 高频 AI 语域词与临床替换建议

| 避免的模板表达 | 临床期刊常见替代 | 原因 |
|---|---|---|
| `utilize` / `leverage` | `use` / `apply` | 临床期刊（如 JAMA、Lancet、BMJ）日常高频动词是 `use` 而非 `utilize` |
| `delve into` / `shed light on` | `examine` / `evaluate` / `clarify` | 避免修辞化、非精确动词 |
| `underscore` / `plays a pivotal/crucial role` | 陈述具体效应量、方向或机制环节 | 夸大强调，掩盖真实证据强度 |
| `groundbreaking` / `paradigm shift` | 删去宣传词，直接写具体方法或人群变化 | 医学编辑最反感的自吹表达 |
| `值得注意的是` / `不可否认的是` | 直接陈述事实或限定条件 | 零信息量填充开头 |
| `首次证明` / `充分证实` | 按设计写“观察到……相关”或“在本随机试验中……” | 避免超出研究设计层级的因果/确证声明 |

## 2. 段落节奏与句式检查

- **主题句先行**：每段第一句说明本段功能（核心发现 / 与既往研究差异 / 机制 / 局限），后续句子给数字与来源。
- **句长自然变化**：不设机械“每句必须 15–20 词”硬阈值，但连续出现超过 45 词/字的长难句时优先拆分，确保主语与效应对象清晰。
- **数字与修饰不分离**：效应量、95% CI、分母和时间点尽量留在同一句，避免前句给强结论、后句再藏不确定性。

## 3. 本地量化检查与跨论文个人风格记忆

运行随包脚本 `scripts/style_check.py`：

```bash
python scripts/style_check.py --input paper/manuscript/discussion.md \
  --memory-file ~/.dyz-med/style-memory.json \
  --report paper/qc/style-report.json
```

添加导师或目标期刊的固定术语偏好（仅在用户明确要求保存时写入个人目录，不影响仓库）：

```bash
python scripts/style_check.py --memory-file ~/.dyz-med/style-memory.json \
  --add-term "utilized" "used"
```

任何语言改写完成后，必须配合 `scripts/compare_protected.py` 核对数字、单位、比较符号、引用和声明未被改动。
