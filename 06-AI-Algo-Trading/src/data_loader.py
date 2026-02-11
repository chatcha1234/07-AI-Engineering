import yfinance as yf
import pandas as pd
import os

def download_data(symbol: str, start: str, end: str, interval: str = "1d"):
    """
    Downloads historical market data from Yahoo Finance.
    """
    print(f"Downloading data for {symbol} from {start} to {end}...")
    data = yf.download(symbol, start=start, end=end, interval=interval)
    
    if data.empty:
        print(f"No data found for {symbol}.")
        return None
    
    # Flatten columns if necessary (yfinance can return multi-index)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    return data

def save_data(data, symbol, folder="data"):
    if data is not None:
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = f"{folder}/{symbol}.csv"
        data.to_csv(filename)
        print(f"Data saved to {filename}")

if __name__ == "__main__":
    # Example usage: Download Bitcoin data
    symbol = "BTC-USD"
    df = download_data(symbol, start="2023-01-01", end="2024-01-01")
    save_data(df, symbol, folder="../data")
