"""End-to-end run: load data, compute every metric, write tables, charts, dashboard and Power BI files.

    python run.py
"""
import json
from pathlib import Path

import pandas as pd

from src.analysis import (stock_metrics, segment, consistency, correlation_pairs, sector_summary,
                          consistent_high_performers, low_corr_pairs, daily_returns, yearly_returns)
from src.data import load_prices, SECTOR, CORPORATE_ACTION_FIXES
from src.visuals import static_plots, dashboard

ROOT = Path(__file__).resolve().parent
OUT, PBI = ROOT / "outputs", ROOT / "powerbi"


def main():
    prices = load_prices()
    metrics = stock_metrics(prices, SECTOR)
    beat, yearly_full, bench = consistency(prices)
    seg = segment(metrics).join(beat)
    top = consistent_high_performers(seg)
    corr, pairs, w0, w1, n_days = correlation_pairs(prices, SECTOR, prices.index[0])
    low = low_corr_pairs(pairs)
    sector_tbl, sector_idx = sector_summary(metrics, prices, SECTOR)
    drawdowns = prices / prices.cummax() - 1

    OUT.mkdir(exist_ok=True)
    seg.round(4).to_csv(OUT / "stock_metrics_segments.csv")
    top.round(4).to_csv(OUT / "high_performers.csv")
    pairs.round(4).to_csv(OUT / "all_pairs_correlation.csv", index=False)
    low.round(4).to_csv(OUT / "low_correlated_pairs.csv", index=False)
    sector_tbl.round(4).to_csv(OUT / "sector_summary.csv")
    yearly_full.round(4).to_csv(OUT / "yearly_returns.csv")

    static_plots(seg, sector_tbl, sector_idx, corr, drawdowns, OUT / "plots")
    dashboard(seg, sector_tbl, sector_idx, corr, low, top[["sector", "cagr", "volatility", "max_drawdown", "sharpe", "beat_rate"]],
              OUT / "dashboard.html")

    # Power BI star schema: one fact table (daily prices + returns) and a stock dimension
    PBI.mkdir(exist_ok=True)
    fact = prices.stack().rename("adj_close").reset_index().rename(columns={"level_0": "date", "level_1": "ticker", "Date": "date"})
    fact.columns = ["date", "ticker", "adj_close"]
    fact["daily_return"] = daily_returns(prices).stack().reindex(pd.MultiIndex.from_frame(fact[["date", "ticker"]])).values
    fact.to_csv(PBI / "fact_prices.csv", index=False)
    seg.reset_index().round(4).to_csv(PBI / "dim_stock.csv", index=False)
    low.round(4).to_csv(PBI / "low_corr_pairs.csv", index=False)

    summary = {
        "data_window": [str(prices.index[0].date()), str(prices.index[-1].date())],
        "years_of_data": round((prices.index[-1] - prices.index[0]).days / 365.25, 1),
        "stocks": prices.shape[1],
        "stocks_with_9plus_years": int((metrics.years >= 9).sum()),
        "trading_days": len(prices),
        "corporate_action_fixes": {k: v[1] for k, v in CORPORATE_ACTION_FIXES.items()},
        "segments": seg.segment.value_counts().to_dict(),
        "consistent_high_performers": top.index.tolist(),
        "n_consistent_high_performers": len(top),
        "correlation_window": [str(w0), str(w1)], "correlation_days": n_days,
        "n_cross_sector_pairs": int(pairs.cross_sector.sum()),
        "n_low_corr_pairs_stable": len(low),
        "n_cross_sector_pairs_below_0.15": int((pairs.cross_sector & (pairs["corr"] < 0.15)).sum()),
        "n_cross_sector_pairs_below_0.20": int((pairs.cross_sector & (pairs["corr"] < 0.20)).sum()),
        "median_pairwise_corr": round(float(pairs["corr"].median()), 3),
    }
    json.dump(summary, open(OUT / "summary.json", "w"), indent=2)
    print(json.dumps(summary, indent=2))
    print("\nConsistently high-performing stocks\n", top[["sector", "cagr", "volatility", "sharpe", "beat_rate"]].round(3))
    print("\nLow-correlated cross-sector pairs\n", low[["stock_a", "stock_b", "corr", "max_yearly_corr"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
