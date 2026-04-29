"""
strategies/base_strategy.py
Abstract base class all strategies must implement.
Strategies receive Bar events and emit Signal events — they never touch
orders, positions, or cash directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from core.models import Bar, Signal, SignalDirection
from utils.logger import get_logger


class BaseStrategy(ABC):
    """
    Contract for all trading strategies.

    Lifecycle:
        1. __init__(config) — set parameters
        2. on_bar(bar, history) — called on every new bar
           → returns Signal or None
        3. on_fill(fill) — notified when an order fills (optional)

    Rules:
        - Strategies must NOT modify portfolio state directly.
        - Strategies must NOT submit orders directly.
        - All output is via returned Signal objects.
    """

    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.config = config
        self.log = get_logger(f"strategy.{name}")
        self._initialized = False

    @property
    @abstractmethod
    def min_bars_required(self) -> int:
        """Minimum number of bars needed before the strategy can generate signals."""
        ...

    @abstractmethod
    def on_bar(self, bar: Bar, history: pd.DataFrame) -> Optional[Signal]:
        """
        Process a new bar.

        Args:
            bar: The latest OHLCV bar.
            history: Full historical DataFrame including the current bar.
                     Columns: open, high, low, close, volume, (+ any added indicators)

        Returns:
            A Signal, or None if no action.
        """
        ...

    def on_fill(self, fill) -> None:
        """Optional hook called when one of the strategy's orders fills."""
        pass

    def _make_signal(
        self,
        bar: Bar,
        direction: SignalDirection,
        strength: float = 1.0,
        metadata: dict | None = None,
    ) -> Signal:
        return Signal(
            symbol=bar.symbol,
            direction=direction,
            strength=max(0.0, min(1.0, strength)),
            strategy_name=self.name,
            timestamp=bar.timestamp,
            metadata=metadata or {},
        )

    def _long(self, bar: Bar, strength: float = 1.0, **meta) -> Signal:
        return self._make_signal(bar, SignalDirection.LONG, strength, meta)

    def _short(self, bar: Bar, strength: float = 1.0, **meta) -> Signal:
        return self._make_signal(bar, SignalDirection.SHORT, strength, meta)

    def _flat(self, bar: Bar, **meta) -> Signal:
        return self._make_signal(bar, SignalDirection.FLAT, 0.0, meta)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
