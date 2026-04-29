"""
core/portfolio.py
Tracks cash, open positions, realized/unrealized P&L, and equity curve.
The portfolio is the single source of truth for account state.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from core.models import Fill, Order, OrderSide, Position
from utils.logger import get_logger

log = get_logger(__name__)


class Portfolio:
    """
    Manages the complete account state:
    - Cash balance
    - Open positions (keyed by symbol)
    - Trade history
    - Equity curve
    """

    def __init__(self, initial_capital: float, commission_pct: float = 0.001) -> None:
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_pct = commission_pct

        self._positions: Dict[str, Position] = {}
        self._fills: List[Fill] = []
        self._equity_curve: List[tuple[datetime, float]] = [
            (datetime.utcnow(), initial_capital)
        ]
        self.realized_pnl: float = 0.0
        self._peak_equity: float = initial_capital

    # ── State Accessors ───────────────────────────────────────────────────────

    @property
    def positions(self) -> Dict[str, Position]:
        return dict(self._positions)

    @property
    def open_position_count(self) -> int:
        return len(self._positions)

    @property
    def market_value(self) -> float:
        """Total market value of all open positions."""
        return sum(p.market_value for p in self._positions.values())

    @property
    def total_equity(self) -> float:
        return self.cash + self.market_value

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self._positions.values())

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def total_return_pct(self) -> float:
        return (self.total_equity - self.initial_capital) / self.initial_capital

    @property
    def max_drawdown(self) -> float:
        """Maximum peak-to-trough drawdown of equity curve."""
        if not self._equity_curve:
            return 0.0
        equities = [e for _, e in self._equity_curve]
        peak = equities[0]
        max_dd = 0.0
        for eq in equities:
            peak = max(peak, eq)
            dd = (peak - eq) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd

    @property
    def current_drawdown(self) -> float:
        """Drawdown from the rolling peak."""
        if self._peak_equity == 0:
            return 0.0
        self._peak_equity = max(self._peak_equity, self.total_equity)
        return (self._peak_equity - self.total_equity) / self._peak_equity

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        return symbol in self._positions

    # ── Price Updates ─────────────────────────────────────────────────────────

    def update_price(self, symbol: str, price: float, timestamp: datetime) -> None:
        """Update the mark price of a position and record equity."""
        if symbol in self._positions:
            self._positions[symbol].current_price = price
        equity = self.total_equity
        self._equity_curve.append((timestamp, equity))
        self._peak_equity = max(self._peak_equity, equity)

    # ── Fill Processing ───────────────────────────────────────────────────────

    def process_fill(self, fill: Fill) -> None:
        """Apply a fill to update cash and positions."""
        self._fills.append(fill)
        symbol = fill.symbol

        if fill.side == OrderSide.BUY:
            self._process_buy(symbol, fill)
        else:
            self._process_sell(symbol, fill)

        log.info(
            f"Fill processed: {fill.side} {fill.quantity} {symbol} @ {fill.price:.4f} "
            f"| Cash: {self.cash:.2f} | Equity: {self.total_equity:.2f}"
        )

    def _process_buy(self, symbol: str, fill: Fill) -> None:
        cost = fill.quantity * fill.price + fill.commission
        if cost > self.cash:
            log.warning(f"Insufficient cash for buy: need {cost:.2f}, have {self.cash:.2f}")
            return

        self.cash -= cost

        if symbol in self._positions:
            pos = self._positions[symbol]
            total_qty = pos.quantity + fill.quantity
            pos.avg_entry_price = (
                (pos.quantity * pos.avg_entry_price + fill.quantity * fill.price)
                / total_qty
            )
            pos.quantity = total_qty
            pos.current_price = fill.price
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=fill.quantity,
                avg_entry_price=fill.price,
                current_price=fill.price,
                opened_at=fill.timestamp,
                strategy_name=fill.side,
            )

    def _process_sell(self, symbol: str, fill: Fill) -> None:
        if symbol not in self._positions:
            log.warning(f"Sell fill for {symbol} but no position found")
            return

        pos = self._positions[symbol]
        proceeds = fill.quantity * fill.price - fill.commission
        self.cash += proceeds

        realized = (fill.price - pos.avg_entry_price) * fill.quantity
        self.realized_pnl += realized

        remaining = pos.quantity - fill.quantity
        if remaining <= 0:
            del self._positions[symbol]
            log.info(f"Position closed: {symbol} | Realized P&L: {realized:.2f}")
        else:
            pos.quantity = remaining
            pos.current_price = fill.price

    # ── Reporting ─────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "cash": round(self.cash, 2),
            "market_value": round(self.market_value, 2),
            "total_equity": round(self.total_equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "total_return_pct": round(self.total_return_pct * 100, 2),
            "max_drawdown_pct": round(self.max_drawdown * 100, 2),
            "current_drawdown_pct": round(self.current_drawdown * 100, 2),
            "open_positions": self.open_position_count,
            "total_trades": len(self._fills),
        }

    def equity_series(self) -> list[dict]:
        return [{"timestamp": ts.isoformat(), "equity": eq} for ts, eq in self._equity_curve]
