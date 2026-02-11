# 📉 AI Algorithmic Trading Project

This project focuses on building and evaluating trading algorithms using Artificial Intelligence and Machine Learning techniques.

## 📂 Project Structure

- `data/`: Raw and processed market data.
- `notebooks/`: Exploratory Data Analysis (EDA) and experimental models.
- `src/`: Core source code.
  - `data_loader.py`: Scripts for fetching market data.
  - `features.py`: Feature engineering and technical indicators.
  - `models.py`: AI model architectures.
- `strategies/`: Trading strategy implementations.
- `backtest/`: Backtesting engine and evaluation notebooks.

## 🚀 Getting Started

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Fetch Data**:
   Run the data loader to get historical data.

3. **Develop Strategy**:
   Experiment in `notebooks/`.

## 🛠 Tech Stack

- **Data**: `yfinance`, `pandas`, `numpy`
- **Indicators**: `pandas-ta`
- **AI/ML**: `scikit-learn`, `pytorch`
- **Backtesting**: `vectorbt` or `Backtrader`
