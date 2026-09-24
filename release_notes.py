from __future__ import annotations

from app_metadata import APP_VERSION


RELEASE_NOTES = [
    {
        "version": APP_VERSION,
        "title": "Portfolio and Quant Reliability",
        "changes": [
            "Consolidated portfolio concentration and risk analytics around canonical risk flags and scoring.",
            "Improved repeated-buy backtest accounting with weighted position cost basis.",
            "Added explicit reporting for terminal open backtest positions and unrealized P&L.",
            "Removed the unused legacy portfolio risk score implementation.",
            "Fixed volatility signal classification for daily percentage volatility.",
            "Centralized RSI and MACD signal helpers and aligned MACD UI messaging with canonical momentum labels.",
        ],
    }
]
