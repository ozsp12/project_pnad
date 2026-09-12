"""Publication visual layer for trusted PNAD outputs.

Stage 05 consumes only canonical trusted Stage 03 tables and trusted microdata.
It preserves a broad set of publication diagnostics in a monochrome style.
Multi-year families use at most 12 panels (3 x 4) per figure.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import LogFormatterMathtext, LogLocator, NullFormatter

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "assets" / "tables_analysis_trusted"
PAPER_TABLES = ROOT / "assets" / "tables_paper"
FIGURES = ROOT / "assets" / "figures_paper"
TRUSTED = ROOT / "data" / "trusted"
METADATA = ROOT / "data" / "metadata" / "df_metadata.xlsx"
GDP = ROOT / "data" / "auxiliary" / "gdp_growth_brazil_1978_2025.csv"

START_YEAR, END_YEAR = 1978, 2025
BOOTSTRAP_REPS = int(os.environ.get("PNAD_BOOTSTRAP_REPS", "1000"))
BOOTSTRAP_SEED = 20090101
MAX_PANELS = 12
PAGE_SIZE = (7.0, 9.5)
SINGLE_SIZE = (7.0, 4.5)
DPI = 300
BOOTSTRAP_OUT = PAPER_TABLES / "moura_ribeiro_2009_bootstrap_uncertainties_trusted_1978_2025.csv"

mpl.rcParams.update({
    "font.family": "serif", "font.size": 8.5, "axes.titlesize": 9,
    "axes.labelsize": 9, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "axes.edgecolor": "0.20", "axes.linewidth": 0.7,
    "xtick.color": "0.15", "ytick.color": "0.15", "text.color": "0.10",
    "axes.labelcolor": "0.10", "xtick.direction": "out", "ytick.direction": "out",
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def years_of(values):
    return sorted(int(y) for y in values if START_YEAR <= int(y) <= END_YEAR)


def groups(years):
    years = list(years)
    return [years[i:i + MAX_PANELS] for i in range(0, len(years), MAX_PANELS)]


def load_inputs():
    stats = pd.read_csv(TABLES / "statistics_annual.csv")
    lorenz = pd.read_csv(TABLES / "lorenz.csv")
    gompertz = pd.read_csv(TABLES / "gompertz_annual.csv")
    pareto = pd.read_csv(TABLES / "pareto_annual.csv")
    curves = pd.read_csv(TABLES / "gompertz_pareto_curves.csv")
    meta = pd.read_excel(METADATA).rename(columns={"ano": "year", "Exchange": "exchange"})
    annual = gompertz.merge(pareto, on="year", validate="one_to_one", suffixes=("", "_pareto"))
    frames = [stats, lorenz, annual, curves, meta]
    for frame in frames:
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
        frame.drop(frame[(frame["year"] < START_YEAR) | (frame["year"] > END_YEAR)].index, inplace=True)
    return stats, lorenz, annual, curves, meta


def income(year, positive=True):
    x = pd.to_numeric(
        pd.read_parquet(TRUSTED / f"pnad_trusted_{year}.parquet", columns=["renda"])["renda"],
        errors="coerce",
    ).to_numpy(float)
    x = x[np.isfinite(x)]
    return x[x > 0] if positive else x


def normalized_income(year):
    x = income(year)
    return x / x.mean()


def adjusted_income(year, meta_i, positive=True):
    x = income(year, positive)
    row = meta_i.loc[year]
    return x / float(row["exchange"]) * float(row["Inflation"])


def clean_figures():
    FIGURES.mkdir(parents=True, exist_ok=True)
    for p in FIGURES.iterdir():
        if p.is_file() and p.suffix.lower() in {".png", ".svg", ".pdf"}:
            p.unlink()


def style(ax, log=False):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.grid(True, which="both" if log else "major", color="0.90", lw=0.42)
    if log:
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(LogLocator(base=10, numticks=6))
            axis.set_major_formatter(LogFormatterMathtext(base=10, labelOnlyBase=True))
            axis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=100))
            axis.set_minor_formatter(NullFormatter())


def annotation(ax, text, x=0.05, y=0.08, ha="left"):
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va="bottom", fontsize=6.7,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="0.55", alpha=0.94))


def save(fig, stem, top=0.985):
    fig.tight_layout(rect=(0.025, 0.025, 0.995, top))
    fig.savefig(FIGURES / f"{stem}.png", dpi=DPI, pil_kwargs={"compress_level": 9})
    plt.close(fig)


def grid(n):
    if n > MAX_PANELS:
        raise ValueError(f"At most {MAX_PANELS} panels are allowed per image.")
    rows = min(4, math.ceil(n / 3))
    return plt.subplots(rows, 3, figsize=PAGE_SIZE, squeeze=False)


def global_legend(fig, axes, used, ncol=4):
    handles, labels, seen = [], [], set()
    for ax in axes.ravel()[:used]:
        for h, label in zip(*ax.get_legend_handles_labels()):
            if label and label not in seen:
                handles.append(h); labels.append(label); seen.add(label)
    if handles:
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.982),
                   ncol=min(ncol, len(handles)), frameon=False, handlelength=2.8)


def finish_grid(fig, axes, used, stem, xlabel, ylabel, legend=False, ncol=4):
    for ax in axes.ravel()[used:]:
        ax.remove()
    fig.supxlabel(xlabel, fontsize=9.5, y=0.005)
    fig.supylabel(ylabel, fontsize=9.5, x=0.006)
    if legend:
        global_legend(fig, axes, used, ncol)
    save(fig, stem, 0.92 if legend else 0.985)


def family(years, stem, draw, xlabel, ylabel, legend=False, ncol=4):
    out = []
    for part, grp in enumerate(groups(years), 1):
        name = f"{stem}_part_{part:02d}"
        fig, axes = grid(len(grp))
        for ax, year in zip(axes.ravel(), grp):
            draw(ax, year)
            ax.set_title(str(year), fontweight="semibold")
        finish_grid(fig, axes, len(grp), name, xlabel, ylabel, legend, ncol)
        out.append(name)
    return out


def bootstrap_line(x, y, rng):
    x, y = np.asarray(x, float), np.asarray(y, float)
    mask = np.isfinite(x) & np.isfinite(y); x, y = x[mask], y[mask]
    if len(x) < 3:
        return np.full(BOOTSTRAP_REPS, np.nan), np.full(BOOTSTRAP_REPS, np.nan)
    idx = rng.integers(0, len(x), size=(BOOTSTRAP_REPS, len(x)))
    xb, yb = x[idx], y[idx]
    xm, ym = xb.mean(1), yb.mean(1)
    den = ((xb - xm[:, None]) ** 2).sum(1)
    slope = np.divide(((xb - xm[:, None]) * (yb - ym[:, None])).sum(1), den,
                      out=np.full(BOOTSTRAP_REPS, np.nan), where=den > 0)
    return ym - slope * xm, slope


def bootstrap(curves, annual):
    rows = []; ai = annual.set_index("year")
    for year in years_of(annual["year"].dropna()):
        f = ai.loc[year]; rng = np.random.default_rng(BOOTSTRAP_SEED + year)
        xg = float(f["gompertz_x_gmax"])
        g = curves[(curves.year == year) & (curves.income_normalized <= xg) & curves.gompertz_transform.notna()]
        gi, gs = bootstrap_line(g.income_normalized, g.gompertz_transform, rng)
        xp = float(f["pareto_x_pmin"])
        p = curves[(curves.year == year) & (curves.income_normalized >= xp) & (curves.empirical_ccdf_percent > 0)]
        pi, ps = bootstrap_line(np.log(p.income_normalized), np.log(p.empirical_ccdf_percent), rng)
        xt = float(f["transition_x_t"]); x = normalized_income(year); z = np.log(x[x >= xt] / xt); n = len(z)
        if n < 2:
            am = np.full(BOOTSTRAP_REPS, np.nan)
        else:
            idx = rng.integers(0, n, size=(BOOTSTRAP_REPS, n)); sums = z[idx].sum(1)
            am = np.divide(n, sums, out=np.full(BOOTSTRAP_REPS, np.nan), where=sums > 0)
        ft = float(np.exp(np.exp(float(f["gompertz_A"]) - float(f["gompertz_B"]) * xt)))
        bm = ft * xt ** am
        sd = lambda v: float(np.nanstd(v, ddof=1))
        rows.append({
            "year": year, "bootstrap_reps": BOOTSTRAP_REPS,
            "gompertz_A_bootstrap_se": sd(gi), "gompertz_B_bootstrap_se": sd(-gs),
            "pareto_alpha_ls_bootstrap_se": sd(-ps), "pareto_beta_ls_bootstrap_se": sd(np.exp(pi)),
            "pareto_alpha_mle_bootstrap_se": sd(am), "pareto_beta_mle_bootstrap_se": sd(bm),
        })
    out = pd.DataFrame(rows); PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    out.to_csv(BOOTSTRAP_OUT, index=False)
    return out


def r2_log(obs, fit):
    obs, fit = np.asarray(obs, float), np.asarray(fit, float)
    m = np.isfinite(obs) & np.isfinite(fit) & (obs > 0) & (fit > 0)
    if m.sum() < 2: return np.nan
    y, yh = np.log(obs[m]), np.log(fit[m]); tss = ((y-y.mean())**2).sum()
    return np.nan if tss <= 0 else float(1 - ((y-yh)**2).sum()/tss)


def plot_histograms(years, meta):
    def draw(ax, year):
        x = income(year, positive=False)
        x = x[x >= 0]
        counts, edges = np.histogram(x, bins=100)
        ax.bar(
            edges[:-1], counts, width=np.diff(edges), align="edge",
            facecolor="white", edgecolor="0.12", linewidth=0.35,
        )
        ax.set_yscale("log")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, axis="y", which="major", color="0.90", lw=0.42)
    return family(years, "histograms", draw, "Income", "Frequency (log)")


def plot_income_statistics(stats, years, meta):
    mi = meta.set_index("year")
    mins = {y: float(adjusted_income(y, mi, False).min()) for y in years}
    d = stats[stats.year.isin(years)].sort_values("year").copy()
    d["std_mean_ratio"] = d["std"]/d["mean"]; d["xmin"] = d["year"].map(mins)
    panels = [("mean","Mean","2025 US$"),("median","Median","2025 US$"),("std","Standard deviation","2025 US$"),
              ("std_mean_ratio",r"Dispersion $\sigma/\mu$",r"$\sigma/\mu$"),("xmax","Maximum","2025 US$"),("xmin","Minimum (sanity check)","2025 US$")]
    fig, axes = plt.subplots(3,2,figsize=(7,6.6),sharex=True)
    for ax,(c,t,ylabel) in zip(axes.ravel(),panels):
        ax.plot(d.year,d[c],color="0.08",marker="o",markerfacecolor="white",ms=3.2,lw=1.05)
        if c=="xmin": ax.axhline(0,color="0.55",ls="--",lw=0.8)
        ax.set_title(t,fontweight="semibold"); ax.set_ylabel(ylabel); style(ax)
    for ax in axes[-1]: ax.set_xlabel("Year")
    save(fig,"income_statistics")


def plot_ccdf(curves, annual, years):
    ai=annual.set_index("year")
    def draw(ax,year):
        xt=float(ai.loc[year,"transition_x_t"]); d=curves[(curves.year==year)&(curves.income_normalized>0)&(curves.empirical_ccdf_percent>0)]
        ax.plot(d.income_normalized,d.empirical_ccdf_percent,color="0.08",lw=1.05,label="Empirical CCDF")
        ax.axvline(xt,color="0.45",ls=":",lw=0.9,label=r"$x_t$")
        ax.set_xscale("log");ax.set_yscale("log");style(ax,True);annotation(ax,rf"$x_t={xt:.3f}$")
    return family(years,"ccdf_loglog",draw,"Normalized individual income, $x$","CCDF, $F(x)$ (%)",True,2)


def plot_lorenz(lorenz,stats,years):
    si=stats.set_index("year")
    def draw(ax,year):
        d=lorenz[lorenz.year==year];r=si.loc[year]
        p_unit=d.population_share.to_numpy(float);L_unit=d.income_share.to_numpy(float)
        p=100*p_unit;L=100*L_unit
        aulc=float(np.trapezoid(L_unit,p_unit))
        ax.fill_between(p,0,L,color="0.95");ax.plot(p,L,color="0.08",lw=1.35,label="Lorenz curve")
        ax.plot([0,100],[0,100],color="0.50",ls="--",lw=0.9,label="Equality line")
        k=100*float(r["Kolkata"]);q=100-k;ax.plot([k,k],[0,q],color="0.35",ls=":",lw=0.85,label="Kolkata construction");ax.plot([0,k],[q,q],color="0.35",ls=":",lw=0.85)
        i=int(np.argmax(p-L));ax.plot([p[i],p[i]],[L[i],p[i]],color="0.25",ls="-.",lw=0.85,label="Pietra construction")
        ax.plot([],[],color="none",label="AULC = area under Lorenz curve")
        ax.set_xlim(0,100);ax.set_ylim(0,100);ax.set_aspect("equal");style(ax)
        text="\n".join([
            f"Gini     = {float(r['Gini']):.3f}",
            f"Kolkata  = {k:.2f}%",
            f"Zanardi  = {float(r['Zanardi']):.3f}",
            f"Pietra   = {100.0*float(r['Pietra']):.2f}%",
            f"AULC     = {aulc:.3f}",
        ])
        ax.text(0.04,0.96,text,transform=ax.transAxes,ha="left",va="top",fontsize=6.6,
                fontfamily="monospace",linespacing=1.18,zorder=10,
                bbox=dict(boxstyle="round,pad=0.25",facecolor="white",edgecolor="0.55",alpha=0.94))
    return family(years,"lorenz_geometry",draw,"Cumulative population (%)","Cumulative income (%)",True,3)


def exponential_fits(curves,annual):
    ai=annual.set_index("year");rows=[]
    for y in years_of(annual.year.dropna()):
        xg=float(ai.loc[y,"gompertz_x_gmax"]);d=curves[(curves.year==y)&(curves.income_normalized<=xg)&(curves.empirical_ccdf_percent>0)]
        x=d.income_normalized.to_numpy(float);z=np.log(d.empirical_ccdf_percent.to_numpy(float));slope,intercept=np.polyfit(x,z,1);fit=intercept+slope*x;tss=((z-z.mean())**2).sum()
        rows.append({"year":y,"intercept":intercept,"alpha":-slope,"r2":np.nan if tss<=0 else 1-((z-fit)**2).sum()/tss,"xg":xg})
    return pd.DataFrame(rows)


def plot_exponential(curves,fits,years):
    fi=fits.set_index("year")
    def draw(ax,y):
        f=fi.loc[y];d=curves[(curves.year==y)&(curves.income_normalized<=f.xg)&(curves.empirical_ccdf_percent>0)]
        x=d.income_normalized.to_numpy(float);z=np.log(d.empirical_ccdf_percent.to_numpy(float))
        ax.scatter(x,z,s=12,facecolors="white",edgecolors="0.15",label="Empirical");ax.plot(x,float(f.intercept)-float(f.alpha)*x,color="0.08",lw=1.1,label="Exponential fit");style(ax)
        annotation(ax,rf"$\alpha={float(f.alpha):.3f}$"+"\n"+rf"$R^2={float(f.r2):.3f}$")
    return family(years,"exponential_fit",draw,"Normalized individual income, $x$",r"$\ln F(x)$",True,2)


def plot_gompertz(curves,annual,boot,years):
    ai=annual.set_index("year");bi=boot.set_index("year")
    def draw(ax,y):
        f,b=ai.loc[y],bi.loc[y];xg=float(f["gompertz_x_gmax"]);d=curves[(curves.year==y)&(curves.income_normalized<=xg)&curves.gompertz_transform.notna()]
        x=d.income_normalized.to_numpy(float);z=d.gompertz_transform.to_numpy(float)
        ax.scatter(x,z,s=12,facecolors="white",edgecolors="0.20",label="Empirical transform")
        ax.plot(x,float(f["gompertz_A"])-float(f["gompertz_B"])*x,color="0.05",lw=1.25,label="Fixed-A Gompertz fit")
        af,bf=float(f.get("gompertz_boundary_A_free",np.nan)),float(f.get("gompertz_boundary_B_free",np.nan))
        if np.isfinite(af) and np.isfinite(bf): ax.plot(x,af-bf*x,color="0.45",ls="--",lw=1.05,label="Free-intercept LSF")
        style(ax);annotation(ax,rf"$A={float(f['gompertz_A']):.3f}$"+"\n"+rf"$B={float(f['gompertz_B']):.3f}\pm{float(b['gompertz_B_bootstrap_se']):.3f}$"+"\n"+rf"$R^2={float(f['gompertz_r2']):.3f}$")
    return family(years,"gompertz_ls_fit",draw,"Normalized individual income, $x$",r"$\ln[\ln F(x)]$",True,3)


def plot_pareto(curves,annual,boot,years,method):
    ai=annual.set_index("year");bi=boot.set_index("year")
    def draw(ax,y):
        f,b=ai.loc[y],bi.loc[y];xt=float(f["transition_x_t"]);xp=float(f["pareto_x_pmin"])
        if method=="ls":
            col="pareto_fitted_ccdf_percent_ls";alpha=float(f["pareto_alpha_ls"]);ase=float(b["pareto_alpha_ls_bootstrap_se"]);beta=float(f["pareto_beta_ls"]);bse=float(b["pareto_beta_ls_bootstrap_se"]);r2=float(f["pareto_ls_r2"]);xmin=min(xt,xp);label="Pareto LSF";ls="--";a=r"\alpha_{\rm LS}";bt=r"\beta_{\rm LS}";rr=r"R^2_{\rm LS}"
        else:
            col="pareto_fitted_ccdf_percent_mle";alpha=float(f["pareto_alpha_mle"]);ase=float(b["pareto_alpha_mle_bootstrap_se"]);beta=float(f["pareto_beta_mle_continuity"]);bse=float(b["pareto_beta_mle_bootstrap_se"]);xmin=xt;label="Pareto MLE";ls="-";a=r"\alpha_{\rm MLE}";bt=r"\beta_{\rm MLE}";rr=r"R^2_{\rm MLE}"
            d0=curves[(curves.year==y)&(curves.income_normalized>=xt)&(curves.empirical_ccdf_percent>0)];r2=r2_log(d0.empirical_ccdf_percent,d0[col])
        d=curves[(curves.year==y)&(curves.income_normalized>=xmin)&(curves.empirical_ccdf_percent>0)]
        ax.scatter(d.income_normalized,d.empirical_ccdf_percent,s=12,facecolors="white",edgecolors="0.20",label="Empirical CCDF")
        m=np.isfinite(pd.to_numeric(d[col],errors="coerce"));ax.plot(d.loc[m,"income_normalized"],d.loc[m,col],color="0.05",ls=ls,lw=1.2,label=label)
        ax.axvline(xt,color="0.50",ls=":",lw=0.9,label=r"$x_t$");ax.set_xscale("log");ax.set_yscale("log");style(ax,True)
        annotation(ax,rf"${a}={alpha:.3f}\pm{ase:.3f}$"+"\n"+rf"${bt}={beta:.2e}\pm{bse:.2e}$"+"\n"+rf"${rr}={r2:.3f}$")
    return family(years,"pareto_ls_fit" if method=="ls" else "pareto_mle_fit",draw,"Normalized individual income, $x$","CCDF, $F(x)$ (%)",True,3)


def line_figure(stats,stem,series,ylabel,scale=1.0):
    d=stats.sort_values("year");fig,ax=plt.subplots(figsize=SINGLE_SIZE);styles=["-","--",":","-."];markers=["o","s","^","D"];grays=["0.05","0.30","0.50","0.65"]
    for i,(col,label) in enumerate(series): ax.plot(d.year,scale*d[col],color=grays[i%4],ls=styles[i%4],marker=markers[i%4],markerfacecolor="white",ms=3.2,lw=1.1,label=label)
    ax.set_xlabel("Year");ax.set_ylabel(ylabel);style(ax);ax.legend(loc="upper center",bbox_to_anchor=(0.5,1.13),ncol=min(4,len(series)),frameon=False);save(fig,stem,0.90)


def plot_inequality_grid(stats):
    d=stats.sort_values("year");fig,axes=plt.subplots(2,2,figsize=(7,6.6),sharex=True)
    for ax,(col,title,scale) in zip(axes.ravel(),[("Gini","Gini",1),("Zanardi","Zanardi",1),("Kolkata","Kolkata",100),("Pietra","Pietra",100)]): ax.plot(d.year,scale*d[col],color="0.08",marker="o",markerfacecolor="white",ms=3.2,lw=1.1);ax.set_title(title);style(ax)
    save(fig,"inequality_indices_grid")


def plot_gini_validation(stats):
    d=stats.sort_values("year");fig,ax=plt.subplots(figsize=SINGLE_SIZE);ax.plot(d.year,d.Gini,color="0.05",lw=1.25,marker="o",markerfacecolor="white",ms=3.5,label="PNAD")
    for col,label,ls,gray in [("IPEA","IPEA","--","0.35"),("Banco_Mundial","World Bank",":","0.55")]:
        if col in d: v=d.dropna(subset=[col]);ax.plot(v.year,v[col],color=gray,ls=ls,lw=1.05,label=label)
    ax.set_xlabel("Year");ax.set_ylabel("Gini coefficient");style(ax);ax.legend(loc="upper center",bbox_to_anchor=(0.5,1.13),ncol=3,frameon=False);save(fig,"gini_validation",0.90)


def plot_top_combined(stats):
    d=stats.sort_values("year");fig,axes=plt.subplots(2,1,figsize=(7,7),sharex=True)
    axes[0].plot(d.year,d["mean"],color="0.08",label="Mean");axes[0].plot(d.year,d["median"],color="0.45",ls="--",label="Median");style(axes[0]);axes[0].legend(frameon=False,ncol=2)
    for c,l,ls,g in [("top_10","Top 10%","-","0.08"),("top_1","Top 1%","--","0.35"),("top_01","Top 0.1%",":","0.55")]: axes[1].plot(d.year,100*d[c],color=g,ls=ls,label=l)
    style(axes[1]);axes[1].legend(frameon=False,ncol=3);axes[1].set_xlabel("Year");save(fig,"top_income_shares_mean_median")


def regime_shares(annual):
    ai=annual.set_index("year");rows=[]
    for y in years_of(annual.year.dropna()):
        xt=float(ai.loc[y,"transition_x_t"]);x=normalized_income(y);g=100*x[x<xt].sum()/x.sum();rows.append((y,g,100-g))
    return pd.DataFrame(rows,columns=["year","gompertz_income_share_pct","pareto_income_share_pct"])


def plot_pareto_share(shares):
    fig,ax=plt.subplots(figsize=SINGLE_SIZE);ax.plot(shares.year,shares.pareto_income_share_pct,color="0.08",marker="o",markerfacecolor="white",lw=1.15);ax.set_xlabel("Year");ax.set_ylabel("Pareto share of total income (%)");style(ax);save(fig,"pareto_income_share")


def plot_gdp():
    d=pd.read_csv(GDP);d=d[(d.year>=START_YEAR)&(d.year<=END_YEAR)];fig,ax=plt.subplots(figsize=SINGLE_SIZE);ax.plot(d.year,d.gdp_growth_pct,color="0.08",marker="s",markerfacecolor="white",lw=1.1);ax.axhline(0,color="0.45",ls="--",lw=0.8);ax.set_xlabel("Year");ax.set_ylabel("Real GDP growth (%)");style(ax);save(fig,"gdp_growth")


def main():
    PAPER_TABLES.mkdir(parents=True,exist_ok=True);clean_figures()
    stats,lorenz,annual,curves,meta=load_inputs();years=years_of(annual.year.dropna())
    boot=bootstrap(curves,annual);fits=exponential_fits(curves,annual);shares=regime_shares(annual)
    plot_histograms(years,meta);plot_income_statistics(stats,years,meta);plot_ccdf(curves,annual,years);plot_lorenz(lorenz,stats,years)
    line_figure(stats,"gini",[("Gini","Gini")],"Gini coefficient");plot_exponential(curves,fits,years)
    plot_gompertz(curves,annual,boot,years);plot_pareto(curves,annual,boot,years,"ls");plot_pareto(curves,annual,boot,years,"mle")
    line_figure(stats,"top_income_shares",[("top_10","Top 10%"),("top_1","Top 1%"),("top_01","Top 0.1%")],"Share of total income (%)",100)
    ex=stats.copy();ex["p90_p99"]=ex.top_10-ex.top_1;ex["p99_p999"]=ex.top_1-ex.top_01;ex["p999_p100"]=ex.top_01
    line_figure(ex,"top_income_exclusive_shares",[("p90_p99","90-99%"),("p99_p999","99-99.9%"),("p999_p100","99.9-100%")],"Share of total income (%)",100)
    plot_top_combined(stats);line_figure(stats,"inequality_indices",[("Gini","Gini"),("Pietra","Pietra"),("Kolkata","Kolkata"),("Zanardi","Zanardi")],"Inequality index")
    plot_inequality_grid(stats);plot_gini_validation(stats);plot_pareto_share(shares);plot_gdp()
    print(f"Stage 05 publication figures generated from trusted data for {len(years)} survey years.")


if __name__ == "__main__":
    main()
