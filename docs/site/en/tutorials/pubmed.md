---
title: PubMed and Chinese Medical Literature Search
description: Build a reproducible medical literature search, record actual database coverage, import reference records and prepare critical reading of key papers.
---
`dyz-med-cnki` is the literature-search skill's directory name. Its scope includes PubMed and Chinese medical sources. The built-in online script covers PubMed; CNKI, Wanfang, VIP and other sources require suitable tools and access.

## Define the question and scope

Provide the population, exposure or intervention, comparator, outcomes and study designs, together with date, language and database limits. A review project also needs a search protocol and eligibility criteria.

> Design a PubMed and Chinese-database search for this question. Identify core concepts, synonyms and subject headings to verify. Record actual access for each source and list sources that could not be searched.

## Execute and preserve the record

1. Agree on concepts and queries, then execute in accessible databases.
2. Save database names, search dates, actual queries, applied limits and result counts.
3. Export native records with provenance. Local import tools support RIS, literal BibTeX, NBIB and PubMed XML.
4. Preserve merge relationships during deduplication. Keep candidate discovery separate from formal systematic-review screening.

Web leads without database execution remain `discovery_only`. Abstract-only access does not count as full-text critical reading.

## Move from candidates to evidence

Use `dyz-med-key-literature` to read accessible full texts in a structured way: design, population, effect estimates, limitations and relevance to the question. Include contradictory evidence and applicability differences alongside supporting studies.

> Select key studies from the verified candidate pool. Distinguish guidelines, reviews, primary studies and contradictory evidence. State which sources were read in full and which are abstract-only.

Outputs include a search plan, execution log, reference pool, deduplication record and paper briefs. See the synthetic [search example]({{repo}}/blob/main/dyz-med-cnki/examples/worked-example.md) and [local literature tool instructions]({{repo}}/blob/main/dyz-med-cnki/references/literature-cli.md), both in Chinese.

For reviews, continue to [screening and PRISMA]({{root}}tutorials/systematic-review/). With reliable evidence ready, proceed to [manuscript writing]({{root}}tutorials/writing/).
