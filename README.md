<!-- README_SYNC: source=working-tree; updated=2026-11-02 -->

<p align="center">
  简体中文 · <a href="README_EN.md">English</a>
</p>

<h1 align="center">DYZ MedPaper — 医学论文写作与科研 Agent Skills</h1>

<p align="center"><strong>32 medical writing and research skills for Claude Code and Codex.</strong><br>面向中国医生与医学研究生，支持中文沟通、中英论文写作、PubMed 文献检索与审稿修回。</p>

<p align="center"><a href="https://duyunzhoudyz.github.io/dyz-med-paper-skills/">中文文档站</a> · <a href="https://duyunzhoudyz.github.io/dyz-med-paper-skills/en/">English docs</a> · <a href="docs/skills.md">32 个技能索引</a> · <a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills/releases">版本发布</a></p>

<p align="center">
  <a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills"><img src="docs/assets/readme-overview.png" alt="DYZ MedPaper：为中国医生与医学研究生定制的医学论文助手。中文沟通、中英写作、导师改稿、投稿修回。仓库：https://github.com/duyunzhoudyz/dyz-med-paper-skills" width="880"></a>
</p>

<h2 align="center">为中国医生与医学研究生<br>定制的医学论文助手</h2>

<h3 align="center">中文沟通 · 中英写作 · 选题到修回</h3>

<p align="center">
  ⭐ <strong><a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills">点亮 Star，把这个科研帮手收进工具箱</a></strong><br>
  临床、轮转、课题已经够忙了，写论文多一个得力帮手。
</p>

<p align="center">
  <a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills"><img src="https://img.shields.io/github/stars/duyunzhoudyz/dyz-med-paper-skills?style=flat-square" alt="Stars"></a>
  <a href="#status"><img src="https://img.shields.io/badge/status-public_beta-amber?style=flat-square" alt="Status: Public Beta"></a>
  <a href="#skills"><img src="https://img.shields.io/badge/Agent_Skills-32_skills-222222?style=flat-square" alt="Agent Skills"></a>
  <a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills/actions/workflows/check.yml"><img src="https://github.com/duyunzhoudyz/dyz-med-paper-skills/actions/workflows/check.yml/badge.svg" alt="Offline checks — 本地工具与安装检查"></a>
  <a href="https://duyunzhoudyz.github.io/dyz-med-paper-skills/"><img src="https://img.shields.io/badge/Docs-中文%20%7C%20English-1c625c?style=flat-square" alt="中英文文档"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-PolyForm_NC_1.0.0-blue?style=flat-square" alt="License: PolyForm NC 1.0.0"></a>
</p>

<p align="center">
  <a href="#skills">能帮你做什么</a> · <a href="#for-clinicians">为你定制</a> · <a href="#examples">任务与示例</a><br>
  <a href="#quick-start">安装使用</a> · <a href="#status">项目状态</a> · <a href="#license">许可与联系</a>
</p>

---

### 从科室病例与毕业课题出发

DYZ MedPaper 是一套**围绕中国医生与医学研究生科研场景设计的 AI 论文工作流**。从科室现有病例和毕业课题出发，用中文梳理研究问题、讨论统计结果，衔接中英文文献与稿件写作，再把导师意见和审稿要求落实到具体修改，帮你把手头材料推进成**能讨论、能修改的论文稿**。

无论是在临床工作间隙推进课题，还是一边轮转、一边准备毕业论文，都可以从当前最需要解决的一步开始：**选题、查文献、写初稿、改讨论、回审稿意见**。

