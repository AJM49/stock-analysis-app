from __future__ import annotations

from app_metadata import APP_VERSION

RELEASE_NOTES = [
    {
        "version": APP_VERSION,
        "title": "Stabilization Release",
        "changes": [
            "Added cache-only safe mode to protect Alpha Vantage quota.",
            "Added cached ticker help panel.",
            "Added developer status sidebar panel.",
            "Added app metadata and version labels.",
            "Added release notes sidebar panel.",
            "Added app diagnostics page.",
            "Added database admin tools.",
            "Added cached ticker seeding workflow.",
            "Added admin safety guard for destructive actions.",
            "Added database export tools.",
            "Added portfolio position management tools.",
            "Added database migration utility.",
            "Added migration status panel.",
            "Added market data quality checks.",
            "Added market data repair tools.",
            "Added cache freshness policy panel.",
            "Added stale cache warning on the main dashboard.",
            "Fixed technical signal helper imports.",
            "Fixed MarketDataCache model and Neon schema alignment.",
        ],
    }
]
