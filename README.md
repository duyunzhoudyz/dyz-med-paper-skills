<!-- README_SYNC: source=working-tree; updated=2026-11-02 -->

简体中文 · [English](README_EN.md)

# DYZ MedPaper

![DYZ MedPaper 工作流介绍：从研究证据、论证规划到稿件写作与修订，面向 Claude Code、Codex 和兼容 Agent Skills 的智能体](docs/assets/readme-overview.png)

**面向临床医生与医学研究生的 AI 论文工作流：从手头的数据、结果和初稿出发，理清论证，推进写作与修订。**

基于 Agent Skills，可接入 **Claude Code、Codex 和其他支持该规范的智能体**。[查看接入方式](#agents)

⭐ [Star 收藏这套工作流](https://github.com/duyunzhoudyz/dyz-med-paper-skills)，方便下次写论文时找到它。

[![Stars](https://img.shields.io/github/stars/duyunzhoudyz/dyz-med-paper-skills?style=flat-square)](https://github.com/duyunzhoudyz/dyz-med-paper-skills)
[![Status: Public Beta](https://img.shields.io/badge/status-public_beta-amber?style=flat-square)](#status)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-32_skills-222222?style=flat-square)](#skills)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](https://www.python.org/downloads/)
[![License: PolyForm NC 1.0.0](https://img.shields.io/badge/License-PolyForm_NC_1.0.0-blue?style=flat-square)](LICENSE)

[查看教学示例](#examples) · [快速开始](#quick-start) · [工作流](#workflow) · [技能地图](#skills)

## 从你卡住的那一步开始

结果表已经有了，论文主线还没理清；文献读了不少，讨论仍在重复结果；收到大修意见，却不知道先改哪一处。DYZ MedPaper 把这些工作拆成可以衔接的任务：判断材料、组织论证、撰写章节、核对证据、整理修订与交付。

安装到所用智能体后，用中文描述任务即可。32 个技能提供各环节的操作说明、模板和部分本地工具，助手根据当前材料选择相应步骤。

| 你手上的材料 | 可以直接这样说 | 这一步的交付 |
|---|---|---|
| 数据字典与研究设想 | 先判断这份数据能回答什么问题，还缺什么，不运行统计。 | 数据充分性判断、缺口与可行路线 |
| 已核实的结果与文献 | 先帮我理清论文主线，再列出讨论每一段要回答的问题。 | 核心论断、证据对应关系与段落计划 |
| 结果表与讨论草稿 | 根据这些材料重写讨论，解释为什么这样组织，缺依据的地方单列。 | 讨论草稿、修改理由与待核实问题 |
| 已有稿件 | 找出最影响这篇论文的几个问题，定位原文，给出修改顺序。 | 稿件诊断与修订优先级 |
| 稿件与审稿意见 | 把每条意见对应到正文修改和回复，区分已完成与待处理。 | 逐条回复表、修改位置与处理状态 |

已有可靠材料，可以从对应环节进入；只做翻译、摘要或局部修订，也可以单独完成。更多输入与交付见[常见任务卡](docs/task-cards.md)。

## 把研究思路写进论文

**先理清论文要回答什么。** 写作计划把研究问题、已有证据、本研究新增内容和核心论断放在一张论证地图上，再分配到各章节。引言提出的问题，在讨论中得到回应。

**让每一段承担明确任务。** 章节写作指导覆盖主题句、文献比较、结果解释、局限性与反向提纲。需要修订时，可以给出“原句 → 改写 → 理由”，说明结构和表达为什么改变。具体方法见[写作说明与合成样例](dyz-med-writing-plan/references/writing-craft.md)。

**把文字与依据放在一起核对。** 文献导入保留来源，正文证据工具检查登记论断与当前稿件的绑定，翻译工具比较数字和引用。机械检查负责发现部分差异，证据是否真正支持结论仍由研究者审阅。

**让下一轮工作有据可接。** 项目状态记录已确认事实、稿件版本、开放问题和修改历史。章节、回复表和基础 Word 审阅稿可以落在论文项目目录中；继续工作时，助手可读取已有记录再推进。

<a id="examples"></a>

## 先看交付长什么样

以下均为仓库内的**合成教学示例**，用于展示方法与输出结构，不是实际用户案例、已发表研究或模型质量评测结果。

| 示例 | 可以看到什么 |
|---|---|
| [从队列研究结果到论证地图](dyz-med-writing-plan/examples/示例-他汀类药物队列论证地图构建.md) | 研究问题、核心发现、文献缺口和讨论段落怎样对应 |
| [一份被拒稿件的诊断](dyz-med-manuscript-diagnose/examples/worked-example-rejected-manuscript.md) | 如何定位问题、分清优先级并安排下一步 |
| [结果段落的中译英](dyz-med-translate/examples/worked-example-cn2en.md) | 原文、受保护内容、译文与稿外提示的完整对照 |
| [审稿意见逐条回复](dyz-med-revision/examples/worked-example-reviewer-response.md) | 意见如何对应回应策略、稿件位置和修改记录 |

另有一个可在本地运行的[合成交付演示](scripts/run_delivery_demo.py)：文献导入 → 正文绑定检查 → 数字与引用比较 → 基础 DOCX 导出，并植入一次数字变化检查工具是否发现差异。它不调用模型，不能作为写作质量证明，运行方法见[验证说明](#validation)。

<a id="quick-start"></a>

## 快速开始

<a id="agents"></a>

### 选择你的智能体

技能以 [Agent Skills](https://agentskills.io/specification) 的 `SKILL.md` 目录形式组织。核心工作流与本地脚本可以随完整技能目录安装到不同宿主；技能发现、工具权限与调用入口由宿主提供。

| 宿主 | 个人级技能目录 | 项目级技能目录 | 显式调用示例 |
|---|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/` | `.claude/skills/` | `/dyz-med-orchestrator` |
| [Codex](https://developers.openai.com/codex/skills) | `~/.agents/skills/` | `.agents/skills/` | `$dyz-med-orchestrator` |
| 其他支持 Agent Skills 的智能体 | 以宿主文档为准 | 以宿主文档为准 | 按宿主方式加载或指定技能 |

下面提供本地安装方式。其他智能体需能读取完整技能目录；执行脚本、检索文献和处理文件时，还需提供相应工具。目录规范兼容不等于所有宿主上的运行行为已经验证，具体验证范围见[当前状态](#status)。

### 1. 准备环境与材料

- 可正常使用、已完成必要账号配置且支持 **Agent Skills** 的智能体，例如 Claude Code 或 Codex。
- **Python 3.10+**，用于安装与本地检查；安装器只使用标准库。
- 一个独立的论文项目文件夹，以及合成材料或已脱敏、获准处理的研究材料。

**数据提示：** 本地脚本运行不代表整个 AI 会话离线。模型服务可能接收会话中提供的内容；请按所在机构要求处理数据，不提交可识别患者信息、医院凭据或未获准材料。

Windows 可先运行 `python --version`；如果使用 `py -3`，将后续 `python` 替换为 `py -3`。macOS/Linux 通常使用 `python3`。Python 可从[官网](https://www.python.org/downloads/)安装。

### 2. 下载并安装

在[仓库主页](https://github.com/duyunzhoudyz/dyz-med-paper-skills)选择 **Code → Download ZIP**，解压后在该目录打开终端；或使用 Git：

```bash
git clone https://github.com/duyunzhoudyz/dyz-med-paper-skills.git
cd dyz-med-paper-skills
```

**Claude Code：**

```bash
python scripts/install_codex.py --target "~/.claude/skills"
python scripts/install_codex.py --target "~/.claude/skills" --check
```

**Codex：**

```bash
python scripts/install_codex.py
python scripts/install_codex.py --check
```

安装器沿用 `install_codex.py` 文件名，默认目录为 `~/.agents/skills/`，也支持通过 `--target` 指定 Claude Code 或其他宿主的技能目录。上述命令均复制全部 32 个技能及许可文件，成功后显示 `PASS`、技能数和安装路径。安装器不联网，不安装模型或 R/Python 包，不修改宿主设置、账号或其他技能；同名技能内容有差异时会停止。

其他智能体可使用 `--target` 指定其文档要求的目录，或按[手动安装说明](#maintenance)复制完整技能文件夹。

<details>
<summary>只为一个论文项目安装</summary>

把路径替换为已经存在的论文项目目录。Claude Code 使用：

```bash
python scripts/install_codex.py --target "/path/to/my-paper/.claude/skills"
python scripts/install_codex.py --target "/path/to/my-paper/.claude/skills" --check
```

Codex 使用：

```bash
python scripts/install_codex.py --project "/path/to/my-paper"
python scripts/install_codex.py --project "/path/to/my-paper" --check
```

`--project` 固定安装到项目的 `.agents/skills/`；Claude Code 项目请使用上面的 `--target`。随后在该项目中打开所选智能体。同一宿主的个人级与项目级安装二选一，避免同名重复条目；Windows 路径含空格时保留引号。

</details>

### 3. 打开论文项目，描述当前任务

例如，把已核实的结果和文献放进项目后输入：

> 请根据这个文件夹里的结果和文献，先整理论文的核心论断和讨论段落计划。标明每段使用的结果与文献，把材料缺口单列，用中文解释安排理由。

这一步的目标是一份**可以审阅的论证计划**。如果材料不足，先得到可用骨架和缺口清单；确认方向后，再要求撰写相应章节。

不确定从哪里开始，可以直接说：

> 请使用 dyz-med-orchestrator，读取现有论文材料，判断当前阶段，并建议下一步。

需要显式调用时，Claude Code 使用 `/dyz-med-orchestrator`，Codex 使用 `$dyz-med-orchestrator`；其他智能体按其调用方式操作。安装发现与排查见[维护和常见问题](#maintenance)。文件自检通过只证明安装内容一致，实际技能加载和任务选择仍需在所用宿主中核实。

<a id="workflow"></a>

## 工作流怎样衔接

```mermaid
flowchart LR
    A[研究想法或现有材料] --> B[问题与可行性]
    B --> C[设计与证据]
    C --> D[获批分析与结果]
    D --> E[论证与章节写作]
    E --> F[修订与审阅稿]
```

这是可选的工作顺序。已有结果可以直接进入写作，已有稿件可以进入诊断或修订；主导航负责判断阶段与推荐下一步，具体任务由所用智能体选择对应技能，整个流程不会自动一次跑完。

| 研究类型 | 工作顺序与衔接重点 |
|---|---|
| 观察性研究 | 方案与字典 → 数据充分性 → 获批分析 → 结果与写作 → 适用报告规范 → 审阅稿；图表与正文使用同一结果版本 |
| 随机试验 | 方案、注册与获批分析计划 → 实际执行记录与结果 → 注册结局对照 → 写作与报告规范核对 → 审阅稿 |
| 系统综述 | 检索协议 → 记录导入与去重 → 独立筛选 → 提取与偏倚评估 → 获批合成 → 写作与报告规范核对 → 审阅稿 |

用户给出完整任务授权后，助手可连续完成必要的辅助步骤；统计执行及方案变更需要针对具体方案的批准，外部投稿需要明确授权和最终确认。只问“下一步做什么”时提供建议。项目状态和工具输入清单由助手维护，用户无需手写 JSON、YAML 或哈希。

具体的文献、正文检查、翻译和导出衔接见[可执行工作流](docs/executable-workflow.md)。

<a id="skills"></a>

## 32 个技能，按任务取用

目录均以 `dyz-med-` 开头。每个技能以 `SKILL.md` 为核心，并按需携带模板、参考材料、示例和脚本。`agents/openai.yaml` 提供 Codex 的附加界面与调用配置；其他宿主按自身机制发现和调用技能。

| 环节 | 技能目录后缀 |
|---|---|
| 起点与状态 | `ideate`、`init`、`manuscript-diagnose`、`orchestrator`、`passport` |
| 研究设计与证据 | `mechanism`、`data-adequacy`、`registration`、`cnki`、`key-literature`、`screening-pipeline`、`evidence-audit` |
| 分析与展示 | `analyze`、`interpret`、`sensitivity`、`figures-tables`、`flowchart` |
| 论证与写作 | `writing-plan`、`introduction`、`methods`、`results`、`discussion`、`abstract`、`write` |
| 修订与交付 | `translate`、`deai`、`guideline`、`review`、`revision`、`journal-finder`、`export`、`submit` |

`passport` 供内部维护项目状态，通常无需单独调用。`cnki` 是中英文文献检索技能的目录名，不附带知网账号或全文下载权限。

<a id="status"></a>

## 当前状态与依赖

**公开测试版，面向 Claude Code、Codex 和其他支持 Agent Skills 的智能体。** 仓库提供技能说明、模板、本地脚本和离线回归。安装检查验证文件复制与字节一致性，不认证任何宿主的实际加载或调用。各宿主的真实自然语言路由准确率、连续多轮使用效果、写作盲评与医学质量尚未完成独立验收；尚未执行的检查保留为 `not_run`。

| 工作 | 所需条件与当前范围 |
|---|---|
| 文本解释、写作与翻译 | 可用的智能体、模型和明确材料；技能正文与多数配套文档以中文为主 |
| 正式统计分析 | 获批计划、R 或项目既定统计引擎及所需包；技能安装不包含这些环境 |
| 文献与期刊要求核查 | 可用网络、检索工具及合法访问权限；内置在线检索脚本仅覆盖 PubMed，不能单独完成多数据库系统综述检索 |
| 文献导入与本地检查 | Python 标准库支持 RIS、字面值 BibTeX、NBIB、PubMed XML 导入，以及正文绑定、数字和引用比较 |
| 文件读取与 Word 交付 | Excel/Word/PDF 读取依赖相应解析工具；内置标准库导出器支持基础 DOCX 审阅稿，复杂排版、公式和原生修订需另用工具；视觉检查需要本地 Word 或 LibreOffice |
| YAML 校验与完整开发回归 | PyYAML；JSON 合同脚本仅用标准库 |

本地检查只能覆盖明确实现的范围。例如，数字比较可能发现增删，却不能识别两组数值互换或结论强度改变；正文绑定一致也不等于来源支持论断。输出需由研究者、相关专业人员审阅，工具不能替代统计、伦理或医学判断，也不保证论文发表。

<a id="maintenance"></a>

## 维护和常见问题

<details>
<summary>安装后没有出现技能</summary>

带上安装时相同的 `--target` 或 `--project` 参数运行 `--check`，核对路径后重新打开宿主。Claude Code 可输入 `/dyz-med-orchestrator`；Codex 可用 `/skills`、`$` 或明确指定 `$dyz-med-orchestrator`。其他智能体使用其技能管理入口。可要求助手说明本轮实际读取了哪个 `SKILL.md`；仅提及技能名不能证明已加载。参见 [Claude Code 技能文档](https://code.claude.com/docs/en/skills)和 [Codex 技能文档](https://developers.openai.com/codex/skills)。

`--check` 附带的环境探测只检查 Codex、Rscript 和 PyYAML 是否能被发现；它不探测 Claude Code 或其他宿主，也不验证账号、网络、包版本或文档工具是否实际可用。

</details>

<details>
<summary>升级、手动安装与卸载</summary>

在新版本源码目录运行安装器，相同内容会跳过。有差异时，先核对是否修改过安装副本，再指定一个尚不存在、位于源码与安装目录之外的备份目录：

```bash
python scripts/install_codex.py --upgrade --backup "/path/to/new-backup"
python scripts/install_codex.py --check
```

以上为 Codex 默认目录示例。Claude Code 或其他自定义目录的升级与自检都须继续带上原来的 `--target`；Codex 项目级安装继续带相同的 `--project`。备份包含被替换的旧文件和安装清单；额外文件会保留并使升级停止。恢复时按备份清单核对，新版本新增文件不会自动删除。

手动安装时，将全部 32 个 `dyz-med-*` 目录完整复制到[宿主对应的技能目录](#agents)：Claude Code 使用 `.claude/skills/`，Codex 使用 `.agents/skills/`，其他宿主以其文档为准。每个技能目录都放入仓库的 `LICENSE`、`NOTICE` 和 `COMMERCIAL-LICENSE.md`。模板与脚本也需复制，不能只复制 `SKILL.md` 或把整个仓库作为单个技能安装。

卸载前备份自己的改动，然后仅删除本项目的 32 个技能目录。论文材料另存在项目目录中。旧版 `med-*` 不会自动删除，自检发现后需自行核对。

</details>

<details>
<summary>论文材料与工具分别放在哪里</summary>

助手应从实际加载的 `SKILL.md` 所在目录定位 `scripts/`、`templates/` 和 `references/`。论文输入与输出位于论文项目目录；不要把稿件写进全局技能目录。各说明中的示意路径应替换成实际路径。

</details>

<a id="validation"></a>

## 开发与验证

无需模型账号即可运行合成工具链演示，输出目录必须是 `tests/results/` 下尚不存在的新目录：

```bash
python -B scripts/run_delivery_demo.py --output tests/results/my-delivery-demo
python -B scripts/sync_shared_resources.py
```

演示生成文献记录、检查报告和带内部审阅标记的 DOCX，并验证一次植入的数值变化。它不联网、不调用模型、不执行统计；Word 视觉检查与语义审阅另计。第二条命令只检查共享资源是否同步。

完整离线回归需要已有 PyYAML；如需安装开发依赖，可运行：

```bash
python -m pip install -r requirements-dev.txt
python -B scripts/run_offline_regression.py
```

回归覆盖技能声明、工件交接、安装自检、本地交付工具和三类合成研究流程；报告写入新的 `tests/results/` 子目录。安装检查在临时目录完成；已有工作区安装副本仅作只读核对。测试范围见[离线回归说明](tests/offline-regression.md)，持续集成配置见 [CI 工作流](.github/workflows/check.yml)。

<details>
<summary>模型评测与写作质量的验证口径</summary>

离线通过不能证明真实技能调用成功、医学结论正确或稿件可以投稿。真实宿主与医学验收应按[模型评测协议](tests/evaluation-protocol.md)记录；写作质量按[写作盲评说明](tests/writing-blind-review.md)另行评价。

准备冻结源码与评测输入：

```bash
python -B scripts/prepare_evaluation.py --output tests/results/my-evaluation
python -B scripts/check_eval_results.py tests/results/my-evaluation/results.json --check-current-source
```

准备脚本生成 60 条输入与首批 30 条顺序，不执行模型，也不填写通过结果。受测会话仅接收当前提示与匹配技能源，不接收评分判据、审计报告或冻结快照内的测试文件。宿主、实际模型、技能集合及人类审阅未核实时保持 `blocked` / `not_run`。历史记录使用匹配旧源码检查，不改写旧快照。

公开源码不包含本机安装副本、内部审计、原始运行日志、认证信息或论文数据。

</details>

## 许可与联系

本项目**源码公开**，采用 [PolyForm Noncommercial License 1.0.0](LICENSE)。许可允许的用途与条件以原文为准；不属于其允许范围的使用，需事先取得[单独书面商业授权](COMMERCIAL-LICENSE.md)。本项目不宣称符合 OSI 的开源定义，第三方资料仍受各自条款约束。

问题可通过 [Issues](https://github.com/duyunzhoudyz/dyz-med-paper-skills/issues) 提交，请附操作系统、智能体名称与版本、复现步骤及脱敏后的报错，不上传患者资料或凭据。

如果这些方法和示例对你有帮助，可以 [Star 收藏](https://github.com/duyunzhoudyz/dyz-med-paper-skills)，留作下一篇论文的工作参考。
