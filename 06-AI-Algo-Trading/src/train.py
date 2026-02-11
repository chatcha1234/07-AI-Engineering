import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib
import os
import argparse

from src.features import prepare_features, add_target, create_sequences
from src.dataset import CryptoDataset
from src.model_factory import LSTMModel, TransformerModel

# --- Configuration ---
SEQ_LENGTH = 60
BATCH_SIZE = 32
EPOCHS = 20
LEARNING_RATE = 0.001
FEATURE_COLS = [
    "Open", "High", "Low", "Close", "Volume",
    "SMA_20", "SMA_50", "EMA_12", "EMA_26",
    "RSI_14", "ATR_14"
]

def train_model(symbol="BTC-USD", model_type="lstm", epochs=EPOCHS, device="cpu"):
    print(f"🚀 Starting training for {symbol} using {model_type.upper()}...")
    
    # 1. Load Data
    print("📥 Loading data...")
    df = prepare_features(symbol, start="2020-01-01", end="2024-01-01")
    df = add_target(df)
    df.dropna(inplace=True)
    
    # 2. Split Data (Time-based split)
    print("✂️ Splitting data...")
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    # 3. Scale Features
    print("⚖️ Scaling features...")
    scaler = StandardScaler()
    train_features = scaler.fit_transform(train_df[FEATURE_COLS])
    test_features = scaler.transform(test_df[FEATURE_COLS])
    
    # Save Scaler
    os.makedirs("models", exist_ok=True)
    joblib.dump(scaler, f"models/scaler_{symbol}_{model_type}.pkl")
    
    # 4. Create Sequences
    print("🔄 Creating sequences...")
    # Note: We must use the SCALED features to create sequences for the model
    
    def create_sequences_from_array(data, targets, seq_length):
        xs, ys = [], []
        for i in range(len(data) - seq_length):
            x = data[i:(i + seq_length)]
            y = targets[i + seq_length]
            xs.append(x)
            ys.append(y)
        return np.array(xs), np.array(ys)

    # Use the scaled features (train_features, test_features) and the raw targets
    X_train, y_train = create_sequences_from_array(train_features, train_df["Target"].values, SEQ_LENGTH)
    X_test, y_test = create_sequences_from_array(test_features, test_df["Target"].values, SEQ_LENGTH)

    print(f"   Train shape: {X_train.shape}, Test shape: {X_test.shape}")

    # 5. DataLoaders
    train_dataset = CryptoDataset(X_train, y_train)
    test_dataset = CryptoDataset(X_test, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # 6. Initialize Model
    input_dim = len(FEATURE_COLS)
    
    if model_type == "lstm":
        model = LSTMModel(input_dim=input_dim, hidden_dim=64, num_layers=2)
    elif model_type == "transformer":
        model = TransformerModel(input_dim=input_dim, d_model=64, nhead=4, num_layers=2)
    else:
        raise ValueError("Invalid model type")
        
    model.to(device)
    
    # 7. Training Loop
    criterion = nn.BCELoss() # Binary Classification
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    best_loss = float('inf')
    
    print("🏋️ Training...")
    for epoch in range(epochs):
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
            
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        train_loss /= len(train_loader)
        
        # Validation
        model.eval()
        val_loss = 0
        correct = 0
        total = 0
        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                val_loss += loss.item()
                
                predicted = (outputs > 0.5).float()
                total += y_batch.size(0)
                correct += (predicted == y_batch).sum().item()
        
        val_loss /= len(test_loader)
        acc = correct / total
        
        print(f"   Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {acc:.4f}")
        
        # Save Best Model
        if val_loss < best_loss:
            best_loss = val_loss
            torch.save(model.state_dict(), f"models/best_{model_type}_{symbol}.pth")
            
    print(f"✅ Training Complete. Best Val Loss: {best_loss:.4f}")
    print(f"💾 Model saved to models/best_{model_type}_{symbol}.pth")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTC-USD")
    parser.add_argument("--model", type=str, default="lstm", choices=["lstm", "transformer"])
    parser.add_argument("--epochs", type=int, default=10) # Default to 10 for quick test
    args = parser.parse_args()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_model(symbol=args.symbol, model_type=args.model, epochs=args.epochs, device=device)
