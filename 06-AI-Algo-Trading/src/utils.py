"""
utils.py — Helper functions for data loading and validation.
"""
import pandas as pd


def load_csv(filepath: str) -> pd.DataFrame:
    """Load a CSV file with datetime index."""
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    df.index.name = "Date"
    return df


def validate_columns(df: pd.DataFrame, required: list[str]) -> bool:
    """Assert that all required columns exist in the DataFrame."""
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return True
