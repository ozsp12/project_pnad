"""Stage 05: presentation-only figures and paper tables from Stage-03 outputs."""
from pathlib import Path
import math
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import LogFormatterMathtext, LogLocator, NullFormatter

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "assets/tables_analysis_trusted"
FIGURES = ROOT / "assets/figures_paper"
TABLES_PAPER = ROOT / "assets/tables_paper"
TRUSTED = ROOT / "data/trusted"
METADATA = ROOT / "data/metadata/df_metadata.xlsx"
GDP = ROOT / "data/auxiliary/gdp_growth_brazil_1978_2025.csv"
START_YEAR, END_YEAR, MAX_PANELS, DPI = 1978, 2025, 12, 300
PAGE_SIZE, SINGLE_SIZE = (7.0, 9.5), (7.0, 4.5)
GOMPERTZ_OUT = TABLES_PAPER / "table_01_gompertz_annual.csv"
PARETO_OUT = TABLES_PAPER / "table_02_pareto_annual.csv"
ECONOMIC_OUT = TABLES_PAPER / "table_03_economic_inequality_annual.csv"
METADATA_OUT = TABLES_PAPER / "table_04_metadata.csv"
CANONICAL_TABLES = {p.name for p in (GOMPERTZ_OUT, PARETO_OUT, ECONOMIC_OUT, METADATA_OUT)}
mpl.rcParams.update({"font.family":"serif","font.size":8.5,"axes.titlesize":9,"axes.labelsize":9,
                     "xtick.labelsize":7,"ytick.labelsize":7,"legend.fontsize":7,
                     "figure.facecolor":"white","axes.facecolor":"white","savefig.facecolor":"white"})


def years_of(values): return sorted(int(y) for y in values if START_YEAR <= int(y) <= END_YEAR)
def groups(years):
    years = list(years); return [years[i:i+MAX_PANELS] for i in range(0, len(years), MAX_PANELS)]
def grid(n):
    if n > MAX_PANELS: raise ValueError(f"At most {MAX_PANELS} panels are allowed per image.")
    return plt.subplots(min(4, math.ceil(n/3)), 3, figsize=PAGE_SIZE, squeeze=False)
def style(ax, log=False):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(True, which="both" if log else "major", color="0.90", lw=.42)
    if log:
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(LogLocator(base=10, numticks=6)); axis.set_major_formatter(LogFormatterMathtext(base=10))
            axis.set_minor_locator(LogLocator(base=10, subs=np.arange(2,10)*.1, numticks=100)); axis.set_minor_formatter(NullFormatter())
def save(fig, stem, top=.985):
    FIGURES.mkdir(parents=True, exist_ok=True); fig.tight_layout(rect=(.025,.025,.995,top))
    fig.savefig(FIGURES/f"{stem}.png", dpi=DPI, pil_kwargs={"compress_level":9}); plt.close(fig)
def clean_figures():
    FIGURES.mkdir(parents=True, exist_ok=True)
    for p in FIGURES.iterdir():
        if p.is_file() and p.suffix.lower() in {".png",".svg",".pdf"}: p.unlink()
def family(years, stem, draw, xlabel, ylabel):
    for part, block in enumerate(groups(years),1):
        fig, axes = grid(len(block))
        for ax, year in zip(axes.ravel(), block): draw(ax, year); ax.set_title(str(year))
        for ax in axes.ravel()[len(block):]: ax.remove()
        fig.supxlabel(xlabel); fig.supylabel(ylabel); save(fig, f"{stem}_part_{part:02d}")

def _year_filter(df):
    df=df.copy(); df["year"]=pd.to_numeric(df["year"],errors="coerce").astype("Int64")
    return df[(df.year>=START_YEAR)&(df.year<=END_YEAR)].copy()
def load_inputs():
    stats=_year_filter(pd.read_csv(TABLES/"statistics_annual.csv")); lorenz=_year_filter(pd.read_csv(TABLES/"lorenz.csv"))
    g=_year_filter(pd.read_csv(TABLES/"gompertz_annual.csv")); p=_year_filter(pd.read_csv(TABLES/"pareto_annual.csv"))
    curves=_year_filter(pd.read_csv(TABLES/"gompertz_pareto_curves.csv")); meta=_year_filter(pd.read_excel(METADATA).rename(columns={"ano":"year","Exchange":"exchange"}))
    annual=g.merge(p,on="year",validate="one_to_one",suffixes=("","_pareto"))
    if "bootstrap_reps_pareto" in annual:
        if not np.array_equal(annual.bootstrap_reps, annual.bootstrap_reps_pareto): raise AssertionError("Bootstrap replication counts differ")
        annual=annual.drop(columns="bootstrap_reps_pareto")
    return stats,lorenz,annual,curves,meta
