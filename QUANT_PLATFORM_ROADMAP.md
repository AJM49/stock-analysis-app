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
