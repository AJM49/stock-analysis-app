from __future__ import annotations

from strategies.base_strategy import BaseStrategy
from strategies.buy_and_hold import BuyAndHoldStrategy
from strategies.moving_average import MovingAverageCrossoverStrategy


def get_available_strategies() -> dict[str, type[BaseStrategy]]:
    """Return available strategy classes."""
    return {
        "Buy and Hold": BuyAndHoldStrategy,
        "Moving Average Crossover": MovingAverageCrossoverStrategy,
    }


def build_strategy(strategy_name: str, **kwargs) -> BaseStrategy:
    """Build a strategy instance from the registry."""
    strategies = get_available_strategies()

    if strategy_name not in strategies:
        available = ", ".join(strategies.keys())
        raise ValueError(
            f"Unknown strategy: {strategy_name}. Available strategies: {available}"
        )

    strategy_class = strategies[strategy_name]

    return strategy_class(**kwargs)