把这 **32 个技能**装进 **Claude Code、Codex 或其他支持 Agent Skills 的智能体**，就可以用中文交代任务，从眼前最头疼的那一步开始。[查看安装方式](#quick-start)

<a id="skills"></a>

## 🎯 从选题到修回，费劲的地方都有帮手

按任务进入教程：[医学论文写作](https://duyunzhoudyz.github.io/dyz-med-paper-skills/tutorials/writing/) · [PubMed 文献检索](https://duyunzhoudyz.github.io/dyz-med-paper-skills/tutorials/pubmed/) · [系统综述与 PRISMA](https://duyunzhoudyz.github.io/dyz-med-paper-skills/tutorials/systematic-review/) · [统计结果解读](https://duyunzhoudyz.github.io/dyz-med-paper-skills/tutorials/statistics/) · [中英翻译](https://duyunzhoudyz.github.io/dyz-med-paper-skills/tutorials/translation/) · [审稿意见回复](https://duyunzhoudyz.github.io/dyz-med-paper-skills/tutorials/reviewer-response/)。

有数据却迟迟定不下选题，结果做出来了却写不出讨论，稿子改了几轮还是说不清亮点——这些都可以成为起点。你把现有材料和想解决的问题交代清楚，助手就能按对应方法帮你往下做。

| 你现在卡在哪 | 它能帮你干什么 | 可以拿到什么 |
|---|---|---|
| **手上有病例数据，不知道能写什么** | 结合临床问题、已有变量和现实条件，梳理可研究的方向，先看缺什么 | 候选选题、可行性判断、需要补的材料 |
| **文献查了一堆，还是理不出头绪** | 设计中英文检索，整理关键研究，比较别人做了什么、你的研究还能回答什么 | 检索方案、文献梳理、值得继续追的问题 |
| **统计结果出来了，不知道怎么讲** | 解释主要结果，区分统计上的差异与临床上的意义，整理图表和结果段落 | 结果解读、图表建议、结果部分草稿 |
| **引言绕来绕去，讨论只会重复结果** | 理顺文章要回答的问题，安排每段写什么，再根据结果和文献起草 | 写作提纲、章节草稿、修改理由 |
| **导师让大改，不知道从哪下手** | 找出最影响文章的问题，定位到段落，排出修改顺序并协助重写 | 问题清单、修改顺序、改写稿 |
| **收到一长串审稿意见** | 拆开每条意见，安排正文修改，起草回复，标清已经改了什么、还差什么 | 逐条回复信、修改位置、待办清单 |
| **写完了，要选刊和整理投稿材料** | 按主题、文章类型、预算和要求筛选期刊，整理摘要、图表与稿件 | 候选期刊及理由、中英文摘要、基础 Word 审阅稿 |

需要做统计时，也能协助讨论分析思路、准备代码和补充分析；**先确认具体方案，再在具备相应软件和数据条件的环境里执行。**

只想翻译一段、改一版摘要，或者救一救讨论，也可以单独做。你不用先学会 32 个技能的名字。更多说法见[常见任务示例](docs/task-cards.md)。

<a id="for-clinicians"></a>

## 🩺 围绕中国医生与医学研究生的科研日常设计

### 用中文想清研究，再写成中英文稿件

选题怎么想、结果怎么看、导师为什么说这一段逻辑不顺，都可以用中文来回讨论。先把研究问题和论证讲清楚，再按需要起草中文论文、英文正文或中英文摘要，让语言转换跟着研究思路走。

### 从科室病例和毕业课题的实际条件出发

有什么病例资料、随访够不够、关键指标有没有、还有多少时间，这些都会影响研究能怎么做。它可以从你的临床观察和现有数据开始，帮你把一个大方向收窄到能继续查、能继续讨论的问题。毕业论文、课题文章或投稿，都能把自己的时间、资源和要求一起带进去。

### 中英文文献和写作能接起来

既能围绕 PubMed 等来源查找研究，也能为知网、万方、维普等中文来源设计检索和整理已有记录；实际检索与全文获取仍需相应权限。中文初稿、英文正文、中英文摘要可以接着做，翻译时重点核对数字、术语和结论的分寸。

### 把导师意见落实到段落和修改清单

导师说“创新性不够”“讨论太散”“结果和结论对不上”，可以把原稿和具体意见一起交给助手。先找出问题在哪、哪些材料还缺，再安排修改顺序、协助重写，并解释修改理由，方便下一轮和导师讨论。

### 兼顾毕业要求、选刊预算和单位口径

把学校的论文要求、目标期刊、版面费预算、时间安排，以及学校或单位认可范围一起提供，助手就能据此整理写作与投稿清单，比较候选期刊并说明理由。具体要求会去核实，查不到的就标出来，方便你和导师一起做决定。

### 工作被打断，下次有记录可接

文章写到哪、哪些数字确认了、导师提出了什么、审稿意见还有几条没处理，都可以记在论文项目里。下次继续时，让助手先读这些记录，再接着推进。章节和回复信也能保存在项目里，整理成基础 Word 稿，方便拿给导师和合作者继续改。

<a id="examples"></a>

## 📝 从任务到稿件

### 把帮助做到具体稿子里

整理材料、搭提纲、起草段落、解释改法、整理回复，这些事可以围着同一篇论文连续做。**你负责把握研究方向，助手帮你把想法展开成文字，把意见落实到改稿。**

比如，材料齐备时可以这样交代：

> 这是我的结果表、几篇已经核实的文献和讨论初稿。帮我把讨论重写一版：先说清主要发现，再和已有研究比较，最后写临床意义和局限。缺依据的地方单列，用中文告诉我为什么这样改。

这项任务可以落到几份具体内容上：

- **一版讨论草稿**：按论文主线组织，写出各段的重点和衔接。
- **结果与文献的对应说明**：让你能回头找到每个重要说法的依据。
- **修改理由**：解释哪里重复、哪里跳得太快、哪里把结论说过了头。
- **还需补充的问题**：缺文献、缺分析或需要你确认的地方，单独列清楚。

接下来还可以要求压缩到期刊字数、改写其中一段、翻成英文，或根据审稿意见继续修订。[写作方法和示例](dyz-med-writing-plan/references/writing-craft.md)里可以看到这些工作如何展开。

### 看看仓库里的教学示例

下面是仓库里的**合成教学示例**，用来展示处理思路和稿件长什么样。它们不是医生使用反馈，也不是已发表论文。

| 你想看哪一步 | 打开后能看到什么 |
|---|---|
| [有结果，怎么搭起一篇论文](dyz-med-writing-plan/examples/示例-他汀类药物队列论证地图构建.md) | 从研究问题到主要发现，再到讨论每一段应该写什么 |
| [被拒稿后，先改哪几个问题](dyz-med-manuscript-diagnose/examples/worked-example-rejected-manuscript.md) | 把问题指出来、排出先后顺序，再安排具体修改 |
| [中文结果段落，怎么翻成英文](dyz-med-translate/examples/worked-example-cn2en.md) | 对照原文和译文，说明哪些内容必须保留、哪些问题需要另外处理 |
| [审稿意见，怎么一条一条回](dyz-med-revision/examples/worked-example-reviewer-response.md) | 回复怎么写、正文改哪里、未完成的工作怎么记录 |

<a id="workflow"></a>

### 从手头这一步开始，后面的事接着做

**只有想法，就先聊选题；有结果，就开始写；有初稿，就直接改；收到了审稿意见，就处理修回。**

不必从头走一遍所有步骤。可以只完成眼前的一件事，也可以明确交代一组连续任务，让助手在你授权的范围里接着做。需要你拍板的地方，再把具体问题拿出来讨论。

这套方法覆盖观察性研究、随机试验和系统综述等写作场景。研究类型不同，要补的材料、要查的规范也不同。助手会根据现有材料选择下一步，整篇论文不会在一次调用后自动完成。

<a id="quick-start"></a>

## 🚀 安装与开始使用

<a id="agents"></a>

### 1. 选择你的智能体

技能以 [Agent Skills](https://agentskills.io/specification) 的 `SKILL.md` 目录形式组织。核心工作流与本地脚本可以随完整技能目录安装到不同宿主；技能发现、工具权限与调用入口由宿主提供。

| 宿主 | 个人级技能目录 | 项目级技能目录 | 显式调用示例 |
|---|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/` | `.claude/skills/` | `/dyz-med-orchestrator` |
| [Codex](https://developers.openai.com/codex/skills) | `~/.agents/skills/` | `.agents/skills/` | `$dyz-med-orchestrator` |
| 其他支持 Agent Skills 的智能体 | 以宿主文档为准 | 以宿主文档为准 | 按宿主方式加载或指定技能 |

下面提供本地安装方式。其他智能体需能读取完整技能目录；执行脚本、检索文献和处理文件时，还需提供相应工具。目录规范兼容不等于所有宿主上的运行行为已经验证，具体验证范围见[当前状态](#status)。

### 2. 准备环境与材料

- 可正常使用、已完成必要账号配置且支持 **Agent Skills** 的智能体，例如 Claude Code 或 Codex。
- **Python 3.10+**，用于安装与本地检查；安装器只使用标准库。
- 一个独立的论文项目文件夹，以及合成材料或已脱敏、获准处理的研究材料。

**数据提示：** 本地脚本运行不代表整个 AI 会话离线。模型服务可能接收会话中提供的内容；请按所在机构要求处理数据，不提交可识别患者信息、医院凭据或未获准材料。

Windows 可先运行 `python --version`；如果使用 `py -3`，将后续 `python` 替换为 `py -3`。macOS/Linux 通常使用 `python3`。Python 可从[官网](https://www.python.org/downloads/)安装。

### 3. 下载并安装

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

### 4. 打开论文项目，交代眼前的任务

在所选智能体中打开论文文件夹，把准备好的材料放进去，然后用平时说话的方式描述需求。不确定先做哪一步，可以说：

> 请使用 dyz-med-orchestrator，看看这个文件夹里的论文材料，告诉我现在最该解决什么，先帮我把这一步做好。需要补充的材料列出来。

需要显式调用时，Claude Code 使用 `/dyz-med-orchestrator`，Codex 使用 `$dyz-med-orchestrator`；其他智能体按其调用方式操作。先看它对任务的理解和材料缺口，再继续写作或修改。

安装自检只能确认文件是否一致，实际技能是否加载还要在所用智能体中核实。遇到问题见下面的[安装维护与排查](#maintenance)。

<a id="maintenance"></a>

### 安装维护与排查

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

<a id="status"></a>

## 📌 项目状态与补充说明

### 目前做到哪一步

目前是**公开测试版**。仓库已有安装与本地工具的自动检查，也有上面的教学示例。真实使用中的连续写作效果、各智能体的实际表现，以及医学内容的独立质量评估，还没有全部完成。写作效果也会受到模型、材料和任务说明的影响。

### 使用前要知道

- 文献检索需要可用网络、工具和数据库权限；安装技能不会附带知网账号。内置在线检索工具目前只覆盖 PubMed，多数据库系统综述还需要其他来源。
- 正式统计需要相应软件和你确认的分析方案。读取 Excel、PDF、Word 等文件也需要对应工具；内置 Word 导出适合基础审阅稿，复杂排版、公式和修订痕迹需另用工具处理。
- 它可以帮你查、写、改、核对，但研究判断和最终稿仍需你与相关专业人员审阅。检查通过不等于结论成立，也不代表论文一定能发表。实际投稿需要你的明确授权和最终确认。

<a id="validation"></a>

### 技能目录与详细文档

在[完整技能索引](docs/skills.md)中查看全部 32 个技能的中英文任务名、最小输入、主要输出和教学示例；也可在[在线技能目录](https://duyunzhoudyz.github.io/dyz-med-paper-skills/skills/)中按关键词筛选。

本地工具的能力范围、演示和测试方法见[完整说明与开发验证](docs/readme-reference.md)；文献整理、正文核对、翻译和 Word 导出如何接起来，见[具体操作说明](docs/executable-workflow.md)。参与改进请看[贡献说明](CONTRIBUTING.md)，版本变化见[更新记录](CHANGELOG.md)。

<a id="license"></a>

## 📄 许可与联系

### 使用许可

本项目**源码公开**，采用 [PolyForm Noncommercial License 1.0.0](LICENSE)，可按许可证规定用于允许的非商业用途。超出许可允许范围的使用，需要事先取得[单独书面商业授权](COMMERCIAL-LICENSE.md)。第三方资料仍按各自条款使用。

### 问题反馈

有问题可以提 [Issue](https://github.com/duyunzhoudyz/dyz-med-paper-skills/issues)，写明使用的系统、智能体、操作步骤和脱敏后的报错，不上传患者资料或账号凭据。

---

<p align="center">
  <strong>把时间留给值得琢磨的研究问题，让论文里的细活多一个帮手。</strong><br> 如果这套方法对你有用，欢迎<a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills">点亮 Star</a>，也让更多正在写论文的同行发现它。
</p>
