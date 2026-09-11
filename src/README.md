# Source modules

The `src` directory contains the canonical scientific workflow of the project. Stages 00–02 build the metadata and refined/trusted data layers; stage 03 performs the complete analytical pipeline independently on refined and trusted distributions; stage 05 produces the Moura–Ribeiro replication/extension assets. `synthetic.py` is a standalone LS–MLE experiment independent of the numbered PNAD stages.

# Scientific pipeline

| Stage | Module | Scientific role | Main output |
| ---: | --- | --- | --- |
| 00 | `src/stage_00_build_metadata.py` | Consolidates historical PNAD/PNAD Contínua extraction specifications and monetary metadata | `data/metadata/df_metadata.xlsx` |
| 01 | `src/stage_01_build_refined_pnad.py` | Harmonizes original survey records into annual income datasets | `data/refined/pnad_refined_YYYY.parquet` |
| 02 | `src/stage_02_build_trusted_pnad.py` | Applies deterministic upper-tail treatment and distribution-level validation | `data/trusted/pnad_trusted_YYYY.parquet` and trusted audit tables |
| 03 | `src/stage_03_pnad_analysis.py` | Complete descriptive, inequality and Gompertz–Pareto analysis for refined and trusted datasets | analytical tables and figures |
| 05 | `src/stage_05_moura_ribeiro.py` | Moura–Ribeiro (2009) replication and extension through 2025 | `assets/figures_paper/` and `assets/tables_paper/` |
| — | `src/synthetic.py` | Standalone synthetic LS–MLE experiment | `assets/tables_synthetic/` |

# Stage 02: trusted distributions

`stage_02_build_trusted_pnad.py` converts refined annual samples into trusted analytical datasets. For each year it evaluates

$$
z_i=\log(1+x_i),
$$

estimates the robust center and scaled median absolute deviation,

$$
m=\operatorname{median}(z_i),\qquad
s=1.4826\operatorname{median}|z_i-m|,
$$

and defines the upper cutoff

$$
x_c=\exp(m+ks)-1,
$$

with `k=6` by default. Structural invalids are removed before statistical trimming. The stage writes the trusted annual Parquet files and the corresponding audit/validation tables.

# Stage 03: refined and trusted analyses

`stage_03_pnad_analysis.py` is the single canonical module for Stage 03. It contains the general analytical routines and the Gompertz–Pareto regime methodology; there is no separate `stage_03_pnad_analysis_core.py` dependency.

| Analysis family | Contents |
| --- | --- |
| Sample diagnostics | counts, missing/zero/negative diagnostics and positive support |
| Descriptive statistics | nominal and adjusted mean, median, standard deviation, minima, maxima and sums |
| Histograms | annual histogram datasets and log-frequency panels |
| Geometric binning | logarithmic edges with ratio `r = 1.10`, counts and summary statistics |
| Distribution functions | empirical CCDF, log-log representation and Gompertz transform |
| Lorenz geometry | Lorenz curves represented on a `100 × 100` percentage grid |
| Inequality | Gini, Pietra, Kolkata and Zanardi indices |
| Concentration | top 10%, top 1% and top 0.1% income shares |
| External validation | calculated Gini versus IPEA and World Bank series |
| Gompertz–Pareto | fixed-normalization Gompertz LSF, explicit regime boundaries, Pareto LSF and direct MLE |

## Normalized income and logarithmic grid

For the regime analysis, each positive adjusted individual income $x'$ is normalized by the corresponding annual positive-income mean,

$$
x=\frac{x'}{\langle x'\rangle}.
$$

The empirical CCDF is evaluated on logarithmically spaced thresholds,

$$
x_j=x_{\min}(1.10)^j.
$$

The CCDF used in the Gompertz analysis is expressed in percent,

$$
0\leq F(x)\leq100,
$$

and the linearizing transformation is

$$
\ln[\ln F(x)].
$$

Only values with $F(x)>1$ enter this transformation.

## Gompertz region

The Gompertz model is

$$
G(x)=\exp\!\left[\exp(A-Bx)\right].
$$

Its normalization at the origin fixes

$$
A=\ln[\ln(100)].
$$

