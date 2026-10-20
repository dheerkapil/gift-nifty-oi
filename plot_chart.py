#!/usr/bin/env python3
"""Build chart.png (GIFT futures OI vs Nifty 50) from the repo's own data files."""
import os
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates

ROOT   = os.path.dirname(os.path.abspath(__file__))
DATA   = os.path.join(ROOT, "data")
OUT    = os.path.join(ROOT, "chart.png")
IN_PER_DAY = 0.052
HEIGHT     = 10

oi = pd.read_csv(os.path.join(DATA, "oi_master.csv")).rename(columns={"nifty_fut_total_oi": "oi"})
oi["d"] = pd.to_datetime(oi["date"], format="%d-%b-%Y")
oi = oi.drop_duplicates("d").sort_values("d").reset_index(drop=True)

nx = pd.read_csv(os.path.join(DATA, "nifty_daily.csv"))
nx["d"] = pd.to_datetime(nx["date"], format="%d-%b-%Y")
nx = nx.drop_duplicates("d").sort_values("d").reset_index(drop=True)

df = oi.merge(nx[["d", "nifty"]], on="d", how="inner").reset_index(drop=True)
df["ma5"] = df["oi"].rolling(5).mean()
print(f"DIAG oi={len(oi)} nifty={len(nx)} merged={len(df)}")
n = len(df)
if n < 30:
    raise SystemExit(f"too few points ({n}) - not sending a chart")
width = max(12.0, round(IN_PER_DAY * n, 1))

fig, (a, b) = plt.subplots(2, 1, figsize=(width, HEIGHT), gridspec_kw={"height_ratios": [2, 1.2]})
ab = a.twinx()
a.plot(df["d"], df["nifty"], color="#1f4e9c", lw=2, label="Nifty 50 spot (L)")
ab.plot(df["d"], df["oi"]/1000, color="#e07b00", lw=.8, alpha=.3)
ab.plot(df["d"], df["ma5"]/1000, color="#b35a00", lw=2.6, label="GIFT futures OI, 5d avg (R)")
a.set_ylabel("Nifty 50 spot", color="#1f4e9c"); a.tick_params(axis="y", labelcolor="#1f4e9c")
ab.set_ylabel("GIFT futures OI ('000)", color="#b35a00"); ab.tick_params(axis="y", labelcolor="#b35a00")
a.set_title(f"GIFT Nifty futures OI vs Nifty 50 spot  ({df['d'].min():%d-%b-%Y} - {df['d'].max():%d-%b-%Y})",
            fontsize=13, weight="bold")
l1, la1 = a.get_legend_handles_labels(); l2, la2 = ab.get_legend_handles_labels()
a.legend(l1+l2, la1+la2, loc="upper left", fontsize=9); a.grid(alpha=.25)
df["chg"] = df["oi"].diff()
colors = np.where(df["chg"].fillna(0) >= 0, "#2e8b57", "#c0392b")
b.bar(df["d"], df["chg"].fillna(0)/1000, color=colors, width=0.85)
b.axhline(0, color="k", lw=.6); b.set_ylabel("dOI ('000/day)"); b.grid(alpha=.25)
b.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); b.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
plt.tight_layout(); plt.savefig(OUT, dpi=130)
print("chart:", OUT, f"{width}x{HEIGHT}in")
