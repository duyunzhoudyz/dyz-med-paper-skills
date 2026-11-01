# 32 Medical Writing & Research Agent Skills: Complete Catalog

[中文首页](../README.md) · [English](../README_EN.md) · [中文索引](skills.md) · [English catalog](skills.en.md)

Choose by your current task. Each entry includes inputs, outputs and a synthetic teaching example, not a published study or user testimonial.

Install complete skill directories in Claude Code, Codex or another Agent Skills host. See [validation scope](../README_EN.md#status).

## Starting points and project state

| Skill / Task | Purpose | Minimum input | Main output | Example |
|---|---|---|---|---|
| [Research questions](../dyz-med-ideate/SKILL.md)<br>dyz-med-ideate | Use for clinical research ideation, PICO questions and feasibility exploration. | Clinical observations, interests and constraints | Candidate questions and feasibility routes | [示例 / Example](../dyz-med-ideate/examples/示例-社区获得性肺炎选题推导.md) |
| [Project setup](../dyz-med-init/SKILL.md)<br>dyz-med-init | Use to initialize a medical manuscript project from an established study. | Research question, design and available materials | Project structure and material gaps | [示例 / Example](../dyz-med-init/examples/示例-老年髋部骨折队列研究立项.md) |
| [Manuscript diagnosis](../dyz-med-manuscript-diagnose/SKILL.md)<br>dyz-med-manuscript-diagnose | Use for read-only manuscript assessment and revision priorities. | Draft, abstract or rejection feedback | Diagnosis and prioritized next steps | [示例 / Example](../dyz-med-manuscript-diagnose/examples/worked-example-rejected-manuscript.md) |
| [Workflow navigation](../dyz-med-orchestrator/SKILL.md)<br>dyz-med-orchestrator | Use to review medical research workflow progress and recommend the next task. | Paper workspace and current request | Progress map and next-step recommendation | [示例 / Example](../dyz-med-orchestrator/examples/虚构项目进度地图样例.md) |
| [Project state](../dyz-med-passport/SKILL.md)<br>dyz-med-passport | Use internally to maintain confirmed project facts, provenance and artifact versions. | Confirmed facts, artifacts and approvals | Traceable project state | [示例 / Example](../dyz-med-passport/examples/虚构项目状态文件样例.yaml) |

## Study design and literature evidence

| Skill / Task | Purpose | Minimum input | Main output | Example |
|---|---|---|---|---|
| [Mechanisms and causality](../dyz-med-mechanism/SKILL.md)<br>dyz-med-mechanism | Use to examine causal reasoning, mechanism hypotheses and study logic. | Research question, design and evidence | Mechanism chain, gaps and validation plan | [示例 / Example](../dyz-med-mechanism/examples/示例-炎症因子与术后认知功能障碍机制推导.md) |
| [Data adequacy](../dyz-med-data-adequacy/SKILL.md)<br>dyz-med-data-adequacy | Use to assess medical research data adequacy before statistical analysis. | Data dictionary, design and authorized data | Adequacy report and defensible analysis scope | [示例 / Example](../dyz-med-data-adequacy/examples/worked-example.md) |
| [Study registration](../dyz-med-registration/SKILL.md)<br>dyz-med-registration | Use to check trial registration records against protocols and manuscripts. | Registry identifier, protocol and manuscript | Registration comparison and unresolved differences | [示例 / Example](../dyz-med-registration/examples/示例-降压药物RCT注册核查.md) |
| [Medical literature search](../dyz-med-cnki/SKILL.md)<br>dyz-med-cnki | Use for PubMed and Chinese medical literature search; database execution requires access. | Question, databases and eligibility scope | Queries, search log and candidate references | [示例 / Example](../dyz-med-cnki/examples/worked-example.md) |
| [Critical literature reading](../dyz-med-key-literature/SKILL.md)<br>dyz-med-key-literature | Use for critical appraisal and synthesis of available full-text medical literature. | Candidate papers and accessible full texts | Paper briefs and evidence map | [示例 / Example](../dyz-med-key-literature/examples/worked-example.md) |
| [Systematic review screening](../dyz-med-screening-pipeline/SKILL.md)<br>dyz-med-screening-pipeline | Use for systematic review and meta-analysis screening, extraction and PRISMA counts. | Search records, screening protocol and full texts | Screening log, extraction tables and counts | [示例 / Example](../dyz-med-screening-pipeline/examples/worked-example.md) |
| [Claim–evidence audit](../dyz-med-evidence-audit/SKILL.md)<br>dyz-med-evidence-audit | Use to audit manuscript claims against cited literature and study evidence. | Manuscript, cited sources and study results | Claim–evidence matrix and located issues | [示例 / Example](../dyz-med-evidence-audit/examples/worked-example.md) |

## Statistical analysis and figures

| Skill / Task | Purpose | Minimum input | Main output | Example |
|---|---|---|---|---|
| [Biostatistical analysis](../dyz-med-analyze/SKILL.md)<br>dyz-med-analyze | Use for biostatistical analysis planning and approved R or other local statistical execution. | Authorized data, dictionary and research question | Analysis plan, scripts and recorded results | [示例 / Example](../dyz-med-analyze/examples/worked-example-cohort.md) |
| [Clinical interpretation](../dyz-med-interpret/SKILL.md)<br>dyz-med-interpret | Use to interpret existing statistical results and clinical importance without rerunning models. | Existing results and sourced clinical thresholds | Outcome-level interpretation and calibrated wording | [示例 / Example](../dyz-med-interpret/examples/worked-example.md) |
| [Sensitivity analysis](../dyz-med-sensitivity/SKILL.md)<br>dyz-med-sensitivity | Use for approved sensitivity analyses and robustness comparisons of existing findings. | Primary results, assumptions and approved scope | Robustness comparisons and limitations | [示例 / Example](../dyz-med-sensitivity/examples/worked-example.md) |
| [Manuscript tables and figures](../dyz-med-figures-tables/SKILL.md)<br>dyz-med-figures-tables | Use for medical manuscript tables, statistical figures and text–figure consistency. | Executed analysis outputs and provenance | Figures, tables, captions and consistency checklist | [示例 / Example](../dyz-med-figures-tables/examples/worked-example.md) |
| [Study flow diagrams](../dyz-med-flowchart/SKILL.md)<br>dyz-med-flowchart | Use for PRISMA, CONSORT and observational study flow diagrams from traceable counts. | Study flow, screening records and counts | Flow diagram, caption and count checks | [示例 / Example](../dyz-med-flowchart/examples/worked-example.md) |

## Argument and manuscript writing

| Skill / Task | Purpose | Minimum input | Main output | Example |
|---|---|---|---|---|
| [Manuscript writing plan](../dyz-med-writing-plan/SKILL.md)<br>dyz-med-writing-plan | Use for medical manuscript argument maps and paragraph-level writing plans. | Question, verified results and literature | Argument map and section outline | [示例 / Example](../dyz-med-writing-plan/examples/示例-他汀类药物队列论证地图构建.md) |
| [Introduction writing](../dyz-med-introduction/SKILL.md)<br>dyz-med-introduction | Use to draft or revise a medical manuscript introduction and research rationale. | Question, outline and verified literature | Introduction draft and rationale | [示例 / Example](../dyz-med-introduction/examples/worked-example-knowledge-gap.md) |
| [Methods writing](../dyz-med-methods/SKILL.md)<br>dyz-med-methods | Use to write methods sections from actual study procedures and approved analysis plans. | Protocol, execution records and analysis plan | Methods draft and missing-information list | [示例 / Example](../dyz-med-methods/examples/示例-队列研究方法部分撰写.md) |
| [Results writing](../dyz-med-results/SKILL.md)<br>dyz-med-results | Use to write results sections while preserving verified effect estimates and numerical provenance. | Verified statistical outputs, tables and figures | Results draft and numerical traceability | [示例 / Example](../dyz-med-results/examples/worked-example-xelox-dfs.md) |
| [Discussion writing](../dyz-med-discussion/SKILL.md)<br>dyz-med-discussion | Use to draft or revise medical discussions, evidence comparisons and limitations. | Verified results, design and literature | Discussion draft and limits of claims | [示例 / Example](../dyz-med-discussion/examples/示例-他汀类药物与骨密度机制论断的证据分级.md) |
| [Titles and abstracts](../dyz-med-abstract/SKILL.md)<br>dyz-med-abstract | Use for medical manuscript titles, structured abstracts and bilingual abstracts. | Completed manuscript, verified results and journal rules | Title, abstract and keywords | [示例 / Example](../dyz-med-abstract/examples/worked-example-zhonghua-trimming.md) |
| [Full manuscript drafting](../dyz-med-write/SKILL.md)<br>dyz-med-write | Use for explicitly requested full manuscript drafts or coherence editing across completed sections. | Confirmed research materials or completed sections | Full draft or coordinated revision | [示例 / Example](../dyz-med-write/examples/worked-example-final-coherence-check.md) |

## Translation, revision and delivery

| Skill / Task | Purpose | Minimum input | Main output | Example |
|---|---|---|---|---|
| [Medical translation](../dyz-med-translate/SKILL.md)<br>dyz-med-translate | Use for Chinese–English medical translation with numerical, citation and terminology preservation. | Source text, glossary and target language | Translation, glossary and protected-content checks | [示例 / Example](../dyz-med-translate/examples/worked-example-cn2en.md) |
| [Academic style editing](../dyz-med-deai/SKILL.md)<br>dyz-med-deai | Use to improve repetitive academic prose while preserving facts and disclosure; not detector evasion. | Draft and style preferences | Edited prose and change notes | [示例 / Example](../dyz-med-deai/examples/worked-example-before-after.md) |
| [Reporting guidelines](../dyz-med-guideline/SKILL.md)<br>dyz-med-guideline | Use to check applicable medical reporting guidelines including STROBE, CONSORT and PRISMA. | Manuscript, study type and applicable guideline | Coverage checklist and located recommendations | [示例 / Example](../dyz-med-guideline/examples/worked-example-consort.md) |
| [Pre-submission review](../dyz-med-review/SKILL.md)<br>dyz-med-review | Use for simulated pre-submission peer review and located revision recommendations. | Near-complete manuscript and supporting files | Simulated review and revision recommendations | [示例 / Example](../dyz-med-review/examples/worked-example-review-council.md) |
| [Revision and reviewer responses](../dyz-med-revision/SKILL.md)<br>dyz-med-revision | Use for manuscript revision, response to reviewers and journal resubmission preparation. | Manuscript, reviewer comments and completed changes | Revision, point-by-point response and change locations | [示例 / Example](../dyz-med-revision/examples/worked-example-reviewer-response.md) |
| [Journal selection](../dyz-med-journal-finder/SKILL.md)<br>dyz-med-journal-finder | Use for medical journal selection based on verified scope, requirements and fees. | Topic, article type, budget and timeline | Tiered journal shortlist and verified rationale | [示例 / Example](../dyz-med-journal-finder/examples/示例-2型糖尿病队列研究期刊推荐.md) |
| [Word review draft export](../dyz-med-export/SKILL.md)<br>dyz-med-export | Use to assemble basic DOCX review drafts; advanced formatting requires suitable external tools. | Completed sections, figures, tables and references | Basic DOCX review draft and export report | [示例 / Example](../dyz-med-export/examples/虚构稿件导出流程示例.md) |
| [Submission package](../dyz-med-submit/SKILL.md)<br>dyz-med-submit | Use to prepare local cover letters and journal submission packages; external submission needs authorization. | Manuscript, confirmed author details and journal rules | Submission package and confirmation checklist | [示例 / Example](../dyz-med-submit/examples/虚构课题投稿材料生成示例.md) |

`passport` primarily supports other skills internally; use `orchestrator` to review progress. Statistical execution, online databases and advanced formatting require the relevant software, access and materials.

<!-- Generated from docs/catalog.json by scripts/build_docs.py; edit the catalog, then use --sync-indexes. -->
