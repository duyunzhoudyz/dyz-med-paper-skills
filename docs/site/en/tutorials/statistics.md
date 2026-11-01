---
title: Interpreting Medical Statistics and Clinical Importance
description: Separate data adequacy, statistical execution, result interpretation and sensitivity analysis when discussing effect sizes, uncertainty and clinical importance.
---
The statistical tasks have distinct owners: `data-adequacy` assesses what data can support; `analyze` plans and executes approved analyses; `interpret` explains existing results; and `sensitivity` examines specific changes in assumptions.

## Choose a starting point

| What you have | Appropriate task |
|---|---|
| Raw data only | Inspect structure, missingness and adequacy |
| A need for primary analysis | Prepare a reviewable plan before execution |
| Existing outputs | Interpret effects, intervals and clinical importance |
| Concern about an assumption | Define the uncertainty and plan sensitivity work |

## Interpret existing results

Provide effect scales, units, reference groups, confidence intervals, populations and model details. Clinical-importance discussion also needs prespecified, sourced thresholds; record missing thresholds rather than inventing them.

> Interpret these existing results without refitting models. For each outcome, explain effect size and interval uncertainty, separating statistical evidence from clinical importance. State where a clinical threshold has not been established.

Check direction, units and reference groups. A nonsignificant finding is not automatically evidence of no effect, and a P value alone does not replace interpretation of effect estimates and uncertainty.

## If additional analysis is needed

Identify the concrete question, such as a missing-data assumption or analysis-population change. Specify alternative assumptions, required inputs, outputs and execution conditions in a plan, then work within the approved scope. Preserve scripts, logs, diagnostics and result versions.

## Hand off to writing

Deliver an outcome-level interpretation table, threshold questions, calibrated wording and proposed additional analyses. `results` writes from verified numbers; `discussion` considers design and evidence; `figures-tables` checks consistency across displays and prose.

[Interpretation example]({{repo}}/blob/main/dyz-med-interpret/examples/worked-example.md) · [Analysis example]({{repo}}/blob/main/dyz-med-analyze/examples/worked-example-cohort.md) · [Manuscript writing]({{root}}tutorials/writing/)

These synthetic examples are teaching materials. Researchers and statistical professionals must review outputs; tool results do not certify study conclusions.
