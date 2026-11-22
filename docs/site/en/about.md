---
title: Project Status, Validation and License
description: Understand the DYZ MedPaper public beta, validation boundaries, tool dependencies, PolyForm Noncommercial license and contribution process.
---
## Current status

DYZ MedPaper is a public beta collection of medical manuscript Agent Skills for doctors and medical postgraduate students in China. It includes 32 skills, templates, references, synthetic examples and local scripts.

| Check | What it establishes | What it does not establish |
|---|---|---|
| Installation and file checks | Complete directory copies and byte consistency | Correct loading or invocation in a host |
| Offline regression and synthetic workflows | Explicitly implemented tool and artifact behavior | Model writing quality or medical validity |
| Documentation build checks | Page, link, language and indexing structure | Search-engine indexing or higher rankings |

Real-host routing, sustained writing and independent medical quality have not all completed acceptance. See [live offline checks]({{repo}}/actions/workflows/check.yml), [validation details]({{repo}}/blob/main/docs/readme-reference.md#validation) and [release notes]({{repo}}/releases).

## Tools and access

- The built-in online search script covers PubMed (reference identity checks also surface Crossref/PubMed retraction, expression-of-concern and erratum alerts). CNKI, Wanfang, VIP and other databases require lawful access. Discovery leads do not establish a completed search or full-text retrieval.
- Formal statistical execution needs approval of a specific plan, R or another established engine, and the necessary packages; stdlib helpers cover local PHI screening, Table 1, KM survival, binary DL meta-analysis, diagnostic 2x2/ROC metrics and provenance-bound SVG figures.
- Local exporters produce basic DOCX review drafts (`export_docx.py`) and native Word tracked-changes drafts (`export_tracked_docx.py` with `<w:trackRevisions/>`). Advanced layout, equations and visual inspection still require Word or LibreOffice.
- Numerical, reporting-checklist (6 full-subitem official checklists) and citation checks cover implemented deterministic comparisons; they do not certify semantic support or formal compliance.

## License

The project is source-available under [PolyForm Noncommercial License 1.0.0]({{repo}}/blob/main/LICENSE). Uses outside the license's permitted noncommercial scope require [separate written commercial authorization]({{repo}}/blob/main/COMMERCIAL-LICENSE.md). Third-party materials retain their own terms.

## Feedback and contributions

The maintainer, public source and change history are available on the [GitHub project page]({{repo}}). The "Current status" and "Tools and access" sections above describe which checks run in local scripts and which still depend on the model and human review.

Report your system, host, reproduction steps and de-identified errors in [GitHub Issues]({{repo}}/issues). Improvements to examples, terminology and installation documentation are welcome. Do not upload patient records or credentials.

[Contributing]({{repo}}/blob/main/CONTRIBUTING.md) · [Maintaining the site and releases]({{repo}}/blob/main/docs/maintaining-discoverability.md) · [Generative engine optimization]({{repo}}/blob/main/docs/geo-playbook.md) · [Project descriptions and links]({{repo}}/blob/main/docs/discovery-kit.md)
