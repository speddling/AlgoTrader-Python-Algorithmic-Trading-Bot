# AlgoTrader — Python Algorithmic Trading Bot

A modular, production-grade algorithmic trading framework with clean architecture, risk management, and multiple strategy support.

## Architecture

```
trading_bot/
├── core/               # Engine, event bus, portfolio
├── strategies/         # Trading strategy implementations
├── data/               # Market data feeds and handlers
├── risk/               # Risk management and position sizing
├── execution/          # Order management and broker adapters
├── utils/              # Logging, metrics, helpers
├── config/             # Configuration management
└── tests/              # Unit and integration tests
```

## Key Features

- **Event-Driven Architecture** — Decoupled components communicate via an async event bus
- **Pluggable Strategies** — Implement `BaseStrategy` to add any strategy
- **Risk Management** — Position sizing, drawdown limits, exposure controls
- **Paper & Live Trading** — Swap broker adapters without changing strategy logic
- **Backtesting Engine** — Replay historical data through the same pipeline
- **Metrics & Reporting** — Sharpe ratio, drawdown, win rate, P&L curves

## Quick Start

```bash
pip install -r requirements.txt

# Run backtest
python main.py --mode backtest --strategy sma_crossover --symbol AAPL --start 2023-01-01 --end 2024-01-01

# Run paper trading
python main.py --mode paper --strategy rsi_mean_reversion --symbol SPY
```

## Strategies Included

| Strategy | Description |
|---|---|
| `sma_crossover` | Golden/death cross on configurable SMA windows |
| `rsi_mean_reversion` | RSI oversold/overbought with trend filter |
| `breakout` | Volatility breakout with ATR-based stops |

## Configuration

Edit `config/settings.yaml` or pass a custom config path:
```bash
python main.py --config config/my_settings.yaml
```
