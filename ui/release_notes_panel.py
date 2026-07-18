from __future__ import annotations

import streamlit as st

from release_notes import RELEASE_NOTES


def render_release_notes_panel():
    """Render recent app release notes in the sidebar."""
    with st.sidebar.expander("Release Notes", expanded=False):
        st.markdown(
            """
            **Sprint 58 — Portfolio Analytics**
            - Added portfolio dashboard rendering.
            - Added unrealized gain/loss summary.
            - Added allocation chart, position weights, sector exposure, risk flags, and CSV export.

            **Sprint 59 — Portfolio Data Quality and Controls**
            - Added edit and delete controls for portfolio positions.
            - Added ticker validation.
            - Added missing price-data warnings.
            - Added expanded sector mapping.
            - Added refresh controls for saved ticker prices.

            **Sprint 60 — Portfolio Performance History**
            - Added portfolio snapshots.
            - Added save snapshot control.
            - Added snapshot history table.
            - Added portfolio value history chart.
            - Added gain/loss history chart.
            - Added snapshot CSV export.

            **Sprint 61 — Portfolio Risk Intelligence**
            - Added best/worst performer summary.
            - Added portfolio concentration score.
            - Added sector concentration warnings.
            - Added snapshot history record filter.
            - Added snapshot cleanup control.
            - Added performance summary cards.

            **Sprint 62 — Portfolio UX and Release Hardening**
            - Added dashboard section expanders.
            - Added analytics help text.
            - Added empty-state guidance.
            - Added visible Sprint 62 sidebar label.
            """
        )

