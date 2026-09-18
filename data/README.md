# Data

The `data` directory contains the empirical material used by the PNAD longitudinal research pipeline. The directory separates source metadata, harmonized annual observations, quality-controlled observations, consolidated cross-year products, and external reference series.

| Directory | Content | Produced or consumed by |
| --- | --- | --- |
| `metadata/` | annual extraction specifications, monetary metadata, and processing information | produced by Stage 00; consumed downstream |
| `refined/` | harmonized annual PNAD/PNAD Contínua baseline datasets before trusted-stage treatment | produced by Stage 01; consumed by Stages 02–04 |
| `trusted/` | benchmark annual datasets after structural cleaning, log-MAD upper-tail treatment, and validation | produced by Stage 02; consumed by Stages 03–04 |
| `analytics/` | consolidated refined/trusted Parquets, annual metadata, and variable-level schemas | produced by Stage 04 |
| `auxiliary/` | external Gini/GDP series and published Moura–Ribeiro 2009 reference values | consumed as external/reference inputs |
| `raw/` | local fixed-width original microdata, approximately 20 GB | deliberately not versioned |

## Dataset interpretation

The collection covers 45 available survey years between 1976 and 2025. The years 1980, 1991, 1994, 2000, and 2010 are explicit survey gaps and are not interpolated. The files represent repeated annual cross-sections rather than a longitudinal panel: records from different years do not identify the same households or persons through time.

The harmonized analytical target is household income expressed on a per-resident basis when required by the annual source definition. Late historical PNAD uses the household per-capita field `V4621`, while PNAD Contínua uses the derived household per-capita field `VD5008`. The 2015–2016 PNAD/PNAD Contínua transition remains an explicit methodological boundary because survey design, interview structure, and construction of income aggregates changed.

The released analytical records do not contain the full original survey expansion weights or complex-sample design variables. Quantities computed directly from these records are therefore record-weighted. Population-design-weighted inference requires reconstruction from the original IBGE microdata with the corresponding annual design variables.

## Raw and refined layers

The raw-to-refined boundary is intentionally external to ordinary GitHub execution. Original fixed-width microdata remain local because of their volume, while materialized `data/refined/` files are the persistent repository baseline for downstream processing. `src/stage_01_build_refined_pnad.py` documents reconstruction from the original files.

Stage 01 uses year-specific extraction metadata rather than a universal fixed-width parser. The metadata identify the original income field, position and width, household-member field when required, missing-value convention, raw-file pattern, scale divisor, currency, exchange factor, and price-index information.

### 2017 PNAD Contínua extraction correction

For 2017, the canonical fixed-width initial position of `VD5008` is `674` with width `8`. The income field is retained on its native scale (`income_scale_divisor = 1.0`). The previously observed approximately 100-fold anomaly was caused by an incorrect field offset rather than by a genuine unit difference or by trusted-layer upper-tail treatment. The correction is therefore implemented at the Stage-00/Stage-01 extraction boundary and protected by regression tests.

## Trusted layer

The `trusted` layer is derived from the refined baseline. Stage 02 removes structurally invalid values and applies the deterministic annual log-MAD upper-tail rule. For 1985 and 1990 only, the effective cutoff is `min(log-MAD, p99)`. These exceptions are defined from within-year distributional diagnostics; IPEA and World Bank Gini series are not used to select or tune the cutoffs.

The untrimmed refined observations are preserved so that analyses sensitive to the upper tail can be repeated without the trusted-stage treatment.

## Analytics layer

Stage 04 publishes five canonical files:

- `pnad_refined_all.parquet`: vertically concatenated refined baseline;
- `pnad_trusted_all.parquet`: vertically concatenated trusted benchmark;
- `pnad_refined_all_schema.csv`: variable-level schema/data dictionary for the refined product;
- `pnad_trusted_all_schema.csv`: variable-level schema/data dictionary for the trusted product;
- `pnad_annual_metadata.csv`: one row per survey year with extraction rules, monetary fields, external validation references, and the realized trusted-treatment audit.

The two consolidated Parquets share the same columns, `renda` and `ano`, and Stage 04 preserves annual values and dtypes without additional statistical transformation. Each survey year is stored as one Parquet row group.

The two schema CSVs have one row per dataset column. They document description, logical and storage type, unit, source, whether the field is calculated, the stage and formula that produce it, logical/storage nullability, valid/missing counts, and the number of distinct values.

`pnad_annual_metadata.csv` is aligned to the survey years present in the consolidated Parquets. It records the source survey and income variable, fixed-width extraction specification, missing-value code, Stage-01 scale/per-capita construction, currency, exchange factor, price index, 2025 adjustment fields, the implemented adjusted-income formula, external IPEA and World Bank Gini values, and the Stage-02 log-MAD/p99 treatment parameters, effective cutoffs, and retained/removed counts. The external Gini series are validation references only.

The former `pnad_analytics_all.parquet`, `pnad_refined_all_metadata.csv`, and `pnad_trusted_all_metadata.csv` products are obsolete.

## Auxiliary series

- `series_gini_ipea_banco_mundial.csv`: external IPEA and World Bank Gini reference series used for validation/comparison;
- `gdp_growth_brazil_1978_2025.csv`: persisted World Bank/WDI Brazil real-GDP-growth series (`NY.GDP.MKTP.KD.ZG`);
- `moura_ribeiro_2009_reference.csv`: numerical values transcribed from Moura Jr. and Ribeiro, *European Physical Journal B* **67**, 101–120 (2009), retained for historical methodological comparison.

External reference series do not determine fitted parameters or trusted-layer treatment rules.