# Data

<p align="justify">The <code>data</code> directory contains the empirical material used by the PNAD longitudinal research pipeline. The data are organized by scientific processing stage rather than by software abstraction. Historical metadata specify the survey-dependent income variables and extraction rules; refined datasets are the harmonized annual samples produced from the original PNAD and PNAD Contínua microdata; trusted datasets are the final annual analytical samples obtained after deterministic upper-tail quality control; and external reference series are kept separate so that comparisons do not obscure the provenance of the PNAD-derived quantities.</p>

| Directory | Content | Produced or consumed by |
| --- | --- | --- |
| <code>metadata/</code> | Annual extraction specifications, monetary metadata and processing summaries | <code>stage_00_build_metadata.py</code>, <code>stage_01_build_refined_pnad.py</code> |
| <code>refined/</code> | Harmonized annual PNAD/PNAD Contínua datasets | produced by <code>stage_01_build_refined_pnad.py</code> |
| <code>data_trusted/</code> | Annual datasets after deterministic log-MAD upper-tail treatment | produced by <code>stage_02_build_trusted_pnad.py</code>; consumed by <code>stage_03_pnad_analysis.py</code> |
| <code>trusted/</code> | Independent external reference series used for validation | consumed by <code>stage_03_pnad_analysis.py</code> |
| <code>raw/</code> | Local original microdata when the extraction pipeline is rerun | not versioned |

<p align="justify">The distinction between <code>refined</code> and <code>data_trusted</code> is substantive. The refined stage performs survey-specific harmonization and removal of structurally invalid or metadata-defined missing values. The trusted stage applies the explicitly documented annual statistical rule and verifies distribution-level invariants before a dataset is accepted for downstream analysis. This separation allows every empirical transformation to be audited independently.</p>
