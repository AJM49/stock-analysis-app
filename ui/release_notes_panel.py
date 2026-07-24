from __future__ import annotations

import streamlit as st


def render_release_notes_panel() -> None:
    """Render release notes for completed portfolio app sprints."""
    with st.expander("Release Notes", expanded=False):
        st.markdown(
            """
### Sprint 68 — Backtesting Engine and Quant Platform Foundation

**Completed features:**

- Added modular backtesting package.
- Added base strategy interface.
- Added moving-average crossover strategy.
- Added simulated trade model.
- Added backtesting performance metrics.
- Added long-only backtesting engine.
- Added pytest coverage for the backtesting engine.
- Added Streamlit Backtesting page.
- Added trade PnL tracking.
- Added completed-trade detail table.
- Added win rate, average gain, average loss, best trade, worst trade, and exposure metrics.
- Added buy-and-hold benchmark comparison.
- Added benchmark equity curve.
- Added strategy excess return.
- Added technical factor library.
- Added reusable daily return, cumulative return, moving average, volatility, momentum, RSI, MACD, volume average, and price-distance factors.
- Added technical factor display to the Backtesting page.
- Added technical factor CSV export.
- Added buy-and-hold strategy class.
- Added strategy registry.
- Added strategy comparison runner.
- Added strategy comparison UI to the Backtesting page.
- Added strategy comparison CSV export.
- Added test coverage for technical factors and strategy comparison.

**Result:**

Sprint 68 moves the project from a stock research and portfolio dashboard into the foundation of a modular quant platform. The app now supports historical backtesting, strategy signals, simulated trades, equity curves, trade-level PnL, benchmark comparison, technical factors, and strategy comparison.

**Next roadmap direction:**

- Risk analytics
- Portfolio optimization
- Paper trading
- Broker integration
- Machine learning model lab

---

### Sprint 67 — Production Hardening and Portfolio Packaging

**Completed features:**

- Added production status banner.
- Added app health check panel.
- Added error logging through `core/app_logging.py`.
- Added deployment checklist panel.
- Added portfolio user guide panel.
- Added project metadata panel.
- Updated README for portfolio presentation.
- Added security ignores for local secrets, runtime logs, and local database files.
- Verified local and live Streamlit deployment readiness.
- Packaged the project for GitHub, recruiter review, and portfolio demonstration.

**Result:**

Sprint 67 moved the app from a functional portfolio project into a production-hardened presentation build. The app now includes user-facing guidance, deployment checks, release notes, health visibility, and project metadata for reviewers.

---

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
