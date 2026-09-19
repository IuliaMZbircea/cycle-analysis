"""
Day 7 of the bootcamp, on REAL data: Marquette NFP cycle records (Fehring).
159 women, 1,665 charted cycles. Tests the claim the whole analysis rests on.
"""
import pandas as pd, numpy as np, warnings, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
PLUM, TEAL, GREY = "#9C2740", "#276560", "#6B5F62"
plt.rcParams.update({"figure.dpi":140,"font.size":9,"axes.spines.top":False,
                     "axes.spines.right":False,"axes.grid":True,"grid.alpha":.25})

df = pd.read_csv("data/fedcycle.csv", low_memory=False)
num = lambda c: pd.to_numeric(df[c], errors="coerce")
d = pd.DataFrame({
    "pid":   df["ClientID"],
    "cycle": num("LengthofCycle"),
    "luteal":num("LengthofLutealPhase"),
    "ovday": num("EstimatedDayofOvulation"),
}).dropna()
d["follicular"] = d.cycle - d.luteal
d = d[(d.cycle.between(20,45)) & (d.luteal.between(8,20)) & (d.follicular > 5)]
print(f"cycles {len(d)} | women {d.pid.nunique()} | median cycles/woman {int(d.groupby('pid').size().median())}\n")

# --- 1. which phase carries the variation? ---
print("=== BETWEEN all cycles ===")
for n,s in [("cycle length",d.cycle),("follicular",d.follicular),("luteal",d.luteal)]:
    print(f"  {n:14s} mean {s.mean():5.2f}  SD {s.std():5.2f}")
wf = d.groupby("pid").follicular.std().median()
wl = d.groupby("pid").luteal.std().median()
print(f"\n=== WITHIN woman (median of per-woman SDs) ===")
print(f"  follicular SD {wf:5.2f}   luteal SD {wl:5.2f}   ratio {wf/wl:.2f}x")
print(f"\ncorr(cycle length, follicular) = {d.cycle.corr(d.follicular):+.3f}")
print(f"corr(cycle length, luteal)     = {d.cycle.corr(d.luteal):+.3f}")
vf = d.follicular.var(); vl = d.luteal.var()
print(f"share of cycle-length variance attributable to follicular: {vf/(vf+vl):.1%}")

# --- 2. what does assuming 'day 14 = ovulation' cost? ---
err = d.ovday - 14
print(f"\n=== error of the day-14 assumption (vs charted ovulation) ===")
print(f"  mean {err.mean():+.2f} d | SD {err.std():.2f} | within 1 day {(err.abs()<=1).mean():.1%}"
      f" | off by >3 days {(err.abs()>3).mean():.1%}")
# backward counting: ovulation = cycle_length - 14
errb = (d.cycle - 13) - d.ovday
print(f"=== error of backward counting (onset - 13) ===")
print(f"  mean {errb.mean():+.2f} d | SD {errb.std():.2f} | within 1 day {(errb.abs()<=1).mean():.1%}"
      f" | off by >3 days {(errb.abs()>3).mean():.1%}")
print(f"\n--> backward counting reduces SD of ovulation-timing error by "
      f"{(1-errb.std()/err.std()):.0%}")

# --- 3. figure ---
fig, ax = plt.subplots(1, 3, figsize=(11, 3.3))
ax[0].hist(d.follicular, bins=range(6,36), color=PLUM, alpha=.85, label=f"follicular (SD {d.follicular.std():.1f})")
ax[0].hist(d.luteal,     bins=range(6,36), color=TEAL, alpha=.85, label=f"luteal (SD {d.luteal.std():.1f})")
ax[0].set_title("Where the variation lives", loc="left"); ax[0].set_xlabel("days"); ax[0].legend(frameon=False, fontsize=8)
ax[1].scatter(d.cycle, d.follicular, s=5, color=PLUM, alpha=.35, label="follicular")
ax[1].scatter(d.cycle, d.luteal,     s=5, color=TEAL, alpha=.35, label="luteal")
ax[1].set_title("Longer cycle = longer follicular", loc="left")
ax[1].set_xlabel("cycle length (days)"); ax[1].set_ylabel("phase length"); ax[1].legend(frameon=False, fontsize=8)
ax[2].hist(err, bins=range(-12,13), color=GREY, alpha=.8, label=f"forward: day 14 (SD {err.std():.1f})")
ax[2].hist(errb, bins=range(-12,13), color=PLUM, alpha=.8, label=f"backward: onset−13 (SD {errb.std():.1f})")
ax[2].axvline(0, color="k", lw=.8)
ax[2].set_title("Ovulation-timing error", loc="left"); ax[2].set_xlabel("days off"); ax[2].legend(frameon=False, fontsize=8)
fig.suptitle("Marquette NFP, 159 women / 1,665 charted cycles — REAL data", x=.02, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig("out/03_marquette.png", bbox_inches="tight")
print("\nwrote out/03_marquette.png")
