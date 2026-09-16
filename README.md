# PNAD Longitudinal Income Research

This repository contains the reproducible computational workflow used to study the Brazilian income distribution with PNAD and PNAD Contínua data. Longitudinal metadata span 1976–2025, including years without a survey. The workflow separates data construction, statistical analysis, cross-year analytics, scientific reproduction diagnostics, and publication assets.

## Scientific pipeline

| Stage | Module | Role | Main output |
| ---: | --- | --- | --- |
| 00 | `src/stage_00_build_metadata.py` | Consolidates extraction specifications and monetary metadata | `data/metadata/df_metadata.xlsx` and `data/metadata/df_metadata.csv` |
| 01 | `src/stage_01_build_refined_pnad.py` | Harmonizes local raw PNAD records into annual income samples | `data/refined/pnad_refined_YYYY.parquet` |
| 02 | `src/stage_02_build_trusted_pnad.py` | Applies deterministic upper-tail treatment and validation | `data/trusted/pnad_trusted_YYYY.parquet` and validation audits |
| 03 | `src/stage_03_pnad_analysis.py` | Runs descriptive, inequality, CCDF, Gompertz–Pareto, bootstrap and Moura Jr.–Ribeiro reproduction analyses on refined and trusted data | analytical CSV and PNG assets |
| 04 | `src/stage_04_build_analytic_pnad.py` | Concatenates trusted annual samples into one validated cross-year Parquet | `data/analytics/pnad_analytics_all.parquet` |
| 05 | `src/stage_05_publication.py` | Builds the complete paper-facing figure and table set from persisted Stage-03 results | `assets/figures_paper/` and `assets/tables_paper/` |

The original fixed-width PNAD microdata are local files of approximately 20 GB and are not versioned under `data/raw/`. The persisted `data/refined/` layer is therefore the normal reproducible starting point inside GitHub. Source code under `src/` is authoritative.

## Trusted upper-tail treatment

Stage 02 uses the annual log-MAD upper-tail rule after structural cleaning. For 1985 and 1990 only, the trusted layer additionally applies the empirical 99th-percentile cutoff, with the effective threshold defined as `min(log-MAD, p99)`. The exception is based exclusively on within-year tail behavior and leverage; IPEA and World Bank Gini series are not used to choose or tune the cutoff. The untrimmed observations remain available in the refined layer. If the resulting trusted tail does not retain the canonical minimum number of Pareto bins, Stage 03 records the Pareto regime as unsupported rather than relaxing the fitting criterion.

## Stage 03 methodology and analytical layers

Stage 03 applies the same analytical pipeline independently to `refined` and `trusted`. The `refined` layer is the baseline and the `trusted` layer is the benchmark. Their analytical directories must remain structurally identical: the same filenames, the same column schemas, and the same metadata schema.

All distributional statistics in this repository are computed on the annual PNAD and PNAD Contínua samples with equal observation weights. Survey expansion weights are intentionally not applied. The reported quantities therefore characterize the empirical distributions of the analyzed samples rather than design-weighted official population estimates. External IPEA and World Bank Gini series are used only as external validation references and are not treated as estimand-equivalent targets.

The six canonical scientific CSVs in both `assets/tables_analysis_refined/` and `assets/tables_analysis_trusted/` are:

- `statistics_annual.csv`;
- `geometric_bins.csv`;
- `gompertz_annual.csv`;
- `pareto_annual.csv`;
- `gompertz_pareto_curves.csv`;
- `lorenz.csv`.

Each directory additionally contains `metadata.csv`, a data dictionary with table-level descriptions and column-level definitions, units, and sources.

Stage 03 includes descriptive statistics, geometric bins with ratio `r = 1.10`, empirical CCDFs, Lorenz geometry, inequality indices, top-income shares, external Gini validation, and Gompertz–Pareto regime estimation. The current Gompertz model fixes

$$
A=\ln[\ln(100)]
$$

and estimates only `B` by least squares. A free-intercept fit is retained as a diagnostic and for comparison with the 2009 methodology. Pareto parameters are estimated by log-log least squares and direct maximum likelihood after determining the transition threshold. Gompertz–Pareto continuity at the transition is used to determine the Pareto amplitude for the direct-MLE branch.

