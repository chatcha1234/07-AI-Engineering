"""
exchange.py — Exchange Connector (Binance + Simulation Mode)

Supports:
  1. Simulation Mode — No API keys needed, uses real prices from yfinance
  2. Binance Testnet — Paper trading with Binance API
  3. Binance Live — Real money trading

Usage:
    # Simulation (default — no API keys needed)
    client = BinanceClient(mode="simulation")

    # Testnet (requires API keys)
    client = BinanceClient(mode="testnet")

    # Live (requires API keys, dangerous!)
    client = BinanceClient(mode="live")
"""
import os
import math
import logging
import random
from datetime import datetime
from typing import Optional, List
from src.stream_manager import StreamManager

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ══════════════════════════════════════════════════════════════
# Simulated Exchange — uses real prices, fake orders
# ══════════════════════════════════════════════════════════════

class SimulatedExchange:
    """
    Local paper-trading simulator.
    Uses yfinance for real-time prices,
    all orders are simulated locally.
    """

    # Mapping Binance symbols → yfinance tickers
    SYMBOL_MAP = {
        "BTCUSDT": "BTC-USD",
        "ETHUSDT": "ETH-USD",
        "BNBUSDT": "BNB-USD",
        "SOLUSDT": "SOL-USD",
        "XRPUSDT": "XRP-USD",
        "DOTUSDT": "DOT-USD",
        "ADAUSDT": "ADA-USD",
        "AVAXUSDT": "AVAX-USD",
    }

    def __init__(self, initial_usdt: float = 10_000.0):
        self.balances = {
            "USDT": {"free": initial_usdt, "locked": 0.0},
            "BTC": {"free": 0.0, "locked": 0.0},
            "ETH": {"free": 0.0, "locked": 0.0},
            "BNB": {"free": 0.0, "locked": 0.0},
        }
        self.orders = []
        self._order_counter = 1000
        self._price_cache = {}
        self._cache_time = None

    def _get_yf_price(self, symbol: str) -> float:
        """Fetch current price using yfinance."""
        import yfinance as yf

        ticker = self.SYMBOL_MAP.get(symbol, symbol)
        try:
            data = yf.Ticker(ticker)
            info = data.fast_info
            price = float(info.get("last_price", info.get("previous_close", 0)))
            if price > 0:
                return price
        except Exception:
            pass

        # Fallback: try download
        try:
            df = yf.download(ticker, period="1d", progress=False)
            if df.empty:
                return 0.0
            # Fix FutureWarning: Access scalar value directly
            return float(df["Close"].iloc[-1])
        except Exception:
            pass

        # Last resort: hardcoded reasonable default
        defaults = {
            "BTCUSDT": 97000, "ETHUSDT": 2600, "BNBUSDT": 630,
            "SOLUSDT": 200, "XRPUSDT": 2.5,
        }
        return defaults.get(symbol, 100.0)

        return self.client
    


    def get_price(self, symbol: str) -> float:
        """Get price with 1-minute cache."""
        now = datetime.now()
        if self._cache_time and (now - self._cache_time).seconds < 60:
            if symbol in self._price_cache:
                return self._price_cache[symbol]

        price = self._get_yf_price(symbol)
        self._price_cache[symbol] = price
        self._cache_time = now
        return price

    def get_all_tickers(self):
        result = []
        for sym in self.SYMBOL_MAP:
            try:
                p = self.get_price(sym)
                result.append({"symbol": sym, "price": str(p)})
            except Exception:
                pass
        return result

    def get_account(self):
        return {
            "balances": [
                {"asset": k, "free": str(v["free"]), "locked": str(v["locked"])}
                for k, v in self.balances.items()
            ]
        }

    def get_symbol_ticker(self, symbol: str):
        return {"symbol": symbol, "price": str(self.get_price(symbol))}

    def get_symbol_info(self, symbol: str):
        """Return simulated symbol info."""
        step_sizes = {
            "BTCUSDT": "0.00001", "ETHUSDT": "0.0001", "BNBUSDT": "0.001",
            "SOLUSDT": "0.01", "XRPUSDT": "0.1",
        }
        return {
            "symbol": symbol,
            "filters": [
                {"filterType": "LOT_SIZE", "stepSize": step_sizes.get(symbol, "0.001")},
            ],
        }

    def create_order(self, symbol: str, side: str, type: str, **kwargs):
        """Simulate a market order."""
        price = self.get_price(symbol)
        base_asset = symbol.replace("USDT", "")

        # Ensure asset exists in balances
        if base_asset not in self.balances:
            self.balances[base_asset] = {"free": 0.0, "locked": 0.0}

        quote_qty = kwargs.get("quoteOrderQty")
        quantity = kwargs.get("quantity")

        if side == "BUY":
            if quote_qty:
                quantity = quote_qty / price
                cost = quote_qty
            else:
                cost = quantity * price

            if self.balances["USDT"]["free"] < cost:
                raise Exception(f"Insufficient USDT balance. Have {self.balances['USDT']['free']:.2f}, need {cost:.2f}")

            self.balances["USDT"]["free"] -= cost
            self.balances[base_asset]["free"] += quantity

        elif side == "SELL":
            if quantity is None:
                raise Exception("Quantity required for sell")

            if self.balances.get(base_asset, {}).get("free", 0) < quantity:
                raise Exception(f"Insufficient {base_asset} balance")

            revenue = quantity * price
            self.balances[base_asset]["free"] -= quantity
            self.balances["USDT"]["free"] += revenue

        self._order_counter += 1
        order = {
            "orderId": self._order_counter,
            "symbol": symbol,
            "side": side,
            "type": type,
            "price": str(price),
            "origQty": str(quantity),
            "status": "FILLED",
            "time": int(datetime.now().timestamp() * 1000),
        }
        self.orders.append(order)
        return order

    def get_open_orders(self, **kwargs):
        return []  # Market orders fill instantly

    def get_my_trades(self, symbol: str = None, limit: int = 10):
        trades = self.orders
        if symbol:
            trades = [o for o in trades if o["symbol"] == symbol]
        return trades[-limit:]

    def get_klines(self, symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 100):
        """Fetch klines using yfinance."""
        import yfinance as yf

        ticker = self.SYMBOL_MAP.get(symbol, symbol)
        interval_map = {"1d": "1d", "1h": "1h", "4h": "1h", "15m": "15m"}
        yf_interval = interval_map.get(interval, "1d")

        if yf_interval == "1h":
            days = int(limit / 24) + 5
            if days <= 5: period = "5d"
            elif days <= 30: period = "1mo"
            elif days <= 90: period = "3mo"
            else: period = "1y"
        elif yf_interval == "15m":
             period = "1mo"
        else:
             period = "max" if limit > 300 else "1y"

        df = yf.download(ticker, period=period, interval=yf_interval, progress=False)

        # Flatten multi-level columns if present
        if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
            df.columns = df.columns.get_level_values(0)

        # Format as Binance-style klines
        result = []
        for idx, row in df.iterrows():
            ts = int(idx.timestamp() * 1000) if hasattr(idx, 'timestamp') else 0
            result.append([
                ts, str(row["Open"]), str(row["High"]), str(row["Low"]),
                str(row["Close"]), str(row.get("Volume", 0)),
                ts, "0", "0", "0", "0", "0",
            ])
        return result[-limit:]


