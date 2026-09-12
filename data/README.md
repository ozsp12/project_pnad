# Data

The `data` directory contains the empirical material used by the PNAD longitudinal research pipeline. Refined and trusted directories represent two versions of the same annual samples, `analytics/` contains the consolidated cross-year trusted product, and `auxiliary/` contains external/reference series rather than PNAD-derived microdata.

| Directory | Content | Produced or consumed by |
| --- | --- | --- |
| `metadata/` | Annual extraction specifications, monetary metadata, and processing information | produced by Stage 00; consumed downstream |
| `refined/` | Harmonized annual PNAD/PNAD Contínua datasets before trusted-stage trimming | produced by Stage 01; consumed by Stages 02–03 |
| `trusted/` | Annual datasets after structural cleaning, log-MAD upper-tail treatment, and validation | produced by Stage 02; consumed by Stages 03–05 |
| `analytics/` | Single vertically concatenated trusted microdata product | produced independently by Stage 04 |
| `auxiliary/` | External Gini/GDP series and published Moura–Ribeiro 2009 reference values | consumed by Stages 03 and 05 |
| `raw/` | Local fixed-width original microdata, approximately 20 GB | deliberately not versioned |

The raw-to-refined boundary is intentionally external to ordinary GitHub execution. Original fixed-width microdata remain local because of their volume, while materialized `data/refined/` files are the persistent repository input for downstream processing. `src/stage_01_build_refined_pnad.py` documents reconstruction from the original files.

The distinction between `refined` and `trusted` is substantive. Stage 03 analyzes both layers with the same analytical functions so the impact of trusted-stage treatment can be assessed without changing the downstream model.

## Analytics layer

`data/analytics/pnad_analytics_all.parquet` is built exclusively from annual trusted Parquet files. Stage 04 performs validation and vertical concatenation only; each survey year is stored as one Parquet row group. Stage 04 is automated independently from Stage 03.

## Auxiliary series

- `series_gini_ipea_banco_mundial.csv`: external Gini reference series.
- `gdp_growth_brazil_1978_2025.csv`: persisted World Bank/WDI Brazil real-GDP-growth series (`NY.GDP.MKTP.KD.ZG`).
- `moura_ribeiro_2009_reference.csv`: values transcribed from the four tables of Moura Jr. and Ribeiro, *Eur. Phys. J. B* **67**, 101–120 (2009), used strictly as the published benchmark for reproduction evidence.

The 2009 reference file preserves the exceptional 1978–1979 Pareto population-share result as an interval rather than inventing a central value. It is not an input to the current estimators; it is used only after estimation to quantify reproduction differences.
