# Demo 02: BCG Meta-Analysis Workflow (PRISMA-2020)

- **Data source**: Colditz et al., *JAMA* 1994 (13 trials, exact `metafor::dat.bcg` 2×2 counts, latitude `ablat`, and `alloc`).
- **Pooled RR (DL)**: 0.490 (95% CI 0.345–0.695; 95% PI 0.14–1.77), I²=92.1%
- **Latitude subgroups**: ≥35° RR=0.30 (I²=75.4%) vs <35° RR=0.76 (I²=72.0%)
- **Leave-one-out range**: RR 0.45–0.54
- **Forest SVG provenance**: `consistent` (`figures/figure1-bcg-forest.svg`, scope=`hash_and_computation_bound`)
- **RoB 2 D1 matrix (all 13 trials, D2–D5 explicitly `no_information`)**: `figures/figure2-rob2.svg`
- **PRISMA-2020 (42 full subitems)**: `valid` (`qc/prisma-audit-summary.json`)
