import time
import signal
import sys
import logging
import argparse
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

from src.exchange import BinanceClient
from src.features import add_indicators
from src.strategy_dl import DLStrategy
from src.notification import NotificationService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("trading.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("LiveTrader")

class LiveTrader:
    def __init__(self, symbol="BTC-USD", strategy="lstm", interval="1h", mode="simulation", limit=100):
        self.symbol = symbol
        self.strategy_name = strategy
        self.interval = interval
        self.mode = mode
        self.running = True
        
        # Notification Service
        self.notifier = NotificationService()
        
        # 1. Initialize Client
        # Force use_stream=True for real-time prices even in simulation
        self.client = BinanceClient(mode=mode, use_stream=True)
        
        # 2. Initialize Strategy
        if strategy in ["lstm", "transformer"]:
            try:
                self.strategy = DLStrategy(model_type=strategy, symbol=symbol)
                logger.info(f"🧠 Strategy loaded: {strategy.upper()}")
            except FileNotFoundError:
                msg = f"❌ Model for {strategy} not found. Train it first!"
                logger.error(msg)
                self.notifier.send(msg, level="ERROR")
                sys.exit(1)
        else:
            msg = f"❌ Strategy {strategy} not implemented or model missing."
            logger.error(msg)
            self.notifier.send(msg, level="ERROR")
            sys.exit(1)
            
        # 3. Risk Management & State
        self.max_position_size = 0.1 # 10% of equity
        self.stop_loss_pct = 0.02    # 2%
        self.position = 0 # 0=Flat, 1=Long
        self.entry_price = 0.0
        
        # Handle Graceful Shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        msg = f"\n🛑 LiveTrader Shutdown Requested ({self.symbol})"
        logger.info(msg)
        self.notifier.send(msg, level="WARNING")
        self.running = False
        if self.client:
            self.client.stop()
        sys.exit(0)

    def run(self):
        initial_equity = self.client.initial_equity_usd if hasattr(self.client, 'initial_equity_usd') else 0
        start_msg = (
            f"🚀 Starting LiveTrader [{self.mode.upper()}]\n"
            f"   Symbol: {self.symbol}\n"
            f"   Strategy: {self.strategy_name}\n"
            f"   Interval: {self.interval}\n"
            f"   Equity: ${initial_equity:,.2f}"
        )
        logger.info(start_msg)
        self.notifier.send(start_msg, level="INFO")
        
        # Subscribe to stream
        if self.client.stream_manager:
            ws_symbol = self.symbol.replace("-", "").replace("/", "")
            self.client.stream_manager.subscribe([ws_symbol])
            logger.info(f"🌊 Subscribed to {ws_symbol} stream.")
            
        while self.running:
            try:
                # 1. Fetch Data
                # limit=500 ensures enough for sequence (60) + indicators (50) + buffer
                df = self.client.get_historical_data(self.symbol, interval=self.interval, limit=500)
                
                if df is None or len(df) < 150:
                    logger.warning(f"⚠️ Not enough data (got {len(df) if df is not None else 0}, need >150). Waiting...")
                    time.sleep(10)
                    continue
                    
                # 2. Add Indicators
                df = add_indicators(df)
                df.dropna(inplace=True)
                
                if df.empty:
                    logger.warning("⚠️ Data empty after indicators. Waiting...")
                    time.sleep(10)
                    continue

                # Live Price check
                live_price = self.client.get_price(self.symbol)
                
                # 3. Get Signal
                prob = self.strategy.predict(df)
                
                if prob is None:
                    logger.warning("⚠️ Prediction returned None")
                    continue
                    
                signal_label = "BUY" if prob > 0.5 else "SELL"
                confidence = prob if prob > 0.5 else 1 - prob
                
                log_msg = f"🔮 Signal: {signal_label} (Prob: {prob:.4f}) | Price: ${live_price:,.2f}"
                logger.info(log_msg)
                
                # 4. Execute Trade (Simple Logic)
                # Buy if prob > 0.6 and Flat
                # Sell if prob < 0.4 and Long
                
                buy_threshold = 0.6
                sell_threshold = 0.4
                
                if signal_label == "BUY" and prob > buy_threshold:
                    if self.position == 0:
                        # LONG
                        amount_usd = 1000 # Fixed amount for simulation
                        self.client.buy(self.symbol.replace("-", ""), usd_amount=amount_usd)
                        self.position = 1
                        self.entry_price = live_price
                        
                        trade_msg = f"🟢 BUY Executed {self.symbol} @ ${live_price:,.2f}"
                        logger.info(trade_msg)
                        self.notifier.send(trade_msg, level="SUCCESS")
                        
                elif signal_label == "SELL" and prob < sell_threshold: # Wait, prob < 0.4 means SELL signal is stronger (prob is P(Up))? 
                    # If prob is P(Up), then Low prob = Down.
                    # Yes, prob < 0.4 is bearish.
                    
                    if self.position == 1:
                        # CLOSE LONG
                        self.client.sell(self.symbol.replace("-", ""), quantity=None) # Sell all
                        self.position = 0
                        
                        pnl = (live_price - self.entry_price) / self.entry_price * 100
                        trade_msg = f"🔴 SELL Executed {self.symbol} @ ${live_price:,.2f} (PnL: {pnl:.2f}%)"
                        logger.info(trade_msg)
                        self.notifier.send(trade_msg, level="SUCCESS" if pnl > 0 else "WARNING")

                # 5. Wait for next Candle
                # Sleep 60s
                logger.info("⏳ Sleeping for 60s...")
                time.sleep(60)
                
            except Exception as e:
                err_msg = f"❌ Error in loop: {e}"
                logger.error(err_msg)
                self.notifier.send(err_msg, level="ERROR")
                time.sleep(10)

if __name__ == "__main__":
    load_dotenv()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTC-USD")
    parser.add_argument("--strategy", type=str, default="lstm")
    parser.add_argument("--interval", type=str, default="1h")
    parser.add_argument("--mode", type=str, default="simulation")
    args = parser.parse_args()
    
    trader = LiveTrader(
        symbol=args.symbol,
        strategy=args.strategy,
        interval=args.interval,
        mode=args.mode
    )
    try:
        trader.run()
    except KeyboardInterrupt:
        trader.shutdown(None, None)
