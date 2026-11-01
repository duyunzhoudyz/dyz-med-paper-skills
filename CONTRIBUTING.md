# Contributing to DYZ MedPaper

[中文首页](README.md) · [English](README_EN.md) · [Skill catalog](docs/skills.en.md)

欢迎反馈安装问题、术语错误、技能职责不清、文档链接失效，以及使用合成材料发现的工具问题。

Contributions to documentation, terminology, examples and reproducible tool behavior are welcome. Most skill instructions are in Chinese; English corrections to task descriptions and documentation are useful too.

## Report a reproducible problem

Include your operating system, Python version, agent host, expected behavior, observed behavior and a minimal synthetic reproduction. Do not upload patient records, private manuscript materials, credentials or raw model logs containing sensitive information.

## Make a focused change

1. Keep the existing `dyz-med-*` identities and task boundaries stable unless the change explicitly addresses them.
2. Update Chinese and English documentation together. Edit `docs/catalog.json` for catalog entries, then run `python scripts/build_docs.py --sync-indexes`.
3. Label teaching examples as synthetic and preserve known capability and validation limits.
4. Describe the change and relevant validation in the pull request.

For skill or tool changes, install `requirements-dev.txt` and run `python -B scripts/run_offline_regression.py`. For documentation-site changes, install `requirements-docs.txt`, run `python scripts/build_docs.py`, then `python scripts/check_docs.py`. See [maintenance instructions](docs/maintaining-discoverability.md).

## License

This repository is source-available under [PolyForm Noncommercial 1.0.0](LICENSE), with [separate commercial licensing](COMMERCIAL-LICENSE.md). Do not introduce incompatible third-party material or present the project as unrestricted commercial software.
