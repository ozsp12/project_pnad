# Zenodo dataset release guide

This directory is the archival data package for the PNAD/PNAD Continua income dataset. The repository should be frozen and all automated checks should pass before deposition.

## Files to upload

Upload the following files to the Zenodo dataset record:

- `README.md`;
- `pnad_refined_all.parquet`;
- `pnad_trusted_all.parquet`;
- `pnad_refined_all_schema.csv`;
- `pnad_trusted_all_schema.csv`;
- `pnad_annual_metadata.csv`;
- `pnad_datasets_metadata.csv`;
- `SHA256SUMS.txt`.

`SHA256SUMS.txt` is generated from the seven package files above other than the checksum file itself. It allows the archived files to be verified independently after download.

## Recommended Zenodo metadata

**Title**

Harmonized Brazilian PNAD and PNAD Continua Household Income Data, 1976–2025

**Resource type**

Dataset.

**Creators**

1. Beatriz Queiroz-Santos — Institute of Economics, Universidade Federal do Rio de Janeiro — ORCID 0009-0002-7287-5888.
2. Sharon Teles — Physics Institute, Universidade Federal do Rio de Janeiro — ORCID 0000-0003-4497-9161.
3. Osvaldo L. Santos-Pereira — Physics Institute, Universidade Federal do Rio de Janeiro — ORCID 0000-0003-2231-517X.
4. Everton M. C. Abreu — Physics Department, Universidade Federal Rural do Rio de Janeiro — ORCID 0000-0002-6638-2588.
5. Marcelo Byrro Ribeiro — Physics Institute, Universidade Federal do Rio de Janeiro — ORCID 0000-0002-6919-2624.

Marcelo Byrro Ribeiro is the corresponding author of the associated manuscript.

**Description**

Harmonized record-level household-income data derived from the Brazilian Pesquisa Nacional por Amostra de Domicilios (PNAD) and PNAD Continua, covering 45 available survey years from 1976 through 2025. The deposit contains a minimally transformed `refined` baseline and a quality-controlled `trusted` benchmark, together with variable-level schemas, annual extraction/monetary/treatment metadata, and dataset-level technical metadata. The observations are repeated annual cross-sections rather than a longitudinal panel. The released records do not contain the full original survey expansion weights or complex-sample design variables; direct estimates from the deposited Parquets are therefore record-weighted rather than official design-weighted population estimates.

**Keywords**

PNAD; PNAD Continua; Brazil; household income; income distribution; inequality; econophysics; reproducible research.

**Related software**

`https://github.com/ozsp12/project_pnad`

## Fields to complete at deposition

The following values should be added only when the archival record is finalized:

- dataset version;
- publication date;
- Zenodo concept DOI and version DOI;
- final data-license selection.

The repository software is distributed under the MIT License. The deposited data are derived from IBGE microdata, so the dataset license should be selected consistently with the applicable IBGE source-data terms rather than inferred automatically from the software license.

## Final repository update after Zenodo publication

After Zenodo assigns the DOI, update `CITATION.cff` and the root `README.md` with the dataset version, release date, and DOI. The Git tag/release should then identify the exact repository state corresponding to the deposited files.
