# Source modules

<p align="justify">The <code>src</code> directory contains the canonical scientific workflow of the project. Modules are numbered according to the empirical procedure. Stages 00–02 construct the metadata, refined and trusted data layers; stage 03 applies the complete analytical pipeline independently to both refined and trusted distributions; later stages are reserved for manuscript-specific experiments.</p>

## Scientific pipeline

| Stage | Module | Scientific role | Main output |
| ---: | --- | --- | --- |
| 00 | <code>src/stage_00_build_metadata.py</code> | Consolidates historical PNAD/PNAD Contínua extraction specifications and monetary metadata | <code>data/metadata/df_metadata.xlsx</code> |
| 01 | <code>src/stage_01_build_refined_pnad.py</code> | Harmonizes original survey records into annual income datasets | <code>data/refined/pnad_refined_YYYY.parquet</code> |
| 02 | <code>src/stage_02_build_trusted_pnad.py</code> | Applies deterministic upper-tail treatment and distribution-level validation | <code>data/trusted/pnad_trusted_YYYY.parquet</code> and trusted audit tables |
| 03 | <code>src/stage_03_pnad_analysis.py</code> | Reproduces the complete general analysis independently for refined and trusted datasets | refined and trusted analytical figures and tables |
| 04 | <code>src/stage_04_pereira_ribeiro.py</code> | Reserved for the synthetic LS–MLE manuscript experiments | paper assets |
| 05 | <code>src/stage_05_moura_ribeiro.py</code> | Reserved for the Moura–Ribeiro replication and 1976–2025 extension | paper assets |

## Stage 02: trusted distributions

<p align="justify"><code>stage_02_build_trusted_pnad.py</code> converts the refined annual samples into the trusted analytical datasets. For each year it evaluates <code>z_i = log(1+x_i)</code>, estimates the robust center <code>m = median(z_i)</code> and scaled median absolute deviation <code>s = 1.4826 median|z_i-m|</code>, and defines the upper cutoff <code>x_c = exp(m+ks)-1</code>, with <code>k=6</code> by default. Non-finite and negative values are treated as structural invalids before statistical trimming. The resulting annual distributions must pass deterministic structural and numerical invariants before acceptance.</p>

The annual validation includes:

- non-empty refined, valid and trusted distributions;
- finite and non-negative valid/trusted income;
- consistency of the survey-year field;
- conservation of observation counts;
- finite and non-negative cutoff;
- maximum retained observation not exceeding the cutoff;
- structural-invalid and statistical-outlier counts;
- removal rates;
- before/after mean and median changes;
- detailed raw, valid and trusted distribution summaries.

<p align="justify">The stage writes <code>trusted_trim_audit_annual.csv</code> and <code>trusted_distribution_tests_annual.csv</code> to <code>assets/tables_analysis_trusted</code>.</p>

## Stage 03: refined and trusted analyses

<p align="justify"><code>stage_03_pnad_analysis.py</code> is the script representation of the analytical content derived from <code>notebook/04_analise_pnad_refined.ipynb</code>. The same functions are executed independently on <code>data/refined</code> and <code>data/trusted</code>. This avoids methodological drift between the pre-trimming and post-trimming analyses and makes every difference attributable to the data layer rather than to different analytical code.</p>

| Analysis family | Contents |
| --- | --- |
| Sample diagnostics | annual counts, missing/zero/negative diagnostics and positive support |
| Descriptive statistics | nominal and adjusted mean, median, standard deviation, minima, maxima and sums |
| Histograms | reusable annual histogram datasets and log-frequency panels |
| Geometric binning | geometric edges, counts, arithmetic/geometric means, medians, standard deviations and CCDF |
| Distribution functions | empirical CCDF, log-log representation and <code>ln[ln(100 F(x))]</code> transformation |
| Lorenz geometry | Lorenz curves and detailed geometric construction |
| Inequality | Gini, Pietra, Kolkata and Zanardi indices |
| Concentration | top 10%, top 1% and top 0.1% income shares, plus a combined mean/median and top-share two-panel figure |
| Longitudinal series | annual mean/median and combined/separate inequality-index panels |
| External validation | calculated Gini versus IPEA and World Bank series |
| Gompertz–Pareto | Gompertz LS body fit and Pareto LS tail fit evaluated from the empirical CCDF, cutoff search and annual fitted curves |

<p align="justify">Refined outputs use the <code>refined_analysis_</code> prefix and are written to <code>assets/figures_analysis_refined</code> and <code>assets/tables_analysis_refined</code>. Trusted outputs use the <code>trusted_analysis_</code> prefix and are written to <code>assets/figures_analysis_trusted</code> and <code>assets/tables_analysis_trusted</code>. Tables with exactly one record per survey year use the <code>_annual</code> suffix.</p>

