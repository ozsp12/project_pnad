# Source modules

The `src` directory contains the canonical scientific workflow of the project. Stages 00–02 build metadata and refined/trusted data layers; Stage 03 performs the complete empirical analysis; Stage 04 consolidates trusted annual microdata into one cross-year analytical Parquet; Stage 05 generates publication figures and uncertainty products; and `paper_tables.py` produces the canonical publication tables.

## Scientific pipeline

| Stage | Module | Scientific role | Main output |
| ---: | --- | --- | --- |
| 00 | `stage_00_build_metadata.py` | Consolidates historical PNAD/PNAD Contínua extraction specifications and monetary metadata | `data/metadata/df_metadata.xlsx` |
| 01 | `stage_01_build_refined_pnad.py` | Harmonizes original survey records into annual income datasets | `data/refined/pnad_refined_YYYY.parquet` |
| 02 | `stage_02_build_trusted_pnad.py` | Applies deterministic upper-tail treatment and distribution-level validation | `data/trusted/pnad_trusted_YYYY.parquet` and trusted audit tables |
| 03 | `stage_03_pnad_analysis.py` | Complete descriptive, inequality, and Gompertz–Pareto analysis for refined and trusted datasets | analytical CSV and PNG assets |
| 04 | `stage_04_build_analytic_pnad.py` | Concatenates all trusted annual microdata into one validated cross-year dataset | `data/analytics/pnad_analytics_all.parquet` |
| 05 | `stage_05_moura_ribeiro.py` | Trusted-data publication layer and Moura Jr.–Ribeiro replication/extension through 2025 | `assets/figures_paper/` and bootstrap uncertainty metrics |
| — | `paper_tables.py` | Consolidates the four canonical publication tables directly from current trusted Stage-03 outputs | `assets/tables_paper/` |

## Stage 02: trusted distributions

`stage_02_build_trusted_pnad.py` converts refined annual samples into trusted analytical datasets. For each year it evaluates

$$
z_i=\log(1+x_i),
$$

estimates

$$
m=\operatorname{median}(z_i),\qquad
s=1.4826\operatorname{median}|z_i-m|,
$$

and defines the upper cutoff

$$
x_c=\exp(m+ks)-1,
$$

with `k=6` by default. Structural invalids are removed before statistical trimming. The stage persists trusted annual Parquet files and audit/validation tables.

## Stage 03: refined and trusted analyses

`stage_03_pnad_analysis.py` is the single canonical Stage-03 module. It contains descriptive statistics, histogram construction, geometric bins, empirical CCDFs, Lorenz geometry, Gini/Pietra/Kolkata/Zanardi indices, top-income shares, external Gini validation, plotting utilities, and the Gompertz–Pareto regime procedure.

The regime analysis uses normalized positive individual income

$$
x=\frac{x'}{\langle x'\rangle},
$$

with geometric thresholds

$$
x_j=x_{\min}(1.10)^j.
$$

The Gompertz CCDF is represented in percent,

$$
0\leq F(x)\leq100,
$$

and linearized through

$$
\ln[\ln F(x)],
$$

using only points with $F(x)>1$.

The Gompertz model is

$$
G(x)=\exp\!\left[\exp(A-Bx)\right],
$$

with the normalization fixed at

$$
A=\ln[\ln(100)].
$$

The final Gompertz fit therefore estimates only $B$ by least squares. A free-intercept diagnostic is used only to identify the empirical upper boundary $x_{G,\max}$ following the operational Moura Jr.–Ribeiro criterion. The reported model retains the fixed value of $A$.

The lower Pareto boundary $x_{P,\min}$ is identified independently in log-log coordinates. Once both boundaries are known,

$$
x_t=x_{G,\max}=x_{P,\min}
$$

when they coincide, or

$$
x_t=\frac{x_{P,\min}+x_{G,\max}}{2},\qquad
\delta x_t=\frac{x_{P,\min}-x_{G,\max}}{2}
$$

when they differ. No joint-SSE cutoff optimization is used.

After determining $x_t$, Pareto parameters are retained from both methods. Least-squares fitting yields

