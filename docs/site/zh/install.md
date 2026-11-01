---
title: 在 Claude Code 与 Codex 安装医学论文 Skills
description: 下载 DYZ MedPaper，使用 Python 安装全部 32 个医学论文技能，检查文件一致性，并在 Claude Code 或 Codex 中开始第一项任务。
---
## 1. 准备智能体与材料

准备支持 Agent Skills、已完成账号配置的智能体，以及 Python 3.10+。安装器只使用 Python 标准库，不安装模型、统计包或数据库账号。

另建一个论文项目文件夹，放置合成材料或获准处理的脱敏材料。本地脚本运行不代表整个 AI 会话离线；模型服务可能接收会话中的内容。

## 2. 下载项目

在 [GitHub 仓库]({{repo}}) 选择 **Code → Download ZIP**，解压并打开终端；也可使用 Git：

```bash
git clone https://github.com/duyunzhoudyz/dyz-med-paper-skills.git
cd dyz-med-paper-skills
```

Windows 可运行 `python --version`；使用 `py -3` 时替换下面的 `python`。macOS/Linux 通常使用 `python3`。

## 3. 选择宿主并安装

### Claude Code

```bash
python scripts/install_codex.py --target "~/.claude/skills"
python scripts/install_codex.py --target "~/.claude/skills" --check
```

### Codex

```bash
python scripts/install_codex.py
python scripts/install_codex.py --check
```

默认目标是 `~/.agents/skills/`。文件名沿用 `install_codex.py`，但可以用 `--target` 指定其他宿主的技能目录。成功时会显示 `PASS`、技能数量和安装路径。同名技能有差异时安装器会停止，避免覆盖本地修改。

### 只给一个论文项目安装

将示例路径替换为已有项目目录。Claude Code 使用：

```bash
python scripts/install_codex.py --target "/path/to/my-paper/.claude/skills"
```

Codex 使用：

```bash
python scripts/install_codex.py --project "/path/to/my-paper"
```

检查时保留相同参数并添加 `--check`。同一宿主的个人级与项目级安装二选一，避免重复。

## 4. 开始第一项任务

在宿主中打开论文文件夹，重新加载技能后直接描述任务：

> 请使用 dyz-med-orchestrator，看看当前论文材料，告诉我最该解决什么，先把这一步做好。需要补充的材料列出来。

Claude Code 可显式调用 `/dyz-med-orchestrator`；Codex 可显式调用 `$dyz-med-orchestrator`。安装自检验证文件一致性，实际加载情况仍须在宿主中核实。

## 升级与排查

先运行带相同目标参数的 `--check`。需要升级时，从新版本源码运行安装器，并提供新的、位于源码与安装目录之外的备份目录：

```bash
python scripts/install_codex.py --upgrade --backup "/path/to/new-backup"
```

Claude Code 需补上原来的 `--target "~/.claude/skills"`。不要只复制 `SKILL.md`；手动安装必须携带完整技能目录，以及 `LICENSE`、`NOTICE` 和 `COMMERCIAL-LICENSE.md`。

[完整安装维护说明]({{repo}}/blob/main/README.md#maintenance) · [浏览技能索引]({{root}}skills/) · [选择任务教程]({{root}})