def income(year, positive=True):
    x=pd.to_numeric(pd.read_parquet(TRUSTED/f"pnad_trusted_{year}.parquet",columns=["renda"])["renda"],errors="coerce").to_numpy(float); x=x[np.isfinite(x)]
    return x[x>0] if positive else x

def line_figure(df, stem, series, ylabel, scale=1.):
    fig,ax=plt.subplots(figsize=SINGLE_SIZE)
    for i,(c,l) in enumerate(series): ax.plot(df.year,scale*df[c],ls=["-","--",":","-."][i%4],marker=["o","s","^","D"][i%4],ms=3,label=l)
    ax.set_xlabel("Year"); ax.set_ylabel(ylabel); style(ax); ax.legend(frameon=False); save(fig,stem)
def plot_histograms(years):
    def draw(ax,y):
        x=income(y,False); x=x[x>=0]; n,e=np.histogram(x,bins=100); ax.bar(e[:-1],n,width=np.diff(e),align="edge",facecolor="white",edgecolor="black",lw=.3); ax.set_yscale("log"); style(ax)
    family(years,"histograms",draw,"Income","Frequency (log)")
def plot_ccdf(curves,annual,years):
    fit=annual.set_index("year")
    def draw(ax,y):
        d=curves[(curves.year==y)&(curves.income_normalized>0)&(curves.empirical_ccdf_percent>0)]; ax.plot(d.income_normalized,d.empirical_ccdf_percent); ax.axvline(fit.loc[y,"transition_x_t"],ls=":"); ax.set_xscale("log"); ax.set_yscale("log"); style(ax,True)
    family(years,"ccdf_loglog",draw,"Normalized income","CCDF (%)")
def plot_lorenz(lorenz,years):
    def draw(ax,y):
        d=lorenz[lorenz.year==y]; ax.plot(100*d.population_share,100*d.income_share); ax.plot([0,100],[0,100],ls="--"); ax.set_xlim(0,100); ax.set_ylim(0,100); style(ax)
    family(years,"lorenz_geometry",draw,"Cumulative population (%)","Cumulative income (%)")
def plot_model_families(curves,annual,years):
    fit=annual.set_index("year")
    def exp(ax,y):
        r=fit.loc[y]; d=curves[(curves.year==y)&(curves.income_normalized<=r.gompertz_x_gmax)&(curves.empirical_ccdf_percent>0)]; x=d.income_normalized.to_numpy(float); ax.scatter(x,np.log(d.empirical_ccdf_percent),s=8); ax.plot(x,r.exponential_intercept-r.exponential_alpha*x); style(ax)
    def gom(ax,y):
        r=fit.loc[y]; d=curves[(curves.year==y)&(curves.income_normalized<=r.gompertz_x_gmax)&curves.gompertz_transform.notna()]; x=d.income_normalized.to_numpy(float); ax.scatter(x,d.gompertz_transform,s=8); ax.plot(x,r.gompertz_A-r.gompertz_B*x); ax.plot(x,r.gompertz_boundary_A_free-r.gompertz_boundary_B_free*x,ls="--"); style(ax)
    family(years,"exponential_fit",exp,"Normalized income",r"$\ln F(x)$"); family(years,"gompertz_ls_fit",gom,"Normalized income",r"$\ln[\ln F(x)]$")
    for method in ("ls","mle"):
        def draw(ax,y,method=method):
            r=fit.loc[y]; col=f"pareto_fitted_ccdf_percent_{method}"; xmin=min(r.transition_x_t,r.pareto_x_pmin) if method=="ls" else r.transition_x_t
            d=curves[(curves.year==y)&(curves.income_normalized>=xmin)&(curves.empirical_ccdf_percent>0)]; ax.scatter(d.income_normalized,d.empirical_ccdf_percent,s=8); ax.plot(d.income_normalized,d[col]); ax.set_xscale("log"); ax.set_yscale("log"); style(ax,True)
        family(years,f"pareto_{method}_fit",draw,"Normalized income","CCDF (%)")
