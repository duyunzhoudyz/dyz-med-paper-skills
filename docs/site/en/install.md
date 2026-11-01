---
title: Install Medical Writing Skills in Claude Code and Codex
description: Install all 32 DYZ MedPaper skills with Python, verify copied files and start a medical manuscript task in Claude Code or Codex.
---
## 1. Prepare a host and materials

Use an account-configured agent that supports Agent Skills and Python 3.10+. The installer uses the standard library; it does not install models, statistical packages or database accounts.

Create a separate paper workspace containing synthetic or authorized, de-identified materials. Local script execution does not make the whole AI session offline: the model service may receive conversation content.

## 2. Download the repository

Choose **Code → Download ZIP** on [GitHub]({{repo}}), extract it and open a terminal in the directory, or use Git:

```bash
git clone https://github.com/duyunzhoudyz/dyz-med-paper-skills.git
cd dyz-med-paper-skills
```

On Windows, check `python --version`; substitute `py -3` if that is your Python launcher. On macOS/Linux, `python3` is often appropriate.

## 3. Install for your host

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

The default destination is `~/.agents/skills/`. The filename remains `install_codex.py`; `--target` supports other hosts' documented skill directories. Success reports `PASS`, the skill count and destination. Different existing content stops installation instead of silently replacing edits.

### Install for one paper project

Replace the example with an existing project directory. For Claude Code:

```bash
python scripts/install_codex.py --target "/path/to/my-paper/.claude/skills"
```

For Codex:

```bash
python scripts/install_codex.py --project "/path/to/my-paper"
```

Keep the same target arguments and add `--check` to verify. Choose personal or project scope for each host to avoid duplicate entries.

## 4. Start a task

Open the paper workspace in your host and reload its skills. Describe the task naturally:

> Use dyz-med-orchestrator to inspect the available manuscript materials, identify the most useful next step and help with that task. List missing inputs separately.

Explicit invocation is `/dyz-med-orchestrator` in Claude Code or `$dyz-med-orchestrator` in Codex. File checks do not certify that a host has loaded or routed a skill correctly; verify that in the host.

## Upgrade and troubleshoot

Run `--check` with the original destination arguments first. To upgrade from a new checkout, provide a new backup directory outside both the source and installation directories:

```bash
python scripts/install_codex.py --upgrade --backup "/path/to/new-backup"
```

For Claude Code, also keep `--target "~/.claude/skills"`. Manual installation must include complete skill directories and the repository's `LICENSE`, `NOTICE` and `COMMERCIAL-LICENSE.md`, not just `SKILL.md` files.

[Full maintenance instructions]({{repo}}/blob/main/README_EN.md#maintenance) · [Skill catalog]({{root}}skills/) · [Task guides]({{root}})
