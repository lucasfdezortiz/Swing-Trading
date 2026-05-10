"""
Main orchestrator — runs the 14-check swing trading scanner.
Usage: python3 scanner.py
"""

import sys
import json
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

warnings.filterwarnings("ignore")

sys.path.insert(0, "/Users/lucasfdezortiz/stock-scanner")

from config import LOOKBACK_DAYS, MIN_AVG_VOLUME, TOP_N_CANDIDATES
from universe import get_full_universe
from market_check import check_market_condition, check_sector_leadership
from rs_rating import compute_rs_ratings, rs_line_at_highs, passes_rs_check
from stock_criteria import (
    check_stage2, check_ma_alignment, find_support_resistance,
    check_rs_rating, check_rs_line, check_volume_accumulation,
    detect_base, check_breakout, check_pivot_distance,
    calculate_stop, calculate_position_size, check_rr_and_earnings,
)

console = Console()


def _download_ticker(ticker: str) -> tuple[str, pd.DataFrame | None]:
    try:
        df = yf.download(ticker, period=f"{LOOKBACK_DAYS}d", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        if df.empty or len(df) < 60:
            return ticker, None
        # Minimum volume filter
        if df["Volume"].tail(20).mean() < MIN_AVG_VOLUME:
            return ticker, None
        return ticker, df
    except Exception:
        return ticker, None


def get_ticker_info(ticker: str) -> dict:
    """Returns sector and company name from yfinance."""
    try:
        info = yf.Ticker(ticker).fast_info
        return {
            "name": getattr(info, "name", ticker),
            "sector": "Unknown",
        }
    except Exception:
        return {"name": ticker, "sector": "Unknown"}


def get_ticker_sector(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info
        return info.get("sector", "Unknown")
    except Exception:
        return "Unknown"


def evaluate_stock(
    ticker: str,
    df: pd.DataFrame,
    spy_prices: pd.Series,
    rs_ratings: dict,
    market_ok: bool,
) -> dict:
    """
    Runs all 14 checks on a single stock without early exit.
    Returns a full result dict with passed/failed checks.
    status: 'confirmed' (14/14), 'watchlist' (fails 1-2 soft checks), 'discard'
    """
    checks = {}
    failed = []

    # ── Check 3: Stage 2
    c3 = check_stage2(df)
    checks["stage2"] = c3
    if not c3["passes"]:
        failed.append(("3-Stage2", c3["details"]))

    # ── Check 4: MA alignment
    c4 = check_ma_alignment(df)
    checks["ma_alignment"] = c4
    if not c4["passes"]:
        failed.append(("4-MAs", c4["details"]))

    # ── Check 5: Support/resistance (informational)
    c5 = find_support_resistance(df)
    checks["sr_levels"] = c5

    # ── Check 6: RS Rating
    rs_rating = rs_ratings.get(ticker, 0)
    c6 = check_rs_rating(rs_rating)
    checks["rs_rating"] = c6
    if not c6["passes"]:
        failed.append(("6-RSRating", c6["details"]))

    # ── Check 7: RS Line at highs
    rs_at_highs = rs_line_at_highs(df["Close"], spy_prices)
    c7 = check_rs_line(rs_at_highs)
    checks["rs_line"] = c7
    if not c7["passes"]:
        failed.append(("7-RSLine", c7["details"]))

    # ── Check 8: Volume accumulation
    c8 = check_volume_accumulation(df)
    checks["vol_accumulation"] = c8
    if not c8["passes"]:
        failed.append(("8-VolAcc", c8["details"]))

    # ── Check 9: Base detection
    c9 = detect_base(df)
    checks["base"] = c9
    if not c9["passes"]:
        failed.append(("9-Base", c9["details"]))

    pivot = c9.get("pivot")

    # ── Check 10: Breakout with volume
    c10 = check_breakout(df, pivot)
    checks["breakout"] = c10
    if not c10["passes"]:
        failed.append(("10-Breakout", c10["details"]))

    # ── Check 11: Distance from pivot
    c11 = check_pivot_distance(df, pivot)
    checks["pivot_distance"] = c11
    if not c11["passes"]:
        failed.append(("11-PivDist", c11["details"]))

    # ── Check 12: Stop loss (always passes)
    c12 = calculate_stop(df, pivot)
    checks["stop"] = c12

    entry = df["Close"].iloc[-1]
    stop = c12["stop"]

    # ── Check 13: Position sizing (always passes)
    c13 = calculate_position_size(entry, stop)
    checks["position_size"] = c13

    # ── Check 14: R:R and earnings
    resistance = c5["resistance"]
    c14 = check_rr_and_earnings(ticker, entry, stop, resistance)
    checks["rr_earnings"] = c14
    if not c14["passes"]:
        failed.append(("14-RR/Earnings", c14["details"]))

    # ── Market check 1
    if not market_ok:
        failed.append(("1-Mercado", "SPY/QQQ fuera de tendencia alcista"))

    checks_passed = 14 - len(failed)

    # ── Classify
    # Hard disqualifiers: Stage2 or MA broken = discard (stock in downtrend)
    hard_fail = any(k in ("3-Stage2", "4-MAs") for k, _ in failed)
    if hard_fail or checks_passed < 12:
        status = "discard"
    elif checks_passed == 14:
        status = "confirmed"
    else:
        status = "watchlist"

    # ── Score
    vol_ratio = c10.get("vol_ratio") or 0
    dist_pct = c11.get("dist_pct") or 0
    rr = c14.get("rr") or 0
    base_weeks = c9.get("base_weeks") or 0
    score = (
        rs_rating * 0.4
        + vol_ratio * 10
        + rr * 5
        + base_weeks * 0.5
        + (100 - abs(dist_pct) * 5)
        + checks_passed * 2
    )

    return {
        "ticker": ticker,
        "status": status,
        "score": round(score, 2),
        "checks_passed": checks_passed,
        "failed_checks": failed,
        "entry": round(entry, 2),
        "stop": stop,
        "target": c14.get("target", entry * 1.15),
        "rr": rr,
        "rs_rating": rs_rating,
        "pattern": c9.get("pattern", "None"),
        "base_weeks": base_weeks,
        "pivot": pivot,
        "dist_pct": dist_pct,
        "vol_ratio": vol_ratio,
        "position_shares": c13.get("shares", 0),
        "position_value": c13.get("position_value", 0),
        "position_pct": c13.get("position_pct", 0),
        "earnings_date": c14.get("earnings_date"),
        "checks": checks,
    }


def print_candidate(rank: int, c: dict, sector: str, name: str):
    stop_pct = abs((c["entry"] - c["stop"]) / c["entry"] * 100)
    target_pct = abs((c["target"] - c["entry"]) / c["entry"] * 100)

    rprint(f"\n[bold cyan]#{rank} {c['ticker']}[/bold cyan] — {name} [dim]({sector})[/dim]")
    rprint(f"  ├── Precio: [green]${c['entry']:.2f}[/green]  |  Pivot: ${c['pivot']:.2f}  |  Dist. pivot: [yellow]{c['dist_pct']:+.1f}%[/yellow]")
    rprint(f"  ├── Patrón: [bold]{c['pattern']}[/bold] ({c['base_weeks']}s)  |  RS Rating: [bold magenta]{c['rs_rating']:.0f}[/bold magenta]  |  Vol breakout: {c['vol_ratio']:.1f}x")
    rprint(f"  ├── Entrada: [green]${c['entry']:.2f}[/green]  |  Stop: [red]${c['stop']:.2f}[/red] (-{stop_pct:.1f}%)  |  Target: [blue]${c['target']:.2f}[/blue] (+{target_pct:.1f}%)")
    rprint(f"  ├── R:R: [bold]{c['rr']:.1f}:1[/bold] ✓  |  Earnings: {c['earnings_date'] or 'Sin datos'}")
    rprint(f"  ├── Sizing: {c['position_shares']} acciones = ${c['position_value']:,.0f} ({c['position_pct']:.1f}% capital)  |  Checks: {c['checks_passed']}/14")
    rprint(f"  └── [dim]{c['checks']['base']['details']}[/dim]")


def print_watchlist(rank: int, c: dict):
    stop_pct = abs((c["entry"] - c["stop"]) / c["entry"] * 100) if c["stop"] else 0
    target_pct = abs((c["target"] - c["entry"]) / c["entry"] * 100) if c["target"] else 0

    rprint(f"\n[bold yellow]#{rank} {c['ticker']}[/bold yellow]  [dim]({c['checks_passed']}/14 checks)[/dim]")
    rprint(f"  ├── Precio: ${c['entry']:.2f}  |  Pivot: ${c['pivot']:.2f}  |  Patrón: {c['pattern']} ({c['base_weeks']}s)  |  RS: {c['rs_rating']:.0f}")
    rprint(f"  ├── Entrada: ${c['entry']:.2f}  |  Stop: ${c['stop']:.2f} (-{stop_pct:.1f}%)  |  Target: ${c['target']:.2f} (+{target_pct:.1f}%)  |  R:R {c['rr']:.1f}:1")
    for check_name, detail in c["failed_checks"]:
        rprint(f"  ├── [red]✗ {check_name}:[/red] {detail}")
    rprint(f"  └── [dim]Qué esperar: {_watchlist_trigger(c['failed_checks'])}[/dim]")


def _watchlist_trigger(failed_checks: list) -> str:
    triggers = []
    for name, _ in failed_checks:
        if "Breakout" in name or "10" in name:
            triggers.append("breakout con volumen ≥ 1.4x la media")
        elif "RSLine" in name or "7" in name:
            triggers.append("RS Line rompa nuevos máximos")
        elif "RSRating" in name or "6" in name:
            triggers.append("RS Rating suba sobre 90")
        elif "VolAcc" in name or "8" in name:
            triggers.append("más días de acumulación que distribución")
        elif "RR" in name or "14" in name:
            triggers.append("precio se aleje del pivot para mejorar R:R, o earnings pasen")
        elif "PivDist" in name or "11" in name:
            triggers.append("precio vuelva al rango del pivot (≤5%)")
        elif "Mercado" in name or "1" in name:
            triggers.append("mercado vuelva a tendencia alcista confirmada")
        else:
            triggers.append(f"check {name} se corrija")
    return " + ".join(triggers) if triggers else "monitorizar"


def run_scan() -> list[dict]:
    console.rule("[bold blue]SWING TRADING SCANNER[/bold blue]")

    # ── Step 1: Market condition
    console.print("\n[bold]Comprobando condición del mercado...[/bold]")
    market = check_market_condition()

    if market["passes"]:
        rprint(f"  [green]✓ Mercado OK[/green] — {market['details']}")
    else:
        rprint(f"  [red]✗ Mercado NO favorable[/red] — {market['details']}")
        rprint("[yellow]⚠ El mercado no cumple los requisitos. Candidatos mostrados con advertencia.[/yellow]")

    # ── Step 2: Download SPY for RS Line calculations
    spy_df = yf.download("SPY", period=f"{LOOKBACK_DAYS}d", progress=False, auto_adjust=True)
    if isinstance(spy_df.columns, pd.MultiIndex):
        spy_df.columns = spy_df.columns.droplevel(1)
    spy_prices = spy_df["Close"]

    # ── Step 3: Build universe and download data
    tickers = get_full_universe()
    console.print(f"\n[bold]Descargando datos de {len(tickers)} tickers...[/bold]")

    all_data: dict[str, pd.DataFrame] = {}
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TaskProgressColumn(), console=console
    ) as progress:
        task = progress.add_task("Descargando...", total=len(tickers))

        # Batch download for speed
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
                        if len(batch) == 1:
                            df = raw.copy()
                        else:
                            df = raw[t].copy() if t in raw.columns.get_level_values(0) else pd.DataFrame()
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.droplevel(1)
                        df = df.dropna(how="all")
                        if not df.empty and len(df) >= 60 and df["Volume"].tail(20).mean() >= MIN_AVG_VOLUME:
                            all_data[t] = df
                    except Exception:
                        pass
            except Exception:
                pass
            progress.advance(task, len(batch))

    console.print(f"  → {len(all_data)} tickers con datos válidos")

    # ── Step 4: Compute RS Ratings
    console.print("\n[bold]Calculando RS Ratings...[/bold]")
    all_prices = {t: df["Close"] for t, df in all_data.items()}
    rs_ratings = compute_rs_ratings(all_prices)

    # ── Step 5: Evaluate each stock
    console.print(f"\n[bold]Evaluando criterios en {len(all_data)} acciones...[/bold]")
    all_results = []

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        BarColumn(), TaskProgressColumn(), console=console
    ) as progress:
        task = progress.add_task("Analizando...", total=len(all_data))
        for ticker, df in all_data.items():
            result = evaluate_stock(ticker, df, spy_prices, rs_ratings, market["passes"])
            all_results.append(result)
            progress.advance(task, 1)

    # ── Step 6: Classify and sort
    confirmed = sorted(
        [r for r in all_results if r["status"] == "confirmed"],
        key=lambda x: x["score"], reverse=True
    )
    watchlist = sorted(
        [r for r in all_results if r["status"] == "watchlist"],
        key=lambda x: x["score"], reverse=True
    )

    top_confirmed = confirmed[:TOP_N_CANDIDATES]
    top_watchlist = watchlist[:10]

    console.print(f"\n  → {len(confirmed)} confirmados (14/14) | {len(watchlist)} en vigilancia (12-13/14)")

    # ── Print confirmed candidates
    console.rule(f"[bold green]✅ CANDIDATOS CONFIRMADOS — LISTOS PARA OPERAR[/bold green]")

    if not market["passes"]:
        rprint("[bold red]⚠ ADVERTENCIA: Mercado no favorable — operar con cautela o esperar.[/bold red]")

    if not top_confirmed:
        rprint("[yellow]  Ningún candidato pasa los 14 checks hoy.[/yellow]")
    else:
        for i, c in enumerate(top_confirmed, 1):
            print_candidate(i, c, "–", c["ticker"])

    # ── Print watchlist
    console.rule(f"[bold yellow]👁  LISTA DE VIGILANCIA — FALTAN 1-2 CHECKS[/bold yellow]")

    if not top_watchlist:
        rprint("[dim]  Sin candidatos en vigilancia.[/dim]")
    else:
        for i, c in enumerate(top_watchlist, 1):
            print_watchlist(i, c)

    console.rule()
    return {"confirmed": top_confirmed, "watchlist": top_watchlist}


