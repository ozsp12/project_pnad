# PNAD Longitudinal Income Research

This repository contains the reproducible computational workflow used to study the Brazilian income distribution with PNAD and PNAD Contínua data. The longitudinal metadata span 1976–2025, including years without a survey, and the empirical workflow is organized into explicit metadata, refined-data, trusted-data, analytical, cross-year analytics, and publication stages.

## Scientific pipeline

| Stage | Module | Role | Main output |
| ---: | --- | --- | --- |
| 00 | `src/stage_00_build_metadata.py` | Consolidates extraction specifications and monetary metadata | `data/metadata/df_metadata.xlsx` |
| 01 | `src/stage_01_build_refined_pnad.py` | Harmonizes local raw PNAD records into annual income samples | `data/refined/pnad_refined_YYYY.parquet` |
| 02 | `src/stage_02_build_trusted_pnad.py` | Applies deterministic upper-tail treatment and validation | `data/trusted/pnad_trusted_YYYY.parquet` and audit tables |
| 03 | `src/stage_03_pnad_analysis.py` | Runs descriptive, inequality, CCDF, and Gompertz–Pareto analyses on refined and trusted data | analytical CSV and PNG assets |
| 04 | `src/stage_04_build_analytic_pnad.py` | Concatenates all trusted annual samples into one validated cross-year Parquet | `data/analytics/pnad_analytics_all.parquet` |
| 05 | `src/stage_05_moura_ribeiro.py` | Builds trusted-data publication figures and parameter-uncertainty products | `assets/figures_paper/` and bootstrap metrics |
| — | `src/paper_tables.py` | Builds the four canonical publication tables from current trusted Stage-03 outputs | `assets/tables_paper/` |

The original fixed-width PNAD microdata are local files of approximately 20 GB and are not versioned under `data/raw/`. The persisted `data/refined/` layer is therefore the normal reproducible starting point inside GitHub. Stage 01 documents the local raw-to-refined reconstruction when the original files are available.

The notebooks under `notebook/` are retained intentionally as historical and pedagogical artifacts. The authoritative implementation of the current workflow is the source code under `src/`.

## Stage 03 methodology

Stage 03 is implemented in a single module, `src/stage_03_pnad_analysis.py`. It runs the same analytical pipeline independently on the refined and trusted layers and includes:

- annual descriptive statistics and diagnostics;
- histograms and geometric bins with ratio `r = 1.10`;
- empirical CCDFs;
- Lorenz curves and inequality geometry;
- Gini, Pietra, Kolkata, and Zanardi indices;
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

and only `B` is estimated by least squares. The empirical boundaries `x_{G,max}` and `x_{P,min}` are identified separately, after which

$$
x_t=\frac{x_{G,\max}+x_{P,\min}}{2}
$$

when the boundaries differ. Pareto parameters are then estimated by both least-squares fitting and direct maximum likelihood on individual observations satisfying $x_i\ge x_t$.

## Stage 04 analytics dataset

Stage 04 reads only `data/trusted/pnad_trusted_YYYY.parquet`. It performs no new statistical transformation. It validates year consistency, finite non-negative trusted income, and annual schema compatibility, then writes the vertically concatenated dataset to `data/analytics/pnad_analytics_all.parquet`.

Each survey year is stored as one Parquet row group, preserving efficient year-level filtering while providing a single file for longitudinal and cross-year analyses. Stage 04 is automated independently from Stage 03, so rebuilding the consolidated analytics dataset does not require rerunning the empirical analysis.

## Stage 05 publication layer

Stage 05 consumes canonical trusted Stage-03 outputs and trusted annual microdata. Its Gompertz uncertainty calculation preserves the model normalization assumption: $A=\ln[\ln(100)]$ remains fixed in every bootstrap resample, and only $B$ is re-estimated. Pareto least-squares and direct-MLE uncertainty calculations are retained separately.

## Automated workflows

The repository separates the main automated products by responsibility:

- `Run PNAD analysis` executes Stage 03 and commits only analytical tables and figures;
- `Build PNAD analytics dataset` executes Stage 04 independently and commits only `data/analytics/`;
- `Build paper assets` executes Stage 05 and `paper_tables.py`, validates publication figures and tables, and commits the canonical paper assets;
- `Unit tests` compiles `src/` and runs the complete `pytest` suite.

This separation prevents a Stage-04-only change from forcing a complete Stage-03 rerun.

## Assets

Current generated outputs are organized as follows:

| Directory | Content |
| --- | --- |
| `assets/figures_analysis_refined/` | PNG analytical figures from refined data |
| `assets/figures_analysis_trusted/` | PNG analytical figures from trusted data |
| `assets/tables_analysis_refined/` | Refined analytical CSV tables |
| `assets/tables_analysis_trusted/` | Trusted audit and analytical CSV tables |
| `assets/figures_paper/` | 300 dpi trusted-data publication figures |
| `assets/tables_paper/` | Four canonical publication CSV tables |

## Dependencies and tests

The repository uses one dependency specification, `requirements.txt`. All direct runtime and test dependencies are pinned to explicit versions so the same environment definition is used locally and in GitHub Actions.

```bash
pip install -r requirements.txt
```

The unit-test suite now covers metadata construction in Stage 00, raw-record parsing and harmonization in Stage 01, trusted-data trimming and invariants in Stage 02, Stage-03 mathematical and Gompertz–Pareto routines, Stage-04 concatenation, and the publication figure/table layer.

## Execution

When refined data are already available, the main empirical workflow is:

```bash
python src/stage_02_build_trusted_pnad.py
python src/stage_03_pnad_analysis.py
python src/stage_04_build_analytic_pnad.py
```

Stage 04 may also be run independently whenever only the consolidated trusted analytics file must be rebuilt.

Publication assets are generated from the trusted analytical outputs with:

```bash
python src/stage_05_moura_ribeiro.py
python src/paper_tables.py
```

The authoritative implementation is the source code under `src`, and the persistent numerical, graphical, and analytical data products are stored under `assets/` and `data/analytics/`.