def plot_income_stats(stats):
    line_figure(stats,"income_statistics",[("mean","Mean"),("median","Median"),("std","Std")],"2025 US$")
def plot_misc(stats,annual):
    line_figure(stats,"gini",[("Gini","Gini")],"Gini coefficient")
    line_figure(stats,"top_income_shares",[("top_10","Top 10%"),("top_1","Top 1%"),("top_01","Top 0.1%")],"Income share (%)",100)
    ex=stats.assign(p90_p99=stats.top_10-stats.top_1,p99_p999=stats.top_1-stats.top_01,p999_p100=stats.top_01)
    line_figure(ex,"top_income_exclusive_shares",[("p90_p99","90-99%"),("p99_p999","99-99.9%"),("p999_p100","99.9-100%")],"Income share (%)",100)
    line_figure(stats,"inequality_indices",[("Gini","Gini"),("Pietra","Pietra"),("Kolkata","Kolkata"),("Zanardi","Zanardi")],"Index")
    line_figure(annual,"pareto_income_share",[("pareto_income_share_pct","Pareto")],"Income share (%)")
    fig,ax=plt.subplots(figsize=SINGLE_SIZE); ax.plot(stats.year,stats["mean"],label="Mean"); ax.plot(stats.year,stats["median"],label="Median"); style(ax); ax.legend(); save(fig,"top_income_shares_mean_median")
    fig,axes=plt.subplots(2,2,figsize=(7,6));
    for ax,(c,s) in zip(axes.ravel(),[("Gini",1),("Zanardi",1),("Kolkata",100),("Pietra",100)]): ax.plot(stats.year,s*stats[c]); ax.set_title(c); style(ax)
    save(fig,"inequality_indices_grid")
    fig,ax=plt.subplots(figsize=SINGLE_SIZE); ax.plot(stats.year,stats.Gini,label="PNAD")
    for c,l in [("IPEA","IPEA"),("Banco_Mundial","World Bank")]:
        d=stats.dropna(subset=[c]); ax.plot(d.year,d[c],label=l)
    ax.legend(); style(ax); save(fig,"gini_validation")
    gdp=_year_filter(pd.read_csv(GDP)); line_figure(gdp,"gdp_growth",[("gdp_growth_pct","GDP")],"Real GDP growth (%)")

TABLE_DESCRIPTIONS={GOMPERTZ_OUT.name:"Annual Gompertz estimates and free-A/B diagnostics.",PARETO_OUT.name:"Annual Pareto LS/MLE estimates and uncertainties.",ECONOMIC_OUT.name:"Annual income and inequality statistics.",METADATA_OUT.name:"Data dictionary for paper tables."}

def build_gompertz_table(a):
    c=["year","gompertz_A","gompertz_B","gompertz_B_bootstrap_se","gompertz_boundary_A_free","gompertz_A_free_bootstrap_se","gompertz_boundary_B_free","gompertz_B_free_bootstrap_se","gompertz_x_gmax","transition_x_t","gompertz_r2","gompertz_population_pct","gompertz_income_share_pct","bootstrap_reps"]
    return a[c].sort_values("year").reset_index(drop=True)
def build_pareto_table(a):
    c=["year","pareto_x_pmin","transition_x_t","transition_delta_x_t","pareto_selection_status","pareto_supported","pareto_alpha_ls","pareto_alpha_ls_bootstrap_se","pareto_beta_ls","pareto_beta_ls_bootstrap_se","pareto_ls_r2","pareto_alpha_mle","pareto_alpha_mle_fisher_se","pareto_alpha_mle_likelihood_se","pareto_alpha_mle_bootstrap_se","pareto_beta_mle_continuity","pareto_beta_mle_likelihood_se","pareto_beta_mle_bootstrap_se","pareto_mle_r2","pareto_population_pct","pareto_income_share_pct","bootstrap_reps"]
    return a[c].sort_values("year").reset_index(drop=True)
