# dyz-med-paper-skills

**用大白话推进医学科研与论文写作的32个 Codex 技能。**

从临床想法、现有数据、已有稿件开始，获得选题、文献、统计计划、写作、修订和投稿材料准备方面的帮助。你可以直接说“先看看这份数据够不够写论文”“把摘要翻成英文，数字别改”，无需记住技能名。

**当前状态：公开测试版。** 已提供离线路由声明和工件合同回归；真实 Codex 自然语言路由准确率、连续多轮使用效果及医学质量尚未完成独立验收。主导航负责判断阶段和推荐下一步，明确任务由 Codex 直接匹配对应技能；这套工具不会自动把所有阶段串完，也不保证论文发表。

**许可：源码公开，非商业用途采用 [PolyForm Noncommercial 1.0.0](LICENSE)，商业用途可申请[单独商业授权](COMMERCIAL-LICENSE.md)。** 由于存在用途限制，本项目不宣称符合 OSI 的开源定义。用途是否获准以许可原文和书面商业协议为准。

## 五分钟开始

### 1. 准备

- 可正常使用、已登录且支持技能的 Codex；项目不会替你配置模型账号或读取凭据。
- Python **3.10或以上**，供安装和本地文件自检使用；安装器仅使用标准库。
- 一个单独的论文项目文件夹。首次体验请用虚构材料或已脱敏且获准处理的数据。

