---
title: Project Status, Validation Scope and License
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

- The built-in online search script covers PubMed. CNKI, Wanfang, VIP and other databases require lawful access. Discovery leads do not establish a completed search or full-text retrieval.
- Statistical execution needs approval of a specific plan, R or another established engine, and the necessary packages. Skill installation does not include those environments.
- The local exporter produces basic DOCX review drafts. Advanced layout, equations, native tracked changes and visual inspection require other tools.
- Numerical and citation checks cover implemented comparisons; they do not certify that a source semantically supports a claim.

## License

The project is source-available under [PolyForm Noncommercial License 1.0.0]({{repo}}/blob/main/LICENSE). Uses outside the license's permitted noncommercial scope require [separate written commercial authorization]({{repo}}/blob/main/COMMERCIAL-LICENSE.md). Third-party materials retain their own terms.

## Feedback and contributions

Report your system, host, reproduction steps and de-identified errors in [GitHub Issues]({{repo}}/issues). Improvements to examples, terminology and installation documentation are welcome. Do not upload patient records or credentials.

[Contributing]({{repo}}/blob/main/CONTRIBUTING.md) · [Maintaining the site and releases]({{repo}}/blob/main/docs/maintaining-discoverability.md) · [Project descriptions and links]({{repo}}/blob/main/docs/discovery-kit.md)
