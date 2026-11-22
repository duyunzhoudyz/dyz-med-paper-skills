# End-to-End Reproducible Demos

以下 3 套端到端演示全部由 `python -B scripts/build_demos.py` 在纯 Python 标准库环境下零依赖计算生成（零硬编码曲线坐标、零虚构偏倚评判）：

| Demo | 研究类型 | 数据来源说明 | 覆盖工具链 |
|---|---|---|---|
| [01_cohort_strobe](01_cohort_strobe/README.md) | 观察性队列（STROBE-Cohort 34 子项） | 固定随机种子合成生存队列（N=240，无真实患者） | PHI 扫描 → 纯基线 Table 1 (多分类 SMD) → 真实 KM+Log-rank+风险表 SVG → 风格检查 → 保护数一致校验 → 证据审计 → STROBE-Cohort → Word 原生修订稿 |
| [02_bcg_meta_prisma](02_bcg_meta_prisma/README.md) | 系统综述/Meta（PRISMA-2020 42 子项） | Colditz et al., *JAMA* 1994 公开 13 项 BCG 试验数据（含真实纬度与分配方式） | DL 合并+95% PI+纬度亚组+留一法 → 发表级森林图 SVG → 全 13 项诚实 D1/no_information RoB2 图 → PRISMA-2020 |
| [03_diagnostic_stard](03_diagnostic_stard/README.md) | 诊断准确性（STARD-2015 34 子项） | 固定随机种子合成诊断队列（N=300，无真实患者） | 2×2 表 + Wilson 95% CI + PPV/NPV/LR + DeLong AUC 95% CI → ROC 曲线 SVG → 证据审计 → STARD-2015 |
