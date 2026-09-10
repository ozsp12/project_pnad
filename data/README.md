# Data

<p align="justify">The <code>data</code> directory contains the empirical material used by the PNAD longitudinal research pipeline. Data are organized by scientific processing stage. The refined and trusted directories represent two distinct versions of the same annual income samples, while auxiliary external series remain isolated from PNAD-derived data.</p>

| Directory | Content | Produced or consumed by |
| --- | --- | --- |
| <code>metadata/</code> | Annual extraction specifications, monetary metadata and processing summaries; <code>df_metadata.xlsx</code> is the canonical metadata input used by stages 03 and 05 | stages 00, 01, 03 and 05 |
| <code>refined/</code> | Persisted harmonized annual PNAD/PNAD Contínua datasets before trusted-stage trimming; current files were materialized outside GitHub from local microdata | produced by stage 01 when extraction is reproduced; consumed by stages 02, 03 and 05 |
| <code>trusted/</code> | Annual datasets after structural cleaning, log-MAD upper-tail treatment and validation | produced by stage 02; consumed by stage 03 |
| <code>auxiliary/</code> | Independent external reference series: IPEA/World Bank Gini validation data and the persisted World Bank/WDI real GDP-growth series <code>gdp_growth_brazil_1978_2025.csv</code> used by stage 05 | consumed by stages 03 and 05 |
| <code>raw/</code> | Local fixed-width original microdata, approximately 20 GB in total | deliberately not versioned |

<p align="justify">The raw-to-refined boundary is intentionally external to ordinary GitHub execution. Original fixed-width microdata remain local because of their volume, while the already materialized <code>data/refined</code> files form the persistent repository input for downstream processing. When reconstruction from the original microdata is required, <code>src/stage_01_build_refined_pnad.py</code> provides the extraction and harmonization procedure.</p>

<p align="justify">The distinction between <code>refined</code> and <code>trusted</code> is substantive. The refined layer preserves the harmonized annual samples before the trusted-stage statistical treatment. The trusted layer excludes structural invalids, applies the documented log-MAD upper cutoff and verifies distribution-level invariants. Stage 03 analyzes both layers using identical analytical functions, allowing direct before/after comparison without changing the methodology. Stage 05 uses the refined layer as the baseline for the Moura Jr.–Ribeiro replication and extension and does not modify either dataset family.</p>

<p align="justify"><code>data/auxiliary/gdp_growth_brazil_1978_2025.csv</code> is a persistent snapshot of World Bank World Development Indicators series <code>NY.GDP.MKTP.KD.ZG</code> for Brazil. Stage 05 reads this local snapshot and performs no network request at execution time.</p>
