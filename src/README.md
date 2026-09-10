# Source modules

<p align="justify">The <code>src</code> directory contains the canonical scientific workflow of the project. Stages 00–02 build metadata and the refined/trusted data layers; stage 03 applies the complete PNAD analysis independently to refined and trusted distributions; stage 05 generates publication assets for the Moura Jr.–Ribeiro replication and extension. <code>synthetic.py</code> is a standalone LS–MLE experiment and is intentionally independent of the numbered PNAD stages.</p>

## Scientific pipeline

| Stage | Module | Scientific role | Main output |
| ---: | --- | --- | --- |
| 00 | <code>src/stage_00_build_metadata.py</code> | Consolidates historical PNAD/PNAD Contínua extraction specifications and monetary metadata | <code>data/metadata/df_metadata.xlsx</code> |
| 01 | <code>src/stage_01_build_refined_pnad.py</code> | Harmonizes original survey records into annual income datasets | <code>data/refined/pnad_refined_YYYY.parquet</code> |
| 02 | <code>src/stage_02_build_trusted_pnad.py</code> | Applies deterministic upper-tail treatment and distribution-level validation | <code>data/trusted/pnad_trusted_YYYY.parquet</code> and trusted audit tables |
| 03 | <code>src/stage_03_pnad_analysis.py</code> | Applies the general analysis and Moura–Ribeiro Gompertz–Pareto procedure independently to refined and trusted datasets | refined/trusted analytical figures and tables |
| 05 | <code>src/stage_05_moura_ribeiro.py</code> | Produces the implemented Moura Jr.–Ribeiro (2009) replication and extension through 2025 | <code>assets/figures_paper/</code> and <code>assets/tables_paper/</code> |
| — | <code>src/synthetic.py</code> | Standalone controlled LS–MLE experiment; independent of PNAD stages | <code>assets/tables_synthetic/table_1.csv</code> and <code>table_2.csv</code> |

## Stage 02: trusted distributions

<p align="justify"><code>stage_02_build_trusted_pnad.py</code> converts refined annual samples into trusted analytical datasets. For each year it evaluates <code>z_i = log(1+x_i)</code>, estimates the robust center <code>m = median(z_i)</code> and scaled median absolute deviation <code>s = 1.4826 median|z_i-m|</code>, and defines the upper cutoff <code>x_c = exp(m+ks)-1</code>, with <code>k=6</code> by default. Non-finite and negative values are treated as structural invalids before statistical trimming. The stage writes <code>trusted_trim_audit_annual.csv</code> and <code>trusted_distribution_tests_annual.csv</code> to <code>assets/tables_analysis_trusted</code>.</p>

## Stage 03: refined and trusted analyses

<p align="justify"><code>stage_03_pnad_analysis.py</code> is the executable stage for the complete refined/trusted analysis. General descriptive statistics, histograms, Lorenz geometry, inequality indices, top-income shares, external Gini validation and common plotting utilities are retained in <code>stage_03_pnad_analysis_core.py</code>; the main stage applies those routines and implements the Gompertz–Pareto regime analysis following the operational methodology of Moura Jr. and Ribeiro, <em>European Physical Journal B</em> 67, 101–120 (2009). The same procedure is run independently on <code>data/refined</code> and <code>data/trusted</code>.</p>

The regime analysis uses normalized individual income

$$
x=\frac{x'}{\langle x'\rangle},
$$

and the empirical CCDF is evaluated on logarithmically spaced thresholds with

$$
x_j=x_{\min}(1.10)^j.
$$

The Gompertz diagnostic is

$$
\ln[\ln F(x)]=A-Bx.
$$

Both <code>A</code> and <code>B</code> are estimated by ordinary least squares. Candidate prefixes are fitted successively and <code>x_G,max</code> is defined as the largest endpoint whose fitted intercept satisfies <code>1.4 ≤ A ≤ 1.6</code>, with <code>B &gt; 0</code>. The theoretical value <code>ln(ln 100)</code> is used only as a fallback reference if no candidate satisfies that interval.</p>

The Pareto region is diagnosed through

$$
\ln F(x)=\ln\beta-\alpha\ln x.
$$

