import torch
import joblib
import pandas as pd
import numpy as np
import os
from src.model_factory import LSTMModel, TransformerModel
from src.features import create_sequences

class DLStrategy:
    def __init__(self, model_type="lstm", symbol="BTC-USD", device="cpu"):
        self.device = device
        self.model_type = model_type
        self.symbol = symbol
        
        # Paths
        self.model_path = f"models/best_{model_type}_{symbol}.pth"
        self.scaler_path = f"models/scaler_{symbol}_{model_type}.pkl"
        
        # Load Scaler
        if not os.path.exists(self.scaler_path):
            raise FileNotFoundError(f"Scaler not found: {self.scaler_path}")
        self.scaler = joblib.load(self.scaler_path)
        
        # Config (Must match training config!)
        # TODO: Load config from a file
        self.seq_length = 60
        self.input_dim = 11 # 11 features defined in train.py
        
        # Load Model
        if model_type == "lstm":
            self.model = LSTMModel(input_dim=self.input_dim, hidden_dim=64, num_layers=2)
        elif model_type == "transformer":
            self.model = TransformerModel(input_dim=self.input_dim, d_model=64, nhead=4, num_layers=2)
            
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
            
        self.model.load_state_dict(torch.load(self.model_path, map_location=device))
        self.model.to(device)
        self.model.eval()
        
    def predict(self, df: pd.DataFrame):
        """
        Predict signal for the LATEST data point.
        df must contain at least (SEQ_LENGTH) rows of features.
        """
        # Ensure we have enough data
        if len(df) < self.seq_length:
            return None
            
        # Get last window
        df_window = df.iloc[-self.seq_length:].copy()
        
        # Select Features (Must match train.py)
        feature_cols = [
            "Open", "High", "Low", "Close", "Volume",
            "SMA_20", "SMA_50", "EMA_12", "EMA_26",
            "RSI_14", "ATR_14"
        ]
        
        # Scale
        features = self.scaler.transform(df_window[feature_cols])
        
        # To Tensor (1, seq_len, input_dim)
        x = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
        
        # Inference
        with torch.no_grad():
            prob = self.model(x).item()
            
        return prob

    def get_signal(self, df: pd.DataFrame, threshold=0.5):
        prob = self.predict(df)
        if prob is None:
            return "NEUTRAL", 0.0
            
        if prob > threshold:
            return "BUY", prob
        else:
            return "SELL", prob
