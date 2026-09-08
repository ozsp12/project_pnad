# PNAD Longitudinal Income Research

<p align="justify">This repository provides a compact and reproducible scientific workflow for longitudinal research on the Brazilian income distribution using the Pesquisa Nacional por Amostra de Domicílios (PNAD) and PNAD Contínua. The empirical series covers the available surveys from 1976 through 2025 and is organized as a sequence of explicit transformations: historical survey metadata are consolidated, annual microdata are harmonized into refined income samples, each annual distribution is subjected to deterministic quality control to produce the trusted analytical datasets, and the resulting distributions are characterized through descriptive statistics, empirical complementary cumulative distribution functions, geometric binning, Lorenz geometry, inequality and concentration measures, external validation and Gompertz–Pareto exploratory fits. The repository is intended primarily as research material and supplementary computational documentation for scientific manuscripts; its structure therefore favors transparent data provenance, numbered analytical stages and persistent tables and figures over software-package abstractions.</p>

## Scientific pipeline

<p align="justify">The source modules are numbered according to the order in which the empirical material is constructed and analyzed. Stages 00–02 define the data pipeline, stage 03 contains the complete general analysis derived from the original exploratory notebook, and subsequent stages are reserved for paper-specific experiments. This numbering makes the repository readable as a scientific procedure: each module has an identifiable input, transformation and output, while generated assets carry the same module prefix so that every table and figure can be traced directly to the code that produced it.</p>

| Stage | Module | Scientific role | Main output |
| ---: | --- | --- | --- |
| 00 | <code>src/stage_00_build_metadata.py</code> | Consolidates historical PNAD/PNAD Contínua extraction specifications and monetary metadata | <code>data/metadata/df_metadata.xlsx</code> |
| 01 | <code>src/stage_01_build_refined_pnad.py</code> | Harmonizes the original survey records into annual income datasets | <code>data/refined/pnad_refined_YYYY.parquet</code> |
| 02 | <code>src/stage_02_build_trusted_pnad.py</code> | Applies deterministic upper-tail treatment and distribution-level validation | <code>data/data_trusted/pnad_trusted_YYYY.parquet</code> and audit tables |
| 03 | <code>src/stage_03_pnad_analysis.py</code> | Reproduces the complete analytical content of notebook 04 | analytical figures and tables |
| 04 | <code>src/stage_04_pereira_ribeiro.py</code> | Reserved for the synthetic LS–MLE manuscript experiments | paper assets |
| 05 | <code>src/stage_05_moura_ribeiro.py</code> | Reserved for the Moura–Ribeiro replication and 1976–2025 extension | paper assets |

## Data and analyses

<p align="justify">Survey definitions are not assumed to be constant through time. The historical PNAD series and the later PNAD Contínua use different variables, layouts and survey regimes, and these differences remain explicit in the metadata rather than being hidden inside a nominally homogeneous dataset. The trusted analytical layer is created only after the refined annual samples pass deterministic checks for finite and non-negative income values, consistency of the survey year, observation counts and the upper-tail cutoff. The general analysis then computes annual descriptive statistics, linear and geometric histogram representations, empirical CCDFs, the double-log Gompertz transformation, Lorenz curves, Gini, Pietra, Kolkata and Zanardi indices, top-income shares, temporal evolution of central tendency and inequality, comparison with external Gini series, and the Gompertz–Pareto least-squares regime analysis present in the original notebook.</p>

## Assets

<p align="justify">Generated research outputs are stored under <code>assets</code> and are separated according to scientific purpose. Complete diagnostics, validation material and intermediate numerical results belong to the analysis directories, whereas only results explicitly selected for manuscripts belong to the paper directories. Trusted-analysis figures and tables use the <code>trusted_analysis_</code> prefix, while trusted-data audit tables use the <code>trusted_</code> prefix. Tables consolidated to exactly one record per survey year additionally use the <code>_annual</code> suffix; for example <code>trusted_analysis_gini_validation.svg</code> or <code>pereira_ribeiro_estimator_comparison.csv</code>. This convention provides a direct provenance link between code and output without requiring a workflow framework.</p>

| Directory | Content |
| --- | --- |
| <code>assets/figures_analysis/</code> | Exploratory, diagnostic and validation figures stored as SVG evidence/artifacts |
| <code>assets/tables_analysis/</code> | Audits, complete results and intermediate analytical tables |
| <code>assets/figures_paper/</code> | Figures explicitly selected for manuscripts |
| <code>assets/tables_paper/</code> | Tables explicitly selected for manuscripts |

## Execution

<p align="justify">The repository uses a deliberately small Python environment. Install the dependencies listed in <code>requirements.txt</code> and execute the numbered modules in sequence according to the stage that must be reconstructed. Rebuilding the complete pipeline from original microdata requires the local PNAD files expected by stage 01; when the refined datasets are already available, execution may begin at stage 02, and when the trusted datasets are already available, the complete general analysis can be regenerated directly with stage 03.</p>

```bash
pip install -r requirements.txt
python src/stage_02_build_trusted_pnad.py
python src/stage_03_pnad_analysis.py
```

<p align="justify">The original notebooks are retained temporarily as methodological provenance while the numbered modules are validated against their outputs. They are not the canonical execution path of the repository. The authoritative computational workflow is the sequential source code under <code>src</code>, and the authoritative numerical outputs are the corresponding persistent assets.</p>