PAPER_ECONOMIC_COLUMNS=["year","gdp_growth_pct","income_observation_n","income_mean_2025_usd","income_median_2025_usd","income_std_2025_usd","gini_pnad","pietra_pnad","kolkata_pnad","zanardi_pnad","gini_ipea","gini_world_bank","p90_p99_population_n","p90_p99_income_share_pct","p90_p99_mean_income_2025_usd","p90_p99_median_income_2025_usd","p90_p99_std_income_2025_usd","p99_p999_population_n","p99_p999_income_share_pct","p99_p999_mean_income_2025_usd","p99_p999_median_income_2025_usd","p99_p999_std_income_2025_usd","p999_p100_population_n","p999_p100_income_share_pct","p999_p100_mean_income_2025_usd","p999_p100_median_income_2025_usd","p999_p100_std_income_2025_usd"]
def build_economic_table(stats):
    d=_year_filter(stats).merge(_year_filter(pd.read_csv(GDP))[["year","gdp_growth_pct"]],on="year",how="left",validate="one_to_one").rename(columns={"Gini":"gini_pnad","Pietra":"pietra_pnad","Kolkata":"kolkata_pnad","Zanardi":"zanardi_pnad","IPEA":"gini_ipea","Banco_Mundial":"gini_world_bank"})
    for c in PAPER_ECONOMIC_COLUMNS:
        if c not in d: d[c]=np.nan
    return d[PAPER_ECONOMIC_COLUMNS].sort_values("year").reset_index(drop=True)
def _meta(table,column):
    unit="dimensionless"
    if column=="year": unit="year"
    elif column.endswith("_pct"): unit="%"
    elif column.endswith("_n") or column=="bootstrap_reps": unit="count"
    elif "2025_usd" in column: unit="2025 US$"
    elif column in {"gompertz_x_gmax","pareto_x_pmin","transition_x_t","transition_delta_x_t"}: unit="normalized income"
    elif "beta" in column: unit="CCDF-percent scale"
    elif column in {"pareto_selection_status"}: unit="text"
    elif column=="pareto_supported": unit="boolean"
    return {"table_name":table,"table_description":TABLE_DESCRIPTIONS[table],"column_name":column,"description":column.replace("_"," ").capitalize()+".","unit":unit,"source":"Stage 03 / Stage 05 consolidation"}
def build_metadata_table(tables):
    rows=[_meta(t,c) for t,f in tables.items() for c in f.columns]
    for c in ("table_name","table_description","column_name","description","unit","source"): rows.append({"table_name":METADATA_OUT.name,"table_description":TABLE_DESCRIPTIONS[METADATA_OUT.name],"column_name":c,"description":f"Metadata field {c}.","unit":"text","source":"paper table schema"})
    return pd.DataFrame(rows)
def validate_tables(g,p,e):
    m=g[["year","gompertz_income_share_pct"]].merge(p[["year","pareto_income_share_pct"]],on="year",validate="one_to_one")
    if not np.allclose(m.gompertz_income_share_pct+m.pareto_income_share_pct,100.,atol=1e-8): raise AssertionError("Gompertz and Pareto income shares must sum to 100%")
    if any(f.year.duplicated().any() for f in (g,p,e)): raise AssertionError("Annual paper tables must have unique years")
def build_paper_tables(stats=None,annual=None):
    if stats is None or annual is None: stats,_,annual,_,_=load_inputs()
    g,p,e=build_gompertz_table(annual),build_pareto_table(annual),build_economic_table(stats); validate_tables(g,p,e)
    md=build_metadata_table({GOMPERTZ_OUT.name:g,PARETO_OUT.name:p,ECONOMIC_OUT.name:e}); TABLES_PAPER.mkdir(parents=True,exist_ok=True)
    for q in TABLES_PAPER.glob("*.csv"): q.unlink()
    for q,f in ((GOMPERTZ_OUT,g),(PARETO_OUT,p),(ECONOMIC_OUT,e),(METADATA_OUT,md)): f.to_csv(q,index=False)
    if {q.name for q in TABLES_PAPER.glob("*.csv")}!=CANONICAL_TABLES: raise AssertionError("Unexpected paper table set")
    return {GOMPERTZ_OUT.name:g,PARETO_OUT.name:p,ECONOMIC_OUT.name:e,METADATA_OUT.name:md}

def main():
    clean_figures(); stats,lorenz,annual,curves,meta=load_inputs(); years=years_of(annual.year.dropna())
    plot_histograms(years); plot_income_stats(stats); plot_ccdf(curves,annual,years); plot_lorenz(lorenz,years); plot_model_families(curves,annual,years); plot_misc(stats,annual)
    out=build_paper_tables(stats,annual); print(f"Stage 05 publication assets generated for {len(years)} survey years."); return out

if __name__=="__main__": main()
