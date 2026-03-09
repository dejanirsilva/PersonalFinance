#!/usr/bin/env python3
"""Replicate the cohort-variation graph from Villaverde post 2023742455204520249.

Setup from post:
- Annual real S&P 500 returns from Damodaran, years 1945-2024.
- Investor contributes once per year for 46 years.
- First contribution is $1 (real), contributions grow 1% real per year.
- Cohorts start each year from 1945 to 1978 (34 cohorts).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "purdue" / "damodaran_sp500_real.csv"
OUT_DIR = ROOT / "retirement" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    df = pd.read_csv(DATA)
    rets = df.set_index("Year")["sp500_real"]

    start_min, start_max = 1945, 1978
    years_working = 46
    c0, c_growth = 1.0, 0.01

    rows = []
    for start in range(start_min, start_max + 1):
        wealth = 0.0
        c = c0
        for year in range(start, start + years_working):
            wealth = (wealth + c) * (1 + rets.loc[year])
            c *= 1 + c_growth
        ann_real = ((1 + rets.loc[start : start + years_working - 1]).prod() ** (1 / years_working)) - 1
        rows.append(
            {
                "start_year": start,
                "retire_year": start + years_working,
                "terminal_wealth": wealth,
                "annualized_real_return": ann_real,
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "villaverde_202374_replication.csv", index=False)

    best = out.loc[out["terminal_wealth"].idxmax()]
    worst = out.loc[out["terminal_wealth"].idxmin()]

    fig, ax1 = plt.subplots(figsize=(11, 6))
    ax1.plot(out["start_year"], out["terminal_wealth"], color="#146c7e", lw=2.2, marker="o", ms=3)
    ax1.set_xlabel("Career Start Year")
    ax1.set_ylabel("Real Terminal Wealth (first contribution = $1)", color="#146c7e")
    ax1.tick_params(axis="y", labelcolor="#146c7e")
    ax1.grid(alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(out["start_year"], 100 * out["annualized_real_return"], color="#e59f2f", lw=1.6, ls="--")
    ax2.set_ylabel("Annualized Real Return (%)", color="#e59f2f")
    ax2.tick_params(axis="y", labelcolor="#e59f2f")

    ax1.scatter([best["start_year"]], [best["terminal_wealth"]], color="#2f7d32", zorder=5)
    ax1.scatter([worst["start_year"]], [worst["terminal_wealth"]], color="#9c4218", zorder=5)
    ax1.annotate(
        f"Best cohort: start {int(best['start_year'])}\nwealth ${best['terminal_wealth']:.0f}\nann. real {100*best['annualized_real_return']:.2f}%",
        xy=(best["start_year"], best["terminal_wealth"]),
        xytext=(best["start_year"] - 7, best["terminal_wealth"] + 35),
        arrowprops={"arrowstyle": "->", "color": "#2f7d32"},
        fontsize=9,
        color="#1c4f1f",
    )
    ax1.annotate(
        f"Worst cohort: start {int(worst['start_year'])}\nwealth ${worst['terminal_wealth']:.0f}\nann. real {100*worst['annualized_real_return']:.2f}%",
        xy=(worst["start_year"], worst["terminal_wealth"]),
        xytext=(worst["start_year"] + 1, worst["terminal_wealth"] + 35),
        arrowprops={"arrowstyle": "->", "color": "#9c4218"},
        fontsize=9,
        color="#7a3110",
    )

    plt.title("Replication: Cohort Timing Effect on 46-Year Real Accumulation (Damodaran S&P)")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "villaverde_202374_replication.png", dpi=170)
    plt.close(fig)

    print(f"Cohorts: {len(out)}")
    print(f"Best: start={int(best['start_year'])}, retire={int(best['retire_year'])}, wealth={best['terminal_wealth']:.3f}, ann_real={100*best['annualized_real_return']:.3f}%")
    print(f"Worst: start={int(worst['start_year'])}, retire={int(worst['retire_year'])}, wealth={worst['terminal_wealth']:.3f}, ann_real={100*worst['annualized_real_return']:.3f}%")


if __name__ == "__main__":
    main()
