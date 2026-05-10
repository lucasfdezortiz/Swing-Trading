"""Stock universe builder — SP500, NASDAQ100, small/mid caps, European."""

import requests
import pandas as pd

# NASDAQ 100 tickers (hardcoded, stable)
NASDAQ_100 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST",
    "ASML", "NFLX", "AMD", "AZN", "ADBE", "QCOM", "PEP", "CSCO", "INTU", "AMAT",
    "TMUS", "TXN", "AMGN", "HON", "SBUX", "INTC", "BKNG", "ISRG", "VRTX", "REGN",
    "MU", "MDLZ", "ADI", "LRCX", "PANW", "KLAC", "SNPS", "CDNS", "MELI", "ABNB",
    "ORLY", "CEG", "CRWD", "FTNT", "MAR", "CTAS", "MNST", "MRVL", "WDAY", "TEAM",
    "ODFL", "ROST", "PAYX", "PCAR", "CPRT", "EXC", "DDOG", "KDP", "FAST", "GEHC",
    "FANG", "ON", "CTSH", "TTD", "ZS", "IDXX", "APP", "DASH", "SMCI", "BIIB",
    "GFS", "MTCH", "WBD", "DLTR", "MDB", "NXPI", "ILMN", "LULU", "VRSK", "ANSS",
    "CSGP", "AEP", "SIRI", "XEL", "BMRN", "ALGN", "DXCM", "CHTR", "LCID", "RIVN",
]

# European liquid tickers (Yahoo Finance format)
EUROPEAN = [
    # Netherlands
    "ASML.AS", "HEIA.AS", "PHIA.AS", "NN.AS", "INGA.AS",
    # Germany
    "SAP.DE", "SIE.DE", "ALV.DE", "MRK.DE", "ADS.DE", "BMW.DE", "VOW3.DE", "BAS.DE", "BAYN.DE",
    # France
    "MC.PA", "OR.PA", "SAN.PA", "AIR.PA", "BNP.PA", "DG.PA", "RI.PA", "SU.PA", "CAP.PA",
    # Denmark
    "NOVO-B.CO", "NZYM-B.CO",
    # Sweden
    "ATCO-A.ST", "VOLV-B.ST", "ERIC-B.ST", "SAND.ST",
    # Switzerland
    "NESN.SW", "ROG.SW", "NOVN.SW", "ABBN.SW", "ZURN.SW",
    # Spain
    "ITX.MC", "SAN.MC", "BBVA.MC", "IBE.MC", "REP.MC",
    # UK
    "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "RIO.L", "GSK.L", "LLOY.L",
    # Italy
    "ENI.MI", "UCG.MI", "ISP.MI", "RACE.MI",
]

# Representative small/mid cap US (Russell 2000 subset — liquid names)
SMALL_MID_CAPS = [
    "SAIA", "SMCI", "WING", "CELH", "DUOL", "FTAI", "CAVA", "AXON", "AEHR",
    "BOOT", "CRVL", "ELF", "ENVA", "EXEL", "FCNCA", "GMED", "GTLS", "HIMS",
    "HQY", "IBP", "INSP", "ITGR", "KMPR", "KRYS", "LNTH", "LQDT", "MEDP",
    "MGNI", "MLTX", "MNDY", "MODG", "MSTR", "NARI", "NEO", "NEOG", "NVST",
    "OGN", "OII", "OMCL", "OPAD", "OPCH", "OSCR", "PCVX", "PLMR", "PRCT",
    "PTCT", "QLYS", "RGEN", "RNG", "ROCK", "RVMD", "RXST", "SFBS", "SHLS",
    "SHO", "SILK", "SLAB", "SLGN", "SMPL", "SOUN", "SPSC", "STEP", "STRL",
    "TMDX", "TNET", "TPVG", "TRMK", "TRNO", "TSEM", "TTGT", "TXRH", "UCBI",
    "UHAL", "URBN", "USPH", "VNET", "VNRX", "WD", "WGS", "WSBC", "WTFC",
    "XPOF", "YELP", "ZING", "ZWS", "ACLS", "ACVA", "ADMA", "AFCG", "AIRS",
]


def get_sp500_tickers() -> list[str]:
    """Fetches S&P500 tickers from Wikipedia."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        sp500 = tables[0]["Symbol"].tolist()
        # Fix Yahoo Finance format (BRK.B → BRK-B)
        return [t.replace(".", "-") for t in sp500]
    except Exception:
        # Fallback: return a curated subset if Wikipedia is unavailable
        return [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "BRK-B", "JPM", "V",
            "UNH", "XOM", "MA", "JNJ", "PG", "HD", "MRK", "ABBV", "ORCL", "CVX",
            "LLY", "PEP", "COST", "AVGO", "MCD", "KO", "BAC", "WMT", "CSCO", "CRM",
            "ACN", "TMO", "DHR", "ADBE", "NFLX", "AMD", "NKE", "TXN", "PM", "QCOM",
            "ABT", "CAT", "INTU", "RTX", "SPGI", "IBM", "GE", "AMGN", "GS", "MS",
        ]


def get_full_universe() -> list[str]:
    """Returns the combined universe of all markets, deduplicated."""
    sp500 = get_sp500_tickers()
    all_tickers = list(dict.fromkeys(sp500 + NASDAQ_100 + SMALL_MID_CAPS + EUROPEAN))
    return all_tickers


def get_us_universe() -> list[str]:
    """US-only universe."""
    sp500 = get_sp500_tickers()
    return list(dict.fromkeys(sp500 + NASDAQ_100 + SMALL_MID_CAPS))
