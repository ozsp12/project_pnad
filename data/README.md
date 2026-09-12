# Data

The `data` directory contains the empirical material used by the PNAD longitudinal research pipeline. Data are organized by scientific processing stage. The refined and trusted directories represent two distinct versions of the same annual income samples, `analytics/` contains the consolidated cross-year trusted product, and auxiliary external series remain isolated from PNAD-derived data.

| Directory | Content | Produced or consumed by |
| --- | --- | --- |
| `metadata/` | Annual extraction specifications, monetary metadata, and processing information | produced by Stage 00; consumed by Stages 01, 03, and 05 |
| `refined/` | Harmonized annual PNAD/PNAD Contínua datasets before trusted-stage trimming; current files were materialized outside GitHub from local microdata | produced by Stage 01; consumed by Stages 02 and 03 |
| `trusted/` | Annual datasets after structural cleaning, log-MAD upper-tail treatment, and validation | produced by Stage 02; consumed by Stages 03, 04, and 05 |
| `analytics/` | Single vertically concatenated trusted microdata product across all survey years | produced independently by Stage 04; intended for cross-year and longitudinal analyses |
| `auxiliary/` | Independent external reference series: IPEA/World Bank Gini data and the persisted World Bank/WDI Brazil real-GDP-growth series | consumed by Stages 03 and 05 |
| `raw/` | Local fixed-width original microdata, approximately 20 GB in total | deliberately not versioned |

The raw-to-refined boundary is intentionally external to ordinary GitHub execution. Original fixed-width microdata remain local because of their volume, while the already materialized `data/refined/` files form the persistent repository input for downstream processing. When reconstruction from the original microdata is required, `src/stage_01_build_refined_pnad.py` provides the extraction and harmonization procedure.

The distinction between `refined` and `trusted` is substantive. The refined layer preserves harmonized annual samples before trusted-stage statistical treatment. The trusted layer excludes structural invalids, applies the documented log-MAD upper cutoff, and verifies distribution-level invariants. Stage 03 analyzes both layers using the same analytical functions, allowing direct before/after comparison without changing the downstream methodology.

## Analytics layer

`data/analytics/pnad_analytics_all.parquet` is produced by `src/stage_04_build_analytic_pnad.py` exclusively from annual trusted Parquet files. Stage 04 introduces no new statistical transformation: it validates trusted invariants and schema compatibility, orders survey years, and vertically concatenates the annual samples. Each survey year is stored as one Parquet row group so year-level filtering remains efficient.

Stage 04 is automated separately from Stage 03. Changes limited to the consolidated analytics product can therefore be rebuilt without rerunning the full empirical analysis.

## Auxiliary series

`series_gini_ipea_banco_mundial.csv` contains external Gini reference series used by Stage 03. `gdp_growth_brazil_1978_2025.csv` is the local snapshot used by `src/stage_05_moura_ribeiro.py` for the GDP-growth comparison. It contains `year`, `gdp_growth_pct`, `indicator`, and `source`; the indicator is `NY.GDP.MKTP.KD.ZG` and the source is World Bank/World Development Indicators (WDI). Persisting this snapshot removes network dependence from Stage 05 while preserving the GDP values used by the publication layer.
