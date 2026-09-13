# Source modules

The `src` directory contains the canonical scientific workflow. Stages 00–02 build the metadata and annual data layers; Stage 03 performs statistical analysis and Moura Jr.–Ribeiro diagnostics; Stage 04 builds the cross-year trusted product; Stage 05 converts persisted scientific results into publication assets.

## Pipeline

| Stage | Module | Scientific role |
| ---: | --- | --- |
| 00 | `stage_00_build_metadata.py` | extraction specifications and monetary metadata |
| 01 | `stage_01_build_refined_pnad.py` | raw fixed-width records → annual refined datasets |
| 02 | `stage_02_build_trusted_pnad.py` | structural cleaning, log-MAD upper-tail treatment and validation |
| 03 | `stage_03_pnad_analysis.py` | descriptive, inequality, CCDF and Gompertz–Pareto analysis for refined/trusted |
| 03 | `stage_03_moura_ribeiro_evidence.py` | 2009-method uncertainty and reproduction diagnostics consolidated into canonical tables |
| 04 | `stage_04_build_analytic_pnad.py` | concatenated trusted analytical Parquet |
| 05 | `stage_05_publication.py` | canonical paper-asset entry point |
| 05 | `stage_05_moura_ribeiro.py` | publication figure routines only |
| 05 | `stage_05_tables.py` | publication-table consolidation only |

## Stage 03

The main regime analysis uses normalized positive individual income, geometric thresholds with ratio `1.10`, and a percent-scale CCDF. The current Gompertz model is

$$
G(x)=\exp[\exp(A-Bx)],\qquad A=\ln[\ln(100)],
$$

with `A` fixed and `B` estimated by least squares. A free-intercept fit is retained as a boundary/replication diagnostic. The Pareto branch retains both log-log least squares and direct MLE,

$$
\widehat\alpha_{\rm MLE}=\frac{n_t}{\sum_i\ln(x_i/x_t)},
$$

with Gompertz–Pareto continuity used to determine the MLE amplitude.

The `refined` layer is the analytical baseline and the `trusted` layer is the benchmark. Their Stage-03 table directories are required to have identical file sets and column schemas. Each contains exactly six scientific tables:

- `statistics_annual.csv`;
- `geometric_bins.csv`;
- `gompertz_annual.csv`;
- `pareto_annual.csv`;
- `gompertz_pareto_curves.csv`;
- `lorenz.csv`.

Each directory also contains `metadata.csv`, which documents the purpose of every table and the scientific meaning, unit/scale, and source of every column.

`stage_03_moura_ribeiro_evidence.py` computes the simulation/inference quantities needed to reproduce Moura Jr. and Ribeiro (2009): fixed-`A` and free-intercept Gompertz bootstrap diagnostics, Pareto LSF/MLE bootstrap uncertainties, the paper-style likelihood width for the MLE exponent, exponential-vs-Gompertz diagnostics, and regime income shares. These quantities are written directly into `gompertz_annual.csv` and `pareto_annual.csv`; no separate bootstrap or reproduction CSVs are persisted.

The 2009 numerical reference dataset remains in `data/auxiliary/moura_ribeiro_2009_reference.csv`; no separate long-form evidence table is generated.

## Stage 04

`stage_04_build_analytic_pnad.py` performs no statistical estimation. It validates the annual trusted files and writes `data/analytics/pnad_analytics_all.parquet`, with one Parquet row group per survey year. Its workflow is independent from Stage 03.

## Stage 05

Stage 05 is strictly publication-only. `stage_05_publication.py` is the canonical executable. It reads the consolidated trusted Stage-03 outputs, calls the figure routines in `stage_05_moura_ribeiro.py`, and calls `stage_05_tables.py` to write four canonical tables.

All fitted parameters, bootstrap standard errors, likelihood-width uncertainties, model-comparison diagnostics, Pareto support diagnostics, and Gompertz/Pareto regime income shares are computed and persisted in Stage 03. Stage 05 does not re-estimate any of these quantities; figure annotations and publication tables consume the persisted values directly.

The fixed normalization parameter `A` has no paper-facing standard error because it is not estimated in the current model. The free-intercept `A` and `B` estimates and their bootstrap uncertainties are retained explicitly as Moura–Ribeiro replication diagnostics. `table_04_metadata.csv` documents both the purpose of each table and the meaning, unit, and source of every paper-facing column.

## Historical notebooks

The notebooks under `notebook/` remain intentionally as historical and pedagogical artifacts. They are not authoritative implementations.

## Tests

The test suite covers Stages 00–04, mathematical/regime routines, Moura–Ribeiro bootstrap and likelihood calculations, Stage-03 baseline/benchmark schema symmetry, metadata definitions, and Stage-05 figure/table construction. GitHub Actions installs the pinned `requirements.txt`, compiles `src`, and runs `pytest`.
