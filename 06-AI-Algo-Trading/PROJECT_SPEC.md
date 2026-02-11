# AI Algo Trading Dashboard — Project Specification

> **Last Updated:** 2026-02-10
> **Status:** Active development — Core features complete, live trading in testing
> **Owner:** @chatchawan

---

## 1. Project Overview

Full-stack algorithmic trading system for cryptocurrency. Combines **technical analysis**, **ML signal prediction**, **vectorized backtesting**, and **live trading** through a Streamlit dashboard.

### Core Capabilities

- 📊 **Data Pipeline** — Download OHLCV from yfinance, compute 14+ technical indicators
- 🧠 **ML Models** — Random Forest & XGBoost for next-day direction prediction
- 📈 **Backtesting** — Vectorized engine (vectorbt) with strategy comparison
- 🔗 **Live Trading** — Binance integration with 3 modes: Simulation / Testnet / Live
- 🎮 **Dashboard** — Streamlit UI with charts, strategy metrics, and manual trading

---

## 2. Architecture

```
06-AI-Algo-Trading/
│
├── app.py                    # Streamlit dashboard (main entry point)
├── requirements.txt          # Python dependencies
├── .env                      # API keys (NOT in git)
├── .env.example              # Template for .env
├── .gitignore                # Excludes .env, __pycache__, data/
│
├── src/                      # Core modules
│   ├── __init__.py
│   ├── data_loader.py        # yfinance download + save
│   ├── features.py           # Technical indicator pipeline (pandas-ta)
│   ├── models.py             # ML training/prediction pipeline
│   ├── exchange.py           # Exchange connector (Binance + Simulation)
│   ├── live_trader.py        # Automated trade executor
│   └── utils.py              # Shared utilities
│
├── strategies/               # Strategy signal generators
│   ├── __init__.py
│   ├── sma_crossover.py      # SMA 20/50 crossover
│   ├── rsi_mean_reversion.py # RSI oversold/overbought
│   └── ml_strategy.py        # ML model predictions as signals
│
├── backtest/                 # Backtesting engine
│   ├── __init__.py
│   ├── engine.py             # vectorbt-based backtest runner
│   ├── run_backtest.py       # CLI backtest script
│   ├── compare_strategies.py # Multi-strategy comparison
│   └── results/              # Saved equity curves
│
├── mcp_server/               # MCP multi-agent system
│   ├── trading_mcp_server.py # FastMCP server (15 tools)
│   ├── agent_prompts.py      # Agent role definitions
│   └── orchestrator.py       # Multi-agent coordinator
│
├── data/                     # Downloaded data + trade logs
└── notebooks/                # Jupyter exploration
```

---

## 3. Module Details

### 3.1 Data Pipeline (`src/data_loader.py` → `src/features.py`)

**Flow:** yfinance download → OHLCV DataFrame → Technical indicators

**Indicators computed by `features.py`:**
| Category | Indicators |
|-----------|------------------------------------------|
| Trend | SMA(20), SMA(50), EMA(12), EMA(26) |
| Momentum | RSI(14), MACD(12,26,9) + Signal + Hist |
| Volatility| Bollinger Bands(20,2σ), ATR(14) |

**Key functions:**

- `download_data(symbol, start, end, interval)` → raw OHLCV DataFrame
- `add_indicators(df)` → DataFrame + all indicator columns
- `prepare_features(symbol, start, end)` → combined convenience function

---

### 3.2 ML Models (`src/models.py`)

**Target:** Binary classification — 1=price UP tomorrow, 0=price DOWN

**Models:**

- `random_forest` → `RandomForestClassifier(n_estimators=200, max_depth=10)`
- `xgboost` → `GradientBoostingClassifier(n_estimators=200, max_depth=5, lr=0.05)`

**Features used (14 columns):**

```
SMA_20, SMA_50, EMA_12, EMA_26, RSI_14,
MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9,
BBL_20_2.0_2.0, BBM_20_2.0_2.0, BBU_20_2.0_2.0,
BBB_20_2.0_2.0, BBP_20_2.0_2.0, ATR_14
```

**Key functions:**

- `create_target(df)` → adds binary `target` column
- `prepare_ml_data(df)` → returns `(X, y)` feature/target split
- `train_test_split_sequential(X, y, 0.8)` → time-series split (NO shuffle)
- `train_model(X_train, y_train, model_type)` → returns `(model, scaler)`
- `evaluate_model(model, scaler, X_test, y_test)` → accuracy, F1, report
- `predict_signals(model, scaler, X)` → array of 1/0 predictions

---

### 3.3 Strategies (`strategies/`)

All strategies expose `generate_signals(df, **params)` → DataFrame with `signal` and `position` columns.

| Strategy           | File                    | Logic                                   |
| ------------------ | ----------------------- | --------------------------------------- |
| SMA Crossover      | `sma_crossover.py`      | BUY when SMA_20 > SMA_50 (Golden Cross) |
| RSI Mean Reversion | `rsi_mean_reversion.py` | BUY when RSI < 30, SELL when RSI > 70   |
| ML Random Forest   | `ml_strategy.py`        | Uses RF model predictions as signals    |
| ML XGBoost         | `ml_strategy.py`        | Uses XGB model predictions as signals   |

