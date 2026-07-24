from __future__ import annotations

import streamlit as st


def render_release_notes_panel() -> None:
    """Render release notes for completed portfolio app sprints."""
    with st.expander("Release Notes", expanded=False):
        st.markdown(
            """
### Sprint 66 — Portfolio Forecast Persistence and Database Integration

**Completed features:**

- Saved scenario history to the database.
- Added database scenario history display.
- Added ticker, risk-level, and decision filters.
- Added database scenario search across ticker, action, risk level, decision, notes, and date.
- Added delete confirmation and selected-scenario preview.
- Added database scenario reporting pack with TXT and CSV exports.
- Added database scenario decision dashboard.
- Added scenario trend charts for value delta, risk score, and gain/loss delta.
- Added scenario database health and cleanup panel.
- Added repair table control and duplicate cleanup safety.
- Completed duplicate helper cleanup and final QA checks.

**Result:**

Sprint 66 moved scenario planning from temporary session memory into a persistent database workflow. Saved scenarios can now be searched, filtered, exported, charted, reported, deleted safely, and checked for database health.

---

### Sprints 58–65 — Portfolio Analytics, Risk Intelligence, Reporting, and Scenario Planning

**Completed foundation:**

- Portfolio dashboard.
- Portfolio positions.
- Watchlist controls.
- Portfolio risk score.
- Snapshot history.
- Risk alerts.
- Portfolio report center.
- What-if scenario planner.
- Scenario exports.
- Scenario comparison summary.
- Scenario risk threshold warnings.
- Scenario reset controls.
- Scenario presets.
- Scenario baseline comparison table.
- Scenario notes and action plan.
- Session-based scenario history.
"""
        )
