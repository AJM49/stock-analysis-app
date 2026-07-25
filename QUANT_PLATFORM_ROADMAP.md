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

---

# Sprint 69 Status Update

Sprint 69 completed the risk analytics foundation layer.

## Completed in Sprint 69

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
- Risk metrics in backtest engine results
- Risk Analytics UI
- Risk Dashboard Summary
- Risk alerts and threshold warnings
- Drawdown analysis
- Rolling volatility analysis
- Risk report exports
- Risk alert exports
- Test coverage

## Current Platform Stage

The app is now in this stage:

Research app
↓
Backtesting platform foundation
↓
Strategy comparison foundation
↓
Risk analytics foundation

## Next Stage

The next major platform layer should be:

Sprint 70 — Portfolio Optimization Foundation

Recommended Sprint 70 features:

1. Portfolio return and covariance module
2. Equal-weight portfolio optimizer
3. Minimum volatility optimizer
4. Maximum Sharpe-style optimizer
5. Allocation constraints
6. Optimization comparison table
7. Portfolio optimization UI
8. Optimized allocation chart
9. Optimization report export
10. Sprint 70 closeout

---

# Sprint 70 Status Update

Sprint 70 completed the portfolio optimization foundation layer.

## Completed in Sprint 70

- Portfolio optimization package
- Portfolio math foundation
- Equal Weight optimizer
- Minimum Volatility optimizer
- Maximum Sharpe-style optimizer
- Optimizer comparison engine
- Portfolio Optimization Streamlit page
- Optimized allocation chart
- Optimization report exports
- Portfolio constraints panel
- Efficient Frontier simulation
- Efficient Frontier CSV export
- Test coverage

## Current Platform Stage

The app is now in this stage:

Research app
↓
Backtesting platform foundation
↓
Strategy comparison foundation
↓
Risk analytics foundation
↓
Portfolio optimization foundation

## Next Stage

The next major platform layer should be:

Sprint 71 — Portfolio Rebalancing and Position Sizing Foundation

Recommended Sprint 71 features:

1. Rebalancing math module
2. Target vs current allocation calculator
3. Dollar trade recommendation engine
4. Share trade recommendation engine
5. Drift detection and rebalance alerts
6. Position sizing rules
7. Risk-budget position sizing
8. Rebalancing Streamlit UI
9. Rebalancing export report
10. Sprint 71 closeout

---

# Sprint 70 Status Update

Sprint 70 completed the portfolio optimization foundation layer.

## Completed in Sprint 70

- Portfolio optimization package
- Portfolio math foundation
- Equal Weight optimizer
- Minimum Volatility optimizer
- Maximum Sharpe-style optimizer
- Optimizer comparison engine
- Portfolio Optimization Streamlit page
- Optimized allocation chart
- Optimization report exports
- Portfolio constraints panel
- Efficient Frontier simulation
- Efficient Frontier CSV export
- Test coverage

## Current Platform Stage

The app is now in this stage:

Research app
↓
Backtesting platform foundation
↓
Strategy comparison foundation
↓
Risk analytics foundation
↓
Portfolio optimization foundation

## Next Stage

The next major platform layer should be:

Sprint 71 — Portfolio Rebalancing and Position Sizing Foundation

Recommended Sprint 71 features:

1. Rebalancing math module
2. Target vs current allocation calculator
3. Dollar trade recommendation engine
4. Share trade recommendation engine
5. Drift detection and rebalance alerts
6. Position sizing rules
7. Risk-budget position sizing
8. Rebalancing Streamlit UI
9. Rebalancing export report
10. Sprint 71 closeout
