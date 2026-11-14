# GEO：让 AI 助手检索到并愿意引用这个项目

[项目首页](../README.md) · [English](../README_EN.md) · [维护与可发现性](maintaining-discoverability.md) · [项目介绍与交叉引用素材](discovery-kit.md)

这份文档处理的是 **GEO（Generative Engine Optimization）**：当医生或研究生在 Gemini、ChatGPT、Claude、豆包、DeepSeek 或某个 Agent 宿主里问“有没有能帮我写医学论文的 skill”时，让这些系统**能找到我们、读懂我们、并在回答里给出仓库地址**。

它不能做的事情先说清楚：**没有任何提交入口可以保证被推荐、固定排名或在某天出现。** 各平台没有公开的收录申请通道，检索与引用由各自的抓取、索引和回答策略决定，会随版本变化。下面每一条都是提高概率的动作，不是承诺。

## 1. 三种系统，三条不同的通道

把“AI 助手”当一个整体是 GEO 最常见的错误。实际上参与回答的系统分三类，对同一份内容的需求完全不同。

| 类型 | 代表 | 真正读什么 | 我们能控制的 |
|---|---|---|---|
| 搜索索引型 | ChatGPT（OAI-SearchBot）、Claude（Claude-SearchBot）、Perplexity | 已被索引的网页、结构化数据、第三方页面上的提及 | 允许抓取、页面结构、schema.org、站点地图 |
| 用户触发抓取型 | ChatGPT-User、Claude-User、Perplexity-User | 用户当场提到的那个 URL 或搜索结果页 | 页面自解释程度、`llms.txt`、正文可抽取性 |
| Agent 宿主 / 开发工具 | Claude Code、Codex、Cursor、WorkBuddy 等 | 仓库文件、`SKILL.md` frontmatter、`llms.txt`、`skills.json` | 机器可读清单、触发词、目录一致性 |

中文平台还有第四条：豆包背后是字节的 `Bytespider` 抓取，DeepSeek 使用自建检索，两者都更依赖**中文网页内容**（知乎、CSDN、公众号、掘金、B 站简介）而不是 GitHub 仓库本身。仓库写得多好，中文索引里没有文章，中文提问里就不会出现。

## 2. 仓库里已经就位的机器层

构建文档站时自动生成，随 `main` 一起部署，不需要额外服务：

| 文件 | 路径 | 作用 |
|---|---|---|
| `llms.txt` | 站点根目录 | 给 agent 的目录页：一句话定义、32 个技能、每个页面的标题与摘要、指向全量文件 |
| `llms-full.txt` | 站点根目录 | 全部页面正文 + 32 个技能完整条目的纯 Markdown，约 100 KB，适合一次性读入上下文 |
| `skills.json` | 站点根目录 | 结构化清单：id、中英标题与摘要、输入输出、`triggers`（直接取自 `SKILL.md` frontmatter）、指令与示例的 GitHub 地址 |
| `robots.txt` | 子路径 | 显式允许 `OAI-SearchBot`、`ChatGPT-User`、`Claude-SearchBot`、`Claude-User`、`PerplexityBot`、`GPTBot`、`ClaudeBot`、`Google-Extended`、`Bytespider` 等抓取，并指向站点地图 |
| 结构化数据 | 每页 `<head>` | `WebSite` + `WebPage`；首页另有 `SoftwareApplication` 与 `FAQPage`；技能目录页是 32 项的 `ItemList`；教程页是 `TechArticle` |
| 页面 meta | 每页 | `robots: index, follow, max-snippet:-1, max-image-preview:large`，允许摘要系统取用长片段 |

关于 `llms.txt` 的实际效果，需要按 2026 年的公开数据说：**没有任何一家大厂公开承诺把它作为生产环境的输入**；面向搜索与回答的机器人中，只有极小比例会请求它。真正会稳定读取的是 IDE 与 Agent 工具（Claude Code、Cursor、Copilot 一类）。对我们来说这恰好是主要分发渠道，所以值得发布；但不能指望它提升 ChatGPT 或 Gemini 的引用率。

`robots.txt` 有一个硬限制：**抓取器只读域名根级的 `robots.txt`**。本项目部署在 `github.io` 的项目子路径下，根级文件由 GitHub 提供，我们改不了。子路径下的这份文件对主动请求该路径的客户端有效，也作为抓取意向的书面记录；真正的收录仍然依赖站点地图、Search Console 与外部链接。

## 3. 分平台动作

### Gemini

- 抓取入口是 Googlebot，AI Overviews 与 AI Mode 使用同一份索引；`Google-Extended` 只控制 Gemini 训练与 grounding，不影响搜索收录。
- 已做：站点地图、canonical、hreflang、结构化数据、Search Console 验证。
- 待人工：在 Search Console 对首页和六个教程页请求编入索引，观察「效果」报告里能出现哪些查询；Bing Webmaster Tools 可导入同一资源，供 Copilot 一侧使用。
- 中文内容不足时，Gemini 更可能引用别人的文章来回答“医学论文 skill 有哪些”。

### ChatGPT

