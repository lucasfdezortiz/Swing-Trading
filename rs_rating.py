"""RS Rating calculation — weighted 12-month relative strength vs universe."""

import numpy as np
import pandas as pd
from config import MIN_RS_RATING


def weighted_return(prices: pd.Series) -> float:
    """Calculates IBD-style weighted return: 40% last 3m + 20% each 3m segment."""
    if len(prices) < 252:
        return np.nan
    p_now = prices.iloc[-1]
    p_3m = prices.iloc[-63]
    p_6m = prices.iloc[-126]
    p_9m = prices.iloc[-189]
    p_12m = prices.iloc[-252]

    r3 = (p_now / p_3m) - 1
    r6 = (p_3m / p_6m) - 1
    r9 = (p_6m / p_9m) - 1
    r12 = (p_9m / p_12m) - 1

    return 0.40 * r3 + 0.20 * r6 + 0.20 * r9 + 0.20 * r12


def compute_rs_ratings(all_prices: dict[str, pd.Series]) -> dict[str, float]:
    """
    Given a dict of {ticker: price_series}, computes RS Rating (0-99) for each ticker.
    Returns {ticker: rs_rating}.
    """
    returns = {}
    for ticker, prices in all_prices.items():
        r = weighted_return(prices)
        if not np.isnan(r):
            returns[ticker] = r

    if not returns:
        return {}

    values = np.array(list(returns.values()))
    tickers = list(returns.keys())

    # Percentile rank (0-99)
    from scipy.stats import rankdata
    ranks = rankdata(values, method="average")
    percentiles = (ranks - 1) / (len(ranks) - 1) * 99 if len(ranks) > 1 else np.array([99.0])

    return {t: round(float(p), 1) for t, p in zip(tickers, percentiles)}


def rs_line_at_highs(stock_prices: pd.Series, spy_prices: pd.Series, lookback: int = 252) -> bool:
    """Returns True if RS line (stock/SPY) is within top 10% of its 52-week range."""
    if len(stock_prices) < lookback or len(spy_prices) < lookback:
        return False

    stock_aligned, spy_aligned = stock_prices.align(spy_prices, join="inner")
    if len(stock_aligned) < lookback:
        return False

    rs_line = stock_aligned / spy_aligned
    rs_recent = rs_line.iloc[-lookback:]

    rs_current = rs_recent.iloc[-1]
    rs_max = rs_recent.max()
    rs_min = rs_recent.min()

    if rs_max == rs_min:
        return True

    percentile = (rs_current - rs_min) / (rs_max - rs_min)
    return percentile >= 0.80


def passes_rs_check(rs_rating: float) -> bool:
    return rs_rating >= MIN_RS_RATING
