# Source modules

The `src` directory contains the canonical scientific workflow. Stages 00–02 build the annual data layers, Stage 03 performs the statistical analysis, Stage 04 constructs the cross-year archival products and their metadata, and Stage 05 generates publication-facing outputs.

## Pipeline

| Stage | Module | Scientific role |
| ---: | --- | --- |
| 00 | `stage_00_build_metadata.py` | annual extraction specifications and monetary metadata |
| 01 | `stage_01_build_refined_pnad.py` | raw fixed-width records → annual refined datasets |
| 02 | `stage_02_build_trusted_pnad.py` | structural cleaning, deterministic upper-tail treatment and validation |
| 03 | `stage_03_pnad_analysis.py` | descriptive, inequality, CCDF, Gompertz–Pareto, uncertainty and 2009-method reproduction analysis |
| 04 | `stage_04_build_analytic_pnad.py` | consolidated refined/trusted Parquets, dataset metadata, annual metadata and variable-level schemas |
| 05 | `stage_05_publication.py` | publication figures and table formatting from persisted Stage-03 results |

## Stage 00 and Stage 01

Stage 00 generates `data/metadata/df_metadata.xlsx` and `data/metadata/df_metadata.csv`. The annual specification records the source income variable, fixed-width position and width, household-member field when needed, file pattern, missing-value code, ingestion-scale divisor, currency, exchange factor and price-index fields.

Stage 01 consumes this specification and reconstructs one `pnad_refined_YYYY.parquet` file per available survey year from the local IBGE fixed-width microdata. When the source field is a household total, Stage 01 divides by the configured household-member count; when the source variable is already per capita, no additional division is applied.

## Stage 02 upper-tail policy

The trusted layer applies structural cleaning followed by the canonical annual log-MAD rule. For non-negative structurally valid income `x`, Stage 02 uses

$$
z_i=\ln(1+x_i),\qquad m=\operatorname{median}(z_i),\qquad
s=1.4826\,\operatorname{median}|z_i-m|,
$$

with the generic cutoff

$$
x_c=\exp(m+6s)-1.
$$

If the scaled MAD is zero, the implementation uses the documented standard-deviation fallback; if dispersion remains zero, the observed maximum is retained. In 1985 and 1990 the effective cutoff is `min(log-MAD, p99)`. These exceptional rules are defined from within-year diagnostics and are not calibrated to IPEA or World Bank Gini values.

Stage 02 writes annual trusted Parquets together with `assets/tables_validation/trusted_trim_audit_annual.csv` and `trusted_distribution_tests_annual.csv`.

## Stage 03 analysis

Stage 03 currently applies the same analytical functions independently to the `refined` baseline and `trusted` benchmark. This parallel structure provides a sensitivity check for the benchmark construction while keeping the statistical model fixed.

The main regime analysis uses normalized positive annual income, geometric thresholds with ratio `r = 1.10`, and a percent-scale empirical CCDF. The Gompertz model is

$$
G(x)=\exp[\exp(A-Bx)],\qquad A=\ln[\ln(100)],
$$

with `A` fixed and `B` estimated by least squares. A free-intercept fit is retained as a diagnostic. The Pareto branch retains both log-log least squares and direct maximum likelihood,

$$
\widehat\alpha_{\rm MLE}=\frac{n_t}{\sum_i\ln(x_i/x_t)},
$$

with Gompertz–Pareto continuity used to determine the direct-MLE amplitude.

Each Stage-03 table directory currently contains six scientific CSVs: `statistics_annual.csv`, `geometric_bins.csv`, `gompertz_annual.csv`, `pareto_annual.csv`, `gompertz_pareto_curves.csv`, and `lorenz.csv`, plus `metadata.csv` as a table/column data dictionary. The refined and trusted directories are required to retain identical file sets and column schemas.

Moura Jr.–Ribeiro reproduction diagnostics are persisted directly in the annual Gompertz and Pareto tables, including fixed-`A` and free-intercept bootstrap diagnostics, Pareto LSF/MLE uncertainty, likelihood-width uncertainty, exponential comparison diagnostics and regime income shares. The historical numerical reference remains in `data/auxiliary/moura_ribeiro_2009_reference.csv`.

