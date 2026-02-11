"""
compare_strategies.py — Compare all strategies side-by-side.

Runs SMA Crossover, RSI Mean Reversion, and ML (Random Forest + XGBoost)
on the same test period and prints a comparison table.

Usage:
  python backtest/compare_strategies.py --symbol BTC-USD --start 2022-01-01 --end 2024-01-01
"""
import argparse
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features import prepare_features
from strategies.sma_crossover import generate_signals as sma_signals
from strategies.rsi_mean_reversion import generate_signals as rsi_signals
from strategies.ml_strategy import generate_signals as ml_signals
from backtest.engine import run_backtest, print_metrics


def main():
    parser = argparse.ArgumentParser(description="Compare all trading strategies")
    parser.add_argument("--symbol", type=str, default="BTC-USD")
    parser.add_argument("--start", type=str, default="2022-01-01")
    parser.add_argument("--end", type=str, default="2024-01-01")
    parser.add_argument("--cash", type=float, default=10_000.0)
    args = parser.parse_args()

    # --- Download & Feature Engineering ---
    print(f"\n{'='*60}")
    print(f"  🏆 Strategy Comparison — {args.symbol}")
    print(f"  Period: {args.start} → {args.end}")
    print(f"{'='*60}")

    df = prepare_features(args.symbol, start=args.start, end=args.end)

    results = []

    # --- Traditional Strategies (full period) ---
    for name, signal_fn in [
        ("SMA Crossover", sma_signals),
        ("RSI Mean Reversion", rsi_signals),
    ]:
        df_strat = signal_fn(df.copy())
        portfolio = run_backtest(df_strat, init_cash=args.cash)
        metrics = print_metrics(portfolio, strategy_name=name)
        results.append(metrics)

    # --- ML Strategies (test period only) ---
    for model_type in ["random_forest", "xgboost"]:
        test_df = ml_signals(df.copy(), model_type=model_type, train_ratio=0.8)
        portfolio = run_backtest(test_df, init_cash=args.cash)
        metrics = print_metrics(portfolio, strategy_name=f"ML ({model_type})")
        results.append(metrics)

    # --- Summary Table ---
    summary = pd.DataFrame(results)
    summary = summary.set_index("strategy")

    print(f"\n{'='*60}")
    print(f"  📊 FINAL COMPARISON")
    print(f"{'='*60}")
    print(summary.to_string())
    print(f"\n🏆 Best Return:  {summary['total_return_pct'].idxmax()} "
          f"({summary['total_return_pct'].max():.2f}%)")
    print(f"🏆 Best Sharpe:  {summary['sharpe_ratio'].idxmax()} "
          f"({summary['sharpe_ratio'].max():.4f})")
    print()


if __name__ == "__main__":
    main()
