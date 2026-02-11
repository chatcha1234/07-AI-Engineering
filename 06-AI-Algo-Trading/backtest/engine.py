"""
engine.py — Vectorized backtesting engine using vectorbt.

Provides functions to:
  - Run a backtest from a signal column
  - Print performance metrics
  - Save equity curve plot
"""
import os
import numpy as np
import pandas as pd
import vectorbt as vbt


def run_backtest(
    df: pd.DataFrame,
    signal_col: str = "signal",
    price_col: str = "Close",
    init_cash: float = 10_000.0,
    fees: float = 0.001,
) -> vbt.Portfolio:
    """
    Run a vectorized backtest.

    Args:
        df:         DataFrame with price and signal columns
        signal_col: Column with 1/0 signals (1=long, 0=flat)
        price_col:  Column with price data
        init_cash:  Starting cash (default $10,000)
        fees:       Trading fees as fraction (default 0.1%)

    Returns:
        vbt.Portfolio object with full backtest results.
    """
    price = df[price_col]
    signal = df[signal_col]

    # Entry = signal goes from 0 to 1, Exit = signal goes from 1 to 0
    entries = (signal == 1) & (signal.shift(1) == 0)
    exits = (signal == 0) & (signal.shift(1) == 1)

    # Fill first row edge case
    entries.iloc[0] = signal.iloc[0] == 1
    exits.iloc[0] = False

    portfolio = vbt.Portfolio.from_signals(
        close=price,
        entries=entries,
        exits=exits,
        init_cash=init_cash,
        fees=fees,
        freq="1D",
    )

    return portfolio


def print_metrics(portfolio: vbt.Portfolio, strategy_name: str = "Strategy") -> dict:
    """
    Print key performance metrics from a backtest.

    Returns a dict of metrics for further use.
    """
    total_return = portfolio.total_return() * 100
    sharpe = portfolio.sharpe_ratio()
    max_dd = portfolio.max_drawdown() * 100
    total_trades = portfolio.trades.count()

    # Win rate
    if total_trades > 0:
        win_rate = portfolio.trades.win_rate() * 100
    else:
        win_rate = 0.0

    metrics = {
        "strategy": strategy_name,
        "total_return_pct": round(total_return, 2),
        "sharpe_ratio": round(sharpe, 4) if not np.isnan(sharpe) else 0.0,
        "max_drawdown_pct": round(max_dd, 2),
        "total_trades": int(total_trades),
        "win_rate_pct": round(win_rate, 2),
    }

    print(f"\n{'='*50}")
    print(f"  📊 {strategy_name} — Backtest Results")
    print(f"{'='*50}")
    print(f"  Total Return:   {metrics['total_return_pct']:>8.2f}%")
    print(f"  Sharpe Ratio:   {metrics['sharpe_ratio']:>8.4f}")
    print(f"  Max Drawdown:   {metrics['max_drawdown_pct']:>8.2f}%")
    print(f"  Total Trades:   {metrics['total_trades']:>8d}")
    print(f"  Win Rate:       {metrics['win_rate_pct']:>8.2f}%")
    print(f"{'='*50}\n")

    return metrics


def save_equity_curve(portfolio: vbt.Portfolio, strategy_name: str = "strategy", output_dir: str = "backtest/results"):
    """Save the equity curve as a PNG image."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{strategy_name}_equity.png")

    fig = portfolio.plot(subplots=["cum_returns", "drawdowns"])
    fig.write_image(filepath, width=1200, height=600)
    print(f"📈 Equity curve saved → {filepath}")

    return filepath
