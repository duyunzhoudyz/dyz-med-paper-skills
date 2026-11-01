# 项目范围、技能目录与开发验证

[返回中文首页](../README.md) · [English README](../README_EN.md)

这里保留完整技能目录、工具能力与限制，以及开发者使用的验证命令。日常使用先看首页的任务说明和安装步骤即可。以下命令均在仓库根目录运行。

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

具体的文献、正文检查、翻译和导出衔接见[可执行工作流](../docs/executable-workflow.md)。

<a id="skills"></a>

## 32 个技能，按任务取用

[完整中英任务索引、输入输出与示例](skills.md) · [English catalog](skills.en.md) · [在线筛选技能](https://duyunzhoudyz.github.io/dyz-med-paper-skills/skills/)

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

回归覆盖技能声明、工件交接、安装自检、本地交付工具和三类合成研究流程；报告写入新的 `tests/results/` 子目录。安装检查在临时目录完成；已有工作区安装副本仅作只读核对。测试范围见[离线回归说明](../tests/offline-regression.md)，持续集成配置见 [CI 工作流](../.github/workflows/check.yml)。

<details>
<summary>模型评测与写作质量的验证口径</summary>

离线通过不能证明真实技能调用成功、医学结论正确或稿件可以投稿。真实宿主与医学验收应按[模型评测协议](../tests/evaluation-protocol.md)记录；写作质量按[写作盲评说明](../tests/writing-blind-review.md)另行评价。

准备冻结源码与评测输入：

```bash
python -B scripts/prepare_evaluation.py --output tests/results/my-evaluation
python -B scripts/check_eval_results.py tests/results/my-evaluation/results.json --check-current-source
```

准备脚本生成 60 条输入与首批 30 条顺序，不执行模型，也不填写通过结果。受测会话仅接收当前提示与匹配技能源，不接收评分判据、审计报告或冻结快照内的测试文件。宿主、实际模型、技能集合及人类审阅未核实时保持 `blocked` / `not_run`。历史记录使用匹配旧源码检查，不改写旧快照。

公开源码不包含本机安装副本、内部审计、原始运行日志、认证信息或论文数据。

</details>
