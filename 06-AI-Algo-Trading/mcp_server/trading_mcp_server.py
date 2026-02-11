"""
trading_mcp_server.py — MCP Server สำหรับ AI Trading System

Exposes trading tools via Model Context Protocol (MCP).
Agents เชื่อมต่อเข้ามาเรียกใช้ tools ได้ตาม role ของตัวเอง

Run:
  fastmcp run mcp_server/trading_mcp_server.py
  # or
  python mcp_server/trading_mcp_server.py
"""
import sys
import os
import json
from datetime import datetime
import subprocess

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP

# ── Initialize MCP Server ─────────────────────────────────
mcp = FastMCP(
    "AI Trading System",
    instructions="""
    This MCP server provides tools for algorithmic crypto trading.
    
    Available tool categories:
    - Market Data: get_price, get_klines, compute_indicators
    - Strategy: get_signal, run_strategy_backtest, compare_strategies
    - Trading: buy_crypto, sell_crypto, get_balance, check_safety
    - Portfolio: get_portfolio, get_trade_history, get_pnl
    
    Always start with Simulation mode for testing.
    Use check_safety before executing any trades.
    """,
)

# ── Lazy-loaded shared state ──────────────────────────────────
_client = None
_client_mode = None


def _get_client(mode: str = "simulation"):
    """Get or create exchange client (singleton per mode)."""
    global _client, _client_mode
    if _client is None or _client_mode != mode:
        from src.exchange import BinanceClient
        _client = BinanceClient(mode=mode)
        _client_mode = mode
    return _client


# ══════════════════════════════════════════════════════════════
# RESOURCES — Read-only data for agents
# ══════════════════════════════════════════════════════════════

@mcp.resource("trading://spec")
def get_project_spec() -> str:
    """Project specification document — architecture, modules, conventions."""
    spec_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "PROJECT_SPEC.md")
    if os.path.exists(spec_path):
        with open(spec_path, "r") as f:
            return f.read()
    return "PROJECT_SPEC.md not found."


@mcp.resource("trading://status")
def get_system_status() -> str:
    """Current system status — connection, balances, safety limits."""
    try:
        client = _get_client()
        status = client.status()
        return json.dumps(status, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("trading://live_prices")
def get_live_prices() -> str:
    """Snapshot of real-time prices from WebSocket cache."""
    try:
        client = _get_client()
        if client.stream_manager:
            prices = client.stream_manager.get_all_prices()
            return json.dumps(prices, indent=2)
        return json.dumps({"status": "Stream manager not active", "prices": {}})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ══════════════════════════════════════════════════════════════
# MARKET DATA TOOLS — Data Agent
# ══════════════════════════════════════════════════════════════

@mcp.tool()
def get_price(symbol: str = "BTCUSDT") -> dict:
    """
    Get current price for a crypto trading pair.
    
    Args:
        symbol: Trading pair (e.g. BTCUSDT, ETHUSDT, BNBUSDT)
    
    Returns:
        Dict with symbol, price, and timestamp.
    """
    client = _get_client()
    price = client.get_price(symbol)
    return {
        "symbol": symbol,
        "price": price,
        "timestamp": datetime.now().isoformat(),
        "mode": client.mode,
    }


@mcp.tool()
def get_multiple_prices(symbols: str = "BTCUSDT,ETHUSDT,BNBUSDT") -> dict:
    """
    Get prices for multiple trading pairs at once.
    
    Args:
        symbols: Comma-separated trading pairs (e.g. "BTCUSDT,ETHUSDT,BNBUSDT")
    
    Returns:
        Dict with prices per symbol.
    """
    client = _get_client()
    symbol_list = [s.strip() for s in symbols.split(",")]
    prices = {}
    for sym in symbol_list:
        try:
            prices[sym] = client.get_price(sym)
        except Exception as e:
            prices[sym] = f"Error: {e}"
    return {
        "prices": prices,
        "timestamp": datetime.now().isoformat(),
    }


@mcp.tool()
def get_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    limit: int = 30,
) -> dict:
    """
    Get historical OHLCV candlestick data.
    
    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        interval: Candle interval — "1d", "1h", "15m"
        limit: Number of candles (max 100)
    
    Returns:
        Dict with OHLCV data as list of dicts.
    """
    client = _get_client()
    df = client.get_klines(symbol, interval=interval, limit=min(limit, 100))
    records = df.tail(limit).reset_index().to_dict(orient="records")
    # Convert timestamps to strings
    for r in records:
        if "timestamp" in r:
            r["timestamp"] = str(r["timestamp"])
    return {
        "symbol": symbol,
        "interval": interval,
        "count": len(records),
        "data": records,
    }


