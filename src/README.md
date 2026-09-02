# Source code

<p align="justify">The <code>src</code> directory contains the reproducible code used to construct the longitudinal PNAD metadata and the annual refined income datasets. The source layer is intentionally small. <code>build_metadata.py</code> defines the historical survey specifications and monetary reference series for 1976–2025, while <code>generate_datasets.py</code> uses those specifications to construct one harmonized income dataset for each available survey year. The scientific information that changes through time—survey variable names, field positions, missing-value codes, source locations, historical currencies, exchange rates, and CPI values—is centralized in the metadata rather than being distributed across separate year-specific scripts.</p>

## Modules

### `build_metadata.py`

<p align="justify"><code>build_metadata.py</code> constructs <code>data/metadata/df_metadata.xlsx</code>, the central specification table of the project. Each row corresponds to one year from 1976 through 2025. The table records the income variable (<code>var_renda</code>), its position and width (<code>pos_renda</code>, <code>tam_renda</code>), the household-size variable when required (<code>var_morador</code>, <code>pos_morador</code>, <code>tam_morador</code>), the official IBGE source URL (<code>link</code>), the expected raw-file organization (<code>raw_subdir</code>, <code>raw_pattern</code>, <code>n_files</code>), and the survey-specific missing-income sentinel (<code>missing_renda</code>). The same table also contains <code>Currency</code>, <code>Exchange</code>, <code>Index</code>, <code>Adjust2025</code>, and <code>Inflation</code>, which provide the monetary metadata required for later normalization and comparison across different Brazilian currency regimes.</p>

### `generate_datasets.py`

<p align="justify"><code>generate_datasets.py</code> is the Python-module version of the <code>01_gera_datasets.ipynb</code> workflow. Its main design principle is that no year-specific PNAD rule is hard-coded in the dataset-generation stage: the module reads the survey layout, missing-income convention, raw-file location and expected file count directly from <code>df_metadata.xlsx</code>. For every available survey year, the raw PNAD or PNAD Contínua source is reduced to a harmonized annual sample with the variables <code>renda</code> and <code>ano</code>, and the result is written to <code>data/refined/pnad_refined_&lt;year&gt;.parquet</code>. When household-size information is required by the historical income definition, the corresponding metadata are used to obtain per-capita income; otherwise the selected survey income field is retained directly. Missing-income sentinels and structurally invalid records are excluded according to the metadata, preserving a common longitudinal analytical variable while keeping the original survey definitions auditable.</p>

<p align="justify">The module also returns an annual processing summary containing the number of source files, raw observations, retained observations, missing-income records, invalid income fields, invalid household-size fields, whether a per-capita transformation was applied, processing time, and the output file name. This summary provides a compact audit trail for the raw-to-refined transformation and can be compared with the historical conversion summary stored under <code>data/metadata/</code>.</p>

## Survey variables

<p align="justify">The income variable is not stable across the PNAD historical record. The table below summarizes the fields currently adopted by the project. Years without a survey—1980, 1991, 1994, 2000, and 2010—remain represented in the metadata chronology but do not generate refined datasets.</p>

| Period | Income variable | Household-size variable when required |
| --- | --- | --- |
| 1976 | `V2954` | — |
| 1977 | `V131` | — |
| 1978 | `V2541` | — |
| 1979 | `V2517` | — |
| 1981 | `V5010` | `V9329` |
| 1982 | `V602` | — |
| 1983–1990 | `V5010` | `V9329` |
| 1992–2003 | `V4614` | `V0105` |
| 2004–2015 | `V4621` | — |
| 2016–2025 | `VD4019` | — |

## Primary data sources

<p align="justify">The original microdata are obtained from the Instituto Brasileiro de Geografia e Estatística (IBGE). Historical annual PNAD files are available through the <a href="https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_anual/microdados/">PNAD annual microdata archive</a>. From 2016 onward, the project uses the <a href="https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Trimestral/Microdados/">PNAD Contínua quarterly microdata archive</a>. The exact year-specific URL used by the pipeline is stored in the <code>link</code> column of <code>df_metadata</code>, including the reweighted PNAD files for 2001–2012 and the specific archive files adopted for later annual PNAD releases.</p>

<p align="justify">The monetary metadata use two external macroeconomic sources. Historical period-average United States dollar exchange-rate values are associated with <a href="https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarValores">Banco Central do Brasil SGS series 3698</a>, and the price index is based on the <a href="https://fred.stlouisfed.org/series/CPIAUCSL">FRED CPIAUCSL Consumer Price Index for All Urban Consumers</a>. For a year <i>t</i>, the metadata define <code>Inflation</code> as the ratio between the 2025 CPI index and the CPI index of year <i>t</i>, with <code>Adjust2025 = Inflation - 1</code>. These quantities are retained as metadata for downstream normalization; they are not silently imposed during the raw-to-refined construction of the annual income samples.</p>

## Trusted reference data

<p align="justify">The repository keeps external validation series outside the processing pipeline under <code>data/trusted/</code>. The current file, <code>series_gini_ipea_banco_mundial.csv</code>, contains Gini-coefficient values from IPEA and the World Bank and is intended for comparison with inequality measures estimated from the PNAD-derived samples. The relevant public reference portals are <a href="http://www.ipeadata.gov.br/Default.aspx">Ipeadata</a> and the <a href="https://data.worldbank.org/indicator/SI.POV.GINI?locations=BR">World Bank Gini index for Brazil</a>.</p>

## Data products

<p align="justify">The metadata stage produces <code>data/metadata/df_metadata.xlsx</code>. The dataset stage produces <code>data/refined/pnad_refined_&lt;year&gt;.parquet</code> for every available survey year, with <code>renda</code> as the harmonized income variable and <code>ano</code> as the reference year. The repository also retains <code>data/metadata/df_summary_raw_to_refined.csv</code> as an audit summary of the historical conversion. Raw IBGE microdata are expected locally under <code>data/raw/</code> when the pipeline is rerun and are not treated as versioned research artifacts.</p>

## Current repository layout

```text
project_pnad/
├── data/
│   ├── metadata/
│   │   ├── df_summary_raw_to_refined.csv
│   │   └── pnad_metadata_old.csv
│   ├── refined/
│   │   └── pnad_refined_<year>.parquet
│   └── trusted/
│       └── series_gini_ipea_banco_mundial.csv
├── notebook/
│   └── 00_cria_metadata.ipynb
└── src/
    ├── README.md
    ├── build_metadata.py
    └── generate_datasets.py
```
