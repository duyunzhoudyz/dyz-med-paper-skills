# Demo 01: Observational Cohort Workflow (STROBE-Cohort)

- **Data note**: Deterministic synthetic clinical cohort (seed=20261122, N=240, exponential event hazard + 36m administrative censoring), zero real patient data.
- **PHI check**: `no_obvious_phi_detected` (`qc/phi-report.json`)
- **Baseline-only Table 1**: `results/table1.md` & `results/table1.json` (age, sex, BMI, HbA1c, 3-level CKD stage with Yang & Dalton |SMD|; outcome/follow-up strictly excluded)
- **Exact KM Survival & Log-rank**: Exposed 36m S=88.7% (13 events) vs Unexposed 36m S=68.2% (37 events), Log-rank P=0.0001 (`results/km-results.json`)
- **KM SVG (with Number-at-Risk table & 95% CI bands)**: `consistent` (`figures/figure1-km.svg`, scope=`hash_and_computation_bound`)
- **Style check findings**: v1=3 -> v2=0
- **Protected numbers**: `consistent` (`qc/protected-compare.json`)
- **Evidence audit**: `consistent` (`qc/evidence-audit-report.json`)
- **STROBE-Cohort (34 full subitems)**: `valid` (`qc/strobe-audit-summary.json`)
- **Native Word tracked changes**: `delivery/results-tracked-v1-to-v2.docx` (`<w:trackRevisions/>` enabled, 5 coalesced revision nodes, 4 internal markers stripped)
