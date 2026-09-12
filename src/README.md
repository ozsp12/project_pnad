# Source modules

The `src` directory contains the canonical scientific workflow. Stages 00–02 build the metadata and annual data layers; Stage 03 performs statistical analysis and Moura Jr.–Ribeiro reproduction diagnostics; Stage 04 builds the cross-year trusted product; Stage 05 converts persisted scientific results into publication assets.

## Pipeline

| Stage | Module | Scientific role |
| ---: | --- | --- |
| 00 | `stage_00_build_metadata.py` | extraction specifications and monetary metadata |
| 01 | `stage_01_build_refined_pnad.py` | raw fixed-width records → annual refined datasets |
| 02 | `stage_02_build_trusted_pnad.py` | structural cleaning, log-MAD upper-tail treatment and validation |
| 03 | `stage_03_pnad_analysis.py` | descriptive, inequality, CCDF and Gompertz–Pareto analysis for refined/trusted |
| 03 | `stage_03_moura_ribeiro_evidence.py` | 2009-method reproduction tests, uncertainty calculations and evidence tables |
| 04 | `stage_04_build_analytic_pnad.py` | concatenated trusted analytical Parquet |
| 05 | `stage_05_publication.py` | canonical paper-asset entry point |
| 05 | `stage_05_moura_ribeiro.py` | publication figure routines |
| 05 | `stage_05_tables.py` | publication-table consolidation |

## Stage 03

The main regime analysis uses normalized positive individual income, geometric thresholds with ratio `1.10`, and a percent-scale CCDF. The current Gompertz model is

$$
G(x)=\exp[\exp(A-Bx)],\qquad A=\ln[\ln(100)],
$$

with `A` fixed and `B` estimated by least squares. A free-intercept fit is retained as a boundary/replication diagnostic. The Pareto branch retains both log-log least squares and direct MLE,

$$
\widehat\alpha_{\rm MLE}=\frac{n_t}{\sum_i\ln(x_i/x_t)},
$$

with continuity used for the MLE amplitude.

`stage_03_moura_ribeiro_evidence.py` owns the simulation/inference layer needed to reproduce Moura Jr. and Ribeiro (2009). For both refined and trusted samples it computes fixed-`A` and free-intercept Gompertz bootstrap diagnostics, Pareto LSF/MLE bootstrap uncertainties, the paper-style likelihood width for the MLE exponent, exponential-vs-Gompertz diagnostics, and direct comparison with the values stored in `data/auxiliary/moura_ribeiro_2009_reference.csv`.

Each Stage-03 table directory therefore contains the six canonical analytical tables plus:

- `moura_ribeiro_bootstrap_annual.csv`;
- `moura_ribeiro_reproduction_annual.csv`;
- `moura_ribeiro_evidence_annual.csv`.

The evidence table is long-form (`year × test × estimator × parameter`) and records the estimate, uncertainty, fit metric, operational criterion, support status, published 2009 value, absolute/relative difference and one-standard-error agreement when defined.

## Stage 04

`stage_04_build_analytic_pnad.py` performs no statistical estimation. It validates the annual trusted files and writes `data/analytics/pnad_analytics_all.parquet`, with one Parquet row group per survey year. Its workflow is independent from Stage 03.

## Stage 05

Stage 05 is publication-only. `stage_05_publication.py` is the canonical executable. It reads persisted Stage-03 outputs, calls the figure routines in `stage_05_moura_ribeiro.py`, and calls `stage_05_tables.py` to write five canonical tables. The former standalone `paper_tables.py` module has been assimilated into Stage 05.

The fixed normalization parameter `A` has no paper-facing standard error because it is not estimated in the current model. The free-intercept `A` and its bootstrap uncertainty are retained explicitly as a Moura–Ribeiro replication diagnostic.

## Historical notebooks

The notebooks under `notebook/` remain intentionally as historical and pedagogical artifacts. They are not authoritative implementations.

## Tests

The test suite covers Stages 00–04, mathematical/regime routines, Moura–Ribeiro bootstrap and likelihood calculations, and Stage-05 figure/table construction. GitHub Actions installs the pinned `requirements.txt`, compiles `src`, and runs `pytest`.