**Signal convention:**

- `signal = 1` → Long position
- `signal = 0` → Flat (no position)
- `position` = diff of signal → `+1` entry, `-1` exit, `0` hold

---

### 3.4 Backtesting Engine (`backtest/engine.py`)

Uses **vectorbt** for vectorized portfolio simulation.

**Key functions:**

- `run_backtest(df, signal_col, price_col, init_cash=10000, fees=0.001)` → `vbt.Portfolio`
- `print_metrics(portfolio, name)` → Total Return, Sharpe, Max DD, Win Rate, Trades
- `save_equity_curve(portfolio, name)` → saves PNG

**Scripts:**

- `run_backtest.py` — single strategy backtest
- `compare_strategies.py` — run all strategies, compare metrics

---

### 3.5 Exchange Connector (`src/exchange.py`)

**`BinanceClient` class** — unified interface for 3 modes:

| Mode         | Description                   | API Keys Required | Data Source |
| ------------ | ----------------------------- | ----------------- | ----------- |
| `simulation` | Local paper trading           | ❌ No             | yfinance    |
| `testnet`    | Binance Testnet paper trading | ✅ Yes            | Binance API |
| `live`       | Real money trading            | ✅ Yes            | Binance API |

**Usage:**

```python
# Simulation (no API keys needed)
client = BinanceClient(mode="simulation")

# Testnet
client = BinanceClient(mode="testnet")

# Live (DANGER!)
client = BinanceClient(mode="live")
```

**Safety features:**

- `max_position` — Max USD per trade (default $50)
- `max_daily_trades` — Max trades per day (default 10)
- Trade logging to in-memory list

**SimulatedExchange class:**

- Fetches real prices from yfinance
- Tracks balances in-memory (starts with $10,000 USDT)
- Simulates market orders with instant fills
- Supports symbols: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, DOTUSDT, ADAUSDT, AVAXUSDT

**Key methods:**

```python
client.get_balance(asset=None)     # → dict of {asset: {free, locked}}
client.get_usdt_balance()          # → float
client.get_price(symbol)           # → float
client.get_prices(symbols)         # → dict
client.get_klines(symbol, interval, limit)  # → DataFrame
client.buy(symbol, usd_amount)     # → order dict
client.sell(symbol, quantity)      # → order dict
client.place_market_order(symbol, side, quantity=, quote_quantity=)
client.status()                    # → status dict
```

---

### 3.6 Live Trader (`src/live_trader.py`)

Automated trading script that:

1. Connects to Binance (or simulation)
2. Downloads live klines → computes indicators
3. Generates strategy signal (SMA/RSI/ML)
4. Executes trade if signal changed
5. Logs to CSV

**CLI usage:**

```bash
python src/live_trader.py --mode paper --symbol BTCUSDT --strategy xgboost --amount 10 --interval 3600
```

**Arguments:**
| Arg | Default | Description |
|-------------|------------|--------------------------------------------|
| `--mode` | `paper` | `paper` (testnet) or `live` |
| `--symbol` | `BTCUSDT` | Trading pair |
| `--strategy` | `xgboost` | `sma`, `rsi`, `random_forest`, `xgboost` |
| `--amount` | `10.0` | USD per trade |
| `--interval` | `3600` | Seconds between cycles (0 = run once) |

---

### 3.7 Dashboard (`app.py`)

**Streamlit app** — `streamlit run app.py`

**Sections:**

1. **Sidebar** — Symbol, date range, strategy selection, Run Backtest button
2. **Tab: Price Charts** — Candlestick + buy/sell markers + indicator overlays
3. **Tab: Strategy Comparison** — Side-by-side metrics table + radar chart
4. **Tab: Equity Curves** — Cumulative returns + drawdown charts
5. **Live Trading Section** — Mode selector (Simulation/Testnet/Live), Connect, balances, live prices, manual Buy/Sell, trade history

---

### 3.8 MCP Multi-Agent System (`mcp_server/`)

**FastMCP server** exposing all trading tools via Model Context Protocol.

**Files:**

```
mcp_server/
├── __init__.py
├── trading_mcp_server.py    # 15 tools + 2 resources
├── agent_prompts.py         # 4 agent role definitions
└── orchestrator.py          # Multi-agent coordinator
```

**Run MCP server:**

```bash
fastmcp run mcp_server/trading_mcp_server.py
# or
python mcp_server/trading_mcp_server.py
```

**Run orchestrator (full trading cycle):**

```bash
python mcp_server/orchestrator.py --symbol BTCUSDT --strategy sma
```

**15 Tools exposed:**
| Category | Tools |
|-------------|--------------------------------------------------------------|
| Market Data | `get_price`, `get_multiple_prices`, `get_klines`, `compute_indicators` |
| Strategy | `get_signal`, `run_strategy_backtest`, `compare_all_strategies` |
| Trading | `buy_crypto`, `sell_crypto`, `get_balance`, `check_safety`, `set_trading_mode` |
| Portfolio | `get_portfolio`, `get_trade_history`, `get_pnl` |

