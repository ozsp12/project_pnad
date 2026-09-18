# Zenodo dataset release

This directory contains the archival data package corresponding to repository release **v1.0.0**.

## Release metadata

- Version: `1.0.0`
- Publication date: `2026-09-18`
- Zenodo record: https://zenodo.org/records/22836608
- Version DOI: `10.5281/zenodo.22836608`
- Resource type: Dataset

## Archived files

The Zenodo dataset package consists of:

- `README.md`;
- `pnad_refined_all.parquet`;
- `pnad_trusted_all.parquet`;
- `pnad_refined_all_schema.csv`;
- `pnad_trusted_all_schema.csv`;
- `pnad_annual_metadata.csv`;
- `pnad_datasets_metadata.csv`;
- `SHA256SUMS.txt`.

`SHA256SUMS.txt` contains SHA-256 hashes for the seven package files other than the checksum file itself and permits independent integrity verification after download.

## Dataset title

**Harmonized PNAD and PNAD Contínua Household Income Microdata for Brazil, 1976–2025**

## Creators

1. Beatriz Queiroz-Santos — Institute of Economics, Universidade Federal do Rio de Janeiro — ORCID 0009-0002-7287-5888.
2. Sharon Teles — Physics Institute, Universidade Federal do Rio de Janeiro — ORCID 0000-0003-4497-9161.
3. Osvaldo L. Santos-Pereira — Physics Institute, Universidade Federal do Rio de Janeiro — ORCID 0000-0003-2231-517X.
4. Everton M. C. Abreu — Physics Department, Universidade Federal Rural do Rio de Janeiro — ORCID 0000-0002-6638-2588.
5. Marcelo Byrro Ribeiro — Physics Institute, Universidade Federal do Rio de Janeiro — ORCID 0000-0002-6919-2624.

Marcelo Byrro Ribeiro is the corresponding author of the associated manuscript.

## Description

Harmonized record-level household-income data derived from the Brazilian Pesquisa Nacional por Amostra de Domicílios (PNAD) and PNAD Contínua, covering 45 available survey years from 1976 through 2025. The deposit contains a minimally transformed `refined` baseline and a quality-controlled `trusted` benchmark, together with variable-level schemas, annual extraction/monetary/treatment metadata, dataset-level technical metadata, and SHA-256 integrity checksums.

The observations are repeated annual cross-sections rather than a longitudinal panel. The released records do not contain the full original survey expansion weights or complex-sample design variables; direct estimates from the deposited Parquets are therefore record-weighted rather than official design-weighted population estimates. IPEA and World Bank Gini series are retained only as external validation references and do not determine the trusted-layer treatment.

The original IBGE fixed-width microdata are not redistributed in the Zenodo deposit. The complete reconstruction and validation workflow is maintained in this repository.

## Keywords

PNAD; PNAD Contínua; Brazil; household income; income distribution; inequality; econophysics; reproducible research.

## Licensing

The repository software is distributed under the MIT License. The deposited harmonized dataset is licensed separately in the Zenodo record. The original PNAD and PNAD Contínua source microdata remain attributable to and governed by the Instituto Brasileiro de Geografia e Estatística (IBGE).

## Repository correspondence

The GitHub repository state corresponding to this archival release is identified as version `v1.0.0`. Repository citation metadata are maintained in the root `CITATION.cff`.