@mcp.tool()
def compute_indicators(
    symbol: str = "BTC-USD",
    start: str = "2024-01-01",
    end: str = "2025-01-01",
) -> dict:
    """
    Download data and compute all technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR).
    
    Args:
        symbol: Yahoo Finance symbol (e.g. BTC-USD, ETH-USD)
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
    
    Returns:
        Dict with latest indicator values and summary stats.
    """
    from src.features import prepare_features

    df = prepare_features(symbol, start, end)
    latest = df.iloc[-1]
    
    # Return latest values for all indicators
    indicators = {}
    indicator_cols = [c for c in df.columns if c not in ["Open", "High", "Low", "Close", "Volume"]]
    for col in indicator_cols:
        val = latest[col]
        indicators[col] = round(float(val), 6) if not isinstance(val, str) else val

    return {
        "symbol": symbol,
        "period": f"{start} to {end}",
        "total_rows": len(df),
        "latest_close": round(float(latest["Close"]), 2),
        "latest_date": str(df.index[-1]),
        "indicators": indicators,
    }


# ══════════════════════════════════════════════════════════════
# STRATEGY TOOLS — Strategy Agent
# ══════════════════════════════════════════════════════════════

@mcp.tool()
def get_signal(
    symbol: str = "BTC-USD",
    strategy: str = "sma",
    start: str = "2024-01-01",
    end: str = "2025-01-01",
) -> dict:
    """
    Get current trading signal from a strategy.
    
    Args:
        symbol: Yahoo Finance symbol (e.g. BTC-USD)
        strategy: Strategy name — "sma", "rsi", "random_forest", "xgboost"
        start: Start date for data
        end: End date for data
    
    Returns:
        Dict with signal (1=BUY, 0=SELL), strategy name, and details.
    """
    from src.features import prepare_features

    df = prepare_features(symbol, start, end)
    
    if strategy == "sma":
        from strategies.sma_crossover import generate_signals
        result_df = generate_signals(df)
    elif strategy == "rsi":
        from strategies.rsi_mean_reversion import generate_signals
        result_df = generate_signals(df)
    elif strategy in ("random_forest", "xgboost"):
        from strategies.ml_strategy import generate_signals
        result_df = generate_signals(df, model_type=strategy)
    elif strategy in ("lstm", "transformer"):
        from src.strategy_dl import DLStrategy
        try:
            # DL Strategy needs the model to be trained first
            dl_strat = DLStrategy(model_type=strategy, symbol=symbol)
            prob = dl_strat.predict(df)
            
            if prob is None:
                 return {"error": "Not enough data for prediction"}
                 
            signal = 1 if prob > 0.5 else 0
            return {
                "symbol": symbol,
                "strategy": strategy,
                "signal": signal,
                "signal_label": "BUY" if signal == 1 else "SELL",
                "probability": round(prob, 4),
                "latest_close": round(float(df.iloc[-1]["Close"]), 2),
                "date": str(df.index[-1]),
            }
        except Exception as e:
            return {"error": f"DL Inference failed: {e}. Train model first?"}
    else:
        return {"error": f"Unknown strategy: {strategy}. Use: sma, rsi, random_forest, xgboost, lstm, transformer"}

    latest = result_df.iloc[-1]
    signal = int(latest["signal"])
    
    return {
        "symbol": symbol,
        "strategy": strategy,
        "signal": signal,
        "signal_label": "BUY (Long)" if signal == 1 else "SELL (Flat)",
        "latest_close": round(float(latest["Close"]), 2),
        "date": str(result_df.index[-1]),
    }


