"""
config/config_manager.py
Strongly-typed configuration using Pydantic models loaded from YAML.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TradingConfig(BaseModel):
    initial_capital: float = 100_000.0
    currency: str = "USD"
    commission_pct: float = 0.001
    slippage_pct: float = 0.0005


class RiskConfig(BaseModel):
    max_position_pct: float = 0.10
    max_portfolio_drawdown: float = 0.15
    max_open_positions: int = 8
    daily_loss_limit_pct: float = 0.03
    atr_risk_multiplier: float = 2.0

    @field_validator("max_position_pct", "max_portfolio_drawdown", "daily_loss_limit_pct")
    @classmethod
    def must_be_fraction(cls, v: float) -> float:
        if not 0 < v < 1:
            raise ValueError("Must be between 0 and 1")
        return v


class DataConfig(BaseModel):
    provider: str = "yfinance"
    bar_size: str = "1d"
    warmup_bars: int = 200


class SmaCrossoverConfig(BaseModel):
    fast_period: int = 20
    slow_period: int = 50
    signal_threshold: float = 0.0


class RsiMeanReversionConfig(BaseModel):
    rsi_period: int = 14
    oversold: float = 30
    overbought: float = 70
    trend_sma_period: int = 200


class BreakoutConfig(BaseModel):
    lookback_period: int = 20
    atr_period: int = 14
    breakout_multiplier: float = 1.5


class StrategiesConfig(BaseModel):
    sma_crossover: SmaCrossoverConfig = SmaCrossoverConfig()
    rsi_mean_reversion: RsiMeanReversionConfig = RsiMeanReversionConfig()
    breakout: BreakoutConfig = BreakoutConfig()


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/trading.log"
    rotation: str = "10 MB"


class BacktestConfig(BaseModel):
    benchmark_symbol: str = "SPY"
    report_dir: str = "reports/"


class AppConfig(BaseModel):
    trading: TradingConfig = TradingConfig()
    risk: RiskConfig = RiskConfig()
    data: DataConfig = DataConfig()
    strategies: StrategiesConfig = StrategiesConfig()
    logging: LoggingConfig = LoggingConfig()
    backtest: BacktestConfig = BacktestConfig()


def load_config(path: str | Path = "config/settings.yaml") -> AppConfig:
    """Load configuration from a YAML file, falling back to defaults."""
    config_path = Path(path)
    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        return AppConfig(**raw)
    return AppConfig()
