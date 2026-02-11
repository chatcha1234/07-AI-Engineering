
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features import prepare_features

if __name__ == "__main__":
    try:
        print("Downloading data for BTC-USD...")
        # Get a chunk of data sufficient for indicators (e.g. 200 days)
        df = prepare_features("BTC-USD", "2023-01-01", "2024-01-01")
        print("\nGenerated Columns:")
        for col in df.columns:
            print(f"- {col}")
    except Exception as e:
        print(f"Error: {e}")
