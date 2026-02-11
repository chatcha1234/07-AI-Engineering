"""
rsi_mean_reversion.py — RSI Mean Reversion Strategy

Rules:
  - BUY  (signal=1): RSI_14 drops below oversold threshold  (default 30)
  - SELL (signal=0): RSI_14 rises above overbought threshold (default 70)
  - Between thresholds: hold current position
"""
import pandas as pd


def generate_signals(
    df: pd.DataFrame,
    rsi_col: str = "RSI_14",
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> pd.DataFrame:
    """
    Generate buy/sell signals based on RSI levels.

    Args:
        df:         DataFrame with RSI column
        rsi_col:    Name of the RSI column
        oversold:   RSI threshold to trigger buy  (default 30)
        overbought: RSI threshold to trigger sell  (default 70)

    Returns:
        DataFrame with added 'signal' and 'position' columns.
    """
    df = df.copy()

    # Initialize signal column — hold (NaN → forward fill later)
    df["signal"] = float("nan")

    # Set buy/sell triggers
    df.loc[df[rsi_col] < oversold, "signal"] = 1    # Oversold → buy
    df.loc[df[rsi_col] > overbought, "signal"] = 0  # Overbought → sell

    # Forward fill: hold the last signal between trigger points
    df["signal"] = df["signal"].ffill().fillna(0).astype(int)

    # position shows changes: +1 = entry, -1 = exit
    df["position"] = df["signal"].diff().fillna(0).astype(int)

    buy_count = (df["position"] == 1).sum()
    sell_count = (df["position"] == -1).sum()
    print(f"📉 RSI Mean Reversion (OS={oversold}, OB={overbought}) — "
          f"Buy signals: {buy_count}, Sell signals: {sell_count}")

    return df


if __name__ == "__main__":
    from src.features import prepare_features

    df = prepare_features("BTC-USD", "2023-01-01", "2024-01-01")
    df = generate_signals(df)
    print(df[["Close", "RSI_14", "signal", "position"]].tail(20))
