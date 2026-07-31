"""PostHog analytics helper for the stock analysis app."""

from __future__ import annotations

import atexit
import os
import uuid

import streamlit as st
from dotenv import load_dotenv
from posthog import Posthog

load_dotenv()

_posthog_client: Posthog | None = None
_initialized = False


def _initialize_posthog() -> Posthog | None:
    global _posthog_client, _initialized

    if _initialized:
        return _posthog_client

    _initialized = True
    token = os.getenv("POSTHOG_PROJECT_TOKEN")

    if not token:
        import sys
        if os.getenv("STREAMLIT_ENV") != "production":
            print(
                "WARNING: POSTHOG_PROJECT_TOKEN variable required by PostHog is missing or "
                "un-configured, this causes events to be silently missed. "
                "This error stops appearing once POSTHOG_PROJECT_TOKEN is configured.",
                file=sys.stderr,
            )
        return None

    client = Posthog(
        token,
        host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
        debug=os.getenv("POSTHOG_DEBUG", "false").lower() == "true",
        enable_exception_autocapture=True,
    )

    atexit.register(client.shutdown)
    _posthog_client = client
    return client


def get_posthog() -> Posthog | None:
    return _initialize_posthog()


def get_distinct_id() -> str:
    """Return a session-scoped distinct ID, creating one if needed."""
    if "posthog_distinct_id" not in st.session_state:
        st.session_state["posthog_distinct_id"] = str(uuid.uuid4())
    return st.session_state["posthog_distinct_id"]


def capture(event: str, properties: dict | None = None) -> None:
    """Capture an analytics event."""
    client = get_posthog()
    if client is None:
        return
    client.capture(
        distinct_id=get_distinct_id(),
        event=event,
        properties=properties or {},
    )


def capture_exception(exc: Exception) -> None:
    """Capture a handled exception."""
    client = get_posthog()
    if client is None:
        return
    client.capture_exception(exc, distinct_id=get_distinct_id())
