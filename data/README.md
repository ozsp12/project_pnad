# Data

The `data` directory contains the empirical material used by the PNAD longitudinal research pipeline. The refined layer is the annual baseline, the trusted layer is the benchmark derived from that baseline, `analytics/` contains the consolidated cross-year trusted product, and `auxiliary/` contains external/reference series rather than PNAD-derived microdata.

| Directory | Content | Produced or consumed by |
| --- | --- | --- |
| `metadata/` | annual extraction specifications, monetary metadata, and processing information | produced by Stage 00; consumed downstream |
| `refined/` | harmonized annual PNAD/PNAD Contínua baseline datasets before trusted-stage treatment | produced by Stage 01; consumed by Stages 02–03 |
| `trusted/` | benchmark annual datasets after structural cleaning, log-MAD upper-tail treatment, and validation | produced by Stage 02; consumed by Stages 03–05 |
| `analytics/` | single vertically concatenated trusted microdata product | produced independently by Stage 04 |
| `auxiliary/` | external Gini/GDP series and published Moura–Ribeiro 2009 reference values | consumed as external/reference inputs |
| `raw/` | local fixed-width original microdata, approximately 20 GB | deliberately not versioned |

The raw-to-refined boundary is intentionally external to ordinary GitHub execution. Original fixed-width microdata remain local because of their volume, while materialized `data/refined/` files are the persistent repository baseline for downstream processing. `src/stage_01_build_refined_pnad.py` documents reconstruction from the original files.

The distinction between `refined` and `trusted` is substantive. Stage 03 analyzes both layers with exactly the same analytical functions and table schemas so the effect of benchmark construction can be assessed without changing the statistical model or output structure.

## Analytics layer

`data/analytics/pnad_analytics_all.parquet` is built exclusively from annual trusted Parquet files. Stage 04 performs validation and vertical concatenation only; each survey year is stored as one Parquet row group. Stage 04 is automated independently from Stage 03 and does not re-estimate analytical quantities.

## Auxiliary series

- `series_gini_ipea_banco_mundial.csv`: external IPEA and World Bank Gini reference series used for annual validation/comparison.
- `gdp_growth_brazil_1978_2025.csv`: persisted World Bank/WDI Brazil real-GDP-growth series (`NY.GDP.MKTP.KD.ZG`).
- `moura_ribeiro_2009_reference.csv`: values transcribed from the four tables of Moura Jr. and Ribeiro, *Eur. Phys. J. B* **67**, 101–120 (2009), retained as a historical numerical reference for comparison with the reproduction diagnostics.

The 2009 reference file preserves the exceptional 1978–1979 Pareto population-share result as an interval rather than inventing a central value. It is not an input to the current Gompertz or Pareto estimators and does not determine any fitted parameter.
