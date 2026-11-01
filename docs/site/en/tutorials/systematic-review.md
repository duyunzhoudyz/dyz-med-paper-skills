---
title: Systematic Review Screening and PRISMA Flow Diagrams
description: Manage record imports, deduplication, eligibility decisions, extraction and PRISMA counts for systematic reviews, meta-analyses and scoping reviews.
---
Start with an established search protocol and database records. `screening-pipeline` maintains the screening evidence trail, `flowchart` prepares diagrams, and `guideline` checks applicable reporting items.

## Required inputs

Provide the protocol, eligibility criteria, native database exports, accessible full texts and screening arrangements. Identify sources not covered. A PubMed-only search does not establish completed multi-database coverage.

> Import these records with source and deduplication provenance. Build title/abstract and full-text screening tables from the protocol. Preserve independent decisions, disagreement resolution and full-text exclusion reasons. List missing inputs first.

## Keep three levels distinct

| Level | Record |
|---|---|
| Search record | Source query, date, returned count and duplicates |
| Report | Citation, full-text access, eligibility decision and exclusion reason |
| Study | Related reports, extraction and risk-of-bias assessment |

Preserve independent screening judgments and how disagreements were resolved. Multiple reports may describe one study; paper counts and study counts are not interchangeable. Keep missing full texts and pending decisions visible.

## Build and reconcile the flow diagram

Check stage totals and branches before asking `flowchart` to prepare a PRISMA diagram and caption. Count validation does not replace eligibility judgment.

> Derive PRISMA counts from completed screening records, separating records, reports and studies. Identify unfinished screening or retrieval steps rather than reporting them as completed.

## Before a meta-analysis

Clarify extraction, report-to-study relationships and the appropriate bias assessment before choosing a synthesis model or sensitivity analysis. `analyze` handles statistical work only within an approved plan and available environment. Installing the skills does not install statistical software or packages.

[Screening example]({{repo}}/blob/main/dyz-med-screening-pipeline/examples/worked-example.md) · [Flow-diagram example]({{repo}}/blob/main/dyz-med-flowchart/examples/worked-example.md) · [Literature-search guide]({{root}}tutorials/pubmed/)

These are synthetic teaching examples in Chinese, not records of a completed real review.
