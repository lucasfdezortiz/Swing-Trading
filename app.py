import streamlit as st
import pandas as pd
import warnings
import yfinance as yf
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Swing Trading Scanner", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow:wght@400;500;600;700&family=Bebas+Neue&display=swap');

html, body, .stApp { background-color: #050f05 !important; }

.terminal-header {
    background: #050f05;
    border: 1px solid #00ff41;
    border-radius: 10px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    font-family: 'Share Tech Mono', monospace;
}
.terminal-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 1.2rem;
}
.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot-r { background: #ff5f57; }
.dot-y { background: #febc2e; }
.dot-g { background: #28c840; }
.terminal-path {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    color: #00ff41;
    margin-left: 8px;
    opacity: 0.7;
}
.terminal-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    color: #00ff41;
    letter-spacing: 4px;
    line-height: 1;
    margin-bottom: 0.3rem;
}
.terminal-title span { color: #ffffff; }
.terminal-subtitle {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    color: #00aa2c;
    margin-top: 0.5rem;
}
.terminal-cursor {
    display: inline-block;
    width: 8px;
    height: 14px;
    background: #00ff41;
    margin-left: 4px;
    animation: blink 1s infinite;
    vertical-align: middle;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }

.metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 1.8rem;
}
.metric {
    background: #050f05;
    border: 1px solid #00ff41;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}
.metric-val {
    font-family: 'Share Tech Mono', monospace;
    font-size: 2rem;
    color: #00ff41;
    line-height: 1;
}
.metric-val.white { color: #ffffff; }
.metric-val.yellow { color: #febc2e; }
.metric-lbl {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.62rem;
    color: #00aa2c;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 6px;
}

.market-ok {
    background: #050f05;
    border: 1px solid #00ff41;
    border-radius: 8px;
    padding: 0.8rem 1.2rem;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #00ff41;
    margin-bottom: 1rem;
}
.market-warn {
    background: #1a0f00;
    border: 1px solid #febc2e;
    border-radius: 8px;
    padding: 0.8rem 1.2rem;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #febc2e;
    margin-bottom: 1rem;
}

.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 1.8rem 0 1rem;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid #00ff41;
}
.section-badge {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 2px;
    padding: 3px 10px;
    border-radius: 4px;
    background: #00ff41;
    color: #050f05;
}
.section-badge.watch {
    background: #050f05;
    color: #febc2e;
    border: 1px solid #febc2e;
}
.section-label {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.9rem;
    color: #00ff41;
    letter-spacing: 2px;
}

.stock-card {
    background: #050f05;
    border: 1px solid #00ff41;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem;
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 1.5rem;
    align-items: start;
}
.stock-card.watch {
    border-color: #febc2e;
    opacity: 0.9;
}

.stock-rank {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.8rem;
    color: #1a3a1a;
    line-height: 1;
    padding-top: 4px;
    min-width: 30px;
}

.stock-ticker {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: #00ff41;
    letter-spacing: 3px;
    line-height: 1;
    margin-bottom: 3px;
}
.stock-card.watch .stock-ticker { color: #febc2e; }

.stock-pattern {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    color: #00aa2c;
    margin-bottom: 8px;
}

.stock-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
}
.pill {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.68rem;
    padding: 3px 10px;
    border-radius: 3px;
    border: 1px solid #1a3a1a;
    color: #00aa2c;
}
.pill.highlight {
    border-color: #00ff41;
    color: #00ff41;
}
.pill.warn {
    border-color: #febc2e;
    color: #febc2e;
}

.stock-right { text-align: right; min-width: 150px; }
.stock-price {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.6rem;
    color: #ffffff;
    line-height: 1;
}
.stock-stop {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    color: #ff5f57;
    margin-top: 4px;
}
.stock-target {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    color: #00ff41;
    margin-top: 2px;
}
.stock-rr {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    color: #febc2e;
    margin-top: 4px;
}
.stock-rs {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    color: #00aa2c;
    margin-top: 2px;
}
.stock-checks {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.7rem;
    color: #1a3a1a;
    margin-top: 8px;
}
.stock-checks span { color: #00ff41; }

.failed-checks {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.68rem;
    color: #ff5f57;
    margin-top: 6px;
}

.empty {
    text-align: center;
    padding: 2.5rem;
    border: 1px dashed #1a3a1a;
    border-radius: 10px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #1a3a1a;
    text-transform: uppercase;
    letter-spacing: 2px;
}

div[data-testid="stButton"] > button {
    background: #00ff41 !important;
    color: #050f05 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.95rem !important;
    letter-spacing: 4px !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.8rem !important;
    width: 100% !important;
}
div[data-testid="stButton"] > button:hover { opacity: 0.85 !important; }

.stDownloadButton > button {
    background: transparent !important;
    color: #00ff41 !important;
    border: 1px solid #1a3a1a !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.78rem !important;
}

div[data-testid="stSpinner"] { color: #00ff41 !important; }
</style>
""", unsafe_allow_html=True)

from datetime import datetime
now = datetime.now()

st.markdown(f"""
<div class="terminal-header">
    <div class="terminal-bar">
        <div class="dot dot-r"></div>
        <div class="dot dot-y"></div>
        <div class="dot dot-g"></div>
        <span class="terminal-path">~/swing-scanner · IBD Methodology · 14-check system</span>
    </div>
    <div class="terminal-title">Swing <span>Scanner</span></div>
    <div class="terminal-subtitle">
        > {now.strftime('%Y-%m-%d %H:%M:%S')} · Capital ${200000:,} · Risk 1% · Stop 7.3%
        <span class="terminal-cursor"></span>
    </div>
</div>
""", unsafe_allow_html=True)

if st.button("▶  RUN SCAN"):
    import sys
    sys.path.insert(0, "/mount/src/swing-trading")

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

    with st.spinner("> Checking market conditions..."):
        market = check_market_condition()

    if market["passes"]:
        st.markdown(f'<div class="market-ok">✓ MARKET OK — {market["details"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="market-warn">⚠ MARKET WARNING — {market["details"]}</div>', unsafe_allow_html=True)

    with st.spinner("> Downloading SPY..."):
        spy_df = yf.download("SPY", period=f"{LOOKBACK_DAYS}d", progress=False, auto_adjust=True)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.droplevel(1)
        spy_prices = spy_df["Close"]

    tickers = get_full_universe()
    st.markdown(f'<div class="market-ok">> Universe loaded: {len(tickers)} tickers</div>', unsafe_allow_html=True)

    all_data = {}
    progress_bar = st.progress(0)
    batch_size = 50

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        batch_str = " ".join(batch)
        try:
            raw = yf.download(batch_str, period=f"{LOOKBACK_DAYS}d",
                progress=False, auto_adjust=True, group_by="ticker")
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

    st.markdown(f'<div class="market-ok">> {len(all_data)} tickers with valid data · Computing RS Ratings...</div>', unsafe_allow_html=True)

    all_prices = {t: df["Close"] for t, df in all_data.items()}
    rs_ratings = compute_rs_ratings(all_prices)

    all_results = []
    progress_bar2 = st.progress(0)
    total = len(all_data)

    for idx, (ticker, df) in enumerate(all_data.items()):
        try:
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
            entry = df["Close"].iloc[-1]
            stop = c12["stop"]
            c13 = calculate_position_size(entry, stop)
            resistance = c5["resistance"]
            c14 = check_rr_and_earnings(ticker, entry, stop, resistance)
            if not c14["passes"]: failed.append(("14-RR/Earnings", c14["details"]))
            if not market["passes"]: failed.append(("1-Mercado", "SPY/QQQ fuera de tendencia"))

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
            score = (rs_rating * 0.4 + vol_ratio * 10 + rr * 5
                + base_weeks * 0.5 + (100 - abs(dist_pct) * 5) + checks_passed * 2)

            all_results.append({
                "ticker": ticker, "status": status, "score": round(score, 2),
                "checks_passed": checks_passed,
                "failed_checks": [f[0] for f in failed],
                "entry": round(entry, 2),
                "stop": round(stop, 2) if stop else None,
                "target": round(c14.get("target", entry * 1.15), 2),
                "rr": round(rr, 2), "rs_rating": round(rs_rating, 1),
                "pattern": c9.get("pattern", "None"),
                "base_weeks": base_weeks, "pivot": round(pivot, 2) if pivot else None,
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

    st.markdown(f"""
    <div class="metrics">
        <div class="metric">
            <div class="metric-val">{len(confirmed)}</div>
            <div class="metric-lbl">Confirmados</div>
        </div>
        <div class="metric">
            <div class="metric-val yellow">{len(watchlist)}</div>
            <div class="metric-lbl">Vigilancia</div>
        </div>
        <div class="metric">
            <div class="metric-val">{len(all_data)}</div>
            <div class="metric-lbl">Analizados</div>
        </div>
        <div class="metric">
            <div class="metric-val white" style="font-size:1.4rem">{now.strftime('%H:%M')}</div>
            <div class="metric-lbl">Timestamp</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    def render_confirmed(stocks):
        st.markdown("""
        <div class="section-header">
            <span class="section-badge">CONFIRMED</span>
            <span class="section-label">READY TO TRADE — 14/14 CHECKS</span>
        </div>
        """, unsafe_allow_html=True)

        if not stocks:
            st.markdown('<div class="empty">No candidates pass all 14 checks today</div>', unsafe_allow_html=True)
            return

        cards = ""
        for i, c in enumerate(stocks, 1):
            stop_pct = abs((c["entry"] - c["stop"]) / c["entry"] * 100) if c["stop"] else 0
            target_pct = abs((c["target"] - c["entry"]) / c["entry"] * 100) if c["target"] else 0
            cards += f"""
            <div class="stock-card">
                <div class="stock-rank">#{i}</div>
                <div>
                    <div class="stock-ticker">{c['ticker']}</div>
                    <div class="stock-pattern">{c['pattern']} · {c['base_weeks']} weeks base · RS {c['rs_rating']:.0f}</div>
                    <div class="stock-pills">
                        <span class="pill highlight">PIVOT ${c['pivot']}</span>
                        <span class="pill highlight">DIST {c['dist_pct']:+.1f}%</span>
                        <span class="pill">{c['shares']} shares</span>
                        <span class="pill">${c['position_value']:,.0f} position</span>
                        <span class="pill">Earnings: {c['earnings_date']}</span>
                    </div>
                </div>
                <div class="stock-right">
                    <div class="stock-price">${c['entry']}</div>
                    <div class="stock-stop">▼ STOP ${c['stop']} (-{stop_pct:.1f}%)</div>
                    <div class="stock-target">▲ TARGET ${c['target']} (+{target_pct:.1f}%)</div>
                    <div class="stock-rr">R:R {c['rr']:.1f}:1</div>
                    <div class="stock-checks"><span>{c['checks_passed']}</span>/14 checks</div>
                </div>
            </div>
            """
        st.markdown(cards, unsafe_allow_html=True)

    def render_watchlist(stocks):
        st.markdown("""
        <div class="section-header">
            <span class="section-badge watch">WATCHLIST</span>
            <span class="section-label">MISSING 1-2 CHECKS</span>
        </div>
        """, unsafe_allow_html=True)

        if not stocks:
            st.markdown('<div class="empty">No watchlist candidates today</div>', unsafe_allow_html=True)
            return

        cards = ""
        for i, c in enumerate(stocks, 1):
            failed_str = " · ".join(c["failed_checks"])
            cards += f"""
            <div class="stock-card watch">
                <div class="stock-rank">#{i}</div>
                <div>
                    <div class="stock-ticker">{c['ticker']}</div>
                    <div class="stock-pattern">{c['pattern']} · {c['base_weeks']}w base · RS {c['rs_rating']:.0f}</div>
                    <div class="failed-checks">✗ {failed_str}</div>
                </div>
                <div class="stock-right">
                    <div class="stock-price">${c['entry']}</div>
                    <div class="stock-stop">▼ STOP ${c['stop']}</div>
                    <div class="stock-target">▲ TARGET ${c['target']}</div>
                    <div class="stock-rr">R:R {c['rr']:.1f}:1</div>
                    <div class="stock-checks"><span>{c['checks_passed']}</span>/14 checks</div>
                </div>
            </div>
            """
        st.markdown(cards, unsafe_allow_html=True)

    render_confirmed(top_confirmed)
    render_watchlist(top_watchlist)

    if all_results:
        df_export = pd.DataFrame([r for r in all_results if r["status"] != "discard"])
        csv = df_export.to_csv(index=False).encode("utf-8")
        st.download_button("↓ Export CSV", csv, f"swing_scan_{now.strftime('%Y%m%d')}.csv", "text/csv")