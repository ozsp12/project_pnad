# Data

<p align="justify">The <code>data</code> directory contains the empirical material used by the PNAD longitudinal research pipeline. Data are organized by scientific processing stage. The refined and trusted directories represent two distinct versions of the same annual income samples, while auxiliary external series remain isolated from PNAD-derived data.</p>

| Directory | Content | Produced or consumed by |
| --- | --- | --- |
| <code>metadata/</code> | Annual extraction specifications, monetary metadata and processing summaries | stages 00, 01 and 03 |
| <code>refined/</code> | Harmonized annual PNAD/PNAD Contínua datasets before trusted-stage trimming | produced by stage 01; consumed by stages 02 and 03 |
| <code>trusted/</code> | Annual datasets after structural cleaning, log-MAD upper-tail treatment and validation | produced by stage 02; consumed by stage 03 and paper-specific stages |
| <code>auxiliary/</code> | Independent external reference series, currently including IPEA and World Bank Gini data | consumed by stage 03 |
| <code>raw/</code> | Local original microdata when the extraction pipeline is rerun | not versioned |

<p align="justify">The distinction between <code>refined</code> and <code>trusted</code> is substantive. The refined layer preserves the harmonized annual samples before the trusted-stage statistical treatment. The trusted layer excludes structural invalids, applies the documented log-MAD upper cutoff and verifies distribution-level invariants. Stage 03 analyzes both layers using identical analytical functions, allowing direct before/after comparison without changing the methodology.</p>
