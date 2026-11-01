<!-- README_SYNC: source=working-tree; updated=2026-11-02 -->

<p align="center">
  <a href="README.md">简体中文</a> · English
</p>

<h1 align="center">DYZ MedPaper</h1>

<p align="center">
  <img src="docs/assets/readme-overview.png" alt="DYZ MedPaper overview: from research evidence and argument planning to manuscript drafting and revision, for Claude Code, Codex and Agent Skills-compatible agents" width="880">
</p>

<p align="center">
  <strong>Clinical work keeps you busy.<br>Give your paper a capable helping hand.</strong>
</p>

<p align="center">
  ⭐ <a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills">Star this research companion for your toolkit</a>, so you can find it when your next draft or revision comes around.
</p>

<p align="center">
  <a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills"><img src="https://img.shields.io/github/stars/duyunzhoudyz/dyz-med-paper-skills?style=flat-square" alt="Stars"></a>
  <a href="#status"><img src="https://img.shields.io/badge/status-public_beta-amber?style=flat-square" alt="Status: Public Beta"></a>
  <a href="#skills"><img src="https://img.shields.io/badge/Agent_Skills-32_skills-222222?style=flat-square" alt="Agent Skills"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-PolyForm_NC_1.0.0-blue?style=flat-square" alt="License: PolyForm NC 1.0.0"></a>
</p>

<p align="center">
  <a href="#skills">What it does</a> · <a href="#for-clinicians">For clinicians</a> · <a href="#examples">Examples</a><br>
  <a href="#quick-start">Install</a> · <a href="#status">Status</a> · <a href="#license">License &amp; contact</a>
</p>

---

DYZ MedPaper is an AI research workflow for **clinicians and medical postgraduate students**. It helps you work through research questions, literature, results, first drafts, discussion sections and reviewer responses—turning the material you already have into a manuscript you can discuss and revise.

