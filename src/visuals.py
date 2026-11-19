"""Static charts (PNG) and a self-contained interactive dashboard (HTML)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

SEG_COLORS = {"High performers": "#16a34a", "Steady compounders": "#2563eb",
              "Average": "#9ca3af", "Laggards / high risk": "#dc2626"}


def _clean(ax):
    ax.spines[["top", "right"]].set_visible(False)


def static_plots(seg, sector_tbl, sector_idx, corr, drawdowns, out):
    out.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    for name, g in seg.groupby("segment"):
        ax.scatter(g.volatility * 100, g.cagr * 100, s=60, label=f"{name} ({len(g)})", color=SEG_COLORS[name])
    for t, r in seg.iterrows():
        ax.annotate(t, (r.volatility * 100, r.cagr * 100), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set(xlabel="Annualised volatility (%)", ylabel="CAGR (%)", title="Risk vs return, NIFTY-50 stocks (Oct 2012 – Oct 2022)")
    ax.legend(frameon=False)
    _clean(ax)
    fig.tight_layout(); fig.savefig(out / "risk_return_segments.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    for s in sector_idx.columns:
        ax.plot(sector_idx.index, sector_idx[s], lw=1.4, label=s)
    ax.set(yscale="log", ylabel="Growth of ₹1 (log scale)", title="Equal-weight sector performance")
    ax.legend(ncol=3, fontsize=8, frameon=False)
    _clean(ax)
    fig.tight_layout(); fig.savefig(out / "sector_growth.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    t = sector_tbl.sort_values("median_sharpe")
    ax.barh(t.index, t.median_sharpe, color="#2563eb")
    ax.set(xlabel="Median Sharpe ratio", title="Risk-adjusted return by sector")
    _clean(ax)
    fig.tight_layout(); fig.savefig(out / "sector_sharpe.png", dpi=150); plt.close(fig)

    order = seg.sort_values(["sector", "ticker"] if "ticker" in seg else "sector").index
    c = corr.loc[order, order]
    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(c, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(c)), c.columns, rotation=90, fontsize=6)
    ax.set_yticks(range(len(c)), c.index, fontsize=6)
    fig.colorbar(im, shrink=0.7, label="Daily return correlation")
    ax.set_title("Return correlation (stocks grouped by sector), Nov 2017 – Oct 2022")
    fig.tight_layout(); fig.savefig(out / "correlation_heatmap.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    worst = seg.max_drawdown.sort_values().head(10).index
    for t in worst:
        ax.plot(drawdowns.index, drawdowns[t] * 100, lw=1, label=t)
    ax.set(ylabel="Drawdown from peak (%)", title="10 deepest drawdowns")
    ax.legend(ncol=5, fontsize=8, frameon=False)
    _clean(ax)
    fig.tight_layout(); fig.savefig(out / "drawdowns.png", dpi=150); plt.close(fig)


def dashboard(seg, sector_tbl, sector_idx, corr, pairs, top, path):
    """One HTML file: risk/return scatter, sector growth, sector table, correlation heatmap, pair list."""
    figs = []
    d = seg.reset_index()
    f = px.scatter(d, x="volatility", y="cagr", color="segment", hover_name="ticker",
                   hover_data={"sector": True, "sharpe": ":.2f", "max_drawdown": ":.1%"},
                   color_discrete_map=SEG_COLORS, title="Risk vs return by segment")
    f.update_layout(xaxis_tickformat=".0%", yaxis_tickformat=".0%")
    figs.append(f)

    f = go.Figure([go.Scatter(x=sector_idx.index, y=sector_idx[s], name=s, mode="lines") for s in sector_idx])
    f.update_layout(title="Equal-weight sector growth of ₹1", yaxis_type="log")
    figs.append(f)

    t = sector_tbl.reset_index()
    f = go.Figure(go.Table(header=dict(values=["Sector", "Stocks", "Median CAGR", "Median vol", "Median max DD", "Median Sharpe"]),
                           cells=dict(values=[t.sector, t.stocks, (t.median_cagr * 100).round(1), (t.median_vol * 100).round(1),
                                              (t.median_mdd * 100).round(1), t.median_sharpe.round(2)])))
    f.update_layout(title="Sector summary (%)")
    figs.append(f)

    f = px.imshow(corr, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title="Return correlation matrix")
    f.update_layout(height=800)
    figs.append(f)

    for frame, title in [(top, "Consistently high-performing stocks"), (pairs, "Low-correlated cross-sector pairs")]:
        fr = frame.reset_index() if frame.index.name else frame
        f = go.Figure(go.Table(header=dict(values=list(fr.columns)),
                               cells=dict(values=[fr[c].round(3) if fr[c].dtype.kind == "f" else fr[c] for c in fr.columns])))
        f.update_layout(title=title)
        figs.append(f)

    html = ["<html><head><meta charset='utf-8'><title>NIFTY-50 Investment Intelligence</title></head>",
            "<body style='font-family:system-ui;max-width:1200px;margin:auto'>",
            "<h1>NIFTY-50 Investment Intelligence</h1><p>Daily adjusted prices, Oct 2012 – Oct 2022.</p>"]
    for i, f in enumerate(figs):
        html.append(f.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False))
    html.append("</body></html>")
    path.write_text("\n".join(html), encoding="utf-8")
