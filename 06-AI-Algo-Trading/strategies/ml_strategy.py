"""
ml_strategy.py — ML-based trading strategy.

Uses a trained ML model's predictions as buy/sell signals:
  - signal=1 (long) when model predicts price will go UP
  - signal=0 (flat) when model predicts price will go DOWN
"""
import pandas as pd

from src.models import (
    FEATURE_COLS,
    create_target,
    prepare_ml_data,
    train_test_split_sequential,
    train_model,
    evaluate_model,
    predict_signals,
)


def generate_signals(
    df: pd.DataFrame,
    model_type: str = "random_forest",
    train_ratio: float = 0.8,
) -> pd.DataFrame:
    """
    Train an ML model and generate signals for the test period.

    Args:
        df:           DataFrame with indicators (from features.py)
        model_type:   "random_forest" or "xgboost"
        train_ratio:  Fraction of data used for training

    Returns:
        DataFrame (test period only) with 'signal' and 'position' columns.
    """
    df = df.copy()
    df = create_target(df)

    # Prepare features
    feature_cols = [c for c in FEATURE_COLS if c in df.columns]
    X, y = prepare_ml_data(df, feature_cols)

    # Time-series split
    X_train, X_test, y_train, y_test = train_test_split_sequential(X, y, train_ratio)

    # Train
    model, scaler = train_model(X_train, y_train, model_type=model_type)

    # Evaluate
    results = evaluate_model(model, scaler, X_test, y_test, model_name=f"ML ({model_type})")

    # Generate signals for test period only
    test_df = df.iloc[len(X_train):len(X_train) + len(X_test)].copy()
    test_df["signal"] = results["predictions"]
    test_df["position"] = test_df["signal"].diff().fillna(0).astype(int)

    buy_count = (test_df["position"] == 1).sum()
    sell_count = (test_df["position"] == -1).sum()
    print(f"🤖 ML ({model_type}) — Buy signals: {buy_count}, Sell signals: {sell_count}")

    return test_df


if __name__ == "__main__":
    from src.features import prepare_features

    df = prepare_features("BTC-USD", "2022-01-01", "2024-01-01")
    test_df = generate_signals(df, model_type="random_forest")
    print(test_df[["Close", "signal", "position"]].tail(20))