- 检索侧是 `OAI-SearchBot`，用户当场给链接时是 `ChatGPT-User`；`GPTBot` 只影响训练语料。
- 已做：两个检索型 UA 都放行；页面正文直接回答“是什么、给谁用、怎么装”，FAQ 用可整段引用的完整句子。
- 待人工：让至少两三个真实第三方页面（skill 列表仓库、作者主页、技术社区文章）带上仓库地址与一句话介绍。**自己的页面说自己好，权重远低于别人提到你。**

### Claude

- 检索侧是 `Claude-SearchBot`，用户触发时是 `Claude-User`。
- 对 Claude Code 这类宿主，实际决定“会不会用这个 skill”的不是网页，而是装载后的 `SKILL.md` frontmatter `description`：它必须同时写出**中文触发场景**和**英文 Use for …**。32 个技能已经这样写，`skills.json` 的 `triggers` 字段与之逐字一致，两个入口不会互相矛盾。
- 待人工：在 ClawHub / skills 目录类站点提交条目（已有素材见 `docs/discovery-kit.md`）。

### Bing / Copilot / Yandex（IndexNow）

IndexNow 是 Bing、Yandex、Seznam 等共同使用的推送协议，也是**唯一能免登录直接提交**的通道；Google 不参与。密钥在 `docs/indexnow.json`，构建时在站点根生成同名 `<key>.txt` 作为归属证明。

```bash
python scripts/submit_indexnow.py --dry-run   # 先看要提交哪些 URL
python scripts/submit_indexnow.py             # 部署完成后再实际提交
```

必须先部署并且 `<key>.txt` 可访问，否则提交会被拒。返回 200/202 只表示对方已接收，不等于已收录。

### 豆包（ByteDance）

- 抓取以 `Bytespider` 为主，中文语料权重高，对 robots.txt 的遵守历史不稳定。
- 已做：放行；页面提供中文全量正文与 `llms-full.txt`。
- 待人工：这是唯一必须靠站外内容才能补的通道——中文平台（知乎回答、公众号长文、CSDN/掘金教程）里出现「DYZ MedPaper + 医学论文 skill + GitHub 地址」的完整组合。不要只贴链接，要写清解决什么问题的正文。

### DeepSeek

- 使用自建检索，没有公开的收录提交入口，主要靠可抓取的中文网页与英文页面。
- 已做：静态 HTML、无 JS 依赖的正文（这一点比很多 SPA 文档站更有利）。
- 待人工：同豆包，中文长文 + 明确的能力边界描述（DeepSeek 用户更容易被“能做什么、不能做什么”这类具体表述取信）。

### WorkBuddy 及其他 Agent 宿主

- 这类宿主读本地技能目录与清单文件，不依赖搜索引擎。
- 已做：32 个技能的目录名、frontmatter `name` 与目录名严格一致；`catalog.json` 是唯一索引源，`skills.json` 与站点索引都由它生成，不会漂移。
- 待人工：安装后用固定问句在目标宿主里实测触发（见下节验收），把结果记录到 `docs/outreach/`。

## 4. 站外杠杆（按投入产出排序）

1. **GitHub 元数据**：Description 与 Topics 是 GitHub 搜索和多数自动索引的第一手字段。字段内容集中在 `docs/repository-metadata.json`，改完需在仓库 About 手动同步。
2. **skill / agent 目录条目**：ClawHub、`awesome-claude-skills` 一类清单仓库、skills 聚合站。按各自贡献规则提 PR；是外部动作，需要维护者账号与明确授权。
3. **中文技术社区长文**：一篇讲清“医学论文从材料到稿件，32 个 skill 各自接哪一步”的实操文章，比十次营销式转发有效。
4. **真实使用记录**：有人在 Issue 里说清楚用了哪一步、卡在哪，比任何自述都有引用价值。不要编造评价或用户反馈。

## 5. 验收：用可复现的查询看变化

每周在固定平台各问一次同样的问题，记录“是否出现仓库、出现在第几位、引用了哪个页面”。记录写入 `docs/outreach/` 下的追踪文件，不要只凭印象。

建议问句（中文平台用中文，英文平台用英文）：

```text
医学论文写作 AI skill 有哪些？有没有支持 Claude Code 的中文的？
帮我找一套能查 PubMed、写讨论、回复审稿意见的 agent skills
medical writing agent skills for Chinese clinicians, Claude Code compatible
how to write a medical manuscript with Claude Code skills
```

配套的站内检查（不联网，可放进 CI）：

```bash
python scripts/build_docs.py
python scripts/check_docs.py
python scripts/submit_indexnow.py            # 仅在站点已部署后
```

`check_docs.py` 会验证 `llms.txt` 覆盖全部 20 个页面与 32 个技能、`llms-full.txt` 未被截断、`skills.json` 与 `catalog.json` 一致、`robots.txt` 保留必要 UA 且没有误加 `Disallow`、首页的 `SoftwareApplication` 与 `FAQPage` 节点存在。它证明的是文件完整，不是搜索引擎或 AI 已经收录。

## 6. 明确不做的事

- 不堆砌关键词、不伪造 FAQ 数量、不写没有出处的数据；
- 不声称已被某个 AI 收录、推荐或排名；
- 不使用隐藏文本、cloaking 或诱导抓取的脚本；
- 不为某个平台单独维护一份会与主站漂移的副本——所有机器可读文件都由 `docs/catalog.json` 与 `docs/faq.json` 生成，改一处即可。
