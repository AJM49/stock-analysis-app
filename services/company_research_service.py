from __future__ import annotations

import math


def _safe_float(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(result):
        return None

    return result


def build_company_research_snapshot(
    info,
    history,
    current_price,
    volatility,
):
    info = info or {}

    snapshot = {
        "current_price": _safe_float(current_price),
        "market_cap": _safe_float(
            info.get("market_cap")
        ),
        "pe_ratio": _safe_float(
            info.get("pe_ratio")
        ),
        "dividend_yield": _safe_float(
            info.get("dividend_yield")
        ),
        "beta": _safe_float(
            info.get("beta")
        ),
        "week_52_high": _safe_float(
            info.get("week_52_high")
        ),
        "week_52_low": _safe_float(
            info.get("week_52_low")
        ),
        "volatility_pct": _safe_float(
            volatility
        ),
        "range_position_pct": None,
        "trend_status": "Unavailable",
        "signals": [],
    }

    current = snapshot["current_price"]
    high = snapshot["week_52_high"]
    low = snapshot["week_52_low"]

    if (
        current is not None
        and high is not None
        and low is not None
        and high > low
    ):
        range_position = (
            (current - low)
            / (high - low)
            * 100
        )

        snapshot["range_position_pct"] = max(
            0.0,
            min(100.0, range_position),
        )

        if range_position >= 80:
            snapshot["signals"].append(
                "Trading near the upper end of its "
                "52-week range."
            )
        elif range_position <= 20:
            snapshot["signals"].append(
                "Trading near the lower end of its "
                "52-week range."
            )

    if (
        history is not None
        and not history.empty
        and "Close" in history.columns
    ):
        close = history["Close"].dropna()

        if len(close) >= 20:
            latest_close = float(close.iloc[-1])
            average_20 = float(
                close.tail(20).mean()
            )

            if latest_close > average_20:
                snapshot["trend_status"] = "Positive"
                snapshot["signals"].append(
                    "Price is above its 20-session "
                    "average."
                )
            elif latest_close < average_20:
                snapshot["trend_status"] = "Negative"
                snapshot["signals"].append(
                    "Price is below its 20-session "
                    "average."
                )
            else:
                snapshot["trend_status"] = "Neutral"

    beta = snapshot["beta"]

    if beta is not None:
        if beta >= 1.25:
            snapshot["signals"].append(
                "Beta indicates above-market "
                "price sensitivity."
            )
        elif beta <= 0.75:
            snapshot["signals"].append(
                "Beta indicates below-market "
                "price sensitivity."
            )

    volatility_pct = snapshot[
        "volatility_pct"
    ]

    if volatility_pct is not None:
        if volatility_pct >= 40:
            snapshot["signals"].append(
                "Historical volatility is elevated."
            )
        elif volatility_pct <= 20:
            snapshot["signals"].append(
                "Historical volatility is relatively low."
            )

    return snapshot
