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

## Standalone synthetic experiment and paper replication

<p align="justify"><code>src/synthetic.py</code> is the currently implemented standalone LS–MLE synthetic experiment. It is independent of stages 00–03 and does not read PNAD data. It regenerates <code>assets/tables_synthetic/table_1.csv</code> and <code>assets/tables_synthetic/table_2.csv</code>; <code>assets/figures_synthetic/</code> is reserved for synthetic figures.</p>

<p align="justify"><code>src/stage_05_moura_ribeiro.py</code> is the implemented manuscript-specific replication and extension of Moura Jr. & Ribeiro (2009) through 2025. It consumes the refined analytical outputs from stage 03, uses <code>data/metadata/df_metadata.xlsx</code> as the canonical monetary metadata source, and reads the persistent World Bank/WDI GDP-growth series from <code>data/auxiliary/gdp_growth_brazil_1978_2025.csv</code>. Paper figures are stored in SVG format only.</p>

## Assets

<p align="justify">Generated research outputs are stored under <code>assets</code>. Refined and trusted analytical artifacts are deliberately separated so that the effect of the trusted-data treatment can be inspected directly. Analytical figures are SVG evidence artifacts; analytical tables are CSV files; publication-specific outputs remain isolated in the paper directories. Tables consolidated to exactly one record per survey year use the <code>_annual</code> suffix.</p>

| Directory | Content |
| --- | --- |
| <code>assets/figures_analysis_refined/</code> | Analytical figures generated from <code>data/refined</code> |
| <code>assets/figures_analysis_trusted/</code> | Analytical figures generated from <code>data/trusted</code> |
| <code>assets/tables_analysis_refined/</code> | Analytical tables generated from <code>data/refined</code> |
| <code>assets/tables_analysis_trusted/</code> | Trusted-data audits and analytical tables generated from <code>data/trusted</code> |
| <code>assets/figures_synthetic/</code> | Reserved for standalone synthetic figures |
| <code>assets/tables_synthetic/</code> | Tables 1 and 2 from <code>src/synthetic.py</code> |
| <code>assets/figures_paper/</code> | SVG figures generated by the implemented Moura–Ribeiro replication |
| <code>assets/tables_paper/</code> | Tables and diagnostics selected for manuscripts |

## Execution

<p align="justify">The repository uses a deliberately small Python environment. <code>requirements.txt</code> remains the ordinary installation specification; <code>requirements-lock.txt</code> records a fixed Python 3.12 runtime snapshot for reproducibility without changing the existing workflow installation policy. Rebuilding from original microdata requires the local PNAD files expected by stage 01. When refined datasets are already available, execution may begin at stage 02. Stage 03 analyzes both refined and trusted distributions and regenerates both analytical asset families.</p>

```bash
pip install -r requirements.txt
python src/stage_02_build_trusted_pnad.py
python src/stage_03_pnad_analysis.py
```

The independent synthetic experiment is run with:

```bash
python src/synthetic.py
```

The Moura–Ribeiro paper assets are generated from the existing refined analysis with:

```bash
python src/stage_05_moura_ribeiro.py
```

<p align="justify">The original notebooks are retained temporarily as methodological provenance while the source modules are validated against their outputs. The authoritative computational workflow is the source code under <code>src</code>, and the authoritative numerical outputs are the corresponding persistent assets.</p>
