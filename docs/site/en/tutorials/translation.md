---
title: Chinese–English Medical Translation with Protected Content
description: Translate medical manuscripts, abstracts and reviewer responses while preserving numbers, statistical values, citations, terminology and claim strength.
---
Use `dyz-med-translate` for Chinese-to-English, English-to-Chinese or bilingual versions. Resolve major argument changes separately; translation follows the confirmed source and does not supply missing study facts.

## Prepare the source and constraints

Provide complete passages, an existing glossary, the target language and intended use. Preserve section titles, citation markers, figure and table numbers, statistical units and registration details. For an abstract, include the journal's current format requirements.

> Translate these results into English. Preserve numbers, units, P values, confidence intervals, citation markers and claim strength. Apply consistent terminology and list source uncertainties outside the manuscript instead of inventing corrections.

## Agree on terminology and compare protected content

Record key terms, abbreviations, disease names and outcomes, then check consistency across the manuscript. Compare values and citations after translation; fluent language alone does not establish accuracy.

| Content | Check |
|---|---|
| Numbers and statistics | Added, missing or altered values and units |
| Citations and numbering | Correspondence with the source |
| Claims | Whether uncertainty became certainty or association became causation |
| Terminology | Consistent names for outcomes, variables and populations |

Local protected-content checks can identify some additions or removals. They cannot reliably detect swapped group values, semantic drift or changes in claim strength; human comparison remains necessary.

## Deliver the translation and review trail

Keep the source, translation, glossary, check report and unresolved questions. If further style work is needed, `deai` can improve repetitive prose while preserving facts, evidence and necessary disclosure.

The [Chinese-to-English teaching example]({{repo}}/blob/main/dyz-med-translate/examples/worked-example-cn2en.md) presents the source, translation and separate issues. See [protected-content tool instructions]({{repo}}/blob/main/dyz-med-deai/references/protected-content-cli.md) for implemented checks.

Continue with [manuscript sections]({{root}}tutorials/writing/) or [reviewer responses]({{root}}tutorials/reviewer-response/).
