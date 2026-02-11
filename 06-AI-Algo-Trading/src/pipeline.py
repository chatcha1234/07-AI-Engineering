
import os
import shutil
import logging
import argparse
from datetime import datetime
import pandas as pd
import torch
import joblib

from src.features import prepare_features, add_target, create_sequences
from src.train import train_model
from src.strategy_dl import DLStrategy
from src.notification import NotificationService

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AutoRetrain")

def evaluate_model(model_path, symbol, scaler_path, data_path=None):
    """
    Evaluate a specific model on recent data.
    Returns: Accuracy (or Loss)
    """
    # 1. Load Data (Last 90 days for evaluation)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - pd.Timedelta(days=90)).strftime("%Y-%m-%d")
    
    logger.info(f"📊 Evaluating model on data from {start_date} to {end_date}...")
    
    try:
        df = prepare_features(symbol, start=start_date, end=end_date)
        df = add_target(df) # Add target for accuracy check
        df.dropna(inplace=True)
        
        # 2. Load Model & Scaler
        # We use DLStrategy to load and predict easily, 
        # but we need to trick it to load a specific path if it's a candidate.
        # Actually, let's just use the DLStrategy class but patch the path? 
        # Or better, just instantiate it and if it fails, it fails.
        
        # NOTE: DLStrategy loads from `models/best_...` by default. 
        # We might need to rename candidate to best temporarily or subclass.
        # For simplicity, let's assume we comparing 'current' (best) vs 'candidate'.
        
        # Let's load manually to be safe
        device = "cpu"
        input_dim = 11 # Feature count
        
        # Check model type from filename
        model_type = "lstm" if "lstm" in model_path else "transformer"
        
        from src.model_factory import LSTMModel, TransformerModel
        
        if model_type == "lstm":
            model = LSTMModel(input_dim=input_dim, hidden_dim=64, num_layers=2)
        else:
            model = TransformerModel(input_dim=input_dim, d_model=64, nhead=4, num_layers=2)
            
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.to(device)
        model.eval()
        
        scaler = joblib.load(scaler_path)
        
        # 3. Predict matches src/strategy_dl.py logic
        correct = 0
        total = 0
        
        # Feature Cols
        feature_cols = [
            "Open", "High", "Low", "Close", "Volume",
            "SMA_20", "SMA_50", "EMA_12", "EMA_26",
            "RSI_14", "ATR_14"
        ]
        
        # Validate data
        if len(df) < 60:
            logger.warning("Not enough data for evaluation.")
            return 0.0

        # Create sequences using the scaler
        # We need to scale the features first
        features = scaler.transform(df[feature_cols])
        
        seq_length = 60
        X_test, y_test = [], []
        
        # Target column
        targets = df["Target"].values
        
        for i in range(len(features) - seq_length):
            x = features[i:(i + seq_length)]
            y = targets[i + seq_length]
            X_test.append(x)
            y_test.append(y)
            
        X_test = torch.tensor(X_test, dtype=torch.float32).to(device)
        y_test = torch.tensor(y_test, dtype=torch.float32).to(device).unsqueeze(1)
        
        # Inference
        with torch.no_grad():
            outputs = model(X_test)
            predicted = (outputs > 0.5).float()
            correct = (predicted == y_test).sum().item()
            total = y_test.size(0)
            
        acc = correct / total if total > 0 else 0
        logger.info(f"   Model: {os.path.basename(model_path)} | Accuracy: {acc:.4f} ({correct}/{total})")
        return acc

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return 0.0

def run_pipeline(symbol="BTC-USD", model_type="lstm"):
    notifier = NotificationService()
    notifier.send(f"🔄 Auto-Retraming Started: {symbol} ({model_type})", level="INFO")
    
    # Paths
    current_model_path = f"models/best_{model_type}_{symbol}.pth"
    candidate_model_path = f"models/candidate_{model_type}_{symbol}.pth"
    scaler_path = f"models/scaler_{symbol}_{model_type}.pkl"
    
    # 1. Train Candidate
    # train_model saves to 'best_...' by default in train.py. 
    # We should modify train.py to accept output path OR rename it after.
    # Let's rename the CURRENT best to 'backup' first? No, if training fails we lose it.
    
    # Hack: We run training. It will overwrite 'best_...'. 
    # So we MUST backup the current best first.
    
    if os.path.exists(current_model_path):
        shutil.copy(current_model_path, current_model_path + ".backup")
        logger.info("Backed up current model.")
        
    # 2. Run Training
    logger.info("🚀 Training new model...")
    try:
        # Train for 20 epochs (can be more for retraining)
        train_model(symbol=symbol, model_type=model_type, epochs=20, device="cpu") 
        # train_model saves to 'models/best_...' automatically
        
        # Rename the NEWLY trained 'best' to 'candidate'
        if os.path.exists(current_model_path):
            shutil.move(current_model_path, candidate_model_path)
            
        # Restore backup as 'current' for comparison
        if os.path.exists(current_model_path + ".backup"):
            shutil.move(current_model_path + ".backup", current_model_path)
            
    except Exception as e:
        logger.error(f"Training failed: {e}")
        notifier.send(f"❌ Training Failed: {e}", level="ERROR")
        # Restore backup if needed
        if os.path.exists(current_model_path + ".backup") and not os.path.exists(current_model_path):
             shutil.move(current_model_path + ".backup", current_model_path)
        return

    # 3. Compare Models
    logger.info("⚔️ Comparing models...")
    
    acc_current = 0.0
    if os.path.exists(current_model_path):
        acc_current = evaluate_model(current_model_path, symbol, scaler_path)
    else:
        logger.warning("No current model found. New model wins by default.")
        
    acc_candidate = evaluate_model(candidate_model_path, symbol, scaler_path)
    
    # 4. Promote or Discard
    msg = f"Current Acc: {acc_current:.4f} | Candidate Acc: {acc_candidate:.4f}"
    logger.info(msg)
    
    if acc_candidate > acc_current:
        logger.info("🏆 New model is BETTER. Promoting...")
        shutil.move(candidate_model_path, current_model_path)
        notifier.send(f"✅ Model Updated! ({symbol})\n{msg}", level="SUCCESS")
    else:
        logger.info("🗑️ New model is WORSE. Discarding...")
        os.remove(candidate_model_path)
        notifier.send(f"zzz No Improvement.\n{msg}", level="WARNING")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTC-USD")
    parser.add_argument("--model", type=str, default="lstm")
    args = parser.parse_args()
    
    run_pipeline(args.symbol, args.model)