Install its **32 skills** in **Claude Code, Codex or another Agent Skills-compatible agent**, describe the task in everyday language, and start with the part that is holding you up. The workflow is primarily written in Chinese. [See installation options](#quick-start).

<a id="skills"></a>

## 🎯 Help from research questions to revisions

You may have data without a clear research question, results without a discussion, or a draft whose contribution is still hard to explain. Start there. Share the material you have and the problem you want to solve; the assistant can use the relevant workflow to help move it forward.

| Where you are stuck | How it can help | What you can work with next |
|---|---|---|
| Clinical data, but no clear paper idea | Consider the clinical question, available variables and practical constraints; identify gaps first | Possible research questions, feasibility assessment and missing material |
| A pile of papers with no clear direction | Plan searches in English and Chinese, organize key studies and compare what remains unanswered | Search plans, literature summaries and questions worth pursuing |
| Statistical results that are hard to explain | Interpret the main findings, distinguish statistical differences from clinical relevance, and organize tables and text | Results explanations, figure and table suggestions, and a draft results section |
| An introduction that wanders or a discussion that repeats results | Clarify the paper's question, plan each paragraph, and draft from the findings and literature | An outline, section drafts and reasons for the changes |
| Major changes requested by a supervisor | Locate the most consequential problems, prioritize them and help rewrite the affected passages | A problem list, revision order and revised text |
| A long set of reviewer comments | Work through each comment, plan manuscript changes and draft replies tied to completed work | A response letter, change locations and outstanding tasks |
| A manuscript that needs a journal and submission materials | Compare journals by topic, article type, budget and requirements; organize abstracts, tables and text | A journal shortlist with reasons, Chinese and English abstracts, and a basic Word review draft |

For statistical work, it can also help discuss the analysis approach, prepare code and plan additional analyses. **Approve the specific plan before execution, with the required software and data available.**

A single paragraph, abstract or discussion section is enough to begin. You do not need to learn all 32 skill names. See [more task examples](docs/task-cards.md).

<a id="for-clinicians"></a>

## 🩺 Built around clinicians in China

### Think it through in Chinese

Research questions, results and revision choices can all be discussed in Chinese. Once the reasoning is clear, work on the English manuscript. This lets you focus first on what the research actually says.

### Start with what your department has

Available records, follow-up, missing measurements and time all shape a feasible study. The workflow can begin with a clinical observation or existing data and help narrow a broad direction into a question worth investigating. Bring the constraints of your thesis, research project or intended submission into that conversation.

### Connect Chinese and English literature and writing

Plan searches around sources such as PubMed, as well as Chinese databases including CNKI, Wanfang and VIP, and organize records you already have. Actual database searches and full texts still require the appropriate access. Continue from a Chinese draft to English sections and bilingual abstracts, checking numbers, terminology and the strength of the claims during translation.

### Include the practicalities of journal selection

Alongside scope and article type, compare publication fees, time constraints and institutional requirements. Get candidate journals with reasons to discuss with your supervisor. Current requirements are checked where possible; unavailable information is marked as such.

### Leave a record for when clinical work interrupts

Keep track of completed sections, confirmed numbers, supervisor feedback and unresolved reviewer comments in the paper project. At the next session, ask the assistant to read those records and continue. Sections and responses can be saved with the project and assembled into a basic Word draft for supervisors and coauthors to edit.

<a id="examples"></a>

## 📝 From tasks to manuscript drafts

### Turn the help into text you can actually work on

Organizing sources, outlining, drafting, explaining edits and preparing replies can all build on the same paper. **You guide the research; the assistant helps put your thinking into words and turn feedback into revisions.**

With the relevant material available, a task might look like this:

> Here are my results tables, several verified papers and a draft discussion. Rewrite the discussion: explain the main findings, compare them with previous studies, then cover clinical relevance and limitations. List unsupported points separately and explain your changes in Chinese.

That task can produce concrete working material:

- **A discussion draft** with a clear purpose and connection for each paragraph.
- **Notes connecting claims to results and sources**, so you can check the basis for important statements.
- **Reasons for the revisions**, explaining repetition, gaps in reasoning or overstated conclusions.
- **A list of open questions**, including missing references, additional analyses or decisions that need your input.

Continue by asking for a shorter version, a rewritten paragraph, an English translation or changes responding to a reviewer. The [writing methods and examples](dyz-med-writing-plan/references/writing-craft.md) show how this work is organized.

### Explore the teaching examples

These are **synthetic teaching examples** from the repository. They illustrate the approach and the resulting documents; they are not clinician testimonials or published studies.

| Step to explore | What the example shows |
|---|---|
| [Building a paper from study results](dyz-med-writing-plan/examples/示例-他汀类药物队列论证地图构建.md) | Connecting the research question and main findings to the purpose of each discussion paragraph |
| [Prioritizing changes after rejection](dyz-med-manuscript-diagnose/examples/worked-example-rejected-manuscript.md) | Locating problems, deciding what matters most and planning concrete revisions |
| [Translating a results passage into English](dyz-med-translate/examples/worked-example-cn2en.md) | Comparing source and translation, preserving essential content and separating issues that need further work |
| [Responding to reviewers comment by comment](dyz-med-revision/examples/worked-example-reviewer-response.md) | Drafting replies, locating manuscript changes and recording unfinished work |

<a id="workflow"></a>

### Start where the paper is now

**An idea calls for a research question. Results call for writing. A draft calls for revision. Reviewer comments call for a response.**

You do not need to repeat every earlier stage. Ask for one bounded task or authorize a connected set of tasks. The assistant can continue within that scope and bring back specific decisions when your judgment is needed.

The workflows cover writing for observational studies, randomized trials and systematic reviews. Different study types need different records and reporting checks. The assistant selects a next step from the available material; a single invocation does not automatically complete the whole paper.

<a id="quick-start"></a>

## 🚀 Installation and first steps

<a id="agents"></a>

### 1. Choose your agent

Skills use the [Agent Skills](https://agentskills.io/specification) directory format built around `SKILL.md`. The core workflow and local scripts travel with the complete skill directory; discovery, tool permissions and invocation are provided by the host.

| Host | Personal skill directory | Project skill directory | Explicit invocation |
|---|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/` | `.claude/skills/` | `/dyz-med-orchestrator` |
| [Codex](https://developers.openai.com/codex/skills) | `~/.agents/skills/` | `.agents/skills/` | `$dyz-med-orchestrator` |
| Other Agent Skills-compatible agents | Follow the host's documentation | Follow the host's documentation | Use the host's skill-loading or invocation mechanism |

Local installation options follow. Other agents must be able to read complete skill directories and provide the tools needed for scripts, literature search and file processing. Format compatibility does not establish verified runtime behavior on every host; see [Status](#status) for the evaluation scope.

### 2. Prepare your environment and material

- A working **Agent Skills** host, such as Claude Code or Codex, with any required account setup completed.
- **Python 3.10+** for installation and local checks. The installer uses only the standard library.
- A separate paper project folder with synthetic material or de-identified research material you are authorized to process.

**Data handling:** Local scripts do not make the whole AI session offline. Model services may receive content supplied in the conversation. Follow your institution's requirements; do not submit identifiable patient information, hospital credentials or unauthorized material.

On Windows, check `python --version`. If your Python command is `py -3`, substitute it for `python` below; macOS/Linux commonly use `python3`. Install Python from its [official website](https://www.python.org/downloads/) if needed.

### 3. Download and install

Choose **Code → Download ZIP** on the [repository page](https://github.com/duyunzhoudyz/dyz-med-paper-skills), extract it and open a terminal in that directory. Alternatively, use Git:

```bash
git clone https://github.com/duyunzhoudyz/dyz-med-paper-skills.git
cd dyz-med-paper-skills
```

**Claude Code:**

```bash
python scripts/install_codex.py --target "~/.claude/skills"
python scripts/install_codex.py --target "~/.claude/skills" --check
```

**Codex:**

```bash
python scripts/install_codex.py
python scripts/install_codex.py --check
```

The installer retains the filename `install_codex.py`. It defaults to `~/.agents/skills/` and accepts `--target` for Claude Code or another host's skill directory. Both options copy all 32 skills and their license files. Successful checks display `PASS`, the skill count and installation path. The installer does not access the network, install models or R/Python packages, or change host settings, accounts or other skills. It stops if an existing skill with the same name has different contents.

For other agents, point `--target` to the documented skill directory, or copy complete skill folders using the [manual installation instructions](#maintenance).

<details>
<summary>Install for a single paper project</summary>

Replace the path with an existing paper project directory. For Claude Code:

```bash
python scripts/install_codex.py --target "/path/to/my-paper/.claude/skills"
python scripts/install_codex.py --target "/path/to/my-paper/.claude/skills" --check
```

For Codex:

```bash
python scripts/install_codex.py --project "/path/to/my-paper"
python scripts/install_codex.py --project "/path/to/my-paper" --check
```

`--project` always installs into the project's `.agents/skills/`; use `--target` as above for Claude Code projects. Open the project in your chosen agent. Within each host, choose either a user-level or project-level installation to avoid duplicate skill names. Keep quotes around Windows paths containing spaces.

</details>

### 4. Open the paper project and describe the immediate task

Open the paper folder in your chosen agent, add the prepared materials and describe what you need in ordinary language. If you are unsure where to begin, ask:

> Use dyz-med-orchestrator to look at the paper materials in this folder. Identify the most important issue to address now and help me work through that step. List any additional material you need.

For explicit invocation, use `/dyz-med-orchestrator` in Claude Code or `$dyz-med-orchestrator` in Codex; follow other agents' invocation mechanisms. Check the assistant's understanding and any missing material before continuing to drafting or revision.

Installation checks establish file consistency. Actual skill loading still needs to be verified in your agent; see [installation maintenance and troubleshooting](#maintenance) below.

<a id="maintenance"></a>

### Installation maintenance and troubleshooting

<details>
<summary>Skills do not appear after installation</summary>

Run `--check` with the same `--target` or `--project` arguments used for installation, verify the path, then reopen the host. In Claude Code, enter `/dyz-med-orchestrator`; in Codex, use `/skills`, `$` or `$dyz-med-orchestrator`. Use other agents' skill-management interfaces as documented. Ask which `SKILL.md` was actually read in the current turn: mentioning a skill name alone does not establish loading. See the [Claude Code skills documentation](https://code.claude.com/docs/en/skills) and [Codex skills documentation](https://developers.openai.com/codex/skills).

The environment probe included in `--check` only detects Codex, Rscript and PyYAML. It does not probe Claude Code or other hosts, or validate accounts, network connectivity, package versions or document-tool functionality.

</details>

<details>
<summary>Upgrade, manual installation and removal</summary>

Run the installer from the new source checkout. Identical content is skipped. If files differ, first review any changes you made to installed copies, then specify a new backup directory outside both the source and installation directories:

```bash
python scripts/install_codex.py --upgrade --backup "/path/to/new-backup"
python scripts/install_codex.py --check
```

The example above uses Codex's default directory. For Claude Code or another custom location, keep the original `--target` in both upgrade and check commands; for a Codex project installation, keep the same `--project`. The backup contains replaced files and an installation manifest. Extra files are preserved and cause the upgrade to stop. Follow the backup manifest when restoring; files added by the new version are not automatically removed.

For manual installation, copy all 32 complete `dyz-med-*` directories into the [appropriate host directory](#agents): `.claude/skills/` for Claude Code, `.agents/skills/` for Codex, or the directory specified by another host. Include the repository's `LICENSE`, `NOTICE` and `COMMERCIAL-LICENSE.md` in every skill directory. Copy templates and scripts too, rather than only `SKILL.md`; do not install the repository's outer directory as a single skill.

Before removal, back up your edits, then remove only this project's 32 skill directories. Paper materials live separately in the paper project. Legacy `med-*` directories are not removed automatically; review any reported by the checker.

</details>

<details>
<summary>Where tools and paper materials belong</summary>

The assistant locates `scripts/`, `templates/` and `references/` relative to the loaded `SKILL.md`. Manuscript inputs and outputs belong in the paper project, not the global skill directory. Replace illustrative paths in individual instructions with actual paths.

</details>

<a id="status"></a>

## 📌 Project status and further details

### Where the project stands

This is a **public beta**. The repository includes automated installation and local tool checks, along with the teaching examples above. Evaluation of sustained writing sessions, behavior across agents and independent medical quality is not yet complete. Results also depend on the model, source material and task instructions.

### Before you use it

- Literature searches need a working network, tools and database access. Installation does not include a CNKI account. The built-in online search tool currently covers PubMed only; a multi-database systematic review needs additional sources.
- Formal statistical work requires the relevant software and your approval of the analysis plan. Reading Excel, PDF and Word files also requires suitable tools. The built-in Word exporter creates basic review drafts; complex layouts, equations and tracked changes need other tools.
- The assistant helps search, write, revise and check. Research judgments and the final manuscript still require review by you and the relevant professionals. Passing a check does not establish that a conclusion is valid or guarantee publication. Actual submission requires your explicit authorization and final confirmation.

<a id="validation"></a>

### Skill catalog and detailed documentation

For all 32 skills, detailed tool capabilities, demos and tests, see the [full reference and developer checks](docs/readme-reference.md). The [step-by-step tool guide](docs/executable-workflow.md) explains how literature records, manuscript checks, translation and Word export connect. Both guides are in Chinese.

<a id="license"></a>

## 📄 License and contact

### License

This project is **source-available** under the [PolyForm Noncommercial License 1.0.0](LICENSE), for noncommercial uses allowed by its terms. Uses outside that permission require [separate written commercial authorization](COMMERCIAL-LICENSE.md). Third-party materials remain subject to their own terms.

### Report a problem

Report problems through [Issues](https://github.com/duyunzhoudyz/dyz-med-paper-skills/issues), including your operating system, agent, reproduction steps and de-identified errors. Do not upload patient records or credentials.

---

<p align="center">
  <strong>Keep your attention on the research questions worth thinking about, with help for the work around them.</strong><br> If these workflows are useful to you, <a href="https://github.com/duyunzhoudyz/dyz-med-paper-skills">give the project a Star</a> and help other clinicians discover it.
</p>
