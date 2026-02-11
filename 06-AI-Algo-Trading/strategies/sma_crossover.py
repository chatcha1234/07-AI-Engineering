"""
sma_crossover.py — Simple Moving Average Crossover Strategy

Rules:
  - BUY  (signal=1): SMA_20 crosses above SMA_50  (Golden Cross)
  - SELL (signal=0): SMA_20 crosses below SMA_50  (Death Cross)
"""
import pandas as pd


def generate_signals(df: pd.DataFrame, fast: str = "SMA_20", slow: str = "SMA_50") -> pd.DataFrame:
    """
    Generate buy/sell signals based on SMA crossover.

    Args:
        df:   DataFrame with indicator columns (must include fast & slow SMA)
        fast: Column name for the fast moving average
        slow: Column name for the slow moving average

    Returns:
        DataFrame with added 'signal' and 'position' columns.
          signal:   1 = long, 0 = flat
          position: change in signal (1 = entry, -1 = exit, 0 = hold)
    """
    df = df.copy()

    # 1 when fast SMA is above slow SMA, else 0
    df["signal"] = 0
    df.loc[df[fast] > df[slow], "signal"] = 1

    # position shows changes: +1 = entry, -1 = exit
    df["position"] = df["signal"].diff().fillna(0).astype(int)

    buy_count = (df["position"] == 1).sum()
    sell_count = (df["position"] == -1).sum()
    print(f"📈 SMA Crossover — Buy signals: {buy_count}, Sell signals: {sell_count}")

    return df


if __name__ == "__main__":
    from src.features import prepare_features

    df = prepare_features("BTC-USD", "2023-01-01", "2024-01-01")
    df = generate_signals(df)
    print(df[["Close", "SMA_20", "SMA_50", "signal", "position"]].tail(20))