@mcp.tool()
def run_strategy_backtest(
    symbol: str = "BTC-USD",
    strategy: str = "sma",
    start: str = "2023-01-01",
    end: str = "2025-01-01",
    init_cash: float = 10000.0,
) -> dict:
    """
    Run a backtest for a specific strategy.
    
    Args:
        symbol: Yahoo Finance symbol
        strategy: "sma", "rsi", "random_forest", "xgboost"
        start: Backtest start date
        end: Backtest end date
        init_cash: Starting capital in USD
    
    Returns:
        Dict with performance metrics (return, sharpe, drawdown, trades, win rate).
    """
    from src.features import prepare_features
    from backtest.engine import run_backtest, print_metrics

    df = prepare_features(symbol, start, end)

    if strategy == "sma":
        from strategies.sma_crossover import generate_signals
        df = generate_signals(df)
    elif strategy == "rsi":
        from strategies.rsi_mean_reversion import generate_signals
        df = generate_signals(df)
    elif strategy in ("random_forest", "xgboost"):
        from strategies.ml_strategy import generate_signals
        df = generate_signals(df, model_type=strategy)
    else:
        return {"error": f"Unknown strategy: {strategy}"}

    portfolio = run_backtest(df, init_cash=init_cash)
    metrics = print_metrics(portfolio, strategy_name=strategy)

    return {
        "symbol": symbol,
        "strategy": strategy,
        "period": f"{start} to {end}",
        "init_cash": init_cash,
        "metrics": metrics,
    }


@mcp.tool()
def compare_all_strategies(
    symbol: str = "BTC-USD",
    start: str = "2023-01-01",
    end: str = "2025-01-01",
) -> dict:
    """
    Compare all 4 strategies on the same data.
    
    Args:
        symbol: Yahoo Finance symbol
        start: Start date
        end: End date
    
    Returns:
        Dict with comparison table and recommendation.
    """
    results = {}
    strategies = ["sma", "rsi", "random_forest", "xgboost"]

    for strat in strategies:
        try:
            result = run_strategy_backtest(symbol, strat, start, end)
            if "metrics" in result:
                results[strat] = result["metrics"]
        except Exception as e:
            results[strat] = {"error": str(e)}

    # Find best strategy
    best = None
    best_return = float("-inf")
    for name, m in results.items():
        if isinstance(m, dict) and "total_return_pct" in m:
            if m["total_return_pct"] > best_return:
                best_return = m["total_return_pct"]
                best = name

    return {
        "symbol": symbol,
        "period": f"{start} to {end}",
        "results": results,
        "best_strategy": best,
        "best_return_pct": best_return,
    }


# ══════════════════════════════════════════════════════════════
# TRADING TOOLS — Execution Agent
# ══════════════════════════════════════════════════════════════

@mcp.tool()
def get_balance(asset: str = "") -> dict:
    """
    Get account balance for a specific asset or all assets.
    
    Args:
        asset: Asset symbol (e.g. "USDT", "BTC"). Empty for all assets.
    
    Returns:
        Dict with free and locked balances.
    """
    client = _get_client()
    if asset:
        balances = client.get_balance(asset)
    else:
        balances = client.get_balance()
    
    # Convert to serializable format
    result = {}
    for k, v in balances.items():
        result[k] = {"free": v["free"], "locked": v["locked"]}
    
    return {
        "mode": client.mode,
        "balances": result,
    }


@mcp.tool()
def check_safety() -> dict:
    """
    Check current safety limits and daily trade count.
    
    Returns:
        Dict with safety status, limits, and remaining capacity.
    """
    client = _get_client()
    client._reset_daily_counter()
    
    current_equity = client.get_total_equity_usd()
    loss_pct = 0.0
    if client.initial_equity_usd and client.initial_equity_usd > 0:
        loss = client.initial_equity_usd - current_equity
        loss_pct = (loss / client.initial_equity_usd) * 100

    return {
        "mode": client.mode,
        "max_position_usd": client.max_position,
        "max_daily_trades": client.max_daily_trades,
        "daily_trades_used": client.daily_trades,
        "daily_trades_remaining": client.max_daily_trades - client.daily_trades,
        "can_trade": client.daily_trades < client.max_daily_trades and loss_pct <= client.max_daily_loss_pct,
        "simulation": client.simulation,
        # New fields
        "initial_equity_usd": client.initial_equity_usd,
        "current_equity_usd": round(current_equity, 2),
        "max_daily_loss_pct": client.max_daily_loss_pct,
        "current_loss_pct": round(loss_pct, 4) if loss_pct > 0 else 0.0,
        "circuit_breaker_triggered": loss_pct > client.max_daily_loss_pct,
    }