<p align="justify"><code>x_P,min</code> is the earliest admissible start of a positive Pareto tail with at least five logarithmic points and <code>R² ≥ 0.98</code>; otherwise the highest-<code>R²</code> candidate is retained and explicitly flagged. When the two empirical regime boundaries differ,</p>

$$
x_t=\frac{x_{P,\min}+x_{G,\max}}{2},
\qquad
\delta x_t=\frac{|x_{P,\min}-x_{G,\max}|}{2}.
$$

The direct Pareto maximum-likelihood estimate is

$$
\widehat\alpha_{\mathrm{MLE}}
=
\frac{n_t}{\displaystyle\sum_{i=1}^{n_t}\ln(x_i/x_t)},
$$

with continuity normalization

$$
F_t=\exp\!\left[\exp(A-Bx_t)\right],
\qquad
\beta_{\mathrm{MLE}}=F_t x_t^{\widehat\alpha_{\mathrm{MLE}}}.
$$

<p align="justify">Population membership is evaluated from individual normalized observations using <code>x_t</code>. The annual <code>*_analysis_gompertz_pareto_annual.csv</code> files contain the fitted Gompertz and Pareto parameters, regime boundaries, fit diagnostics, population counts and complementary population percentages. The empirical CCDF tables use the explicit <code>_ccdf_empirical.csv</code> suffix.</p>

## Standalone synthetic LS–MLE experiment

<p align="justify"><code>synthetic.py</code> implements the controlled synthetic comparison. It does not read PNAD data and does not call stages 00–05. A single pseudo-random stream <code>U_i ~ U(0,1)</code> is generated with seed <code>20260902</code>; all reported sample sizes are nested prefixes of this stream. The deterministic design uses <code>beta = 10</code>, <code>alpha_0 = 2.5</code> and <code>x_t = 1</code>:</p>

$$
x_i=1+19U_i,
\qquad
y_i=\beta x_i^{-\alpha_0},
$$

and the same uniforms generate the Pareto observations

$$
X_i=x_t(1-U_i)^{-1/\alpha_0}.
$$

The finite-sample corrected estimator used in the synthetic comparison is

$$
\widetilde{\alpha}_{\mathrm{MLE}}
=
\frac{n-1}{\displaystyle\sum_{i=1}^{n}\ln(X_i/x_t)}.
$$

<p align="justify">The script writes <code>assets/tables_synthetic/table_1.csv</code> for the fixed <code>n=50</code> realization and <code>assets/tables_synthetic/table_2.csv</code> for <code>n=50,100,200,500,1000</code>. Table 1 is sorted by <code>x_i</code> and its display index <code>i</code> is numbered sequentially from 1 through 50 after sorting. <code>assets/figures_synthetic/</code> is reserved for future synthetic figures.</p>

## Stage 05: Moura Jr.–Ribeiro replication and extension

<p align="justify"><code>stage_05_moura_ribeiro.py</code> is implemented. It produces the publication-specific replication/extension of Moura Jr. and Ribeiro (2009) over the available 1978–2025 PNAD series. It reuses the refined stage-03 analytical assets and reads refined annual Parquet files only where the income-share decomposition requires individual observations; it does not alter stage-03 results or rebuild refined/trusted data.</p>

<p align="justify">Stage 05 uses <code>data/metadata/df_metadata.xlsx</code> as the canonical metadata source. The fields <code>ano</code>, <code>Currency</code> and <code>Exchange</code> provide the year, currency and exchange information used in Table 1 of the replication. The GDP-growth input for Fig. 15 is the local snapshot <code>data/auxiliary/gdp_growth_brazil_1978_2025.csv</code>, containing the World Bank/WDI indicator <code>NY.GDP.MKTP.KD.ZG</code>. Stage 05 performs no network request at runtime.</p>

<p align="justify">Publication tables are written to <code>assets/tables_paper/</code>. Publication figures are written to <code>assets/figures_paper/</code> in SVG format only. The replication manifest lists the SVG figure assets and the generated CSV tables.</p>

## Dependency reproducibility

<p align="justify"><code>requirements.txt</code> remains the simple installation specification used by normal execution and existing workflows. <code>requirements-lock.txt</code> records the runtime dependency versions actually resolved on CPython 3.12.14 under Ubuntu 24.04 in GitHub Actions on 2026-09-10. It is a reproducibility snapshot and is not required by the workflows.</p>
