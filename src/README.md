# Source modules

<p align="justify">The <code>src</code> directory contains the canonical scientific workflow of the project. Stages 00–02 build the metadata and refined/trusted data layers, and stage 03 applies the full analytical pipeline independently to both distributions. <code>synthetic.py</code> is a standalone LS–MLE experiment independent of those PNAD stages. Stage 05 is the implemented manuscript-specific Moura Jr.–Ribeiro replication and extension.</p>

# Scientific pipeline

| Stage | Module | Scientific role | Main output |
| ---: | --- | --- | --- |
| 00 | <code>src/stage_00_build_metadata.py</code> | Consolidates historical PNAD/PNAD Contínua extraction specifications and monetary metadata | <code>data/metadata/df_metadata.xlsx</code> |
| 01 | <code>src/stage_01_build_refined_pnad.py</code> | Harmonizes original survey records into annual income datasets | <code>data/refined/pnad_refined_YYYY.parquet</code> |
| 02 | <code>src/stage_02_build_trusted_pnad.py</code> | Applies deterministic upper-tail treatment and distribution-level validation | <code>data/trusted/pnad_trusted_YYYY.parquet</code> and trusted audit tables |
| 03 | <code>src/stage_03_pnad_analysis.py</code> | Runs the complete general analysis and Moura–Ribeiro-inspired Gompertz–Pareto procedure independently for refined and trusted datasets | refined and trusted analytical figures and tables |
| 05 | <code>src/stage_05_moura_ribeiro.py</code> | Produces the Moura Jr.–Ribeiro (2009) replication/extension from the refined analytical baseline | <code>assets/figures_paper/</code> and <code>assets/tables_paper/</code> |

<p align="justify"><code>src/synthetic.py</code> is intentionally not numbered as a PNAD stage. It is an independent manuscript experiment and writes only to the synthetic asset directories.</p>

# Stage 02: trusted distributions

<p align="justify"><code>stage_02_build_trusted_pnad.py</code> converts the refined annual samples into the trusted analytical datasets. For each year it evaluates <code>z_i = log(1+x_i)</code>, estimates the robust center <code>m = median(z_i)</code> and scaled median absolute deviation <code>s = 1.4826 median|z_i-m|</code>, and defines the upper cutoff <code>x_c = exp(m+ks)-1</code>, with <code>k=6</code> by default. Non-finite and negative values are treated as structural invalids before statistical trimming. The resulting annual distributions must pass deterministic structural and numerical invariants to be accepted.</p>

The annual validation includes non-empty refined/valid/trusted distributions, finite and non-negative income, consistency of survey year, conservation of observation counts, cutoff checks, removal rates, before/after mean and median changes, and detailed distribution summaries. The stage writes <code>trusted_trim_audit_annual.csv</code> and <code>trusted_distribution_tests_annual.csv</code> to <code>assets/tables_analysis_trusted</code>.

# Stage 03: refined and trusted analyses

<p align="justify"><code>stage_03_pnad_analysis.py</code> is the executable stage for the complete refined/trusted analysis. General descriptive statistics, histograms, Lorenz geometry, inequality indices, top-income shares, external Gini validation and common plotting utilities are retained in <code>stage_03_pnad_analysis_core.py</code>; the main stage applies those routines and implements the Gompertz–Pareto regime analysis following the operational methodology of Moura Jr. and Ribeiro, <em>European Physical Journal B</em> 67, 101–120 (2009). The same procedure is run independently on <code>data/refined</code> and <code>data/trusted</code>.</p>

| Analysis family | Contents |
| --- | --- |
| Sample diagnostics | annual counts, missing/zero/negative diagnostics and positive support |
| Descriptive statistics | nominal and adjusted mean, median, standard deviation, minima, maxima and sums |
| Histograms | reusable annual histogram datasets and log-frequency panels |
| Geometric binning | logarithmic edges with ratio <code>r = 1.10</code>, counts, arithmetic/geometric means, medians, standard deviations and CCDF |
| Distribution functions | empirical CCDF, log-log representation and <code>ln[ln(100 F(x))]</code> transformation |
| Lorenz geometry | Lorenz curves and detailed geometric construction |
| Inequality | Gini, Pietra, Kolkata and Zanardi indices |
| Concentration | top 10%, top 1% and top 0.1% income shares |
| External validation | calculated Gini versus IPEA and World Bank series |
| Gompertz–Pareto | normalized individual income, free Gompertz LS fit, explicit regime boundaries, Pareto LS and direct MLE |

<p align="justify">For the regime analysis, each positive adjusted individual income <code>x'</code> is normalized by the corresponding annual positive-income mean:</p>

$$
x=\frac{x'}{\langle x'\rangle}.
$$

The empirical CCDF is evaluated on logarithmically spaced thresholds

$$
x_j=x_{\min}(1.10)^j,
$$

and the Gompertz region is analyzed through

$$
\ln[\ln F(x)]=A-Bx.
$$

