# PNAD Longitudinal Income Research

<p align="justify">This repository provides a compact and reproducible scientific workflow for longitudinal research on the Brazilian income distribution using the Pesquisa Nacional por Amostra de Domicílios (PNAD) and PNAD Contínua. The empirical series covers the available surveys from 1976 through 2025 and is organized as a sequence of explicit transformations: historical survey metadata are consolidated, annual microdata are harmonized into refined income samples, refined distributions are subjected to deterministic quality control to produce trusted datasets, and the same analytical pipeline is then applied independently to the refined and trusted layers. The repository is intended primarily as research material and supplementary computational documentation for scientific manuscripts.</p>

## Data and analyses

<p align="justify">The original PNAD microdata are local fixed-width text files totaling approximately 20 GB and are deliberately not versioned under <code>data/raw</code>. The current <code>data/refined</code> layer was materialized outside the GitHub environment from those local microdata and is treated as the persistent input for subsequent stages. <code>src/stage_01_build_refined_pnad.py</code> documents and implements the raw-to-refined transformation when that extraction must be reproduced locally.</p>

<p align="justify">Survey definitions are not assumed to be constant through time. Historical PNAD and PNAD Contínua use different variables, layouts and survey regimes, and these differences remain explicit in the metadata. The refined layer preserves the harmonized pre-trimming distributions, while the trusted layer applies the documented log-MAD upper-tail treatment and distribution-level validation. Stage 03 reproduces the same analysis on both layers so that the consequences of the trusted-data treatment remain directly auditable.</p>

The analytical workflow includes:

- annual sample diagnostics: total observations, finite observations, NaN, zero and negative counts;
- nominal income statistics: positive minimum, maximum, mean, median, standard deviation and aggregate income;
- income normalization to 2025 US dollars using the monetary metadata;
- adjusted-income statistics: minimum, maximum, mean, median, standard deviation and aggregate income;
- linear histograms and persistent histogram-bin datasets;
- geometric binning with bin limits, geometric centers, counts, arithmetic means, geometric means, medians, standard deviations and CCDF values;
- empirical complementary cumulative distribution functions (CCDF);
- log-log CCDF representations for upper-tail inspection;
- the Gompertz diagnostic transformation <code>ln[ln(100 F(x))]</code>;
- Lorenz curves on a common population-share grid;
- Gini coefficient;
- Pietra index and its geometric construction;
- Kolkata index and Kolkata percentage;
- Zanardi index;
- income shares of the top 10%, top 1% and top 0.1%;
- temporal evolution of mean and median adjusted income;
- temporal evolution of Gini, Pietra, Kolkata and Zanardi indices;
- comparison of the calculated Gini series with IPEA and World Bank reference series;
- Gompertz least-squares body fits;
- Pareto least-squares upper-tail fits;
- admissible cutoff search separating Gompertz and Pareto regimes;
- annual fitted-regime diagnostics, parameters, fit quality and persistent fitted curves.

## Assets

<p align="justify">Generated research outputs are stored under <code>assets</code>. Refined and trusted analytical artifacts are deliberately separated so that the effect of the trusted-data treatment can be inspected directly. Analytical figures are SVG evidence artifacts; analytical tables are CSV files; publication-specific outputs remain isolated in the paper directories. Tables consolidated to exactly one record per survey year use the <code>_annual</code> suffix.</p>

| Directory | Content |
| --- | --- |
| <code>assets/figures_analysis_refined/</code> | Analytical figures generated from <code>data/refined</code> |
| <code>assets/figures_analysis_trusted/</code> | Analytical figures generated from <code>data/trusted</code> |
| <code>assets/tables_analysis_refined/</code> | Analytical tables generated from <code>data/refined</code> |
| <code>assets/tables_analysis_trusted/</code> | Trusted-data audits and analytical tables generated from <code>data/trusted</code> |
| <code>assets/figures_paper/</code> | Figures explicitly selected for manuscripts |
| <code>assets/tables_paper/</code> | Tables explicitly selected for manuscripts |

## Execution

<p align="justify">The repository uses a deliberately small Python environment. Rebuilding from original microdata requires the local PNAD files expected by stage 01. When refined datasets are already available, execution may begin at stage 02. Stage 03 analyzes both refined and trusted distributions and regenerates both analytical asset families.</p>

```bash
pip install -r requirements.txt
python src/stage_02_build_trusted_pnad.py
python src/stage_03_pnad_analysis.py
```

<p align="justify">The original notebooks are retained temporarily as methodological provenance while the source modules are validated against their outputs. The authoritative computational workflow is the sequential source code under <code>src</code>, and the authoritative numerical outputs are the corresponding persistent assets.</p>
