"""
Day 6-10 of the bootcamp, on the Arslan et al. (2018) SYNTHETIC diary data.
Source: https://osf.io/csr9p/  (synthpop-generated; NOT the real diary)
"""
import pandas as pd, numpy as np, warnings, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

PLUM, TEAL, GREY = "#9C2740", "#276560", "#6B5F62"
plt.rcParams.update({"figure.dpi":140,"font.size":9,"axes.spines.top":False,
                     "axes.spines.right":False,"axes.grid":True,
                     "grid.alpha":.25,"grid.linewidth":.6})

df = pd.read_csv("data/arslan/diary_synthetic_FAKE.csv", low_memory=False)

# ---------- 1. clean ----------
d = df.copy()
d["hc"] = d["hormonal_contra"].map({True:1, False:0, "True":1, "False":0})
for c in ["in_pair_desire","extra_pair_desire","extra_pair_sexual_fantasies"]:
    d.loc[d[c] >= 90, c] = np.nan          # 99 = missing code
d["bwd"] = d["menstrual_onset_days_until"] # 0 = onset day, negative = days before
d = d[d["bwd"].between(-30, 0) | d["bwd"].isna()]

print("rows %d | persons %d | NC %d / HC %d"
      % (len(d), d.person.nunique(), (d.hc==0).sum(), (d.hc==1).sum()))

# ---------- 2. forward vs backward counting: coverage ----------
fwd_ok = df["days_since_menstrual_onset"].notna().mean()
bwd_ok = df["menstrual_onset_days_until"].notna().mean()
fw_fwd = df["fertile_window_forward_counted"].notna().mean()
fw_bwd = df["fertile_window"].notna().mean()
print("\n=== phase assignment coverage ===")
print(f"forward count available : {fwd_ok:6.1%}")
print(f"backward count available: {bwd_ok:6.1%}")
print(f"fertile window (forward-counted) labelled: {fw_fwd:6.1%}")
print(f"fertile window (backward-inferred)       : {fw_bwd:6.1%}")

agree = df.dropna(subset=["fertile_window","fertile_window_forward_counted"])
if len(agree):
    same = (agree["fertile_window"] == agree["fertile_window_forward_counted"]).mean()
    print(f"where both exist (n={len(agree)}), the two methods agree: {same:6.1%}")

# ---------- 3. population curve by backward cycle day ----------
def curve(sub, col):
    g = sub.dropna(subset=["bwd", col]).groupby("bwd")[col]
    m, se, n = g.mean(), g.std()/np.sqrt(g.count()), g.count()
    keep = n >= 25
    return m[keep], se[keep]

fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5), sharex=True)
for ax, col, title in zip(axes,
        ["in_pair_desire","extra_pair_desire"],
        ["In-pair desire","Extra-pair desire"]):
    for hc, colr, lab in [(0, PLUM, "Naturally cycling"), (1, TEAL, "Hormonal contraception")]:
        m, se = curve(d[d.hc==hc], col)
        ax.plot(m.index, m.values, color=colr, lw=1.6, label=lab)
        ax.fill_between(m.index, m-1.96*se, m+1.96*se, color=colr, alpha=.15, lw=0)
    ax.axvspan(-19, -13, color=GREY, alpha=.10, lw=0)   # approx fertile window
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_xlabel("Days until next menstrual onset")
axes[0].set_ylabel("Mean rating (1–6)")
axes[0].legend(frameon=False, fontsize=8)
fig.suptitle("Desire across the cycle — SYNTHETIC data, marginal means only",
             x=.02, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig("out/01_population_curves.png", bbox_inches="tight")
print("\nwrote out/01_population_curves.png")

# ---------- 4. the paper's actual design: fertile-window contrast, NC vs HC ----------
d["fertile"] = (d["fertile_window"] == "narrow").astype(float)
d.loc[d["fertile_window"].isna(), "fertile"] = np.nan
print("\n=== fertile-window contrast (diff-in-diff vs HC control) ===")
for col in ["in_pair_desire","extra_pair_desire","had_sexual_intercourse"]:
    sub = d.dropna(subset=[col,"fertile","hc"])
    tab = sub.groupby(["hc","fertile"])[col].mean().unstack()
    nc  = tab.loc[0,1.0] - tab.loc[0,0.0]
    hcd = tab.loc[1,1.0] - tab.loc[1,0.0]
    print(f"{col:26s} NC {nc:+.4f}   HC {hcd:+.4f}   diff-in-diff {nc-hcd:+.4f}")

# ---------- 5. individual heterogeneity ----------
nc = d[d.hc==0].dropna(subset=["bwd","in_pair_desire"])
counts = nc.groupby("person").size().sort_values(ascending=False)
picks = counts.head(12).index
fig, axes = plt.subplots(3, 4, figsize=(10, 6), sharex=True, sharey=True)
for ax, p in zip(axes.ravel(), picks):
    s = nc[nc.person==p].sort_values("bwd")
    ax.plot(s.bwd, s.in_pair_desire, "o-", color=PLUM, ms=2.5, lw=.9, alpha=.85)
    ax.axhline(nc.in_pair_desire.mean(), color=GREY, lw=.7, ls="--")
    ax.set_title(f"person {p}  (n={len(s)})", fontsize=7.5, loc="left")
for ax in axes[-1]: ax.set_xlabel("days until onset", fontsize=8)
for ax in axes[:,0]: ax.set_ylabel("in-pair desire", fontsize=8)
fig.suptitle("Twelve individuals, plotted separately — the average describes none of them",
             x=.02, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig("out/02_individuals.png", bbox_inches="tight")
print("wrote out/02_individuals.png")

# ---------- 6. mixed model: pipeline built here, estimates NOT interpretable ----------
m = d.dropna(subset=["in_pair_desire","fertile","hc","person"]).copy()
fit = smf.mixedlm("in_pair_desire ~ fertile * hc", m, groups=m["person"],
                  re_formula="~fertile").fit(method="lbfgs")
fe   = fit.fe_params.get("fertile", np.nan)
cov  = fit.cov_re
sd_s = np.sqrt(cov.iloc[1,1]) if cov.shape[0] > 1 else np.nan
print("\n=== mixed model, random intercept + random slope on `fertile` ===")
print(f"fixed effect of fertile window : {fe:+.4f}")
print(f"SD of the random slope          : {sd_s:.4f}")
print(f"ratio SD(slope) / |fixed effect|: {sd_s/abs(fe):.2f}")
print("\n(structure validated; estimates not interpretable on synthetic data — see notes)")
