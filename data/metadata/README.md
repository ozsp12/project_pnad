# Metadata

<p align="justify"><code>df_metadata.xlsx</code> and <code>df_metadata.csv</code> are generated together by <code>src/stage_00_build_metadata.py</code>. They contain the same annual PNAD/PNAD Contínua extraction specifications and monetary fields used by the longitudinal normalization. The Excel file remains the canonical input consumed by Stage 01, while the CSV mirror is versioned for direct inspection through the GitHub web interface.</p>

## Monetary fields

| Field | Meaning in the current code |
| --- | --- |
| <code>Exchange</code> | Annual exchange factor used by stage 03 when converting nominal income before the 2025 price adjustment. |
| <code>Index</code> | Annual price-index level stored in the metadata series and used to derive the 2025 normalization factor. |
| <code>Adjust2025</code> | Relative adjustment to the 2025 index level, computed as <code>Index_2025 / Index_year - 1</code>. |
| <code>Inflation</code> | Multiplicative 2025 adjustment factor, computed as <code>Adjust2025 + 1 = Index_2025 / Index_year</code>. |

<p align="justify">The current stage-03 transformation for adjusted income is <code>income_adjusted = income_nominal / Exchange * Inflation</code>, producing the project's 2025-US$ analytical scale. This documentation records the transformation exactly as implemented; it does not modify the monetary series, values or formulas.</p>

## Provenance note

<p align="justify">The repository currently stores the numerical <code>Exchange</code> and <code>Index</code> series in <code>stage_00_build_metadata.py</code>, but the exact documentary provenance of those two historical series is not recorded alongside the code. That source documentation should be added when the original references are identified. No bibliographic source or URL is inferred here.</p>