## Stage 04 archival products

Stage 04 performs validation and vertical concatenation only. It does not filter observations, transform income values or fit scientific models. Annual values and dtypes are preserved, years are ordered chronologically, and each survey year occupies one Parquet row group.

The six canonical data products are:

- `data/analytics/pnad_refined_all.parquet`;
- `data/analytics/pnad_trusted_all.parquet`;
- `data/analytics/pnad_refined_all_schema.csv`;
- `data/analytics/pnad_trusted_all_schema.csv`;
- `data/analytics/pnad_annual_metadata.csv`;
- `data/analytics/pnad_datasets_metadata.csv`.

The schema CSVs are variable-level data dictionaries. `pnad_annual_metadata.csv` combines Stage-00 extraction and monetary metadata, external IPEA/World Bank Gini references, and the realized Stage-02 trusted-treatment audit. Its monetary provenance explicitly identifies Banco Central do Brasil SGS series 3692 for the exchange-rate series and U.S. Bureau of Labor Statistics CPIAUCSL distributed through FRED for the U.S. price index. External Gini values are validation-only.

`pnad_datasets_metadata.csv` contains one row for each consolidated Parquet. It records dataset role, processing level, source stage, file/schema names, row and column counts, year coverage, row-group count, compression, file size, schema version, observation unit and weighting convention. This file documents the datasets themselves; the `*_schema.csv` files document variables; `pnad_annual_metadata.csv` documents year-specific provenance and treatment.

The obsolete `pnad_analytics_all.parquet`, `pnad_refined_all_metadata.csv`, and `pnad_trusted_all_metadata.csv` products are removed when Stage 04 runs. The directory-level contract is documented in `data/analytics/README.md`.

## Stage 05 publication layer

Stage 05 is presentation-only. `stage_05_publication.py` consumes persisted Stage-03 scientific results and builds the paper-facing figures and tables. Statistical estimation, bootstrap resampling, likelihood calculations, regime-share estimation and model diagnostics remain in Stage 03.

The paper tables are `table_01_gompertz_annual.csv`, `table_02_pareto_annual.csv`, `table_03_economic_inequality_annual.csv`, and `table_04_metadata.csv`. Table 04 documents the purpose and schema of the paper-facing tables.

## Execution

The repository targets Python 3.12 and pins direct runtime and test dependencies in `requirements.txt`.

```bash
pip install -r requirements.txt
```

Metadata generation:

```bash
python src/stage_00_build_metadata.py
```

With the persisted refined layer available:

```bash
python src/stage_02_build_trusted_pnad.py
python src/stage_03_pnad_analysis.py
python src/stage_04_build_analytic_pnad.py
python src/stage_05_publication.py
```

Stage 01 requires the original local IBGE fixed-width files and is therefore not part of ordinary GitHub execution.

## Automated workflows

The repository uses GitHub Actions to keep generated products synchronized with their source stages:

- `Build metadata`: regenerates and validates Stage-00 CSV/XLSX metadata;
- `Build trusted PNAD`: rebuilds Stage-02 trusted annual datasets and validation audits from persisted refined data;
- `Run PNAD analysis`: executes Stage 03 and validates refined/trusted analytical symmetry;
- `Build PNAD analytics datasets`: executes Stage 04, validates the six canonical cross-year data products plus the analytics README, and runs after successful trusted builds;
- `Build paper assets`: consumes persisted Stage-03 tables and executes Stage 05;
- `Unit tests`: compiles `src/` and executes the complete `pytest` suite.

## Tests

The test suite covers Stages 00–04, extraction metadata, trusted-layer invariants, mathematical/regime routines, Moura Jr.–Ribeiro bootstrap and likelihood calculations, Stage-03 baseline/benchmark schema symmetry, Stage-04 consolidated products and metadata, and Stage-05 figure/table construction.