`stage_03_pnad_analysis.py` also contains the uncertainty calculations required to reproduce Moura Jr. and Ribeiro, *Eur. Phys. J. B* **67**, 101–120 (2009): fixed-`A` Gompertz bootstrap uncertainty for `B`, free-intercept Gompertz bootstrap diagnostics for `A` and `B`, Pareto LSF/MLE bootstrap uncertainties, the likelihood-width uncertainty for the MLE exponent, exponential-versus-Gompertz diagnostics, and regime income shares. These quantities are persisted directly in `gompertz_annual.csv` and `pareto_annual.csv`; separate `moura_ribeiro_bootstrap_annual.csv` and `moura_ribeiro_reproduction_annual.csv` files are not used.

The numerical values reported in the 2009 paper remain available in `data/auxiliary/moura_ribeiro_2009_reference.csv` as a historical reference dataset.

## Stage 04 analytics dataset

Stage 04 reads only `data/trusted/pnad_trusted_YYYY.parquet`. It introduces no statistical transformation: it validates year consistency, finite non-negative income and schema compatibility, then writes `data/analytics/pnad_analytics_all.parquet`. Each survey year occupies one Parquet row group. Stage 04 has an independent workflow and does not require Stage 03 to be rerun.

## Stage 05 publication layer

Stage 05 is presentation-only. `stage_05_publication.py` contains the figure and table-formatting features and consumes persisted Stage-03 scientific results. Statistical estimation, bootstrap, likelihood calculations and top-income-band aggregation belong to Stage 03.

The paper table set contains:

- `table_01_gompertz_annual.csv`;
- `table_02_pareto_annual.csv`;
- `table_03_economic_inequality_annual.csv`;
- `table_04_metadata.csv`.

Because the current model fixes `A`, Table 01 does not report a standard error for fixed `A`. The free-intercept `A` and `B` estimates and their bootstrap uncertainties are retained explicitly as the 2009-method diagnostics. Table 04 is the data dictionary for the paper-facing tables and includes both table-level and column-level descriptions.

## Automated workflows

- `Build metadata` executes Stage 00, validates that the generated XLSX and CSV match `build_metadata_df()`, and commits both metadata artifacts when they change.
- `Run PNAD analysis` executes the canonical Stage-03 analysis, consolidates the Moura–Ribeiro diagnostics into the annual tables, validates baseline/benchmark schema symmetry, and commits analytical assets.
- `Build PNAD analytics dataset` executes Stage 04 independently and commits only `data/analytics/`.
- `Build paper assets` refreshes the consolidated Stage-03 diagnostics, executes the canonical Stage-05 publication entry point, validates figures/tables, and commits paper assets on `main`.
- `Unit tests` compiles `src/` and runs the complete `pytest` suite.

## Assets

| Directory | Content |
| --- | --- |
| `assets/figures_analysis_refined/` | analytical figures from the refined baseline |
| `assets/figures_analysis_trusted/` | analytical figures from the trusted benchmark |
| `assets/tables_analysis_refined/` | six canonical baseline tables plus `metadata.csv` |
| `assets/tables_analysis_trusted/` | six canonical benchmark tables plus `metadata.csv` |
| `assets/figures_paper/` | 300 dpi paper figures |
| `assets/tables_paper/` | four canonical paper-facing CSV tables |

## Dependencies and execution

The reproducible environment targets **Python 3.12**, matching the GitHub Actions workflows. All direct runtime and test dependencies are pinned in `requirements.txt`.

```bash
pip install -r requirements.txt
```

Metadata artifacts are generated with:

```bash
python src/stage_00_build_metadata.py
```

With refined data already available, the analytical workflow is:

```bash
python src/stage_02_build_trusted_pnad.py
python src/stage_03_pnad_analysis.py
python src/stage_04_build_analytic_pnad.py
```

Stage 04 may be executed independently. Publication assets are generated with one canonical command:

```bash
python src/stage_05_publication.py
```

## Citation and license

Repository citation metadata are provided in `CITATION.cff`. The software in this repository is released under the MIT License; see `LICENSE`. Upstream PNAD and PNAD Contínua microdata remain subject to the terms and conditions of their original data providers.
