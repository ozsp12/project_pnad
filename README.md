# PNAD Longitudinal Income Research

## Overview

This repository contains the reproducible data-construction and analysis workflow for a harmonized record-level household-income dataset derived from the Brazilian *Pesquisa Nacional por Amostra de Domicílios* (PNAD) and *PNAD Contínua*. The project covers all 45 available survey years between 1976 and 2025 and preserves the explicit survey gaps in 1980, 1991, 1994, 2000, and 2010.

The released records are repeated annual cross-sections rather than a longitudinal panel. The workflow harmonizes year-specific income fields into a common analytical structure, preserves a minimally transformed `refined` baseline, constructs a quality-controlled `trusted` benchmark, and produces documented cross-year data products suitable for scientific reuse and archival deposition.

The research is developed in the context of econophysics and income-distribution studies at the Federal University of Rio de Janeiro and collaborating institutions. The research group is led by **Marcelo Byrro Ribeiro**, who is also the corresponding author of the associated manuscript. The current manuscript author list and affiliations are documented below.

## Research team

| Researcher | Affiliation | Contact | ORCID |
| --- | --- | --- | --- |
| Beatriz Queiroz-Santos | Institute of Economics, Universidade Federal do Rio de Janeiro, Rio de Janeiro, Brazil | beatriz.santos@graduacao.ie.ufrj.br | [0009-0002-7287-5888](https://orcid.org/0009-0002-7287-5888) |
| Sharon Teles | Physics Institute, Universidade Federal do Rio de Janeiro, Rio de Janeiro, Brazil | steles.ts@gmail.com | [0000-0003-4497-9161](https://orcid.org/0000-0003-4497-9161) |
| Osvaldo L. Santos-Pereira | Physics Institute, Universidade Federal do Rio de Janeiro, Rio de Janeiro, Brazil | olsp@if.ufrj.br | [0000-0003-2231-517X](https://orcid.org/0000-0003-2231-517X) |
| Everton M. C. Abreu | Physics Department, Universidade Federal Rural do Rio de Janeiro, Seropédica, Brazil | — | [0000-0002-6638-2588](https://orcid.org/0000-0002-6638-2588) |
| Marcelo Byrro Ribeiro | Physics Institute, Universidade Federal do Rio de Janeiro, Rio de Janeiro, Brazil | mbr@if.ufrj.br | [0000-0002-6919-2624](https://orcid.org/0000-0002-6919-2624) |

## Scientific scope

The harmonized target is household income expressed on a per-resident basis when required by the original survey field. PNAD and PNAD Contínua use different survey designs and income constructions, so the 2015–2016 transition is retained as an explicit comparability boundary rather than treated as a measurement-equivalent continuation.

The processed research datasets do not retain the full original survey expansion weights and complex-design variables. Statistics computed directly from the released records are therefore record-weighted and should not be interpreted as official design-weighted population estimates. External IPEA and World Bank Gini series are used only as validation references.

## Scientific pipeline

| Stage | Main role | Output |
| ---: | --- | --- |
| 00 | annual extraction and monetary metadata | `data/metadata/` |
| 01 | raw fixed-width records → harmonized annual baseline | `data/refined/` |
| 02 | structural cleaning, deterministic upper-tail treatment, validation | `data/trusted/`, validation tables |
| 03 | descriptive, inequality, CCDF and Gompertz–Pareto analysis | analytical tables and figures |
| 04 | cross-year consolidation and publication metadata | `data/analytics/` |
| 05 | paper-facing figures and tables | publication assets |

The two principal consolidated record-level products are `data/analytics/pnad_refined_all.parquet` and `data/analytics/pnad_trusted_all.parquet`. They share the same schema (`renda`, `ano`). Stage 04 also publishes dataset-level metadata, variable-level schema dictionaries, and annual extraction, monetary, validation and treatment metadata.

## Repository documentation

Detailed technical documentation is intentionally kept close to the corresponding material:

- [`src/README.md`](src/README.md): scientific stages, methods, execution contracts, tests and automation;
- [`data/README.md`](data/README.md): raw/refined/trusted/analytics layers, metadata, provenance and dataset interpretation;
- [`data/analytics/README.md`](data/analytics/README.md): consolidated Parquets and metadata hierarchy;
- [`assets/README.md`](assets/README.md): analytical, validation and publication assets;
- [`data/metadata/README.md`](data/metadata/README.md): extraction and monetary metadata.

## Reproducible execution

The repository targets Python 3.12 and pins direct runtime and test dependencies in `requirements.txt`.

```bash
pip install -r requirements.txt
```

With the persisted refined layer available, the downstream workflow is:

```bash
python src/stage_02_build_trusted_pnad.py
python src/stage_03_pnad_analysis.py
python src/stage_04_build_analytic_pnad.py
python src/stage_05_publication.py
```

Reconstruction from the original IBGE fixed-width files is documented in Stage 01; the approximately 20 GB local raw-data collection is deliberately not versioned in this repository.

## Citation and license

Citation metadata are provided in [`CITATION.cff`](CITATION.cff). The software is released under the MIT License. Original PNAD and PNAD Contínua microdata remain subject to the terms and conditions of the Instituto Brasileiro de Geografia e Estatística (IBGE). Dataset and code persistent identifiers will be recorded with the frozen archival release.
