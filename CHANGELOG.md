# Changelog

## Unreleased

Added deterministic safety hooks, modular plugin packaging, clinical utility scripts, structured reporting checklists, reproducible demos, and clinician-friendly installers:

- **Plugin packaging & workflow hooks**: Added `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (full suite + 5 stage packs to fit host skill-description budgets), `hooks/hooks.json`, and `hooks/med_guard.py` (PHI guard, plan-first gates, post-edit numeric/tag reminders; `advisory` default, `DYZ_MED_HOOK_MODE=strict` blocks with exit 2).
- **Local deterministic scripts (pure Python stdlib)**:
  - `dyz-med-data-adequacy/scripts/deidentify_check.py`: zero-network Chinese/English PHI scanner & optional pseudonymizer.
  - `dyz-med-export/scripts/export_tracked_docx.py`: native OOXML `<w:ins>`/`<w:del>` Word tracked-changes generator for revision delivery.
  - `dyz-med-cnki/scripts/verify_references.py`: extended with PubMed/Crossref retraction, expression-of-concern, and erratum alerts (`retraction_alerts`).
  - `dyz-med-analyze/scripts/table1_summary.py`: reproducible Table 1 with Mean±SD, Median[IQR], missingness, SMD, and input SHA-256 provenance.
  - `dyz-med-figures-tables/scripts/plot_clinical_svg.py`: colorblind-safe forest, Kaplan-Meier, and RoB 2 SVG generator with `.provenance.json` integrity verification.
  - `dyz-med-guideline/scripts/audit_guideline.py` + `data/structured-checklists.json`: structured audit skeletons & coverage validator for STROBE, PRISMA-2020, CONSORT-2025, STARD-2015, CARE, and TRIPOD+AI.
  - `dyz-med-deai/scripts/style_check.py` + `references/clinical-style-card.md`: quantitative EN/ZH cliche/overclaim check and opt-in personal terminology memory.
  - `dyz-med-journal-finder/scripts/fetch_journal_policy.py`: offline-default / opt-in `--online` journal guideline & AI-policy extractor.
- **Review & revision rigor**: Added explicit `KILL / Major Re-scope` routing for fatal design flaws in `dyz-med-review` and response-withheld blind re-review protocol in `dyz-med-revision/references/blind-rereview-protocol.md`.
- **Reproducible end-to-end demos**: Added `scripts/build_demos.py` generating `demos/01_cohort_strobe`, `demos/02_bcg_meta_prisma` (Colditz 1994 13-trial dataset), and `demos/03_diagnostic_stard`.
- **Installers & academic metadata**: Added `installers/install-windows.bat`, `installers/install-macos.command`, `docs/host-compatibility.md`, `CITATION.cff`, and plain-language noncommercial license clarification in READMEs.

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
