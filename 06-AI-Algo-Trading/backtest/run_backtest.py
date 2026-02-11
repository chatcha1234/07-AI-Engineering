"""
run_backtest.py — End-to-end CLI script to run a backtest.

Usage:
  python backtest/run_backtest.py --symbol BTC-USD --strategy sma_crossover
  python backtest/run_backtest.py --symbol ETH-USD --strategy rsi_mean_reversion --start 2022-01-01 --end 2024-01-01
"""
import argparse
import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features import prepare_features
from strategies.sma_crossover import generate_signals as sma_signals
from strategies.rsi_mean_reversion import generate_signals as rsi_signals
from backtest.engine import run_backtest, print_metrics, save_equity_curve


STRATEGIES = {
    "sma_crossover": {
        "fn": sma_signals,
        "name": "SMA Crossover (20/50)",
    },
    "rsi_mean_reversion": {
        "fn": rsi_signals,
        "name": "RSI Mean Reversion (30/70)",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Run a trading strategy backtest")
    parser.add_argument("--symbol", type=str, default="BTC-USD", help="Ticker symbol (default: BTC-USD)")
    parser.add_argument("--strategy", type=str, default="sma_crossover",
                        choices=list(STRATEGIES.keys()), help="Strategy to test")
    parser.add_argument("--start", type=str, default="2023-01-01", help="Start date (default: 2023-01-01)")
    parser.add_argument("--end", type=str, default="2024-01-01", help="End date (default: 2024-01-01)")
    parser.add_argument("--cash", type=float, default=10_000.0, help="Initial cash (default: 10000)")
    parser.add_argument("--fees", type=float, default=0.001, help="Trading fees fraction (default: 0.001)")

    args = parser.parse_args()

    # --- 1. Download + Feature Engineering ---
    print(f"\n🔄 Preparing data for {args.symbol}...")
    df = prepare_features(args.symbol, start=args.start, end=args.end)

    # --- 2. Generate Signals ---
    strat = STRATEGIES[args.strategy]
    print(f"\n🎯 Applying strategy: {strat['name']}")
    df = strat["fn"](df)

    # --- 3. Run Backtest ---
    print(f"\n🧪 Running backtest (cash=${args.cash:,.0f}, fees={args.fees*100:.1f}%)...")
    portfolio = run_backtest(df, init_cash=args.cash, fees=args.fees)

    # --- 4. Print Results ---
    metrics = print_metrics(portfolio, strategy_name=strat["name"])

    # --- 5. Save Equity Curve ---
    try:
        save_equity_curve(portfolio, strategy_name=args.strategy)
    except Exception as e:
        print(f"⚠️  Could not save equity curve image: {e}")
        print("   (Install 'kaleido' for image export: pip install kaleido)")

    return metrics


if __name__ == "__main__":
    main()
