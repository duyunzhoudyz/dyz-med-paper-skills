# 翻译保护内容检查

Python 3.10+ 标准库。源稿、译稿只读，报告路径必须尚不存在。

```text
python "<技能目录>/scripts/compare_protected.py" --source source.md --target translation.md --phrases protected.json --output comparison-v1.json
```

protected.json 是数组，每项包含 id、kind、source、target 四个非空字符串。source/target 为明确的原文与获确认译法，例：

```json
[
  {"id":"dose","kind":"dose","source":"每日5 mg","target":"5 mg daily"},
  {"id":"time","kind":"timepoint","source":"随访30天","target":"30-day follow-up"},
  {"id":"ai","kind":"disclosure","source":"使用AI辅助语言编辑","target":"AI was used for language editing"}
]
```

脚本逐项比较数字和引用出现次数，并比较显式双语短语。允许数字末尾零、科学计数法、千位逗号与全角符号的明确规范化；不做单位换算。数字或引用替换、剂量或声明缺失会产生问题。

consistent 仅说明已检查的计数与短语相符。交换两个结果的数值可能保持计数，否定、比较组、因果强度与整句含义也不是计数能判定的；semantic_review 始终 required。将保护短语缩小到有意义的句子片段，结合逐句人工/模型语义复核。不要靠词数比例证明忠实翻译。

退出0：机械比较无差异；1：发现差异；2：输入或路径错误。报告记录输入原始字节哈希。deai 技能携带相同脚本，独立安装也可用。
