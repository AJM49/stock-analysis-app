from __future__ import annotations

from app_metadata import APP_VERSION

RELEASE_NOTES = [
    {
        "version": APP_VERSION,
        "title": "Current Build",
        "changes": [
            "Added app metadata and version label.",
            "Added developer status sidebar panel.",
            "Added cache-only safe mode to protect Alpha Vantage quota.",
            "Added cached ticker help panel.",
            "Improved market-data cache messaging.",
        ],
    }
]
