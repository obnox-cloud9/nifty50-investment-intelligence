"""Risk/return metrics, segmentation and correlation analysis."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

TRADING_DAYS = 252
RISK_FREE = 0.065  # approx. Indian 10y G-sec / T-bill level over the period


def daily_returns(prices):
    return prices.pct_change(fill_method=None)


def max_drawdown(p):
    p = p.dropna()
    return float((p / p.cummax() - 1).min())


def stock_metrics(prices, sectors):
    r = daily_returns(prices)
    rows = []
    for t in prices.columns:
        p = prices[t].dropna()
        years = (p.index[-1] - p.index[0]).days / 365.25
        cagr = (p.iloc[-1] / p.iloc[0]) ** (1 / years) - 1
        vol = r[t].std() * np.sqrt(TRADING_DAYS)
        downside = r[t][r[t] < 0].std() * np.sqrt(TRADING_DAYS)
        rows.append({"ticker": t, "sector": sectors[t], "start": p.index[0].date(), "end": p.index[-1].date(),
                     "years": round(years, 2), "cagr": cagr, "volatility": vol, "max_drawdown": max_drawdown(p),
                     "sharpe": (cagr - RISK_FREE) / vol, "sortino": (cagr - RISK_FREE) / downside})
    return pd.DataFrame(rows).set_index("ticker")


def yearly_returns(prices):
    last = prices.resample("YE").last()
    first_px = prices.apply(lambda s: s.dropna().iloc[0])
    yr = last.pct_change(fill_method=None)
    first_year = last.index[0]
    yr.loc[first_year] = last.loc[first_year] / first_px - 1   # partial first year from listing date
    return yr


def consistency(prices):
    """Share of calendar years each stock beat the equal-weight NIFTY-50 average (full years only)."""
    yr = yearly_returns(prices)
    full = yr.loc[(yr.index.year > prices.index[0].year) & (yr.index.year < prices.index[-1].year)]
    bench = full.mean(axis=1)
    beat = full.gt(bench, axis=0).where(full.notna())
    return beat.mean().rename("beat_rate"), full, bench


def segment(metrics, k=4, seed=0):
    """K-means on standardised return/risk features, clusters labelled by mean Sharpe."""
    feats = ["cagr", "volatility", "max_drawdown", "sharpe"]
    z = StandardScaler().fit_transform(metrics[feats])
    labels = KMeans(k, n_init=20, random_state=seed).fit_predict(z)
    m = metrics.assign(cluster=labels)
    order = m.groupby("cluster").sharpe.mean().sort_values(ascending=False).index
    names = ["High performers", "Steady compounders", "Average", "Laggards / high risk"][:k]
    return m.assign(segment=m.cluster.map(dict(zip(order, names)))).drop(columns="cluster")


def correlation_pairs(prices, sectors, window_start):
    """Pairwise daily-return correlation on the common window where every stock trades."""
    r = daily_returns(prices.loc[window_start:]).dropna(how="all")
    common = r.dropna()
    corr = common.corr()
    t = corr.columns
    pairs = [(a, b, corr.loc[a, b], sectors[a], sectors[b])
             for i, a in enumerate(t) for b in t[i + 1:]]
    df = pd.DataFrame(pairs, columns=["stock_a", "stock_b", "corr", "sector_a", "sector_b"])
    df["cross_sector"] = df.sector_a != df.sector_b
    # stability: correlation in each calendar year, the pair has to stay low in all of them
    yearly = {y: g.corr() for y, g in common.groupby(common.index.year) if len(g) > 120}
    df["max_yearly_corr"] = [max(c.loc[a, b] for c in yearly.values()) for a, b in zip(df.stock_a, df.stock_b)]
    return corr, df.sort_values("corr"), common.index[0].date(), common.index[-1].date(), len(common)


def sector_summary(metrics, prices, sectors):
    r = daily_returns(prices)
    sec_ret = r.T.groupby(pd.Series(sectors)).mean().T     # equal-weight daily sector return
    idx = (1 + sec_ret.fillna(0)).cumprod()
    agg = metrics.groupby("sector").agg(stocks=("cagr", "size"), median_cagr=("cagr", "median"),
                                        median_vol=("volatility", "median"), median_mdd=("max_drawdown", "median"),
                                        median_sharpe=("sharpe", "median"))
    return agg.sort_values("median_sharpe", ascending=False), idx


def consistent_high_performers(seg, sharpe_quantile=0.5, min_beat_rate=0.5):
    """Beat the equal-weight NIFTY-50 average in more than half of full calendar years AND
    have above-median Sharpe. Both thresholds are fixed up front, not tuned to hit a count."""
    m = seg[(seg.beat_rate > min_beat_rate) & (seg.sharpe > seg.sharpe.quantile(sharpe_quantile))]
    return m.sort_values("sharpe", ascending=False)


def low_corr_pairs(pairs, threshold=0.15, yearly_cap=0.30):
    """Cross-sector pairs with full-window correlation below `threshold` that never exceed
    `yearly_cap` in any single calendar year (so the diversification holds up, not just on average)."""
    p = pairs[pairs.cross_sector]
    return p[(p["corr"] < threshold) & (p.max_yearly_corr < yearly_cap)]