**4 Agent Roles:**
| Agent | Role |
|------------------|-----------------------------------------|
| 📊 Data Agent | Fetch prices, compute indicators |
| 🧠 Strategy Agent | Generate signals, run backtests |
| 🎯 Execution Agent| Execute trades with safety checks |
| 📋 Monitor Agent | Track portfolio, measure P&L |

**Orchestrator workflow:** Data → Strategy → Execution → Monitor

---

## 4. Environment Variables (`.env`)

```bash
# Binance Testnet (Paper Trading)
BINANCE_TESTNET_API_KEY=<your_testnet_key>
BINANCE_TESTNET_SECRET=<your_testnet_secret>

# Binance Live (Real Money)
# BINANCE_API_KEY=
# BINANCE_SECRET=

# Safety Limits
MAX_POSITION_USD=50        # Max single trade size
MAX_DAILY_TRADES=10        # Max trades per day
MAX_DAILY_LOSS_PCT=5       # Max daily loss percentage (planned)
```

> ⚠️ **SECURITY:** `.env` is in `.gitignore` — NEVER commit API keys.

---

## 5. Dependencies

```
yfinance          # Market data
pandas-ta         # Technical indicators
vectorbt          # Backtesting engine
scikit-learn      # ML models
plotly            # Charts
streamlit         # Dashboard
python-binance    # Binance API
python-dotenv     # Environment variables
fastmcp           # MCP server framework
torch             # Deep learning (future)
matplotlib        # Plotting
```

**Python environment:** `/home/chatchawan/Coding/07_AI_Engineering/ai_env`

---

## 6. Current Status

### ✅ Completed

- [x] Data pipeline (yfinance → indicators)
- [x] Feature engineering (14 technical indicators)
- [x] ML models (Random Forest, XGBoost)
- [x] 4 strategies (SMA, RSI, RF, XGB)
- [x] Vectorized backtesting engine
- [x] Strategy comparison framework
- [x] Streamlit dashboard with charts
- [x] Exchange connector (3 modes)
- [x] Manual trading controls in dashboard
- [x] Simulation mode (no API keys needed, real prices)
- [x] Binance Testnet API keys configured
- [x] MCP Server (FastMCP) with 15 trading tools
- [x] Multi-agent orchestrator (Data/Strategy/Execution/Monitor)

### 🔄 In Progress

- [ ] Binance Testnet connection testing (Testnet may be intermittently down)
- [ ] Live trader integration into dashboard

### 📋 Planned / Future

- [x] `MAX_DAILY_LOSS_PCT` enforcement (circuit breaker)
- [ ] Limit orders (not just market orders)
- [ ] WebSocket streaming for real-time prices (lower latency)
- [ ] Portfolio tracking dashboard (P&L over time)
- [ ] Multi-symbol simultaneous trading
- [ ] Strategy parameter optimization (grid search)
- [ ] Deep learning models (LSTM, Transformer)
- [ ] Risk management module (position sizing, stop-loss)
- [ ] Alert system (Telegram/LINE notifications)
- [ ] Docker deployment

---

## 7. How to Run

```bash
# Activate environment
source /home/chatchawan/Coding/07_AI_Engineering/ai_env/bin/activate

# Install dependencies (if needed)
pip install yfinance pandas-ta vectorbt scikit-learn plotly streamlit python-binance python-dotenv

# Run dashboard
cd /home/chatchawan/Coding/07_AI_Engineering/06-AI-Algo-Trading
streamlit run app.py

# Run backtest from CLI
python backtest/run_backtest.py

# Run live trader (paper mode)
python src/live_trader.py --mode paper --symbol BTCUSDT --strategy xgboost
```

---

## 8. Design Decisions & Conventions

1. **Signal convention:** All strategies output `signal` (1=long, 0=flat) and `position` (diff)
2. **Time-series split:** ML uses sequential 80/20 split — NO shuffling — to prevent look-ahead bias
3. **Safety first:** All live trades go through `_check_safety()` before execution
4. **Mode hierarchy:** Simulation → Testnet → Live (always test thoroughly before upgrading)
5. **Data source:** yfinance for historical data; Binance API or yfinance for live data (depending on mode)
6. **Feature scaling:** `StandardScaler` fitted on training data only
7. **Fees:** Backtest uses 0.1% per trade (Binance fee level)

---

## 9. Known Issues & Gotchas

1. **Binance Testnet** (`testnet.binance.vision`) is intermittently down — use **Simulation mode** as fallback
2. **yfinance FutureWarning:** Fixed in `src/exchange.py`.
3. **ML strategies return only test-period data** — they need training data, so backtest period is shorter
4. **vectorbt** may have breaking changes between versions — pin if stability matters
5. **Session state:** Dashboard exchange client lives in `st.session_state` — reconnects if mode changes
