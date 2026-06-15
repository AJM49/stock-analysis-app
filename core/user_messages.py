from __future__ import annotations


def get_user_safe_market_data_error(message: str | None, is_quota_error: bool = False) -> str:
    if is_quota_error:
        return "Market data provider quota is currently limited. Cached data may still be available."

    if not message:
        return "Market data is temporarily unavailable. Cached data may still be available."

    lowered = message.lower()

    if "missing alpha vantage api key" in lowered:
        return "Market data is not configured yet. Please check the app secrets."

    if "timed out" in lowered:
        return "Market data request timed out. Try again later or use cached data."

    if "request error" in lowered or "connection" in lowered:
        return "Market data provider connection failed. Cached data may still be available."

    if "cache read error" in lowered:
        return "Cached market data is temporarily unavailable. Please check the database connection."

    if "not cached" in lowered or "no cached market data" in lowered:
        return message

    if "no market data found" in lowered:
        return message

    return "Market data is temporarily unavailable. Cached data may still be available."


def get_user_safe_app_error() -> str:
    return "The app hit an unexpected issue. Please retry, then check diagnostics if the problem continues."
