import logging
import time
from typing import Dict, List, Optional
from binance import ThreadedWebsocketManager
# from binance.exceptions import BinanceAPIException # Not needed for basic stream

logger = logging.getLogger(__name__)

class StreamManager:
    """
    Manages WebSocket connections to Binance for real-time price updates.
    Uses ThreadedWebsocketManager from python-binance.
    """
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.twm = ThreadedWebsocketManager(api_key=self.api_key, api_secret=self.api_secret, testnet=self.testnet)
        self.latest_prices: Dict[str, float] = {}
        self.active_streams: List[str] = []
        self._is_running = False

    def start(self):
        """Start the WebSocket manager."""
        if self._is_running:
            return
        
        logger.info(f"Starting WebSocket Manager (Testnet: {self.testnet})...")
        self.twm.start()
        self._is_running = True

    def stop(self):
        """Stop the WebSocket manager."""
        if not self._is_running:
            return
            
        logger.info("Stopping WebSocket Manager...")
        self.twm.stop()
        self._is_running = False

    def subscribe(self, symbols: List[str]):
        """
        Subscribe to symbol ticker streams for the given symbols.
        Args:
            symbols: List of symbols (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        if not self._is_running:
            self.start()

        for symbol in symbols:
            stream_name = self.twm.start_symbol_ticker_socket(
                callback=self._handle_socket_message,
                symbol=symbol
            )
            self.active_streams.append(stream_name)
            logger.info(f"Subscribed to {symbol} ticker stream: {stream_name}")

    def _handle_socket_message(self, msg: Dict):
        """
        Callback for handling incoming WebSocket messages.
        Updates the local price cache.
        Example msg: {'e': '24hrTicker', 'E': 167..., 's': 'BTCUSDT', 'c': '69000.00', ...}
        """
        if msg.get('e') == 'error':
            logger.error(f"WebSocket Error: {msg}")
            return

        try:
            # Check message type. symbol_ticker returns '24hrTicker' event type?
            # Actually start_symbol_ticker_socket usually returns a 24hr ticker object
            # format: https://binance-docs.github.io/apidocs/spot/en/#24hr-ticker-price-change-statistics
            
            # Note: python-binance might wrap it.
            # 'c' is the last price.
            if 'c' in msg and 's' in msg:
                symbol = msg['s']
                price = float(msg['c'])
                self.latest_prices[symbol] = price
                # logger.debug(f"Stream update: {symbol} = {price}")
                
        except Exception as e:
            logger.error(f"Error parsing socket message: {e}")

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest cached price for a symbol.
        Returns None if price is not available in cache.
        """
        return self.latest_prices.get(symbol)

    def get_all_prices(self) -> Dict[str, float]:
        """Get a copy of all cached prices."""
        return self.latest_prices.copy()
