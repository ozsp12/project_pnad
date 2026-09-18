# Analytics data products

The `data/analytics` directory contains the canonical cross-year record-level products prepared for scientific reuse and archival deposition. Stage 04 validates and concatenates the annual `refined` and `trusted` layers without applying additional statistical filtering or re-estimating scientific models.

## Canonical files

| File | Role |
| --- | --- |
| `pnad_refined_all.parquet` | consolidated minimally transformed baseline |
| `pnad_trusted_all.parquet` | consolidated quality-controlled benchmark |
| `pnad_refined_all_schema.csv` | variable-level data dictionary for the refined Parquet |
| `pnad_trusted_all_schema.csv` | variable-level data dictionary for the trusted Parquet |
| `pnad_annual_metadata.csv` | annual extraction, monetary, external-validation and trusted-treatment metadata |
| `pnad_datasets_metadata.csv` | dataset/file-level metadata for the two consolidated Parquets |
| `SHA256SUMS.txt` | SHA-256 integrity manifest for the archival package |

The two Parquets share the same record-level schema, currently `renda` and `ano`. Each available survey year occupies one Parquet row group. The collection contains repeated annual cross-sections rather than a longitudinal panel.

## Metadata hierarchy

`pnad_datasets_metadata.csv` describes the datasets themselves. It has one row for the refined product and one row for the trusted product and records the file name, processing level, source stage, row and column counts, survey-year coverage, row-group count, compression, file size, schema version, associated schema file, observation unit and weighting convention.

The two `*_schema.csv` files describe variables. Each row corresponds to one dataset column and records its description, logical and storage type, unit, provenance, construction stage and formula, nullability, valid/missing counts and number of distinct values.

`pnad_annual_metadata.csv` describes survey-year-specific provenance and treatment. It records the original PNAD/PNAD Continua income field, fixed-width extraction specification, missing-value convention, per-resident construction, contemporaneous currency, exchange factor, price-index factor, 2025 accounting adjustment, external Gini reference values, and the realized Stage-02 trusted-treatment audit.

The exchange-rate series is documented as Banco Central do Brasil SGS series 3692. The U.S. price-index series is the Bureau of Labor Statistics CPIAUCSL series distributed through FRED by the Federal Reserve Bank of St. Louis. These values are persisted in the repository metadata and are not fetched at Stage 04 runtime. IPEA and World Bank Gini series are external validation references only and do not determine the trusted cutoffs.

## Integrity and archival deposition

`src/build_release_manifest.py` computes SHA-256 digests for the canonical archival files and writes `SHA256SUMS.txt`. The same utility validates the manifest immediately after generation so that stale or altered package files are detected before deposition.

The intended Zenodo upload set and the recommended deposit metadata are documented in [`RELEASE.md`](RELEASE.md). DOI, release date, dataset version and the final data-license selection are intentionally completed only when the Zenodo record is finalized.

## Interpretation

`refined` is the preserved baseline before trusted-stage upper-tail treatment. `trusted` is the validated benchmark after structural cleaning and deterministic Stage-02 row selection. Stage 04 does not change the income values retained in either annual layer.

The record-level release does not contain the full original survey expansion weights or complex-design variables. Direct estimates from these Parquets are therefore record-weighted rather than official population-design-weighted estimates.

The 2015–2016 PNAD/PNAD Continua transition remains a methodological comparability boundary. Users requiring population-representative inference or survey-design reconstruction should return to the original IBGE microdata and corresponding annual documentation.