The final model therefore estimates only $B$ by least squares. To identify the empirical upper boundary $x_{G,\max}$ according to the operational procedure of Moura Jr. and Ribeiro (2009), candidate prefixes are inspected with a free-intercept straight-line diagnostic. The largest range whose diagnostic intercept satisfies

$$
1.4\leq A_{\rm diagnostic}\leq1.6
$$

is selected. The free intercept is used only to identify $x_{G,\max}$; the reported Gompertz parameter remains fixed at $A=\ln[\ln(100)]$.

## Pareto region and transition

The Paretian tail is represented by

$$
P(x)=\beta x^{-\alpha}.
$$

The lower boundary $x_{P,\min}$ is identified independently in log-log coordinates. The implementation selects the earliest positive-exponent tail with at least five logarithmic points and $R^2\geq0.98$; if no candidate satisfies this deterministic criterion, the highest-$R^2$ candidate is explicitly retained as a fallback.

The transition is determined only after both empirical boundaries are known. If they coincide,

$$
x_t=x_{G,\max}=x_{P,\min},\qquad \delta x_t=0.
$$

If they differ,

$$
x_t=\frac{x_{P,\min}+x_{G,\max}}{2},\qquad
\delta x_t=\frac{x_{P,\min}-x_{G,\max}}{2}.
$$

No joint-SSE cutoff optimization is used.

## Pareto LSF and MLE

After $x_t$ has been established, the Pareto parameters are estimated by both methods. Least-squares fitting is applied to the log-binned Paretian region to obtain

$$
\alpha_{\rm LSF},\qquad \beta_{\rm LSF}.
$$

The direct Pareto maximum-likelihood estimator uses the individual normalized observations satisfying $x_i\geq x_t$,

$$
\widehat\alpha_{\rm MLE}
=\frac{n_t}{\displaystyle\sum_{i=1}^{n_t}\ln(x_i/x_t)}.
$$

For the MLE branch, continuity with the Gompertz curve at the transition gives

$$
F_t=\exp\!\left[\exp(A-Bx_t)\right],\qquad
\beta_{\rm MLE}=F_t x_t^{\widehat\alpha_{\rm MLE}}.
$$

Both LSF and MLE estimates are retained in the annual outputs.

## Stage 03 outputs

Refined outputs are written to `assets/tables_analysis_refined/` and `assets/figures_analysis_refined/`. Trusted outputs are written to `assets/tables_analysis_trusted/` and `assets/figures_analysis_trusted/`.

The principal annual/reusable tables are:

- `*_analysis_statistics_annual.csv`;
- `*_analysis_ccdf_empirical.csv`;
- `*_analysis_geometric_bins.csv`;
- `*_analysis_lorenz.csv`;
- `*_analysis_histograms.csv`;
- `*_analysis_gini_validation_vs_ipea_wb_annual.csv`;
- `*_analysis_gompertz_pareto_annual.csv`;
- `*_analysis_regime_curves.csv`.

The trusted versions of `statistics_annual`, `ccdf_empirical`, `lorenz`, `gompertz_pareto_annual`, and `regime_curves` are the canonical Stage 05 inputs.

# Standalone synthetic LS–MLE experiment

`synthetic.py` implements a controlled comparison between a deterministic power-law relation and a probabilistic Pareto model. A single pseudo-random stream is used to construct nested samples. The deterministic branch is exactly linear in log-log coordinates, while the probabilistic branch samples a Pareto distribution and evaluates the corresponding likelihood-based estimator. The experiment is independent of PNAD ingestion and of the numbered analysis stages.

# Stage 05: Moura–Ribeiro replication and extension

`stage_05_moura_ribeiro.py` is a publication layer. It does not import Stage 03 as a Python module; it consumes the persisted trusted analytical CSVs produced by Stage 03 and reads trusted annual Parquet files where individual observations are required, including bootstrap and income-share calculations. It preserves the four-table and fifteen-figure-family structure of Moura Jr. and Ribeiro (2009), extends the available series through 2025, and writes publication assets to `assets/tables_paper/` and `assets/figures_paper/`.

# Dependency reproducibility

`requirements.txt` is the normal installation specification. `requirements-lock.txt` is the pinned runtime snapshot. Unit tests compile `src` and run with `pytest` through `.github/workflows/tests.yml`.
