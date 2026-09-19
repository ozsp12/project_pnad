# Metadata

<p align="justify"><code>df_metadata.xlsx</code> and <code>df_metadata.csv</code> are generated together by <code>src/stage_00_build_metadata.py</code>. They contain the same annual PNAD/PNAD Contínua extraction specifications and monetary fields used by the cross-year analytical normalization. The Excel file remains the canonical input consumed by the analytical pipeline, while the CSV mirror is versioned for direct inspection through the GitHub web interface.</p>

<p align="justify">The <code>Build metadata</code> GitHub Actions workflow runs with Python 3.12, regenerates both files from Stage 00, validates them against <code>build_metadata_df()</code>, and commits refreshed artifacts only when their generated content changes. The metadata files should therefore not be edited manually.</p>

## Monetary fields

| Field | Meaning in the current code |
| --- | --- |
| <code>Exchange</code> | Annual exchange factor used by Stage 03 when converting nominal income before the 2025 price adjustment. |
| <code>Index</code> | Annual price-index level stored in the metadata series and used to derive the 2025 normalization factor. |
| <code>Adjust2025</code> | Relative adjustment to the 2025 index level, computed as <code>Index_2025 / Index_year - 1</code>. |
| <code>Inflation</code> | Multiplicative 2025 adjustment factor, computed as <code>Adjust2025 + 1 = Index_2025 / Index_year</code>. |

<p align="justify">The current Stage-03 transformation for adjusted income is <code>income_adjusted = income_nominal / Exchange * Inflation</code>, producing the project's 2025-US$ analytical scale. This documentation records the transformation exactly as implemented; it does not modify the monetary series, values or formulas.</p>

## Provenance note

<p align="justify">The archival metadata identify the exchange-rate series as Banco Central do Brasil SGS series 3692 and the U.S. price-index series as the Bureau of Labor Statistics CPIAUCSL series distributed through FRED by the Federal Reserve Bank of St. Louis. The numerical <code>Exchange</code> and <code>Index</code> values are persisted in the repository and are not fetched dynamically during Stage 04.</p>
