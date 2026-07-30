from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4


class OrderSide(str, Enum):
    BUY = "Buy"
    SELL = "Sell"


class OrderStatus(str, Enum):
    PENDING = "Pending"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"


class OrderType(str, Enum):
    MARKET = "Market"
    LIMIT = "Limit"


@dataclass(frozen=True)
class PaperTradingAccount:
    """Paper trading account state."""
    account_id: str
    account_name: str
    starting_cash: float
    cash_balance: float
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.account_id:
            raise ValueError("account_id cannot be empty")

        if not self.account_name:
            raise ValueError("account_name cannot be empty")

        if self.starting_cash <= 0:
            raise ValueError("starting_cash must be greater than zero")

        if self.cash_balance < 0:
            raise ValueError("cash_balance cannot be negative")


@dataclass(frozen=True)
class PaperOrder:
    """Simulated order ticket."""
    order_id: str
    account_id: str
    ticker: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id cannot be empty")

        if not self.account_id:
            raise ValueError("account_id cannot be empty")

        if not self.ticker:
            raise ValueError("ticker cannot be empty")

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        if self.order_type == OrderType.LIMIT:
            if self.limit_price is None:
                raise ValueError("limit_price is required for limit orders")

            if self.limit_price <= 0:
                raise ValueError("limit_price must be greater than zero")

        object.__setattr__(self, "ticker", self.ticker.strip().upper())


@dataclass(frozen=True)
class PaperTrade:
    """Filled simulated trade."""
    trade_id: str
    order_id: str
    account_id: str
    ticker: str
    side: OrderSide
    quantity: float
    fill_price: float
    commission: float = 0.0
    filled_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.trade_id:
            raise ValueError("trade_id cannot be empty")

        if not self.order_id:
            raise ValueError("order_id cannot be empty")

        if not self.account_id:
            raise ValueError("account_id cannot be empty")

        if not self.ticker:
            raise ValueError("ticker cannot be empty")

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        if self.fill_price <= 0:
            raise ValueError("fill_price must be greater than zero")

        if self.commission < 0:
            raise ValueError("commission cannot be negative")

        object.__setattr__(self, "ticker", self.ticker.strip().upper())

    @property
    def gross_value(self) -> float:
        """Trade value before commission."""
        return float(self.quantity * self.fill_price)

    @property
    def net_cash_impact(self) -> float:
        """Cash impact from the trade."""
        if self.side == OrderSide.BUY:
            return float(-(self.gross_value + self.commission))

        return float(self.gross_value - self.commission)


@dataclass(frozen=True)
class PaperPosition:
    """Open simulated position."""
    account_id: str
    ticker: str
    quantity: float
    average_cost: float
    current_price: float | None = None

    def __post_init__(self) -> None:
        if not self.account_id:
            raise ValueError("account_id cannot be empty")

        if not self.ticker:
            raise ValueError("ticker cannot be empty")

        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")

        if self.average_cost <= 0:
            raise ValueError("average_cost must be greater than zero")

        if self.current_price is not None and self.current_price <= 0:
            raise ValueError("current_price must be greater than zero")

        object.__setattr__(self, "ticker", self.ticker.strip().upper())

    @property
    def cost_basis(self) -> float:
        """Total cost basis."""
        return float(self.quantity * self.average_cost)

    @property
    def market_value(self) -> float:
        """Current market value."""
        price = self.current_price if self.current_price is not None else self.average_cost
        return float(self.quantity * price)

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss."""
        return float(self.market_value - self.cost_basis)

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized profit/loss percentage."""
        if self.cost_basis == 0:
            return 0.0

        return float(self.unrealized_pnl / self.cost_basis * 100)


@dataclass(frozen=True)
class ClosedPaperTrade:
    """Closed simulated trade record."""
    account_id: str
    ticker: str
    quantity: float
    entry_price: float
    exit_price: float
    commission: float = 0.0
    closed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.account_id:
            raise ValueError("account_id cannot be empty")

        if not self.ticker:
            raise ValueError("ticker cannot be empty")

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        if self.entry_price <= 0:
            raise ValueError("entry_price must be greater than zero")

        if self.exit_price <= 0:
            raise ValueError("exit_price must be greater than zero")

        if self.commission < 0:
            raise ValueError("commission cannot be negative")

        object.__setattr__(self, "ticker", self.ticker.strip().upper())

    @property
    def realized_pnl(self) -> float:
        """Realized profit/loss."""
        gross_pnl = (self.exit_price - self.entry_price) * self.quantity
        return float(gross_pnl - self.commission)

    @property
    def realized_pnl_pct(self) -> float:
        """Realized profit/loss percentage."""
        entry_value = self.entry_price * self.quantity

        if entry_value == 0:
            return 0.0

        return float(self.realized_pnl / entry_value * 100)


@dataclass(frozen=True)
class TradeJournalEntry:
    """Trade journal note attached to a simulated trade or ticker."""
    journal_id: str
    account_id: str
    ticker: str
    note: str
    linked_trade_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.journal_id:
            raise ValueError("journal_id cannot be empty")

        if not self.account_id:
            raise ValueError("account_id cannot be empty")

        if not self.ticker:
            raise ValueError("ticker cannot be empty")

        if not self.note.strip():
            raise ValueError("note cannot be empty")

        object.__setattr__(self, "ticker", self.ticker.strip().upper())


def create_account(
    account_name: str = "Paper Trading Account",
    starting_cash: float = 10000.0,
) -> PaperTradingAccount:
    """Factory for a new paper trading account."""
    return PaperTradingAccount(
        account_id=str(uuid4()),
        account_name=account_name,
        starting_cash=starting_cash,
        cash_balance=starting_cash,
    )


def create_market_order(
    account_id: str,
    ticker: str,
    side: OrderSide,
    quantity: float,
) -> PaperOrder:
    """Factory for a market order."""
    return PaperOrder(
        order_id=str(uuid4()),
        account_id=account_id,
        ticker=ticker,
        side=side,
        quantity=quantity,
        order_type=OrderType.MARKET,
    )


def create_limit_order(
    account_id: str,
    ticker: str,
    side: OrderSide,
    quantity: float,
    limit_price: float,
) -> PaperOrder:
    """Factory for a limit order."""
    return PaperOrder(
        order_id=str(uuid4()),
        account_id=account_id,
        ticker=ticker,
        side=side,
        quantity=quantity,
        order_type=OrderType.LIMIT,
        limit_price=limit_price,
    )