def print_watchlist(rank: int, c: dict):
    stop_pct = abs((c["entry"] - c["stop"]) / c["entry"] * 100) if c["stop"] else 0
    target_pct = abs((c["target"] - c["entry"]) / c["entry"] * 100) if c["target"] else 0

    rprint(f"\n[bold yellow]#{rank} {c['ticker']}[/bold yellow]  [dim]({c['checks_passed']}/14 checks)[/dim]")
    rprint(f"  ├── Precio: ${c['entry']:.2f}  |  Pivot: ${c['pivot']:.2f}  |  Patrón: {c['pattern']} ({c['base_weeks']}s)  |  RS: {c['rs_rating']:.0f}")
    rprint(f"  ├── Entrada: ${c['entry']:.2f}  |  Stop: ${c['stop']:.2f} (-{stop_pct:.1f}%)  |  Target: ${c['target']:.2f} (+{target_pct:.1f}%)  |  R:R {c['rr']:.1f}:1")
    for check_name, detail in c["failed_checks"]:
        rprint(f"  ├── [red]✗ {check_name}:[/red] {detail}")
    rprint(f"  └── [dim]Qué esperar: {_watchlist_trigger(c['failed_checks'])}[/dim]")


def _watchlist_trigger(failed_checks: list) -> str:
    triggers = []
    for name, _ in failed_checks:
        if "Breakout" in name or "10" in name:
            triggers.append("breakout con volumen ≥ 1.4x la media")
        elif "RSLine" in name or "7" in name:
            triggers.append("RS Line rompa nuevos máximos")
        elif "RSRating" in name or "6" in name:
            triggers.append("RS Rating suba sobre 90")
        elif "VolAcc" in name or "8" in name:
            triggers.append("más días de acumulación que distribución")
        elif "RR" in name or "14" in name:
            triggers.append("precio se aleje del pivot para mejorar R:R, o earnings pasen")
        elif "PivDist" in name or "11" in name:
            triggers.append("precio vuelva al rango del pivot (≤5%)")
        elif "Mercado" in name or "1" in name:
            triggers.append("mercado vuelva a tendencia alcista confirmada")
        else:
            triggers.append(f"check {name} se corrija")
    return " + ".join(triggers) if triggers else "monitorizar"


if __name__ == "__main__":
    results = run_scan()
    output_path = "/Users/lucasfdezortiz/stock-scanner/last_scan.json"
    with open(output_path, "w") as f:
        clean = {
            "confirmed": [{k: v for k, v in r.items() if k != "checks"} for r in results["confirmed"]],
            "watchlist": [{k: v for k, v in r.items() if k != "checks"} for r in results["watchlist"]],
        }
        json.dump(clean, f, indent=2, default=str)
    console.print(f"\n[dim]Resultados guardados en {output_path}[/dim]")