## Synthetic LS–MLE experiment

<p align="justify"><code>synthetic.py</code> implements a controlled comparison between a deterministic power-law relation and a probabilistic Pareto model. The experiment is independent of the numbered PNAD stages. A single pseudo-random stream <code>U_i ~ U(0,1)</code> is generated with seed <code>20260902</code>, and all reported sample sizes are nested prefixes of this same stream. The design uses <code>beta = 10</code>, <code>alpha_0 = 2.5</code> and <code>x_t = 1</code>.</p>

The deterministic design is constructed as

$$
x_i = 1 + 19U_i,
\qquad
y_i = \beta x_i^{-\alpha_0},
$$

so that

$$
\ln y_i = \ln \beta - \alpha_0 \ln x_i.
$$

Consequently, ordinary least squares in log-log coordinates recovers the exact deterministic parameters, up to floating-point precision. The same uniform draws are also mapped into a Pareto random variable,

$$
X_i = x_t(1-U_i)^{-1/\alpha_0},
$$

whose complementary cumulative distribution is

$$
P(X\ge x)=\left(\frac{x}{x_t}\right)^{-\alpha_0},
\qquad x\ge x_t.
$$

The finite-sample corrected Pareto estimator used in the synthetic comparison is

$$
\widetilde{\alpha}_{\mathrm{MLE}}
=
\frac{n-1}
{\displaystyle\sum_{i=1}^{n}\ln(X_i/x_t)},
$$

while the same Pareto-form statistic applied directly to the deterministic design coordinates is

$$
\widetilde{\alpha}_{\mathrm{design}}
=
\frac{n-1}
{\displaystyle\sum_{i=1}^{n}\ln(x_i/x_t)}.
$$

This distinction is essential: the first estimator is applied to observations generated from a Pareto probability law; the second applies the same likelihood-derived formula to deterministic design coordinates that do not follow that sampling model.

### Pareto and exponential distributions

The exponential distribution provides a useful contrast because both models have simple CCDFs but different tail behavior and different linearizing transformations. For

$$
X\sim\mathrm{Exp}(\lambda),
$$

the probability density and CCDF are

$$
p(x)=\lambda e^{-\lambda x},
\qquad
P(X\ge x)=e^{-\lambda x},
\qquad x\ge0,
$$

and therefore

$$
\ln P(X\ge x)=-\lambda x.
$$

Thus, the exponential distribution is linear in a semi-log representation, whereas the Pareto distribution is linear in log-log coordinates:

$$
\ln P(X\ge x)
=
-\alpha\ln\left(\frac{x}{x_t}\right).
$$

| Aspect | Pareto | Exponential |
| --- | --- | --- |
| Random variable | $X\sim\mathrm{Pareto}(\alpha,x_t)$ | $X\sim\mathrm{Exp}(\lambda)$ |
| Support | $x\ge x_t>0$ | $x\ge0$ |
| PDF | $p(x)=\alpha x_t^\alpha x^{-(\alpha+1)}$ | $p(x)=\lambda e^{-\lambda x}$ |
| CCDF | $P(X\ge x)=(x/x_t)^{-\alpha}$ | $P(X\ge x)=e^{-\lambda x}$ |
| Tail type | Power law, heavy tail | Exponential, light tail |
| Log-linear form | $\ln P(X\ge x)=-\alpha\ln(x/x_t)$ | $\ln P(X\ge x)=-\lambda x$ |
| Linearization | log-log | semi-log |
| Parameter | $\alpha>0$ | $\lambda>0$ |
| Mean | $\alpha x_t/(\alpha-1)$, if $\alpha>1$ | $1/\lambda$ |
| Variance | $\alpha x_t^2/[(\alpha-1)^2(\alpha-2)]$, if $\alpha>2$ | $1/\lambda^2$ |
| Tail decay | Polynomial: $x^{-\alpha}$ | Exponential: $e^{-\lambda x}$ |
| Large values | Relatively frequent | Much rarer |

An exact connection between the models follows from the transformation

$$
Z=\ln\left(\frac{X}{x_t}\right).
$$

If $X\sim\mathrm{Pareto}(\alpha,x_t)$, then $Z\sim\mathrm{Exp}(\alpha)$. This relation explains why the logarithmic Pareto sufficient statistic is naturally connected to sums of exponential random variables.

<p align="justify">The script writes <code>assets/tables_synthetic/table_1.csv</code> for the fixed <code>n=50</code> realization and <code>assets/tables_synthetic/table_2.csv</code> for the nested samples <code>n = 50, 100, 200, 500, 1000</code>. It does not read PNAD data and does not execute the Gompertz–Pareto analyses of stage 03.</p>
