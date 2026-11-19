"""Load daily NIFTY-50 prices and attach sectors."""
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SOURCE = "https://github.com/Ram9219/NIFTY-50-Stock-Market-Data-2000---2022-"

SECTOR = {
    "ADANIENT": "Metals & Mining", "ADANIPORTS": "Services", "APOLLOHOSP": "Healthcare",
    "ASIANPAINT": "Consumer Durables", "AXISBANK": "Financials", "BAJAJ-AUTO": "Automobile",
    "BAJAJFINSV": "Financials", "BAJFINANCE": "Financials", "BHARTIARTL": "Telecom",
    "BPCL": "Oil & Gas", "BRITANNIA": "FMCG", "CIPLA": "Healthcare", "COALINDIA": "Metals & Mining",
    "DIVISLAB": "Healthcare", "DRREDDY": "Healthcare", "EICHERMOT": "Automobile",
    "GRASIM": "Construction Materials", "HCLTECH": "IT", "HDFC": "Financials", "HDFCBANK": "Financials",
    "HDFCLIFE": "Financials", "HEROMOTOCO": "Automobile", "HINDALCO": "Metals & Mining",
    "HINDUNILVR": "FMCG", "ICICIBANK": "Financials", "INDUSINDBK": "Financials", "INFY": "IT",
    "ITC": "FMCG", "JSWSTEEL": "Metals & Mining", "KOTAKBANK": "Financials", "LT": "Construction",
    "M_and_M": "Automobile", "MARUTI": "Automobile", "NESTLEIND": "FMCG", "NTPC": "Power",
    "ONGC": "Oil & Gas", "POWERGRID": "Power", "RELIANCE": "Oil & Gas", "SBILIFE": "Financials",
    "SBIN": "Financials", "SUNPHARMA": "Healthcare", "TATACONSUM": "FMCG", "TATAMOTORS": "Automobile",
    "TATASTEEL": "Metals & Mining", "TCS": "IT", "TECHM": "IT", "TITAN": "Consumer Durables",
    "ULTRACEMCO": "Construction Materials", "UPL": "Chemicals", "WIPRO": "IT",
}


# Level shifts in the source data that are not real price moves. History before each date is
# rescaled so the series is continuous (this is what a correct adjusted close would show).
CORPORATE_ACTION_FIXES = {
    "TATASTEEL": ("2022-06-16", "split not adjusted in source: price doubles overnight"),
    "HDFC": ("2015-12-28", "stale/incorrect prices before this date: flat for days, then +50% jump"),
    "ADANIENT": ("2015-06-03", "2015 demerger not adjusted in source: -39% on the record date"),
}


def fix_level_shifts(prices):
    p = prices.copy()
    for t, (date, _) in CORPORATE_ACTION_FIXES.items():
        i = p.index.get_loc(pd.Timestamp(date))
        ratio = p[t].iloc[i] / p[t].iloc[i - 1]
        p.loc[p.index[:i], t] *= ratio
    return p


def download():
    if not RAW.exists():
        subprocess.run(["git", "clone", "--depth", "1", SOURCE, str(RAW)], check=True)


def load_prices() -> pd.DataFrame:
    """Wide frame of adjusted closes: index = date, columns = tickers."""
    download()
    series = {}
    for f in sorted(RAW.glob("*.csv")):
        d = pd.read_csv(f)
        # two files use DD-MM-YYYY, the rest ISO dates
        d["Date"] = pd.to_datetime(d["Date"], format="%d-%m-%Y" if "-" in d.Date[0][:3] else "%Y-%m-%d")
        s = d.set_index("Date")["Adj Close"].astype(float)
        series[f.stem] = s[s > 0]
    return fix_level_shifts(pd.DataFrame(series).sort_index())
