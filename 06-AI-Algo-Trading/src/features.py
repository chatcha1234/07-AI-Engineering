"""
features.py — Technical indicator pipeline using pandas-ta.

Adds common indicators to an OHLCV DataFrame:
  SMA (20, 50), EMA (12, 26), RSI (14), MACD, Bollinger Bands, ATR (14)
"""
import pandas as pd
import pandas_ta as ta
import numpy as np

from src.data_loader import download_data


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to an OHLCV DataFrame.
    
    Expects columns: Open, High, Low, Close, Volume
    Returns the DataFrame with new indicator columns appended.
    """
    df = df.copy()

    # --- Trend ---
    df["SMA_20"] = ta.sma(df["Close"], length=20)
    df["SMA_50"] = ta.sma(df["Close"], length=50)
    df["EMA_12"] = ta.ema(df["Close"], length=12)
    df["EMA_26"] = ta.ema(df["Close"], length=26)

    # --- Momentum ---
    df["RSI_14"] = ta.rsi(df["Close"], length=14)

    # MACD returns a DataFrame with 3 columns
    macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
    if macd is not None:
        df = pd.concat([df, macd], axis=1)

    # --- Volatility ---
    bbands = ta.bbands(df["Close"], length=20, std=2.0)
    if bbands is not None:
        df = pd.concat([df, bbands], axis=1)

    df["ATR_14"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)

    return df


def prepare_features(symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """
    Convenience function: download data and apply all indicators.
    
    Args:
        symbol:   Ticker symbol (e.g. "BTC-USD")
        start:    Start date string  (e.g. "2023-01-01")
        end:      End date string    (e.g. "2024-01-01")
        interval: Data interval      (default "1d")
    
    Returns:
        DataFrame with OHLCV + all indicators, NaN rows dropped.
    """
    df = download_data(symbol, start=start, end=end, interval=interval)
    if df is None:
        raise ValueError(f"Could not download data for {symbol}")

    df = add_indicators(df)
    df.dropna(inplace=True)

    print(f"✅ Features ready — {len(df)} rows, {len(df.columns)} columns")
    return df


def add_target(df: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """
    Add target column for classification.
    Target = 1 if Close[t+horizon] > Close[t], else 0.
    """
    # 1 if price goes up, 0 otherwise
    df["Target"] = (df["Close"].shift(-horizon) > df["Close"]).astype(int)
    return df


def create_sequences(df: pd.DataFrame, seq_length: int, feature_cols: list, target_col: str = "Target"):
    """
    Create sequences for Time-Series models (LSTM/Transformer).
    
    Args:
        df: DataFrame with features and target.
        seq_length: Length of input sequence (e.g. 60).
        feature_cols: List of column names to use as features.
        target_col: Name of the target column.
        
    Returns:
        X (np.array): (num_samples, seq_length, num_features)
        y (np.array): (num_samples,)
    """
    data_array = df[feature_cols].values
    target_array = df[target_col].values
    
    xs = []
    ys = []
    
    for i in range(len(df) - seq_length):
        x = data_array[i:(i + seq_length)]
        y = target_array[i + seq_length] # Predict the NEXT step after the sequence
        xs.append(x)
        ys.append(y)
        
    return np.array(xs), np.array(ys)



if __name__ == "__main__":
    df = prepare_features("BTC-USD", "2023-01-01", "2024-01-01")
    print(df.tail())
    print(f"\nColumns: {list(df.columns)}")
