from __future__ import annotations

TICKER_SECTOR_MAP = {
    # Technology
    "AAPL": "Technology",
    "MSFT": "Technology",
    "NVDA": "Technology",
    "AMD": "Technology",
    "MU": "Technology",

    # Communication Services
    "GOOGL": "Communication Services",
    "META": "Communication Services",
    "NFLX": "Communication Services",
    "SIRI": "Communication Services",
    "T": "Communication Services",

    # Consumer Discretionary
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    "SBUX": "Consumer Discretionary",
    "WING": "Consumer Discretionary",

    # Consumer Staples
    "WMT": "Consumer Staples",

    # Financials
    "V": "Financials",

    # ETFs / Funds
    "VTV": "ETF / Fund",
    "SPCX": "ETF / Fund",

    # Unknown / pending classification
    "BOSH": "Other",
}

DEFAULT_SECTOR = "Other"
