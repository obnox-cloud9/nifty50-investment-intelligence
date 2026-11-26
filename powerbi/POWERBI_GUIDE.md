# Power BI dashboard

**Quick start:** open `NIFTY50_Dashboard.pbip` in Power BI Desktop and click **Home → Refresh**. The data loads from this repo's raw CSVs on GitHub. If Power BI asks how to connect to `raw.githubusercontent.com`, choose **Anonymous**. If an older Desktop version won't open `.pbip` files, turn on *File → Options → Preview features → Power BI Project (.pbip) save option* and restart.

**Pages:** Overview (KPI cards, risk vs return scatter, sector and segment slicers) · Sectors (median Sharpe and CAGR by sector, growth of Rs 1 by sector) · Volatility & drawdowns (volatility by stock, drawdown over time with a stock slicer) · High performers & pairs (the 14 stocks and 13 pairs).

The rest of this file documents the model, in case you want to rebuild it by hand.


`run.py` writes three Power BI-ready tables to this folder:

| File | Grain | Key columns |
|---|---|---|
| `fact_prices.csv` | one row per stock per trading day (123K rows) | date, ticker, adj_close, daily_return, growth_of_1, drawdown |
| `dim_stock.csv` | one row per stock | ticker, sector, cagr, volatility, max_drawdown, sharpe, sortino, beat_rate, segment |
| `low_corr_pairs.csv` | one row per selected pair | stock_a, stock_b, corr, max_yearly_corr |

## Model
1. In **Get Data → Text/CSV**, load all three files. Set `date` to Date type and `daily_return` to Decimal.
2. Add a date table: **Modeling → New table** `Calendar = CALENDARAUTO()`, then mark it as a date table.
3. Relationships: `Calendar[Date]` 1→* `fact_prices[date]`, and `dim_stock[ticker]` 1→* `fact_prices[ticker]`.

## Measures (DAX)
```DAX
Avg Daily Return = AVERAGE ( fact_prices[daily_return] )

Annualised Return = ( 1 + [Avg Daily Return] ) ^ 252 - 1

Annualised Volatility = STDEV.S ( fact_prices[daily_return] ) * SQRT ( 252 )

Sharpe = DIVIDE ( [Annualised Return] - 0.065, [Annualised Volatility] )

Growth of 1 =
PRODUCTX (
    FILTER ( fact_prices, fact_prices[date] <= MAX ( Calendar[Date] ) ),
    1 + fact_prices[daily_return]
)
```

## Pages
1. **Overview:** KPI cards (stocks, years of data, median CAGR, median volatility), plus a scatter with `volatility` on X, `cagr` on Y and colour = `segment`.
2. **Sector comparison:** clustered bar of median Sharpe by sector, a line chart of the Growth of 1 measure by sector over `Calendar[Date]`, and slicers for sector and year.
3. **Volatility and drawdown:** a line of rolling volatility by stock, and a table of `max_drawdown` sorted ascending.
4. **High performers and diversification:** a table of `dim_stock` filtered to the 14 consistent high performers, and the `low_corr_pairs` table.
