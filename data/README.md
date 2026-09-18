# Data

The `data` directory contains the empirical material used by the PNAD longitudinal research pipeline. The refined layer is the annual baseline, the trusted layer is the benchmark derived from that baseline, `analytics/` contains consolidated cross-year products and their publication metadata, and `auxiliary/` contains external/reference series rather than PNAD-derived microdata.

| Directory | Content | Produced or consumed by |
| --- | --- | --- |
| `metadata/` | annual extraction specifications, monetary metadata, and processing information | produced by Stage 00; consumed downstream |
| `refined/` | harmonized annual PNAD/PNAD Contínua baseline datasets before trusted-stage treatment | produced by Stage 01; consumed by Stages 02–04 |
| `trusted/` | benchmark annual datasets after structural cleaning, log-MAD upper-tail treatment, and validation | produced by Stage 02; consumed by Stages 03–04 |
| `analytics/` | consolidated refined/trusted Parquets, annual metadata, and variable-level schemas | produced by Stage 04 |
| `auxiliary/` | external Gini/GDP series and published Moura–Ribeiro 2009 reference values | consumed as external/reference inputs |
| `raw/` | local fixed-width original microdata, approximately 20 GB | deliberately not versioned |

The raw-to-refined boundary is intentionally external to ordinary GitHub execution. Original fixed-width microdata remain local because of their volume, while materialized `data/refined/` files are the persistent repository baseline for downstream processing. `src/stage_01_build_refined_pnad.py` documents reconstruction from the original files.

The distinction between `refined` and `trusted` is substantive. Stage 03 currently analyzes both layers with exactly the same analytical functions and table schemas so the effect of benchmark construction can be assessed without changing the statistical model or output structure.

## Analytics layer

Stage 04 publishes five canonical files:

- `pnad_refined_all.parquet`: vertically concatenated refined baseline;
- `pnad_trusted_all.parquet`: vertically concatenated trusted benchmark;
- `pnad_refined_all_schema.csv`: variable-level schema/data dictionary for the refined product;
- `pnad_trusted_all_schema.csv`: variable-level schema/data dictionary for the trusted product;
- `pnad_annual_metadata.csv`: one row per survey year with extraction rules, monetary fields, external Gini references, and the realized trusted-treatment audit.

The two schema CSVs have one row per dataset column. They document description, logical and storage type, unit, source, whether the field is calculated, the stage and formula that produce it, logical/storage nullability, valid/missing counts, and the number of distinct values. Dataset/file-level properties such as Parquet compression and row-group counts are not repeated as variable metadata.

`pnad_annual_metadata.csv` is aligned exactly to the survey years present in the consolidated Parquets. It records the PNAD/PNAD Contínua source field and fixed-width extraction specification, missing-value code, Stage-01 scale/per-capita construction, currency, exchange factor, price index, 2025 adjustment fields, the implemented adjusted-income formula, external IPEA and World Bank Gini reference values, and the Stage-02 log-MAD/p99 treatment parameters, realized cutoffs, and retained/removed counts. The external Gini series are explicitly marked as validation references only; they are not inputs to cutoff selection.

Stage 04 does not filter observations, change income values, or fit scientific models. Each survey year is stored as one Parquet row group. The former `pnad_analytics_all.parquet`, `pnad_refined_all_metadata.csv`, and `pnad_trusted_all_metadata.csv` products are obsolete.

## Auxiliary series

- `series_gini_ipea_banco_mundial.csv`: external IPEA and World Bank Gini reference series used for annual validation/comparison.
- `gdp_growth_brazil_1978_2025.csv`: persisted World Bank/WDI Brazil real-GDP-growth series (`NY.GDP.MKTP.KD.ZG`).
- `moura_ribeiro_2009_reference.csv`: values transcribed from the four tables of Moura Jr. and Ribeiro, *Eur. Phys. J. B* **67**, 101–120 (2009), retained as a historical numerical reference for comparison with the reproduction diagnostics.

The 2009 reference file preserves the exceptional 1978–1979 Pareto population-share result as an interval rather than inventing a central value. It is not an input to the current Gompertz or Pareto estimators and does not determine any fitted parameter.
