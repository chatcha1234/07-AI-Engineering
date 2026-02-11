"""
models.py — ML pipeline for trading signal prediction.

Uses technical indicators as features to predict next-day price direction:
  - Target: 1 = price goes up tomorrow, 0 = price goes down
  - Models: Random Forest, XGBoost (Gradient Boosting)
  - Walk-forward split to avoid look-ahead bias
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.preprocessing import StandardScaler


# ── Feature columns used by the model ──────────────────────────
FEATURE_COLS = [
    "SMA_20", "SMA_50", "EMA_12", "EMA_26",
    "RSI_14",
    "MACD_12_26_9", "MACDh_12_26_9", "MACDs_12_26_9",
    "BBL_20_2.0_2.0", "BBM_20_2.0_2.0", "BBU_20_2.0_2.0",
    "BBB_20_2.0_2.0", "BBP_20_2.0_2.0",
    "ATR_14",
]


def create_target(df: pd.DataFrame, price_col: str = "Close") -> pd.DataFrame:
    """
    Create binary target: 1 if tomorrow's close > today's close, else 0.
    Drops the last row (no future data to label).
    """
    df = df.copy()
    df["target"] = (df[price_col].shift(-1) > df[price_col]).astype(int)
    df.dropna(subset=["target"], inplace=True)
    df["target"] = df["target"].astype(int)
    return df


def prepare_ml_data(df: pd.DataFrame, feature_cols: list[str] = None):
    """
    Prepare X (features) and y (target) from a DataFrame.

    Returns:
        X: DataFrame of features
        y: Series of binary targets
    """
    if feature_cols is None:
        feature_cols = [c for c in FEATURE_COLS if c in df.columns]

    X = df[feature_cols].copy()
    y = df["target"].copy()

    return X, y


def train_test_split_sequential(X, y, train_ratio: float = 0.8):
    """
    Time-series split: first N% for training, rest for testing.
    No shuffling — preserves temporal order to avoid look-ahead bias.
    """
    split_idx = int(len(X) * train_ratio)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"📊 Train: {len(X_train)} rows | Test: {len(X_test)} rows "
          f"({train_ratio*100:.0f}/{(1-train_ratio)*100:.0f} split)")

    return X_train, X_test, y_train, y_test


def train_model(X_train, y_train, model_type: str = "random_forest"):
    """
    Train a classification model.

    Args:
        model_type: "random_forest" or "xgboost"

    Returns:
        Tuple of (trained model, fitted scaler)
    """
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    if model_type == "random_forest":
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )
    elif model_type == "xgboost":
        model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    model.fit(X_scaled, y_train)
    print(f"✅ {model_type} trained on {len(X_train)} samples")

    return model, scaler


def evaluate_model(model, scaler, X_test, y_test, model_name: str = "Model") -> dict:
    """
    Evaluate model on test set and print classification report.

    Returns dict with accuracy and F1 score.
    """
    X_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_scaled)

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")

    print(f"\n{'='*50}")
    print(f"  🤖 {model_name} — Evaluation")
    print(f"{'='*50}")
    print(f"  Accuracy:  {acc*100:.2f}%")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"{'='*50}")
    print(classification_report(y_test, y_pred, target_names=["Down", "Up"]))

    return {"accuracy": round(acc, 4), "f1": round(f1, 4), "predictions": y_pred}


def predict_signals(model, scaler, X: pd.DataFrame) -> np.ndarray:
    """Generate predictions for the full dataset."""
    X_scaled = scaler.transform(X)
    return model.predict(X_scaled)


def feature_importance(model, feature_cols: list[str], top_n: int = 10):
    """Print top feature importances."""
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]

    print(f"\n🏆 Top {top_n} Feature Importances:")
    for i, idx in enumerate(indices):
        print(f"  {i+1}. {feature_cols[idx]:25s} {importances[idx]:.4f}")


if __name__ == "__main__":
    from src.features import prepare_features

    # 1. Prepare data
    df = prepare_features("BTC-USD", "2022-01-01", "2024-01-01")
    df = create_target(df)

    # 2. Split
    X, y = prepare_ml_data(df)
    X_train, X_test, y_train, y_test = train_test_split_sequential(X, y)

    # 3. Train & evaluate both models
    for model_type in ["random_forest", "xgboost"]:
        model, scaler = train_model(X_train, y_train, model_type=model_type)
        evaluate_model(model, scaler, X_test, y_test, model_name=model_type)
        feature_importance(model, X.columns.tolist())