<p align="justify">Both <code>A</code> and <code>B</code> are estimated by ordinary least squares. Candidate prefixes are fitted successively, and <code>x_G,max</code> is the largest endpoint whose fitted intercept remains in <code>1.4 ≤ A ≤ 1.6</code>, with <code>B &gt; 0</code>. The theoretical normalization value <code>ln(ln 100)</code> is used only as a deterministic fallback reference if no candidate satisfies that interval.</p>

<p align="justify">The Pareto region is identified independently in log-log coordinates from</p>

$$
\ln F(x)=\ln\beta-\alpha\ln x.
$$

<p align="justify"><code>x_P,min</code> is the earliest admissible start with at least five logarithmic points and <code>R² ≥ 0.98</code>; otherwise the highest-<code>R²</code> tail is retained and flagged as a fallback. If the two regime boundaries differ,</p>

$$
x_t=\frac{x_{P,\min}+x_{G,\max}}{2},\qquad
\delta x_t=\frac{|x_{P,\min}-x_{G,\max}|}{2}.
$$

The direct Pareto maximum-likelihood estimate is

$$
\widehat\alpha_{\mathrm{MLE}}=
\frac{n_t}{\displaystyle\sum_{i=1}^{n_t}\ln(x_i/x_t)},
$$

with continuity normalization

$$
F_t=\exp[\exp(A-Bx_t)],\qquad
\beta_{\mathrm{MLE}}=F_t x_t^{\widehat\alpha_{\mathrm{MLE}}}.
$$

Population membership is evaluated directly from individual normalized observations, with <code>x &lt; x_t</code> assigned to Gompertz and <code>x ≥ x_t</code> to Pareto, so the two reported population percentages sum to 100%.

<p align="justify">Refined outputs use the <code>refined_analysis_</code> prefix under <code>assets/figures_analysis_refined</code> and <code>assets/tables_analysis_refined</code>. Trusted outputs use <code>trusted_analysis_</code> under the parallel trusted directories. Empirical CCDF tables use <code>_ccdf_empirical.csv</code>, and external Gini validation tables use <code>_gini_validation_vs_ipea_wb_annual.csv</code>.</p>

# Standalone synthetic LS–MLE experiment

<p align="justify"><code>synthetic.py</code> implements a controlled comparison between a deterministic power-law relation and a probabilistic Pareto model. It is independent of stages 00–03, reads no PNAD data and uses a single pseudo-random stream <code>U_i ~ U(0,1)</code> with seed <code>20260902</code>. All sample sizes are nested prefixes of the same stream. The design uses <code>beta = 10</code>, <code>alpha_0 = 2.5</code> and <code>x_t = 1</code>:</p>

$$
x_i=1+19U_i,\qquad y_i=\beta x_i^{-\alpha_0},
$$

$$
X_i=x_t(1-U_i)^{-1/\alpha_0}.
$$

The finite-sample corrected Pareto estimator used in the synthetic comparison is

$$
\widetilde{\alpha}_{\mathrm{MLE}}=
\frac{n-1}{\displaystyle\sum_{i=1}^{n}\ln(X_i/x_t)},
$$

while the same Pareto-form statistic applied directly to the deterministic design coordinates is

$$
\widetilde{\alpha}_{\mathrm{design}}=
\frac{n-1}{\displaystyle\sum_{i=1}^{n}\ln(x_i/x_t)}.
$$

<p align="justify">The script writes <code>assets/tables_synthetic/table_1.csv</code> for the fixed <code>n=50</code> realization and <code>assets/tables_synthetic/table_2.csv</code> for <code>n=50,100,200,500,1000</code>. Table 1 is sorted by <code>x_i</code> and then enumerated <code>i=1,...,50</code>. <code>assets/figures_synthetic/</code> is reserved for future synthetic figures and is not populated by the current script.</p>

# Stage 05: Moura–Ribeiro replication and extension

<p align="justify"><code>stage_05_moura_ribeiro.py</code> is implemented. It reproduces the organization of the four tables and fifteen figures of Moura Jr. & Ribeiro (2009) and extends the available PNAD series through 2025 without modifying stage 03. Its baseline is the refined analysis: it reads <code>assets/tables_analysis_refined</code> and accesses <code>data/refined</code> only where individual observations are required for the income-share decomposition.</p>

<p align="justify">Stage 05 uses <code>data/metadata/df_metadata.xlsx</code> as its canonical metadata source, taking the existing fields <code>ano</code>, <code>Currency</code> and <code>Exchange</code> without redefining their values or formulas. Figure 15 uses the persistent local World Bank/World Development Indicators series <code>NY.GDP.MKTP.KD.ZG</code> stored at <code>data/auxiliary/gdp_growth_brazil_1978_2025.csv</code>; no World Bank network request is made during stage execution.</p>

<p align="justify">Generated manuscript tables are written to <code>assets/tables_paper/</code>. The fifteen paper figures are written to <code>assets/figures_paper/</code> in SVG format only. <code>moura_ribeiro_2009_replication_manifest.csv</code> records the direct correspondence between the original table/figure numbering and the maintained assets.</p>
