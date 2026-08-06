# Stock Analysis App

A Python Streamlit application for stock research, portfolio tracking, risk analysis, scenario planning, and persistent portfolio reporting.

This project started as a basic stock dashboard and evolved into a full portfolio analytics platform with database-backed watchlists, saved portfolio positions, snapshot history, what-if scenario modeling, scenario persistence, reporting exports, production health checks, and deployment hardening.

## Live App
https://ajm49appio-7wf27c54dht8q23cmhftst.streamlit.app/

## Quant Platform Roadmap

The next planned evolution of this project is documented in:

- `QUANT_PLATFORM_ROADMAP.md`

The next major sprint is:

- Sprint 68 — Backtesting Engine Foundation

The roadmap moves the app from a stock research and portfolio dashboard toward a modular quant platform with backtesting, technical factors, strategy comparison, risk analytics, portfolio optimization, paper trading, broker integration, and machine learning.

---

## Sprint 68 Quant Platform Foundation

Sprint 68 added the first quant-platform layer to the Stock Analysis App.

New capabilities:

- Backtesting page
- Moving-average crossover strategy
- Buy-and-hold strategy
- Simulated trades
- Equity curve tracking
- Trade PnL metrics
- Buy-and-hold benchmark comparison
- Technical factor library
- Strategy comparison UI
- CSV exports for technical factors and strategy comparison
- Pytest coverage for quant modules

The project now has a modular foundation for backtesting, strategy research, and future risk analytics.

---

## Sprint 69 Risk Analytics Foundation

Sprint 69 added the risk analytics layer to the Stock Analysis App quant platform.

New capabilities:

- Risk metrics module
- Annualized return
- Annualized volatility
- Sharpe-style ratio
- Sortino-style ratio
- Maximum drawdown
- Drawdown duration
- Historical Value at Risk
- Historical Conditional Value at Risk
- Calmar-style ratio
- Risk Analytics section on the Backtesting page
- Risk Dashboard Summary
- Risk alerts and threshold warnings
- Drawdown chart and table
- Rolling volatility chart and table
- Risk report exports
- Risk alert exports
- Pytest coverage for risk metrics

The project now supports risk-aware strategy review before moving into portfolio optimization, paper trading, broker integration, or machine learning.

---

## Sprint 70 Portfolio Optimization Foundation

Sprint 70 added portfolio optimization capabilities to the Stock Analysis App quant platform.

New capabilities:

- Portfolio optimization package
- Daily asset return calculation
- Annualized return calculation
- Covariance matrix calculation
- Portfolio return calculation
- Portfolio volatility calculation
- Portfolio Sharpe-style ratio calculation
- Equal Weight optimizer
- Minimum Volatility optimizer
- Maximum Sharpe-style optimizer
- Optimizer comparison engine
- Portfolio Optimization page
- Multi-ticker price loading
- Allocation comparison table
- Optimized allocation chart
- Optimization report exports
- Portfolio constraints panel
- Efficient Frontier simulation view
- Efficient Frontier CSV export
- Pytest coverage for portfolio optimization logic

The project now supports multi-asset portfolio construction research before moving into rebalancing, position sizing, risk budgeting, paper trading, broker integration, or machine learning.

---

## Sprint 70 Portfolio Optimization Foundation

Sprint 70 added portfolio optimization capabilities to the Stock Analysis App quant platform.

New capabilities:

- Portfolio optimization package
- Daily asset return calculation
- Annualized return calculation
- Covariance matrix calculation
- Portfolio return calculation
- Portfolio volatility calculation
- Portfolio Sharpe-style ratio calculation
- Equal Weight optimizer
- Minimum Volatility optimizer
- Maximum Sharpe-style optimizer
- Optimizer comparison engine
- Portfolio Optimization page
- Multi-ticker price loading
- Allocation comparison table
- Optimized allocation chart
- Optimization report exports
- Portfolio constraints panel
- Efficient Frontier simulation view
- Efficient Frontier CSV export
- Pytest coverage for portfolio optimization logic

The project now supports multi-asset portfolio construction research before moving into rebalancing, position sizing, risk budgeting, paper trading, broker integration, or machine learning.

---

## Sprint 71 Portfolio Rebalancing and Position Sizing Foundation

Sprint 71 added portfolio rebalancing and position sizing capabilities to the Stock Analysis App quant platform.

New capabilities:

- Portfolio rebalancing package
- Current value calculation
- Current allocation calculation
- Target vs current allocation comparison
- Allocation drift detection
- Dollar trade recommendations
- Share trade recommendations
- Fractional-share mode
- Whole-share mode
- Post-trade allocation estimates
- Drift detection alerts
- Rebalance alert summary
- Position sizing rules
- Risk-per-trade sizing
- Stop-loss-based sizing
- Maximum position weight cap
- Risk-budget position sizing
- Portfolio Rebalancing page
- Editable holdings input table
- Editable position sizing candidate table
- Rebalancing summary dashboard
- Target vs Current Allocation table
- Dollar Trade Recommendations table
- Share Trade Recommendations table
- Drift Detection and Rebalance Alerts table
- Position Sizing Rules table
- Risk-Budget Position Sizing table
- CSV exports
- Rebalancing report TXT export
- Pytest coverage for rebalancing and position sizing

The project now supports portfolio execution planning after strategy research, risk analytics, and portfolio optimization.

## Sprint 72 — Paper Trading and Trade Journal Foundation

Sprint 72 adds a complete simulated paper-trading workflow to the Stock Analysis App.

### New Paper Trading Features

- Paper trading account setup
- Simulated order ticket
- Buy/sell order preview
- Paper trade execution
- Open positions ledger
- Closed trades ledger
- Trade journal notes
- Paper trading export report

### Paper Trading Page

A new Streamlit page is available:

```text
Paper Trading Sprint 1
```

## Supported environment

The current validated release environment is:

- Python 3.14
- Streamlit 1.60.0
- SQLAlchemy
- PostgreSQL 18
- SQLite for local fallback and isolated tests
- pytest 9.1.1

The application uses naive UTC timestamps for compatibility
with the existing database schema. Timestamp creation uses
timezone-aware UTC internally and removes the timezone
marker before persistence.

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install runtime dependencies:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Install development and testing dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

## Configuration

Create the Streamlit secrets directory:

```bash
mkdir -p .streamlit
nano .streamlit/secrets.toml
```

Add your credentials:

```toml
DATABASE_URL = "your-postgresql-connection-string"
ALPHA_VANTAGE_API_KEY = "your-alpha-vantage-api-key"
```

Do not commit `.streamlit/secrets.toml` to Git.

## Run the Application

```bash
python3 -m streamlit run stock_app.py
```

## Run the Test Suite

```bash
python3 -m pytest -W error -q
```

The current validated release branch passes 339 tests.