$$
\alpha_{\rm LSF},\qquad \beta_{\rm LSF},
$$

while direct maximum likelihood on individual observations $x_i\geq x_t$ gives

$$
\widehat\alpha_{\rm MLE}
=\frac{n_t}{\displaystyle\sum_{i=1}^{n_t}\ln(x_i/x_t)}.
$$

For the MLE branch, continuity with the Gompertz curve gives

$$
F_t=\exp\!\left[\exp(A-Bx_t)\right],\qquad
\beta_{\rm MLE}=F_t x_t^{\widehat\alpha_{\rm MLE}}.
$$

### Stage-03 outputs

Refined outputs are written to `assets/tables_analysis_refined/` and `assets/figures_analysis_refined/`. Trusted outputs are written to `assets/tables_analysis_trusted/` and `assets/figures_analysis_trusted/`.

The table layout is identical in both analysis directories. Because the directory already identifies the data layer, table filenames do not repeat `trusted`, `refined`, or `analysis` prefixes. Tables with one row per survey year use the `_annual` suffix.

The canonical Stage-03 tables are:

- `statistics_annual.csv`: annual descriptive statistics, inequality indices, top-income shares, and IPEA/World Bank Gini validation fields;
- `geometric_bins.csv`: descriptive statistics on the geometric income grid;
- `lorenz.csv`: sampled Lorenz-curve coordinates;
- `gompertz_annual.csv`: annual Gompertz parameters, boundary diagnostics, and population share;
- `pareto_annual.csv`: annual Pareto boundaries, transition quantities, LSF/MLE estimates, and population share;
- `gompertz_pareto_curves.csv`: empirical CCDF and fitted Gompertz/Pareto curves on the common normalized-income grid.

Histogram and descriptive CCDF datasets are built directly from the annual Parquet files for plotting but are not persisted as separate CSV tables.

## Stage 04: concatenated trusted analytics dataset

`stage_04_build_analytic_pnad.py` creates a single cross-year microdata product from the annual trusted files. It performs no new statistical transformation: trusted columns and values are preserved, annual datasets are ordered by `ano`, and the output is written to `data/analytics/pnad_analytics_all.parquet`.

Before writing, Stage 04 verifies that every annual file contains `renda` and `ano`, that the year stored in the data matches the year encoded in the filename, and that trusted income remains finite and non-negative. Annual schemas must also agree. Each survey year is written as one Parquet row group so the combined file remains efficient for year-level filtering.

Stage 04 has its own GitHub Actions workflow. It can therefore rebuild the cross-year analytics product independently from Stage 03 whenever trusted annual inputs or the Stage-04 implementation change.

## Stage 05: publication layer

`stage_05_moura_ribeiro.py` consumes persisted canonical trusted Stage-03 outputs and reads trusted annual Parquet files only where individual observations are required. It owns the complete paper-figure set, so publication figures do not require a separate figure-postprocessing module.

The Gompertz bootstrap follows the same fixed-normalization model used in Stage 03: $A=\ln[\ln(100)]$ is held fixed in every bootstrap resample and only $B$ is re-estimated. Consequently, `gompertz_A_bootstrap_se` is zero by construction and retained only for schema compatibility.

`paper_tables.py` reads the current canonical trusted Stage-03 tables directly: `statistics_annual.csv`, `gompertz_annual.csv`, `pareto_annual.csv`, and `gompertz_pareto_curves.csv`. It combines them with Stage-05 bootstrap uncertainties and trusted microdata to produce exactly four paper-facing tables.

## Historical notebooks

The notebooks under `notebook/` are intentionally retained in the repository as historical and pedagogical artifacts. They are not the authoritative implementation of the current pipeline; the source modules under `src/` are canonical.

## Dependencies and tests

The repository uses a single pinned `requirements.txt` for both runtime and test dependencies. GitHub Actions installs this file, compiles `src`, and runs `pytest`.

The test suite covers Stage-00 metadata construction, Stage-01 fixed-width parsing and annual harmonization, Stage-02 log-MAD trimming and trusted invariants, Stage-03 mathematical and Gompertz–Pareto routines, Stage-04 concatenation, and the publication figure/table layer.
