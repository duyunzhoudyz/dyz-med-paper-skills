# 多宿主适配与插件分包说明

DYZ MedPaper 遵循 [Agent Skills](https://agentskills.io/specification) 目录规范，支持多个主流 AI 编程与科研宿主。

## 1. 宿主安装路径与支持矩阵

| 宿主 | 全局技能目录 | 项目级技能目录 | 插件/Hooks 支持 | 调用示例 |
|---|---|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` | 支持 `.claude-plugin/marketplace.json` 阶段分包与 inline Hooks（已通过 `claude plugin validate` 结构验证） | `/dyz-med-orchestrator` |
| **Codex** | `~/.agents/skills/` | `.agents/skills/` | 读取 `SKILL.md` + `agents/openai.yaml`；`install_codex.py --pack` 支持按阶段安装 | `$dyz-med-orchestrator` |
| **Cursor** | `~/.cursor/skills/` | `.cursor/skills/` | 遵循 Agent Skills 目录规范（亦兼容 `~/.claude/skills/`） | 提及技能名或任务描述 |
| **GitHub Copilot** | `~/.copilot/skills/` | `.github/skills/` | 遵循 Agent Skills 目录规范 | 在聊天中说明医学写作任务 |
| **Gemini CLI** | `~/.gemini/skills/` | `.gemini/skills/` | 遵循 Agent Skills 目录规范 | 在会话中指定技能名 |

> 注意：目录规范兼容不等于全部宿主已完成端到端实测；`hooks/hooks.json` 与 marketplace inline Hooks 仅针对 **Claude Code** 生效。无终端经验的用户可直接双击运行 [Windows 安装器](../installers/install-windows.bat) 或 [macOS 安装器](../installers/install-macos.command)（macOS 首次从 ZIP 解压若被系统拦截，可右键点击选择「打开」或在终端执行 `chmod +x installers/install-macos.command`）。

## 2. 按阶段分包安装（与 `docs/catalog.json` 严格对齐）

部分宿主对单次会话加载的技能描述总字数有上限（例如我们在 2026-11-02 的基线探测中观察到宿主技能描述超预算时会截断部分描述）。无论通过 Claude Code 插件市场还是本地 `scripts/install_codex.py --pack <pack>`，均可按以下 5 个阶段轻量包或完整包安装：

| 分包名 | 技能数 | 包含技能 | Claude Code 插件安装命令 |
|---|---|---|---|
| `dyz-med-all` | 32 | 全部 32 个技能 + Hooks | `/plugin install dyz-med-all --marketplace duyunzhoudyz/dyz-med-paper-skills` |
| `dyz-med-start` | 5 | `ideate`、`init`、`manuscript-diagnose`、`orchestrator`、`passport` | `/plugin install dyz-med-start --marketplace duyunzhoudyz/dyz-med-paper-skills` |
| `dyz-med-evidence` | 7 | `mechanism`、`data-adequacy`、`registration`、`cnki`、`key-literature`、`screening-pipeline`、`evidence-audit` | `/plugin install dyz-med-evidence --marketplace duyunzhoudyz/dyz-med-paper-skills` |
| `dyz-med-analysis` | 5 | `analyze`、`interpret`、`sensitivity`、`figures-tables`、`flowchart` | `/plugin install dyz-med-analysis --marketplace duyunzhoudyz/dyz-med-paper-skills` |
| `dyz-med-writing` | 7 | `writing-plan`、`introduction`、`methods`、`results`、`discussion`、`abstract`、`write` | `/plugin install dyz-med-writing --marketplace duyunzhoudyz/dyz-med-paper-skills` |
| `dyz-med-delivery` | 8 | `translate`、`deai`、`guideline`、`review`、`revision`、`journal-finder`、`export`、`submit` | `/plugin install dyz-med-delivery --marketplace duyunzhoudyz/dyz-med-paper-skills` |

本地终端按阶段分包安装示例（适用于 Codex / Cursor / Copilot / Gemini CLI / Claude Code 本地目录）：

```bash
python scripts/install_codex.py --pack writing --target "~/.claude/skills"
python scripts/install_codex.py --pack writing --target "~/.claude/skills" --check
```

## 3. 安全与流程 Hooks 启用方式（Claude Code）

仓库提供 `hooks/med_guard.py`（纯标准库，支持 `Write|Edit|MultiEdit|Bash|PowerShell`），并已作为 inline Hooks 内嵌在 `.claude-plugin/marketplace.json` 中：

- **默认模式（`advisory`）**：检测 PHI（身份证校验码、带分隔符手机号、住院流水号/患者姓名/病区床号、敏感表头，排除基金号/PMID 误报）、Plan-first 门禁（对齐 `paper/sections/`、`paper/analysis/analysis-plan.md` 与 `paper/writing/manuscript_argument_map.yaml`）、未授权联网/外传命令与编辑后统计段落提醒，按 Claude Code 官方 `systemMessage` + `hookSpecificOutput.additionalContext` 协议返回。
- **严格模式（`DYZ_MED_HOOK_MODE=strict`）**：在 `PreToolUse` 阶段遇到 PHI 风险、缺少已批计划或缺少在线授权时返回 `permissionDecision: "deny"` 阻断执行（`--format raw` 下返回退出码 `2`）。
