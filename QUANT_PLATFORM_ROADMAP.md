# Roadmap: Evolve Stock Analysis App Into a Quant Platform

## Feature Build Order

1. Backtesting engine
2. Technical factors
3. Strategy comparison
4. Risk analytics
5. Portfolio optimization
6. Paper trading
7. Broker integration
8. Machine learning

## Engineering Principle

The central principle is separation of concerns.

The Streamlit interface should display results. It should not contain the calculation engine, database logic, and trading rules inside the same file.

## Next Sprint

Sprint 68 — Backtesting Engine Foundation

## Phase 1: Backtesting Engine

A backtesting engine simulates how a strategy would have performed using historical market data.

Core workflow:

Historical prices
↓
Strategy generates signals
↓
Backtester processes signals
↓
Simulated positions and trades
↓
Performance report

Every strategy should receive the same DataFrame structure:

- Date
- Open
- High
- Low
- Close
- Volume

## Long-Term Direction

The app should evolve from a Streamlit stock research dashboard into a modular quant platform with backtesting, technical factors, strategy comparison, risk analytics, optimization, paper trading, broker integration, and machine learning.
---

# Sprint 68 Status Update

Sprint 68 completed the first quant-platform foundation layer.

## Completed in Sprint 68

- Backtesting module structure
- Base strategy interface
- Moving-average crossover strategy
- Buy-and-hold strategy
- Backtesting engine
- Trade model
- Backtesting metrics
- Buy-and-hold benchmark
- Strategy comparison runner
- Technical factor library
- Streamlit Backtesting page
- Strategy comparison UI
- Technical factor UI
- Test coverage

## Current Platform Stage

The app is now in this stage:

Research app
↓
Backtesting platform foundation
↓
Strategy comparison foundation

## Next Stage

The next major platform layer should be:

Sprint 69 — Risk Analytics Foundation

Recommended Sprint 69 features:

1. Strategy risk metric module
2. Sharpe-style return/risk metric
3. Sortino-style downside risk metric
4. Drawdown duration
5. Rolling volatility analysis
6. Value at Risk estimate
7. Risk comparison table
8. Risk analytics UI
9. Risk report export
10. Sprint 69 closeout
