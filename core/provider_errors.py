from __future__ import annotations


QUOTA_ERROR_MARKERS = [
    "provider limit reached",
    "rate limit",
    "25 requests per day",
    "premium",
    "standard api rate limit",
]


FRIENDLY_QUOTA_MESSAGE = (
    "Market data provider limit reached. "
    "Use cached tickers today or refresh again tomorrow."
)


def is_provider_quota_error(error_message: object) -> bool:
    if not error_message:
        return False

    lowered = str(error_message).lower()

    return any(marker in lowered for marker in QUOTA_ERROR_MARKERS)


def clean_provider_error_message(message: object) -> str:
    text = str(message)

    if is_provider_quota_error(text):
        return FRIENDLY_QUOTA_MESSAGE

    return text
