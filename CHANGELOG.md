# Changelog

## Unreleased

Added a machine-readable layer for AI assistants and skill directories, plus the strategy behind it.

- The documentation build now emits `llms.txt`, `llms-full.txt` and `skills.json`, all generated from `docs/catalog.json`, `docs/faq.json` and the skill frontmatters so they cannot drift from the site.
- `skills.json` carries the authored trigger text of all 32 skills, matching what a host reads from `SKILL.md`.
- Structured data now includes a `SoftwareApplication` and `FAQPage` on both home pages, and a 32-item `ItemList` on the skill catalogs; pages declare snippet-friendly `robots` metadata.
- `robots.txt` explicitly allows search, user-triggered and training AI crawlers instead of relying on a wildcard.
- `scripts/check_docs.py` verifies these artifacts, their coverage of all 20 pages and 32 skills, and that no crawler is disallowed.
- Added `docs/geo-playbook.md` with the per-platform mechanism, outside-the-repository work and reproducible check queries.

These artifacts make the project easier to fetch and quote. They do not establish or predict indexing, ranking or recommendation by any AI platform.

## v0.1.0-beta.1 — 2026-11-02

First tagged public beta of DYZ MedPaper's 32 medical writing and research Agent Skills.

- Added a bilingual documentation site with installation instructions, a searchable skill catalog and six task guides in each language.
- Added a complete linked catalog of skill inputs, outputs and synthetic teaching examples, generated from a shared source.
- Clarified the Chinese-first medical research audience and Claude Code / Codex positioning in both READMEs; added documentation and offline-check badges.
- Added English task descriptions to the 32 skill frontmatters while retaining their existing instructions and boundaries.
- Added social preview artwork, versioned repository metadata, documentation build checks and a GitHub Pages workflow.

The project remains a public beta. File installation and offline tool checks do not certify host routing, model writing quality, medical validity or publication readiness. Database access, statistical environments and advanced document formatting need appropriate external tools. Source-available under PolyForm Noncommercial 1.0.0; separate commercial licensing applies outside its permitted scope.