@mcp.tool()
def buy_crypto(
    symbol: str = "BTCUSDT",
    amount_usd: float = 10.0,
) -> dict:
    """
    Buy crypto with a specified USD amount. ⚠️ Checks safety limits first.
    
    Args:
        symbol: Trading pair (e.g. BTCUSDT, ETHUSDT)
        amount_usd: Amount to spend in USD (max depends on MAX_POSITION_USD)
    
    Returns:
        Dict with order details and updated balance.
    """
    client = _get_client()
    
    # Pre-check safety
    try:
        client._check_safety(amount_usd)
    except ValueError as e:
        return {"error": str(e), "order": None}

    try:
        order = client.buy(symbol, usd_amount=amount_usd)
        usdt_bal = client.get_usdt_balance()
        return {
            "success": True,
            "mode": client.mode,
            "order_id": order.get("orderId"),
            "symbol": symbol,
            "side": "BUY",
            "amount_usd": amount_usd,
            "price": float(order.get("price", 0)),
            "status": order.get("status"),
            "usdt_remaining": usdt_bal,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def sell_crypto(
    symbol: str = "BTCUSDT",
    quantity: float = 0.0,
    sell_all: bool = False,
) -> dict:
    """
    Sell crypto. Can sell a specific quantity or all holdings.
    
    Args:
        symbol: Trading pair (e.g. BTCUSDT)
        quantity: Amount of base asset to sell (e.g. 0.001 BTC)
        sell_all: If True, sells entire balance of the base asset
    
    Returns:
        Dict with order details.
    """
    import math
    client = _get_client()
    base_asset = symbol.replace("USDT", "")

    try:
        if sell_all:
            bal = client.get_balance(base_asset)
            quantity = bal.get(base_asset, {}).get("free", 0)
            if quantity <= 0:
                return {"success": False, "error": f"No {base_asset} balance to sell"}

            # Round down to valid precision
            info = client.client.get_symbol_info(symbol)
            step = float([f for f in info["filters"] if f["filterType"] == "LOT_SIZE"][0]["stepSize"])
            precision = int(round(-math.log(step, 10), 0))
            quantity = math.floor(quantity * 10**precision) / 10**precision

        if quantity <= 0:
            return {"success": False, "error": "Quantity must be > 0"}

        order = client.sell(symbol, quantity=quantity)
        return {
            "success": True,
            "mode": client.mode,
            "order_id": order.get("orderId"),
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": float(order.get("price", 0)),
            "status": order.get("status"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def set_trading_mode(mode: str = "simulation") -> dict:
    """
    Switch trading mode. Use this before trading.
    
    Args:
        mode: "simulation" (no API keys), "testnet" (Binance paper), "live" (real money!)
    
    Returns:
        Connection status.
    """
    global _client, _client_mode
    if mode not in ("simulation", "testnet", "live"):
        return {"error": f"Invalid mode: {mode}. Use: simulation, testnet, live"}
    
    try:
        _client = None
        _client_mode = None
        client = _get_client(mode)
        status = client.status()
        return {
            "success": True,
            "mode": mode,
            "connected": status["connected"],
            "usdt_balance": status.get("usdt_balance"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# PORTFOLIO TOOLS — Monitor Agent
# ══════════════════════════════════════════════════════════════

@mcp.tool()
def get_portfolio() -> dict:
    """
    Get full portfolio overview — all balances with USD valuations.
    
    Returns:
        Dict with all asset balances, total value, and mode.
    """
    client = _get_client()
    balances = client.get_balance()
    
    portfolio = []
    total_usd = 0.0
    
    for asset, bal in balances.items():
        entry = {
            "asset": asset,
            "free": bal["free"],
            "locked": bal["locked"],
        }
        
        if asset == "USDT":
            entry["usd_value"] = bal["free"]
            total_usd += bal["free"]
        else:
            try:
                price = client.get_price(f"{asset}USDT")
                usd_val = bal["free"] * price
                entry["price"] = price
                entry["usd_value"] = round(usd_val, 2)
                total_usd += usd_val
            except Exception:
                entry["usd_value"] = None
        
        portfolio.append(entry)
    
    return {
        "mode": client.mode,
        "total_usd_value": round(total_usd, 2),
        "assets": portfolio,
        "timestamp": datetime.now().isoformat(),
    }


@mcp.tool()
def train_model(symbol: str = "BTC-USD", model_type: str = "lstm", epochs: int = 10) -> dict:
    """
    Train a Deep Learning model (LSTM or Transformer) for a specific symbol.
    
    Args:
        symbol: Trading pair (e.g., "BTC-USD").
        model_type: "lstm" or "transformer".
        epochs: Number of training epochs.
        
    Returns:
        Training status, duration, and model path.
    """
    try:
        # Run training as a subprocess to avoid blocking the server/event loop
        # We assume the server is running from the project root
        cmd = [
            "python", "-m", "src.train",
            "--symbol", symbol,
            "--model", model_type,
            "--epochs", str(epochs)
        ]
        
        start_time = datetime.now()
        # Run and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = datetime.now() - start_time
        
        # Get the last few lines of output for context
        output_lines = result.stdout.splitlines()
        last_output = "\n".join(output_lines[-10:]) if len(output_lines) > 10 else result.stdout

        return {
            "success": True,
            "message": "Training completed successfully",
            "duration": str(duration),
            "last_output": last_output,
            "model_path": f"models/best_{model_type}_{symbol}.pth"
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False, 
            "error": "Training failed", 
            "details": e.stderr,
            "stdout": e.stdout
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# DATA TOOLS — Data Agent (Legacy/Helper)
# ══════════════════════════════════════════════════════════════

@mcp.tool()
def get_trade_history(limit: int = 20) -> dict:
    """
    Get recent trade history from the current session.
    
    Args:
        limit: Max number of trades to return
    
    Returns:
        Dict with list of recent trades.
    """
    client = _get_client()
    trades = client.trade_log[-limit:]
    
    # Also check CSV log
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "trade_log.csv")
    csv_trades = []
    if os.path.exists(log_path):
        import pandas as pd
        df = pd.read_csv(log_path)
        csv_trades = df.tail(limit).to_dict(orient="records")
    
    return {
        "session_trades": trades,
        "session_count": len(trades),
        "csv_trades": csv_trades,
        "csv_count": len(csv_trades),
    }


@mcp.tool()
def get_pnl() -> dict:
    """
    Calculate profit/loss for the current session.
    
    Returns:
        Dict with starting balance, current value, P&L, and percentage.
    """
    client = _get_client()
    
    start_balance = client.initial_equity_usd if client.initial_equity_usd else None
    
    # Get current portfolio value
    current_value = client.get_total_equity_usd()
    
    result = {
        "mode": client.mode,
        "current_value_usd": current_value,
        "total_trades": len(client.trade_log),
        "daily_trades": client.daily_trades,
    }
    
    if start_balance is not None:
        pnl = current_value - start_balance
        pnl_pct = (pnl / start_balance) * 100
        result["start_balance_usd"] = start_balance
        result["pnl_usd"] = round(pnl, 2)
        result["pnl_pct"] = round(pnl_pct, 4)
    
    return result


# ══════════════════════════════════════════════════════════════
# Server entry point
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 Starting AI Trading MCP Server...")
    print("   Tools: get_price, get_klines, compute_indicators,")
    print("          get_signal, run_strategy_backtest, compare_all_strategies,")
    print("          buy_crypto, sell_crypto, get_balance, check_safety,")
    print("          get_portfolio, get_trade_history, get_pnl,")
    print("          set_trading_mode, get_multiple_prices")
    print("")
    print("   Run with: fastmcp run mcp_server/trading_mcp_server.py")
    mcp.run()
