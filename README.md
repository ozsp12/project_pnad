# PNAD Longitudinal Income Research

This repository contains the reproducible computational workflow used to study the Brazilian income distribution with PNAD and PNAD Contínua data. The available longitudinal series spans 1976–2025 and is organized into explicit metadata, refined-data, trusted-data, analytical, and publication stages.

## Scientific pipeline

| Stage | Module | Role | Main output |
| ---: | --- | --- | --- |
| 00 | `src/stage_00_build_metadata.py` | Consolidates extraction specifications and monetary metadata | `data/metadata/df_metadata.xlsx` |
| 01 | `src/stage_01_build_refined_pnad.py` | Harmonizes local raw PNAD records into annual income samples | `data/refined/pnad_refined_YYYY.parquet` |
| 02 | `src/stage_02_build_trusted_pnad.py` | Applies deterministic upper-tail treatment and validation | `data/trusted/pnad_trusted_YYYY.parquet` and audit tables |
| 03 | `src/stage_03_pnad_analysis.py` | Runs descriptive, inequality, CCDF and Gompertz–Pareto analyses on refined and trusted data | analytical CSV and PNG assets |
| 05 | `src/stage_05_moura_ribeiro.py` | Builds the Moura Jr.–Ribeiro replication/extension from trusted Stage-03 outputs | publication figures and intermediate paper metrics |
| — | `src/paper_figures.py` | Finalizes publication figures | `assets/figures_paper/` |
| — | `src/paper_tables.py` | Builds the canonical publication tables | `assets/tables_paper/` |

The original fixed-width PNAD microdata are local files of approximately 20 GB and are not versioned under `data/raw/`. The persisted `data/refined/` layer is therefore the normal reproducible starting point inside GitHub. Stage 01 documents the local raw-to-refined reconstruction when the original files are available.

## Stage 03 methodology

Stage 03 is implemented in a single module, `src/stage_03_pnad_analysis.py`. It runs the same general analytical pipeline independently on the refined and trusted layers and includes:

- annual descriptive statistics and diagnostics;
- histograms and geometric bins with ratio `r = 1.10`;
- empirical CCDFs;
- Lorenz curves on a `100 × 100` percentage geometry;
- Gini, Pietra, Kolkata and Zanardi indices;
- top-income shares;
- external Gini comparison with IPEA and World Bank series;
- Gompertz–Pareto regime estimation.

For the Gompertz branch, the empirical CCDF is expressed in percent and linearized as

$$
\ln[\ln F(x)].
$$

The normalization parameter is fixed at

$$
A=\ln[\ln(100)],
$$

and only `B` is estimated by least-squares fitting. The empirical boundaries `x_{G,max}` and `x_{P,min}` are identified separately, after which

$$
x_t=\frac{x_{G,\max}+x_{P,\min}}{2}
$$

when the boundaries differ. Pareto parameters are then estimated by both least-squares fitting and direct maximum likelihood on individual observations satisfying $x_i\ge x_t$.

## Assets

Current generated outputs are organized as follows:

| Directory | Content |
| --- | --- |
| `assets/figures_analysis_refined/` | PNG analytical figures from refined data |
| `assets/figures_analysis_trusted/` | PNG analytical figures from trusted data |
| `assets/tables_analysis_refined/` | Refined analytical CSV tables |
| `assets/tables_analysis_trusted/` | Trusted audit and analytical CSV tables |
| `assets/figures_paper/` | 300 dpi PNG publication figures |
| `assets/tables_paper/` | Four canonical publication CSV tables |


## Dependencies

The repository uses one dependency specification: `requirements.txt`. All direct project and test dependencies are pinned to explicit versions so the same file is used locally and in GitHub Actions.

```bash
pip install -r requirements.txt
```

## Execution

When refined data are already available, the main empirical workflow is:

```bash
python src/stage_02_build_trusted_pnad.py
python src/stage_03_pnad_analysis.py
```

Publication assets are generated from the trusted analytical outputs with:

```bash
python src/stage_05_moura_ribeiro.py
python src/paper_figures.py
python src/paper_tables.py
```

The authoritative implementation is the source code under `src`, and the persistent numerical and graphical outputs are stored under `assets`.
