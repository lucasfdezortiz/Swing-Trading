"""
Stock-level checks: Criteria 3–14 of the 14-point swing trading checklist.
Each check returns a dict with 'passes' (bool) and 'details' (str).
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from config import (
    STOP_PCT, MAX_PIVOT_DISTANCE, MIN_VOLUME_SPIKE,
    MIN_BASE_WEEKS, MIN_RR, EARNINGS_BUFFER_DAYS, CAPITAL, MAX_RISK_PCT,
    MAX_BASE_DEPTH_FLAT, MAX_BASE_DEPTH_CUP, VCP_CONTRACTION_THRESHOLD,
)


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def _slope_positive(s: pd.Series, n: int = 5) -> bool:
    """True if series has risen over the last n periods."""
    if len(s) < n + 1:
        return False
    return s.iloc[-1] > s.iloc[-n]


# ── Check 3: Stage 2 ──────────────────────────────────────────────────────────

def check_stage2(df: pd.DataFrame) -> dict:
    close = df["Close"]
    sma200 = _sma(close, 200)

    if sma200.isna().iloc[-1]:
        return {"passes": False, "details": "SMA200 no disponible (datos insuficientes)"}

    price = close.iloc[-1]
    sma200_val = sma200.iloc[-1]
    sma200_rising = _slope_positive(sma200, 10)

    high_52w = close.tail(252).max()
    dist_from_high = (high_52w - price) / high_52w

    above_sma200 = price > sma200_val
    near_highs = dist_from_high <= 0.30

    passes = above_sma200 and sma200_rising and near_highs
    details = (
        f"Precio ${price:.2f} vs SMA200 ${sma200_val:.2f} "
        f"({'↑' if above_sma200 else '↓'}) | SMA200 {'subiendo' if sma200_rising else 'plana/bajando'} | "
        f"Dist. máx 52s: {dist_from_high*100:.1f}%"
    )
    return {"passes": passes, "details": details, "price": price, "sma200": sma200_val}


# ── Check 4: MA alignment ─────────────────────────────────────────────────────

def check_ma_alignment(df: pd.DataFrame) -> dict:
    close = df["Close"]
    sma20 = _sma(close, 20)
    sma50 = _sma(close, 50)
    sma200 = _sma(close, 200)

    if any(s.isna().iloc[-1] for s in [sma20, sma50, sma200]):
        return {"passes": False, "details": "MAs no disponibles"}

    p = close.iloc[-1]
    m20 = sma20.iloc[-1]
    m50 = sma50.iloc[-1]
    m200 = sma200.iloc[-1]

    order_ok = p > m20 > m50 > m200
    slopes_ok = (
        _slope_positive(sma20) and
        _slope_positive(sma50) and
        _slope_positive(sma200, 10)
    )

    passes = order_ok and slopes_ok
    details = (
        f"P${p:.2f} > SMA20${m20:.2f} > SMA50${m50:.2f} > SMA200${m200:.2f} "
        f"({'✓' if order_ok else '✗'}) | Pendientes: {'↑' if slopes_ok else 'alguna plana/↓'}"
    )
    return {"passes": passes, "details": details, "sma20": m20, "sma50": m50, "sma200": m200}


# ── Check 5: Support & resistance levels (informational) ─────────────────────

def find_support_resistance(df: pd.DataFrame) -> dict:
    """Finds nearest support and resistance using recent swing highs/lows."""
    close = df["Close"].tail(60)
    high = df["High"].tail(60)
    low = df["Low"].tail(60)
    price = close.iloc[-1]

    # Swing highs: local max in a 5-bar window
    swing_highs = []
    swing_lows = []
    for i in range(2, len(close) - 2):
        if high.iloc[i] == high.iloc[i-2:i+3].max():
            swing_highs.append(high.iloc[i])
        if low.iloc[i] == low.iloc[i-2:i+3].min():
            swing_lows.append(low.iloc[i])

    resistance_near = min((h for h in swing_highs if h > price), default=None)
    support = max((l for l in swing_lows if l < price), default=price * 0.93)

    # If nearest resistance is within 3%, extend to 52-week high or use measured move (15%)
    if resistance_near is None or (resistance_near - price) / price < 0.03:
        high_52w = df["High"].tail(252).max()
        if (high_52w - price) / price > 0.05:
            resistance = high_52w
        else:
            resistance = price * 1.15  # Measured move fallback
    else:
        resistance = resistance_near

    return {
        "passes": True,
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "details": f"Soporte: ${support:.2f} | Resistencia: ${resistance:.2f}",
    }


# ── Check 6 & 7: RS Rating passed from rs_rating.py ──────────────────────────

def check_rs_rating(rs_rating: float) -> dict:
    from config import MIN_RS_RATING
    passes = rs_rating >= MIN_RS_RATING
    return {
        "passes": passes,
        "details": f"RS Rating: {rs_rating:.0f} ({'✓' if passes else f'< {MIN_RS_RATING} ✗'})",
    }


def check_rs_line(rs_line_at_highs: bool) -> dict:
    return {
        "passes": rs_line_at_highs,
        "details": f"RS Line: {'en máximos ✓' if rs_line_at_highs else 'no en máximos ✗'}",
    }


# ── Check 8: Volume accumulation ─────────────────────────────────────────────

def check_volume_accumulation(df: pd.DataFrame) -> dict:
    recent = df.tail(50).copy()
    up_days = recent[recent["Close"] >= recent["Open"]]
    down_days = recent[recent["Close"] < recent["Open"]]

    vol_up = up_days["Volume"].sum()
    vol_down = down_days["Volume"].sum()
    acc_days = len(up_days)
    dist_days = len(down_days)

    ratio = vol_up / vol_down if vol_down > 0 else 999
    passes = ratio >= 1.2 and acc_days >= dist_days

    details = (
        f"Acumulación/Distribución: {acc_days}d/{dist_days}d | "
        f"Vol ratio: {ratio:.2f} ({'✓' if passes else '✗'})"
    )
    return {"passes": passes, "details": details, "vol_ratio": round(ratio, 2)}


# ── Check 9: Base detection ───────────────────────────────────────────────────

def detect_base(df: pd.DataFrame) -> dict:
    """
    Detects consolidation bases: Flat Base, Cup (& Handle), or VCP.
    Uses weekly data derived from daily OHLC.
    """
    # Resample to weekly
    weekly = df["Close"].resample("W").last().dropna()

    if len(weekly) < MIN_BASE_WEEKS:
        return {"passes": False, "pattern": "None", "base_weeks": 0,
                "pivot": None, "details": "Datos insuficientes para detectar base"}

    best_result = {"passes": False, "pattern": "None", "base_weeks": 0,
                   "pivot": None, "score": 0, "details": "No base encontrada"}

    # Scan windows of varying length (5 to 26 weeks)
    for window in range(MIN_BASE_WEEKS, min(27, len(weekly) + 1)):
        segment = weekly.tail(window)
        high = segment.max()
        low = segment.min()
        depth = (high - low) / high
        pivot = high  # Potential pivot = high of base

        # Check volume contraction during base (weekly volume proxy via daily)
        daily_seg = df.tail(window * 5)
        if len(daily_seg) >= 10:
            first_half_vol = daily_seg.head(len(daily_seg) // 2)["Volume"].mean()
            second_half_vol = daily_seg.tail(len(daily_seg) // 2)["Volume"].mean()
            vol_contracting = second_half_vol < first_half_vol * 1.1
        else:
            vol_contracting = True

        # Flat Base
        if depth <= MAX_BASE_DEPTH_FLAT and vol_contracting:
            score = (1 - depth) * 50 + window
            if score > best_result["score"]:
                best_result = {
                    "passes": True, "pattern": "Flat Base", "base_weeks": window,
                    "pivot": round(pivot, 2), "depth_pct": round(depth * 100, 1),
                    "score": score,
                    "details": f"Flat Base {window} semanas | Profundidad {depth*100:.1f}% | Pivot ${pivot:.2f}",
                }

        # Cup (& Handle)
        elif MAX_BASE_DEPTH_FLAT < depth <= MAX_BASE_DEPTH_CUP and window >= 7 and vol_contracting:
            # Cup shape: price lower in middle
            mid_idx = len(segment) // 2
            mid_low = segment.iloc[mid_idx - 1:mid_idx + 2].min()
            cup_shape = mid_low < segment.iloc[0] * 0.98 and mid_low < segment.iloc[-1] * 0.98
            if cup_shape:
                score = (1 - depth) * 40 + window * 0.8
                if score > best_result["score"]:
                    best_result = {
                        "passes": True, "pattern": "Cup & Handle", "base_weeks": window,
                        "pivot": round(pivot, 2), "depth_pct": round(depth * 100, 1),
                        "score": score,
                        "details": f"Cup & Handle {window} semanas | Profundidad {depth*100:.1f}% | Pivot ${pivot:.2f}",
                    }

        # VCP (Volatility Contraction Pattern) — decreasing price swings
        elif depth <= MAX_BASE_DEPTH_CUP and window >= MIN_BASE_WEEKS:
            swings = []
            for i in range(1, len(segment)):
                swings.append(abs(segment.iloc[i] - segment.iloc[i - 1]) / segment.iloc[i - 1])
            if len(swings) >= 3:
                contracting = all(
                    swings[i] <= swings[i - 1] * (1 + VCP_CONTRACTION_THRESHOLD)
                    for i in range(1, len(swings))
                )
                if contracting and vol_contracting:
                    score = (1 - depth) * 45 + window * 0.9
                    if score > best_result["score"]:
                        best_result = {
                            "passes": True, "pattern": "VCP", "base_weeks": window,
                            "pivot": round(pivot, 2), "depth_pct": round(depth * 100, 1),
                            "score": score,
                            "details": f"VCP {window} semanas | Profundidad {depth*100:.1f}% | Pivot ${pivot:.2f}",
                        }

    return best_result


# ── Check 10: Breakout with volume ────────────────────────────────────────────

def check_breakout(df: pd.DataFrame, pivot: float) -> dict:
    if pivot is None:
        return {"passes": False, "details": "Sin pivot definido", "vol_ratio": None}

    price = df["Close"].iloc[-1]
    vol_avg50 = df["Volume"].tail(50).mean()

    # Check if any of the last 10 days had a breakout with volume
    recent_5 = df.tail(10)
    best_vol_ratio = 0.0
    best_day = None
    for i in range(len(recent_5)):
        day_price = recent_5["Close"].iloc[i]
        day_vol = recent_5["Volume"].iloc[i]
        if day_price >= pivot * 0.995:  # Near or above pivot
            ratio = day_vol / vol_avg50 if vol_avg50 > 0 else 0
            if ratio > best_vol_ratio:
                best_vol_ratio = ratio
                best_day = i

    is_breaking = price >= pivot * 0.995
    vol_ok = best_vol_ratio >= MIN_VOLUME_SPIKE
    days_ago = (len(recent_5) - 1 - best_day) if best_day is not None else None

    passes = is_breaking and vol_ok
    day_str = f"hace {days_ago}d" if days_ago is not None and days_ago > 0 else "hoy"
    details = (
        f"Precio ${price:.2f} vs Pivot ${pivot:.2f} | "
        f"Mejor volumen ({day_str}): {best_vol_ratio:.1f}x media50d ({'✓' if vol_ok else '✗ (< 1.4x)'})"
    )
    return {"passes": passes, "details": details, "vol_ratio": round(best_vol_ratio, 2)}


# ── Check 11: Distance from pivot ────────────────────────────────────────────

def check_pivot_distance(df: pd.DataFrame, pivot: float) -> dict:
    if pivot is None:
        return {"passes": False, "details": "Sin pivot"}

    price = df["Close"].iloc[-1]
    dist = (price - pivot) / pivot

    passes = dist <= MAX_PIVOT_DISTANCE
    if dist < -0.005:
        details = f"Precio ${price:.2f} aún bajo pivot ${pivot:.2f} — posible pre-breakout"
    elif passes:
        details = f"Precio ${price:.2f} dentro del {dist*100:.1f}% del pivot ${pivot:.2f} ✓"
    else:
        details = f"Precio ${price:.2f} extended {dist*100:.1f}% sobre pivot — esperar siguiente base"

    return {"passes": passes, "details": details, "dist_pct": round(dist * 100, 2)}


# ── Check 12: Stop loss ───────────────────────────────────────────────────────

def calculate_stop(df: pd.DataFrame, pivot: float) -> dict:
    price = df["Close"].iloc[-1]
    stop_from_pivot = pivot * (1 - STOP_PCT) if pivot else price * (1 - STOP_PCT)

    # Also use handle/base low as alternative stop
    base_low = df["Low"].tail(30).min()
    stop = max(stop_from_pivot, base_low * 0.99)

    stop_pct = (price - stop) / price
    details = f"Stop: ${stop:.2f} ({stop_pct*100:.1f}% bajo precio actual)"
    return {"passes": True, "stop": round(stop, 2), "stop_pct": round(stop_pct * 100, 2), "details": details}


# ── Check 13: Position sizing ─────────────────────────────────────────────────

def calculate_position_size(entry: float, stop: float) -> dict:
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return {"passes": False, "shares": 0, "details": "Stop superior a entrada — error de cálculo"}

    max_risk_usd = CAPITAL * MAX_RISK_PCT
    shares = int(max_risk_usd / risk_per_share)
    position_value = shares * entry
    position_pct = position_value / CAPITAL * 100

    details = (
        f"Riesgo: ${max_risk_usd:.0f} | "
        f"Acciones: {shares} @ ${entry:.2f} = ${position_value:,.0f} ({position_pct:.1f}% capital)"
    )
    return {
        "passes": shares > 0,
        "shares": shares,
        "position_value": round(position_value, 2),
        "position_pct": round(position_pct, 1),
        "details": details,
    }


# ── Check 14: R:R and earnings ────────────────────────────────────────────────

def check_rr_and_earnings(ticker: str, entry: float, stop: float, resistance: float) -> dict:
    target = resistance
    risk = entry - stop
    reward = target - entry

    rr = reward / risk if risk > 0 else 0
    rr_ok = rr >= MIN_RR

    # Earnings check
    earnings_ok = True
    earnings_date = None
    earnings_detail = "Earnings: sin datos"

    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        if cal is not None and not cal.empty:
            # Handle both dict and DataFrame formats
            if isinstance(cal, dict):
                earnings_dates = cal.get("Earnings Date", [])
                if earnings_dates:
                    earnings_date = pd.Timestamp(earnings_dates[0])
            elif isinstance(cal, pd.DataFrame):
                if "Earnings Date" in cal.columns:
                    earnings_date = pd.Timestamp(cal["Earnings Date"].iloc[0])
                elif "Earnings Date" in cal.index:
                    earnings_date = pd.Timestamp(cal.loc["Earnings Date"].iloc[0])

            if earnings_date:
                days_to_earnings = (earnings_date - pd.Timestamp.now()).days
                earnings_ok = days_to_earnings >= EARNINGS_BUFFER_DAYS
                earnings_detail = (
                    f"Earnings: {earnings_date.strftime('%Y-%m-%d')} "
                    f"({days_to_earnings}d) {'✓' if earnings_ok else '✗ (<14d)'}"
                )
    except Exception:
        pass  # If we can't get earnings, don't block

    passes = rr_ok and earnings_ok
    details = (
        f"Target: ${target:.2f} | R:R {rr:.1f}:1 ({'✓' if rr_ok else f'< {MIN_RR} ✗'}) | "
        f"{earnings_detail}"
    )

    return {
        "passes": passes,
        "rr": round(rr, 2),
        "target": round(target, 2),
        "earnings_date": str(earnings_date) if earnings_date else None,
        "details": details,
    }