# ══════════════════════════════════════════════════════════════
# BinanceClient — unified interface
# ══════════════════════════════════════════════════════════════

class BinanceClient:
    """
    Unified exchange connector.

    Modes:
      - "simulation": Local paper trading (no API keys needed)
      - "testnet": Binance Testnet (requires API keys)
      - "live": Binance Live (requires API keys)

    Args:
        mode:           "simulation", "testnet", or "live"
        api_key:        API key (testnet/live)
        api_secret:     API secret (testnet/live)
        max_position:   Max position size in USD
        max_daily_trades: Max trades per day
        initial_usdt:   Starting USDT for simulation mode
    """

    def __init__(
        self,
        mode: str = "simulation",
        testnet: bool = None,
        api_key: str = None,
        api_secret: str = None,
        max_position: float = None,
        max_daily_trades: int = None,
        initial_usdt: float = 10_000.0,
        use_stream: bool = True,
    ):
        # Handle legacy testnet=True/False parameter
        if testnet is not None:
            mode = "testnet" if testnet else "live"

        self.mode = mode
        self.testnet = mode in ("simulation", "testnet")
        self.simulation = mode == "simulation"
        self.daily_trades = 0
        self.daily_trades_date = datetime.now().date()
        self.trade_log = []

        # Safety limits
        self.max_position = max_position or float(os.getenv("MAX_POSITION_USD", "50"))
        self.max_daily_trades = max_daily_trades or int(os.getenv("MAX_DAILY_TRADES", "10"))
        self.max_daily_loss_pct = float(os.getenv("MAX_DAILY_LOSS_PCT", "5.0"))
        
        # Initial equity tracking for circuit breaker
        self.initial_equity_usd = None
        self._last_equity_check = None

        # ── API Key Setup ──
        if mode == "testnet":
            self.api_key = api_key or os.getenv("BINANCE_TESTNET_API_KEY", "")
            self.api_secret = api_secret or os.getenv("BINANCE_TESTNET_SECRET", "")
        else:
            self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
            self.api_secret = api_secret or os.getenv("BINANCE_SECRET", "")

        # ── Client Setup ──
        if self.simulation:
            # Simulation Mode
            self.client = SimulatedExchange(initial_usdt=initial_usdt)
            logger.info(f"🎮 SIMULATION mode — ${initial_usdt:,.0f} starting balance")
            logger.info(f"Safety: max_position=${self.max_position}, max_daily_trades={self.max_daily_trades}")
        else:
            # Binance API Mode
            if self.api_key and self.api_secret:
                from binance.client import Client
                self.client = Client(self.api_key, self.api_secret, testnet=(mode == "testnet"))
                label = "🧪 TESTNET" if mode == "testnet" else "🔴 LIVE"
                logger.info(f"Binance client initialized — {label}")
            else:
                self.client = None
                logger.warning("No API keys. Use mode='simulation' for paper trading.")

        # ── WebSocket Manager ──
        self.stream_manager = None
        if use_stream:
            try:
                # Common symbols to pre-subscribe
                common_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
                
                # Use Mainnet stream for Simulation (real prices)
                # Use Testnet stream for Testnet (match execution)
                stream_testnet = self.testnet
                if self.simulation:
                    stream_testnet = False
                
                self.stream_manager = StreamManager(
                    api_key=self.api_key, 
                    api_secret=self.api_secret, 
                    testnet=stream_testnet
                )
                self.stream_manager.subscribe(common_symbols)
                label = "Real-Time (Mainnet)" if not stream_testnet else "Testnet Stream"
                logger.info(f"🌊 WebSocket Manager started [{label}] (subscribed to {len(common_symbols)} symbols)")
            except Exception as e:
                logger.warning(f"Failed to start WebSocket Manager: {e}")

        
        # Set initial equity on startup (lazy load on first check if needed)
        try:
            self.initial_equity_usd = self.get_total_equity_usd()
            logger.info(f"💰 Initial Equity: ${self.initial_equity_usd:,.2f} (Loss limit: {self.max_daily_loss_pct}%)")
        except Exception as e:
            logger.warning(f"Could not fetch initial equity: {e}")
            self.initial_equity_usd = 0.0

    def status(self) -> dict:
        """Return current connection status and balance summary."""
        try:
            usdt_bal = self.get_usdt_balance()
            equity = self.get_total_equity_usd()
            return {
                "status": "connected",
                "mode": self.mode,
                "usdt_balance": round(usdt_bal, 2),
                "total_equity": round(equity, 2),
                "connected": True
            }
        except Exception as e:
            return {
                "status": "error",
                "mode": self.mode,
                "error": str(e),
                "connected": False
            }

    def _check_client(self):
        if self.client is None:
            raise ConnectionError(
                "Not connected. Set API keys in .env or use mode='simulation'."
            )

    def _reset_daily_counter(self):
        today = datetime.now().date()
        if today != self.daily_trades_date:
            self.daily_trades = 0
            self.daily_trades_date = today

    def _check_safety(self, quantity_usd: float):
        self._reset_daily_counter()
        if quantity_usd > self.max_position:
            raise ValueError(
                f"🛑 Order ${quantity_usd:.2f} exceeds limit ${self.max_position:.2f}. "
                f"Adjust MAX_POSITION_USD in .env."
            )
        if self.daily_trades >= self.max_daily_trades:
            raise ValueError(f"🛑 Daily trade limit ({self.max_daily_trades}) reached.")

        # Circuit Breaker: Daily Loss Limit
        if self.initial_equity_usd and self.initial_equity_usd > 0:
            current_equity = self.get_total_equity_usd()
            loss = self.initial_equity_usd - current_equity
            loss_pct = (loss / self.initial_equity_usd) * 100
            
            if loss_pct > self.max_daily_loss_pct:
                 raise ValueError(
                     f"🛑 CIRCUIT BREAKER TRIGGERED: Daily loss {loss_pct:.2f}% "
                     f"exceeds limit {self.max_daily_loss_pct}%. Trading halted."
                 )

    # ── Account ───────────────────────────────────────────

    def get_balance(self, asset: str = None) -> dict:
        self._check_client()
        account = self.client.get_account()
        balances = {}
        for b in account["balances"]:
            free = float(b["free"])
            locked = float(b["locked"])
            if free > 0 or locked > 0:
                balances[b["asset"]] = {"free": free, "locked": locked}
        if asset:
            return {asset: balances.get(asset, {"free": 0.0, "locked": 0.0})}
        return balances

    def get_usdt_balance(self) -> float:
        bal = self.get_balance("USDT")
        return bal.get("USDT", {}).get("free", 0.0)

    def get_total_equity_usd(self) -> float:
        """Calculate total account value in USD (USDT + crypto assets)."""
        balances = self.get_balance()
        total_usd = 0.0
        
        for asset, bal in balances.items():
            amount = bal["free"] + bal["locked"]
            if amount <= 0:
                continue
                
            if asset == "USDT":
                total_usd += amount
            else:
                try:
                    price = self.get_price(f"{asset}USDT")
                    total_usd += amount * price
                except Exception:
                    pass
        return total_usd

    # ── Market Data ───────────────────────────────────────

    def get_historical_data(self, symbol: str, interval: str = "1h", limit: int = 100):
        """Fetch klines and return as DataFrame for DL strategies."""
        import pandas as pd
        
        # Fetch klines (works for both Simulation and Live/Testnet via existing get_klines)
        klines = self.get_klines(symbol, interval=interval, limit=limit)
        
        if klines is None or len(klines) == 0:
            return None
            
        df = pd.DataFrame(klines, columns=[
            "Open Time", "Open", "High", "Low", "Close", "Volume",
            "Close Time", "Quote Asset Volume", "Number of Trades",
            "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
        ])
        
        # Convert to numeric
        numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        # Set Index
        df["Open Time"] = pd.to_datetime(df["Open Time"], unit="ms")
        df.set_index("Open Time", inplace=True)
        
        return df[["Open", "High", "Low", "Close", "Volume"]]

    def get_price(self, symbol: str = "BTCUSDT") -> float:
        """Get current price, preferring WebSocket cache if available."""
        # 1. Check WebSocket Cache
        if self.stream_manager:
            price = self.stream_manager.get_price(symbol)
            if price:
                return price
            # If not in cache, fallback but maybe subscribe for future?
            # self.stream_manager.subscribe([symbol]) 
        
        # 2. Fallback to REST API / Simulation
        self._check_client()
        if self.simulation:
            return self.client.get_price(symbol)
            
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    def stop(self):
        """Stop background threads."""
        if self.stream_manager:
            self.stream_manager.stop()

    def get_prices(self, symbols: list = None) -> dict:
        self._check_client()
        tickers = self.client.get_all_tickers()
        prices = {t["symbol"]: float(t["price"]) for t in tickers}
        if symbols:
            return {s: prices.get(s, 0.0) for s in symbols}
        return prices

    def get_klines(self, symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 100):
        self._check_client()
        import pandas as pd

        klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)

        df = pd.DataFrame(klines, columns=[
            "timestamp", "Open", "High", "Low", "Close", "Volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms")
        df.set_index("timestamp", inplace=True)

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = df[col].astype(float)

        return df[["Open", "High", "Low", "Close", "Volume"]]

    # ── Orders ────────────────────────────────────────────

    def place_market_order(self, symbol, side, quantity=None, quote_quantity=None):
        self._check_client()
        side = side.upper()

        price = self.get_price(symbol)
        usd_value = quote_quantity if quote_quantity else (quantity * price if quantity else 0)
        if usd_value == 0:
            raise ValueError("Specify quantity or quote_quantity")

        self._check_safety(usd_value)

        kwargs = {}
        if quote_quantity:
            kwargs["quoteOrderQty"] = quote_quantity
        else:
            kwargs["quantity"] = quantity

        order = self.client.create_order(symbol=symbol, side=side, type="MARKET", **kwargs)
        self.daily_trades += 1

        trade_info = {
            "time": datetime.now().isoformat(),
            "symbol": symbol,
            "side": side,
            "quantity": quantity or (quote_quantity / price if quote_quantity else 0),
            "price": price,
            "usd_value": usd_value,
            "order_id": order.get("orderId"),
            "status": order.get("status"),
            "mode": self.mode,
        }
        self.trade_log.append(trade_info)

        label = "SIM" if self.simulation else ("TESTNET" if self.testnet else "LIVE")
        logger.info(f"✅ [{label}] {side} {symbol} — ${usd_value:.2f} @ ${price:,.2f}")
        return order

    def buy(self, symbol="BTCUSDT", usd_amount=10.0):
        return self.place_market_order(symbol, "BUY", quote_quantity=usd_amount)

    def sell(self, symbol="BTCUSDT", quantity=None):
        return self.place_market_order(symbol, "SELL", quantity=quantity)

    def get_open_orders(self, symbol=None):
        self._check_client()
        return self.client.get_open_orders(symbol=symbol) if symbol else self.client.get_open_orders()

    def get_recent_trades(self, symbol="BTCUSDT", limit=10):
        self._check_client()
        return self.client.get_my_trades(symbol=symbol, limit=limit)

    # ── Status ────────────────────────────────────────────

    def status(self) -> dict:
        info = {
            "connected": self.client is not None,
            "mode": self.mode.upper(),
            "simulation": self.simulation,
            "daily_trades": self.daily_trades,
            "max_daily_trades": self.max_daily_trades,
            "max_position_usd": self.max_position,
        }
        if self.client:
            try:
                info["usdt_balance"] = self.get_usdt_balance()
                info["btc_price"] = self.get_price("BTCUSDT")
            except Exception:
                pass
        return info


if __name__ == "__main__":
    # Quick test — Simulation mode (no API keys needed!)
    client = BinanceClient(mode="simulation")
    print("\n📊 Status:", client.status())

    print("\n💰 Balances:")
    for asset, bal in client.get_balance().items():
        if bal["free"] > 0:
            print(f"  {asset}: {bal['free']:.8g}")

    print(f"\n📈 BTC Price: ${client.get_price('BTCUSDT'):,.2f}")
    print(f"📈 ETH Price: ${client.get_price('ETHUSDT'):,.2f}")

    # Test buy
    print("\n🛒 Buying $10 of BTC...")
    order = client.buy("BTCUSDT", usd_amount=10)
    print(f"  Order: {order['orderId']} — {order['status']}")

    print("\n💰 Updated Balances:")
    for asset, bal in client.get_balance().items():
        if bal["free"] > 0:
            print(f"  {asset}: {bal['free']:.8g}")
