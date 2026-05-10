"""Market condition checks — Criteria 1 and 2 of the 14-point checklist."""

import pandas as pd
import yfinance as yf
from config import MAX_DISTRIBUTION_DAYS

# GICS sector → ETF sectorial mapping
SECTOR_ETF_MAP = {
    "Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
    # European / general
    "Unknown": "SPY",
}


def _download(ticker: str, period: str = "1y") -> pd.DataFrame:
    df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df


def _distribution_days(df: pd.DataFrame, window: int = 20) -> int:
    """Counts distribution days in the last `window` sessions."""
    recent = df.tail(window).copy()
    vol_avg = recent["Volume"].mean()
    down_days = recent[recent["Close"] < recent["Open"]]
    dist_days = down_days[down_days["Volume"] > vol_avg * 1.0]
    return len(dist_days)


def _sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()


def check_market_condition() -> dict:
    """
    Check 1: SPY + QQQ in confirmed uptrend.
    Returns dict with pass/fail and details.
    """
    result = {"passes": False, "spy": {}, "qqq": {}, "distribution_days": {}, "details": ""}

    spy = _download("SPY", "1y")
    qqq = _download("QQQ", "1y")

    if spy.empty or qqq.empty:
        result["details"] = "No se pudo descargar SPY/QQQ"
        return result

    spy_price = spy["Close"].iloc[-1]
    spy_sma200 = _sma(spy["Close"], 200).iloc[-1]
    qqq_price = qqq["Close"].iloc[-1]
    qqq_sma200 = _sma(qqq["Close"], 200).iloc[-1]

    spy_above = spy_price > spy_sma200
    qqq_above = qqq_price > qqq_sma200

    spy_dist = _distribution_days(spy)
    qqq_dist = _distribution_days(qqq)
    max_dist = max(spy_dist, qqq_dist)

    result["spy"] = {"price": round(spy_price, 2), "sma200": round(spy_sma200, 2), "above": spy_above}
    result["qqq"] = {"price": round(qqq_price, 2), "sma200": round(qqq_sma200, 2), "above": qqq_above}
    result["distribution_days"] = {"spy": spy_dist, "qqq": qqq_dist}

    passes = spy_above and qqq_above and max_dist <= MAX_DISTRIBUTION_DAYS
    result["passes"] = passes

    if not spy_above:
        result["details"] += f"SPY bajo SMA200 (${spy_price:.0f} < ${spy_sma200:.0f}). "
    if not qqq_above:
        result["details"] += f"QQQ bajo SMA200 (${qqq_price:.0f} < ${qqq_sma200:.0f}). "
    if max_dist > MAX_DISTRIBUTION_DAYS:
        result["details"] += f"Demasiados distribution days (SPY:{spy_dist}, QQQ:{qqq_dist}). "
    if passes:
        result["details"] = f"Mercado alcista ✓ — SPY ${spy_price:.0f} (+{((spy_price/spy_sma200)-1)*100:.1f}% sobre SMA200), dist. days: {max_dist}"

    return result


def check_sector_leadership(sector: str, spy_df: pd.DataFrame = None) -> dict:
    """
    Check 2: Sector ETF outperforms SPY over last 4 weeks.
    """
    etf = SECTOR_ETF_MAP.get(sector, "SPY")
    result = {"passes": False, "etf": etf, "sector_ret_4w": None, "spy_ret_4w": None, "details": ""}

    if etf == "SPY":
        result["passes"] = True
        result["details"] = f"Sector '{sector}' sin ETF específico — omitido"
        return result

    try:
        etf_df = _download(etf, "3mo")
        if spy_df is None:
            spy_df = _download("SPY", "3mo")

        if etf_df.empty or spy_df.empty or len(etf_df) < 20 or len(spy_df) < 20:
            result["details"] = f"Datos insuficientes para {etf}"
            result["passes"] = True  # Pass by default if no data
            return result

        etf_ret = (etf_df["Close"].iloc[-1] / etf_df["Close"].iloc[-20]) - 1
        spy_ret = (spy_df["Close"].iloc[-1] / spy_df["Close"].iloc[-20]) - 1

        result["sector_ret_4w"] = round(etf_ret * 100, 2)
        result["spy_ret_4w"] = round(spy_ret * 100, 2)
        result["passes"] = etf_ret >= spy_ret

        if result["passes"]:
            result["details"] = f"{etf} lidera: +{etf_ret*100:.1f}% vs SPY +{spy_ret*100:.1f}% (4 semanas)"
        else:
            result["details"] = f"{etf} rezagado: +{etf_ret*100:.1f}% vs SPY +{spy_ret*100:.1f}% (4 semanas)"

    except Exception as e:
        result["passes"] = True
        result["details"] = f"Error comprobando sector: {e}"

    return result