Windows 可在终端运行 `python --version`；若你的命令是 `py -3`，可把下文 `python` 换成 `py -3`。macOS/Linux 通常用 `python3`。没有 Python 时可从 [python.org](https://www.python.org/downloads/) 安装，或采用下面的手动安装方式。

### 2. 下载

在 [仓库主页](https://github.com/duyunzhoudyz/dyz-med-paper-skills) 点击 **Code → Download ZIP**，解压后在该文件夹打开终端。

熟悉 Git 的用户也可以运行：

```bash
git clone https://github.com/duyunzhoudyz/dyz-med-paper-skills.git
cd dyz-med-paper-skills
```

### 3. 安装并自检

```bash
python scripts/install_codex.py
python scripts/install_codex.py --check
```

默认复制全部32个 `dyz-med-*` 技能到 `~/.agents/skills/`；Windows 的 `~` 指当前用户主目录。每个技能同时携带许可文件。成功后会显示 `PASS`、技能数、安装路径和下一步提示。

安装器不会修改 Codex 设置、登录状态或其他技能，不联网、不安装 Python/R 包，也不会运行模型。重复安装相同内容不会重写文件；发现同名技能内容不同会停止，升级方法见下文。

只想让一个论文项目使用这些技能时，指定已有项目目录：

```bash
python scripts/install_codex.py --project "/path/to/my-paper"
python scripts/install_codex.py --project "/path/to/my-paper" --check
```

随后在该项目目录启动 Codex。不要同时安装个人级和项目级副本，以免出现同名重复条目。命令中的路径请替换成你自己的目录；Windows路径含空格时保留引号。

### 4. 在 Codex 说第一句话

打开你的论文项目文件夹，在 Codex 中输入：

> 我想开展一个医学论文项目。先不要写正文，帮我判断我现在处于哪个阶段；每次只问当前最必要的问题，用中文解释下一步。

也可以从具体工作开始：

| 你想做什么 | 可以直接这样说 |
|---|---|
| 找研究方向 | 我是呼吸科医生，手上有一批回顾性资料，帮我先找可行问题，不要编造数据。 |
| 看数据能做什么 | 先判断这份数据能支持什么问题、还缺什么，不要跑统计模型。 |
| 正式分析 | 帮我检查这份数据并拟一个统计分析计划，等我确认后再执行。 |
| 诊断已有稿件 | 帮我看看这篇稿子最需要改什么，先别改原文。 |
| 翻译 | 把这段摘要翻成英文，保留数字、引用和结论强度。 |
| 写讨论 | 根据这些已核实的结果帮我写讨论，缺依据的地方单独列出来。 |
| 看进度 | 读取这个文件夹里的论文材料，告诉我做到哪一步、下一步最值得做什么。 |
| 回复审稿人 | 根据这份审稿意见准备逐条回复，没做的分析不要写成已经完成。 |

Codex CLI/IDE 中可用 `/skills` 或输入 `$` 查看技能；主导航名为 `dyz-med-orchestrator`，显示名称为“医学论文进度导航”。如果没有自动选中，可明确输入：

```text
$dyz-med-orchestrator 请先判断这个论文项目现在到哪一步，并建议下一步。
```

Codex 按名称和描述发现技能，选中后读取完整说明。安装后没出现时，先核对安装路径和 `--check` 输出，再重新打开 Codex。文件自检通过不等于宿主实际加载或模型路由通过；可要求 Codex说明本轮实际读取了哪个 `SKILL.md`，不要把回答中仅提及技能名称当成调用证据。参见 [Codex官方技能文档](https://developers.openai.com/codex/build-skills)。

## 主路由怎样工作

- **具体任务**：直接选择最窄职责技能，不要求每次先运行主导航。
- **不知道从哪开始 / 查询进度**：主导航结合已有材料解释阶段并推荐下一步。
- **信息不足**：先澄清影响判断的问题，不猜研究设计、伦理信息、缺失值编码或结果。
- **下一步执行**：你明确提出任务后再推进；统计执行需要针对具体分析计划的批准，外部投稿另需明确授权和最终确认。

例如，“下一步干什么”只要求建议；“按你的建议，先检查数据是否够用”则是具体任务。“继续”不能替代尚未确认的统计分析计划。项目状态文件由助手维护，你不需要手写 JSON、YAML 或哈希。

## 能力与依赖

安装技能提供的是操作说明、模板和部分本地检查脚本，不会自动安装完整科研软件环境。

| 工作 | 可能还需要 |
|---|---|
| 解释、翻译、整理粘贴文本 | 可用的 Codex 模型和明确材料 |
| Excel/Word/PDF读取与导出 | 本机可用的解析或导出工具，具体依格式而定 |
| 运行正式统计分析 | 获批计划、R或项目既定统计引擎及所需包 |
| YAML合同校验、完整开发回归 | PyYAML；JSON合同脚本使用标准库 |
| 文献、注册与期刊要求核查 | 当前可用的网络/检索工具，部分数据库需合法访问权限 |

`--check` 会提示当前能发现的 Codex、Rscript 和 PyYAML，但不会因某个可选依赖缺失而阻止纯文本任务。它不验证账号、网络、R包或文档工具是否实际可用。

**隐私：本地运行脚本不等于整个 AI 会话离线。** Codex模型服务可能接收会话中提供的内容；不要把可识别患者信息、医院凭据或未获准材料提交给模型或公开 Issue。先遵守所在机构的数据处理规定并完成必要脱敏。工具不能替代研究者、临床专家、统计师或伦理审查。

## 全部32个技能

| 环节 | 技能目录（均以 `dyz-med-` 开头） |
|---|---|
| 起点与状态 | `ideate`、`init`、`manuscript-diagnose`、`orchestrator`、`passport` |
| 研究设计与证据 | `mechanism`、`data-adequacy`、`registration`、`cnki`、`key-literature`、`screening-pipeline`、`evidence-audit` |
| 分析与展示 | `analyze`、`interpret`、`sensitivity`、`figures-tables`、`flowchart` |
| 论证与写作 | `writing-plan`、`introduction`、`methods`、`results`、`discussion`、`abstract`、`write` |
| 修订与交付 | `translate`、`deai`、`guideline`、`review`、`revision`、`journal-finder`、`export`、`submit` |

`passport` 是内部状态维护入口，一般无需医生单独调用。`cnki` 是中英文文献检索技能名称，不代表自带知网账号或全文下载权限。

## 升级、手动安装与卸载

升级时先下载新版本，在新版本源码目录运行。相同内容直接跳过；若提示差异，请先检查自己是否改过安装副本，再显式升级并指定一个尚不存在的备份目录：

```bash
python scripts/install_codex.py --upgrade --backup "/path/to/new-backup"
python scripts/install_codex.py --check
```

项目级安装需继续带相同的 `--project` 参数。备份包括被替换的旧文件和安装清单；不会删除额外文件或其他技能。发现安装目录内额外文件时停止，先自行审阅与保留。恢复时按备份清单逐项核对，新版本新增文件不会自动删除。

手动安装：把32个 `dyz-med-*` 目录完整复制到 `~/.agents/skills/`（或论文项目的 `.agents/skills/`），每个技能目录中都放入仓库的 `LICENSE`、`NOTICE` 和 `COMMERCIAL-LICENSE.md`。不要只复制 `SKILL.md`，模板与脚本同样需要。不要把外层整个仓库当成单个技能目录。

卸载：先备份自己修改过的内容，然后仅删除所选安装目录下本项目的32个 `dyz-med-*` 文件夹。论文项目材料位于你的工作目录，与技能安装目录分开保存。旧版 `med-*` 不会自动删除，自检会提示可能重复，需自行确认后处理。

## 本地工具路径

助手应从实际加载的 `SKILL.md` 所在目录定位 `scripts/`、`templates/`、`references/`。论文输入和输出路径相对于你的论文项目根目录。两者不是同一目录。技能内 `"<技能目录>/..."` 是需要替换为实际路径的示意，不应原样运行，也不要把论文输出写进全局技能目录。

## 开发与验证

安装器及其自检不需要第三方包。完整开发回归需要已有PyYAML；如需安装，以下命令由你主动执行：

```bash
python -m pip install -r requirements-dev.txt
python -B scripts/run_offline_regression.py
```

默认报告写入全新的 `tests/results/offline-<时间戳>/`，不覆盖历史。完整回归覆盖32技能声明、38条语义规格、192个声明负向变体、23组命名合同分支与三类合成流程。参见 [离线回归说明](tests/offline-regression.md) 和 [真实模型评测协议](tests/evaluation-protocol.md)。

公开仓库不包含本机安装副本、内部审计、原始运行日志、认证信息或论文数据。干净下载可独立运行回归；回归会在临时目录完成安装和自检，不要求你先改动个人技能目录。若仓库已有本地安装副本，会另外只读核对它。

离线测试通过不能证明模型医学结论正确、文献真实、实际技能调用成功或稿件可以投稿。真实宿主与医学验收未完成的项目仍明确标为 `not_run`。

## 反馈与商业授权

通过 [Issues](https://github.com/duyunzhoudyz/dyz-med-paper-skills/issues) 提交可复现问题，说明操作系统、Codex版本、使用的句子及脱敏后的报错。请勿提交患者资料或凭据。

商业授权请阅读 [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md)，再联系维护者；未签署有效书面协议前，按 [LICENSE](LICENSE) 判断你的用途是否获准。
