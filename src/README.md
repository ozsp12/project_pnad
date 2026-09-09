# Source modules

<p align="justify">The <code>src</code> directory contains the canonical scientific workflow of the project. Modules are numbered according to the empirical procedure. Stages 00–02 construct the metadata, refined and trusted data layers; stage 03 applies the complete analytical pipeline independently to both refined and trusted distributions; later stages are reserved for manuscript-specific experiments.</p>

## Scientific pipeline

| Stage | Module | Scientific role | Main output |
| ---: | --- | --- | --- |
| 00 | <code>src/stage_00_build_metadata.py</code> | Consolidates historical PNAD/PNAD Contínua extraction specifications and monetary metadata | <code>data/metadata/df_metadata.xlsx</code> |
| 01 | <code>src/stage_01_build_refined_pnad.py</code> | Harmonizes original survey records into annual income datasets | <code>data/refined/pnad_refined_YYYY.parquet</code> |
| 02 | <code>src/stage_02_build_trusted_pnad.py</code> | Applies deterministic upper-tail treatment and distribution-level validation | <code>data/trusted/pnad_trusted_YYYY.parquet</code> and trusted audit tables |
| 03 | <code>src/stage_03_pnad_analysis.py</code> | Reproduces the complete general analysis independently for refined and trusted datasets | refined and trusted analytical figures and tables |
| 04 | <code>src/stage_04_pereira_ribeiro.py</code> | Reserved for the synthetic LS–MLE manuscript experiments | paper assets |
| 05 | <code>src/stage_05_moura_ribeiro.py</code> | Reserved for the Moura–Ribeiro replication and 1976–2025 extension | paper assets |

## Stage 02: trusted distributions

<p align="justify"><code>stage_02_build_trusted_pnad.py</code> converts the refined annual samples into the trusted analytical datasets. For each year it evaluates <code>z_i = log(1+x_i)</code>, estimates the robust center <code>m = median(z_i)</code> and scaled median absolute deviation <code>s = 1.4826 median|z_i-m|</code>, and defines the upper cutoff <code>x_c = exp(m+ks)-1</code>, with <code>k=6</code> by default. Non-finite and negative values are treated as structural invalids before statistical trimming. The resulting annual distributions must pass deterministic structural and numerical invariants before acceptance.</p>

The annual validation includes:

- non-empty refined, valid and trusted distributions;
- finite and non-negative valid/trusted income;
- consistency of the survey-year field;
- conservation of observation counts;
- finite and non-negative cutoff;
- maximum retained observation not exceeding the cutoff;
- structural-invalid and statistical-outlier counts;
- removal rates;
- before/after mean and median changes;
- detailed raw, valid and trusted distribution summaries.

<p align="justify">The stage writes <code>trusted_trim_audit_annual.csv</code> and <code>trusted_distribution_tests_annual.csv</code> to <code>assets/tables_analysis_trusted</code>.</p>

## Stage 03: refined and trusted analyses

<p align="justify"><code>stage_03_pnad_analysis.py</code> is the script representation of the analytical content derived from <code>notebook/04_analise_pnad_refined.ipynb</code>. The same functions are executed independently on <code>data/refined</code> and <code>data/trusted</code>. This avoids methodological drift between the pre-trimming and post-trimming analyses and makes every difference attributable to the data layer rather than to different analytical code.</p>

| Analysis family | Contents |
| --- | --- |
| Sample diagnostics | annual counts, missing/zero/negative diagnostics and positive support |
| Descriptive statistics | nominal and adjusted mean, median, standard deviation, minima, maxima and sums |
| Histograms | reusable annual histogram datasets and log-frequency panels |
| Geometric binning | geometric edges, counts, arithmetic/geometric means, medians, standard deviations and CCDF |
| Distribution functions | empirical CCDF, log-log representation and <code>ln[ln(100 F(x))]</code> transformation |
| Lorenz geometry | Lorenz curves and detailed geometric construction |
| Inequality | Gini, Pietra, Kolkata and Zanardi indices |
| Concentration | top 10%, top 1% and top 0.1% income shares, plus a combined mean/median and top-share two-panel figure |
| Longitudinal series | annual mean/median and combined/separate inequality-index panels |
| External validation | calculated Gini versus IPEA and World Bank series |
| Gompertz–Pareto | Gompertz LS body fit and Pareto LS tail fit evaluated from the empirical CCDF, cutoff search and annual fitted curves |

<p align="justify">Refined outputs use the <code>refined_analysis_</code> prefix and are written to <code>assets/figures_analysis_refined</code> and <code>assets/tables_analysis_refined</code>. Trusted outputs use the <code>trusted_analysis_</code> prefix and are written to <code>assets/figures_analysis_trusted</code> and <code>assets/tables_analysis_trusted</code>. Tables with exactly one record per survey year use the <code>_annual</code> suffix.</p>

## Synthetic LS–MLE experiment

<p align="justify"><code>synthetic.py</code> is independent of the numbered PNAD stages and contains only the manuscript's synthetic LS-versus-MLE experiment migrated from <code>project_ls_vs_mle</code>. It generates one fixed <code>U(0,1)</code> stream with seed <code>20260902</code>, constructs the deterministic power-law design and its Pareto transform, validates the mathematical identities and nested samples, and writes <code>assets/tables_synthetic/table_1.csv</code> and <code>assets/tables_synthetic/table_2.csv</code>. The experiment uses <code>beta=10</code>, <code>alpha0=2.5</code>, <code>x_t=1</code> and sample sizes 50, 100, 200, 500 and 1000. It does not read PNAD data and does not execute Gompertz–Pareto analyses.</p>
