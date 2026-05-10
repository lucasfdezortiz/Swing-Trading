import streamlit as st
import sys
import warnings
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

sys.path.insert(0, "/Users/lucasfdezortiz/Documents/Swing-Trading")

from config import LOOKBACK_DAYS, MIN_AVG_VOLUME, TOP_N_CANDIDATES
from universe import get_full_universe
from market_check import check_market_condition
from rs_rating import compute_rs_ratings, rs_line_at_highs
from stock_criteria import (
    check_stage2, check_ma_alignment, find_support_resistance,
    check_rs_rating, check_rs_line, check_volume_accumulation,
    detect_base, check_breakout, check_pivot_distance,
    calculate_stop, calculate_position_size, check_rr_and_earnings,
)

st.set_page_config(
    page_title="Swing Trading Scanner",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Swing Trading Scanner")
st.caption("14 checks · IBD Methodology · RS Rating · Kelly Sizing")

if st.button("🔍 Escanear hoy", type="primary", use_container_width=True):

    # Mercado
    with st.spinner("Comprobando condición del mercado..."):
        market = check_market_condition()

    if market["passes"]:
        st.success(f"✅ Mercado OK — {market['details']}")
    else:
        st.warning(f"⚠️ Mercado no favorable — {market['details']}")

    # SPY para RS Line
    with st.spinner("Descargando SPY..."):
        spy_df = yf.download("SPY", period=f"{LOOKBACK_DAYS}d", progress=False, auto_adjust=True)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.droplevel(1)
        spy_prices = spy_df["Close"]

    # Universo
    tickers = get_full_universe()
    st.info(f"Escaneando {len(tickers)} tickers...")

    all_data = {}
    progress_bar = st.progress(0)
    batch_size = 50

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        batch_str = " ".join(batch)
        try:
            raw = yf.download(
                batch_str, period=f"{LOOKBACK_DAYS}d",
                progress=False, auto_adjust=True, group_by="ticker"
            )
            for t in batch:
                try:
                    df = raw[t].copy() if len(batch) > 1 and t in raw.columns.get_level_values(0) else raw.copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.droplevel(1)
                    df = df.dropna(how="all")
                    if not df.empty and len(df) >= 60 and df["Volume"].tail(20).mean() >= MIN_AVG_VOLUME:
                        all_data[t] = df
                except Exception:
                    pass
        except Exception:
            pass
        progress_bar.progress(min((i + batch_size) / len(tickers), 1.0))

    st.info(f"{len(all_data)} tickers con datos válidos. Calculando RS Ratings...")

    # RS Ratings
    all_prices = {t: df["Close"] for t, df in all_data.items()}
    rs_ratings = compute_rs_ratings(all_prices)

    # Evaluar acciones
    all_results = []
    progress_bar2 = st.progress(0)
    total = len(all_data)

    for idx, (ticker, df) in enumerate(all_data.items()):
        try:
            checks = {}
            failed = []

            c3 = check_stage2(df)
            if not c3["passes"]: failed.append(("3-Stage2", c3["details"]))

            c4 = check_ma_alignment(df)
            if not c4["passes"]: failed.append(("4-MAs", c4["details"]))

            c5 = find_support_resistance(df)
            rs_rating = rs_ratings.get(ticker, 0)

            c6 = check_rs_rating(rs_rating)
            if not c6["passes"]: failed.append(("6-RSRating", c6["details"]))

            rs_at_highs = rs_line_at_highs(df["Close"], spy_prices)
            c7 = check_rs_line(rs_at_highs)
            if not c7["passes"]: failed.append(("7-RSLine", c7["details"]))

            c8 = check_volume_accumulation(df)
            if not c8["passes"]: failed.append(("8-VolAcc", c8["details"]))

            c9 = detect_base(df)
            if not c9["passes"]: failed.append(("9-Base", c9["details"]))

            pivot = c9.get("pivot")
            c10 = check_breakout(df, pivot)
            if not c10["passes"]: failed.append(("10-Breakout", c10["details"]))

            c11 = check_pivot_distance(df, pivot)
            if not c11["passes"]: failed.append(("11-PivDist", c11["details"]))

            c12 = calculate_stop(df, pivot)
            c13 = calculate_position_size(df["Close"].iloc[-1], c12["stop"])

            resistance = c5["resistance"]
            entry = df["Close"].iloc[-1]
            stop = c12["stop"]

            c14 = check_rr_and_earnings(ticker, entry, stop, resistance)
            if not c14["passes"]: failed.append(("14-RR/Earnings", c14["details"]))

            if not market["passes"]:
                failed.append(("1-Mercado", "SPY/QQQ fuera de tendencia alcista"))

            checks_passed = 14 - len(failed)
            hard_fail = any(k in ("3-Stage2", "4-MAs") for k, _ in failed)

            if hard_fail or checks_passed < 12:
                status = "discard"
            elif checks_passed == 14:
                status = "confirmed"
            else:
                status = "watchlist"

            vol_ratio = c10.get("vol_ratio") or 0
            dist_pct = c11.get("dist_pct") or 0
            rr = c14.get("rr") or 0
            base_weeks = c9.get("base_weeks") or 0
            score = (
                rs_rating * 0.4 + vol_ratio * 10 + rr * 5
                + base_weeks * 0.5 + (100 - abs(dist_pct) * 5)
                + checks_passed * 2
            )

            all_results.append({
                "ticker": ticker,
                "status": status,
                "score": round(score, 2),
                "checks_passed": checks_passed,
                "failed_checks": [f[0] for f in failed],
                "entry": round(entry, 2),
                "stop": round(stop, 2) if stop else None,
                "target": round(c14.get("target", entry * 1.15), 2),
                "rr": round(rr, 2),
                "rs_rating": round(rs_rating, 1),
                "pattern": c9.get("pattern", "None"),
                "base_weeks": base_weeks,
                "pivot": round(pivot, 2) if pivot else None,
                "dist_pct": round(dist_pct, 2),
                "shares": c13.get("shares", 0),
                "position_value": c13.get("position_value", 0),
                "earnings_date": c14.get("earnings_date", "—"),
            })
        except Exception:
            pass
        progress_bar2.progress((idx + 1) / total)

    confirmed = sorted([r for r in all_results if r["status"] == "confirmed"], key=lambda x: x["score"], reverse=True)
    watchlist = sorted([r for r in all_results if r["status"] == "watchlist"], key=lambda x: x["score"], reverse=True)

    top_confirmed = confirmed[:TOP_N_CANDIDATES]
    top_watchlist = watchlist[:10]

    # Métricas resumen
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Confirmados", len(confirmed))
    col2.metric("👁 En Vigilancia", len(watchlist))
    col3.metric("📊 Tickers Analizados", len(all_data))

    # Tabla confirmados
    if top_confirmed:
        st.subheader("✅ Candidatos Confirmados — Listos para operar")
        rows = []
        for c in top_confirmed:
            stop_pct = abs((c["entry"] - c["stop"]) / c["entry"] * 100) if c["stop"] else 0
            target_pct = abs((c["target"] - c["entry"]) / c["entry"] * 100) if c["target"] else 0
            rows.append({
                "Ticker": c["ticker"],
                "Precio": f"${c['entry']}",
                "Pivot": f"${c['pivot']}",
                "Dist. Pivot": f"{c['dist_pct']:+.1f}%",
                "Patrón": c["pattern"],
                "Base (sem)": c["base_weeks"],
                "RS Rating": c["rs_rating"],
                "Stop": f"${c['stop']} (-{stop_pct:.1f}%)",
                "Target": f"${c['target']} (+{target_pct:.1f}%)",
                "R:R": f"{c['rr']:.1f}:1",
                "Acciones": c["shares"],
                "Valor pos.": f"${c['position_value']:,.0f}",
                "Earnings": c["earnings_date"],
                "Checks": f"{c['checks_passed']}/14",
                "Score": c["score"],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.warning("Ningún candidato pasa los 14 checks hoy.")

    # Tabla vigilancia
    if top_watchlist:
        st.subheader("👁 Lista de Vigilancia — Faltan 1-2 checks")
        rows_w = []
        for c in top_watchlist:
            rows_w.append({
                "Ticker": c["ticker"],
                "Precio": f"${c['entry']}",
                "Patrón": c["pattern"],
                "RS Rating": c["rs_rating"],
                "R:R": f"{c['rr']:.1f}:1",
                "Checks": f"{c['checks_passed']}/14",
                "Checks fallados": ", ".join(c["failed_checks"]),
                "Score": c["score"],
            })
        st.dataframe(rows_w, use_container_width=True, hide_index=True)

    # Exportar
    if all_results:
        df_export = pd.DataFrame([r for r in all_results if r["status"] != "discard"])
        csv = df_export.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar CSV", csv, "swing_scan_hoy.csv", "text/csv")