"""
orchestrator.py — Multi-Agent Trading Orchestrator

Coordinates specialized agents through the MCP server.
Routes tasks to the right agent and manages the workflow.

Usage:
    python mcp_server/orchestrator.py
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.agent_prompts import AGENT_PROMPTS, ORCHESTRATOR_PROMPT


class TradingOrchestrator:
    """
    Coordinates 4 trading agents through a structured workflow.
    
    Agents:
        data_agent      → Market data + indicators
        strategy_agent   → Signal generation + backtesting
        execution_agent  → Order execution + safety
        monitor_agent    → Portfolio tracking + risk
    """

    def __init__(self):
        self.action_log = []
        self.current_state = {
            "last_data": None,
            "last_signal": None,
            "last_trade": None,
            "portfolio": None,
        }

    def log_action(self, agent: str, action: str, result: dict):
        """Log an agent action for audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "action": action,
            "result": result,
        }
        self.action_log.append(entry)
        emoji = AGENT_PROMPTS.get(agent, {}).get("emoji", "🔧")
        print(f"  {emoji} [{agent}] {action}")

    # ── Workflow Steps ──────────────────────────────────

    def step_1_fetch_data(self, symbol: str = "BTCUSDT") -> dict:
        """Step 1: Data Agent — Fetch current market data."""
        from mcp_server.trading_mcp_server import get_price, get_multiple_prices

        print(f"\n📊 Step 1: Fetching market data for {symbol}...")
        
        result = get_price(symbol)
        all_prices = get_multiple_prices("BTCUSDT,ETHUSDT,BNBUSDT")
        
        data = {
            "primary": result,
            "all_prices": all_prices,
        }
        self.current_state["last_data"] = data
        self.log_action("data_agent", f"get_price({symbol})", result)
        return data

    def step_2_analyze_strategy(
        self,
        symbol: str = "BTC-USD",
        strategy: str = "sma",
        start: str = "2024-01-01",
        end: str = "2025-01-01",
    ) -> dict:
        """Step 2: Strategy Agent — Generate trading signal."""
        from mcp_server.trading_mcp_server import get_signal

        print(f"\n🧠 Step 2: Running {strategy} strategy on {symbol}...")
        
        result = get_signal(symbol, strategy, start, end)
        self.current_state["last_signal"] = result
        self.log_action("strategy_agent", f"get_signal({symbol}, {strategy})", result)
        return result

    def step_3_execute_trade(
        self,
        symbol: str = "BTCUSDT",
        signal: int = 0,
        amount_usd: float = 10.0,
    ) -> dict:
        """Step 3: Execution Agent — Execute trade based on signal."""
        from mcp_server.trading_mcp_server import check_safety, buy_crypto, sell_crypto

        print(f"\n🎯 Step 3: Executing trade — signal={signal}...")
        
        # Always check safety first
        safety = check_safety()
        self.log_action("execution_agent", "check_safety()", safety)
        
        if not safety.get("can_trade"):
            result = {"skipped": True, "reason": "Safety limit reached"}
            self.log_action("execution_agent", "SKIPPED", result)
            return result

        if signal == 1:
            result = buy_crypto(symbol, amount_usd)
            self.log_action("execution_agent", f"buy({symbol}, ${amount_usd})", result)
        elif signal == 0:
            result = sell_crypto(symbol, sell_all=True)
            self.log_action("execution_agent", f"sell_all({symbol})", result)
        else:
            result = {"skipped": True, "reason": "No signal change"}
            self.log_action("execution_agent", "HOLD", result)

        self.current_state["last_trade"] = result
        return result

    def step_4_monitor(self) -> dict:
        """Step 4: Monitor Agent — Check portfolio and P&L."""
        from mcp_server.trading_mcp_server import get_portfolio, get_pnl

        print(f"\n📋 Step 4: Monitoring portfolio...")
        
        portfolio = get_portfolio()
        pnl = get_pnl()
        
        result = {
            "portfolio": portfolio,
            "pnl": pnl,
        }
        self.current_state["portfolio"] = result
        self.log_action("monitor_agent", "get_portfolio()", portfolio)
        self.log_action("monitor_agent", "get_pnl()", pnl)
        return result

    # ── Full Pipeline ──────────────────────────────────

    def run_full_cycle(
        self,
        symbol_binance: str = "BTCUSDT",
        symbol_yf: str = "BTC-USD",
        strategy: str = "sma",
        amount_usd: float = 10.0,
        start: str = "2024-01-01",
        end: str = "2025-01-01",
    ) -> dict:
        """
        Run one complete trading cycle:
        Data → Strategy → Execution → Monitor
        """
        print("=" * 60)
        print(f"  🔄 Trading Cycle — {symbol_binance} / {strategy}")
        print("=" * 60)

        # Step 1: Data
        data = self.step_1_fetch_data(symbol_binance)
        
        # Step 2: Strategy
        signal_result = self.step_2_analyze_strategy(symbol_yf, strategy, start, end)
        signal = signal_result.get("signal", -1)
        
        # Step 3: Execute (only if signal is actionable)
        if signal in (0, 1):
            trade = self.step_3_execute_trade(symbol_binance, signal, amount_usd)
        else:
            trade = {"skipped": True, "reason": "No valid signal"}
            print(f"\n🎯 Step 3: SKIP — no actionable signal")

        # Step 4: Monitor
        monitor = self.step_4_monitor()

        print(f"\n{'=' * 60}")
        print(f"  ✅ Cycle Complete")
        print(f"     Signal: {signal_result.get('signal_label', 'N/A')}")
        pnl_data = monitor.get("pnl", {})
        if "pnl_usd" in pnl_data:
            print(f"     P&L: ${pnl_data['pnl_usd']:+.2f} ({pnl_data['pnl_pct']:+.2f}%)")
        print(f"     Portfolio: ${monitor['portfolio']['total_usd_value']:,.2f}")
        print(f"{'=' * 60}\n")

        return {
            "data": data,
            "signal": signal_result,
            "trade": trade,
            "portfolio": monitor,
            "action_log": self.action_log,
        }

    def print_action_log(self):
        """Print the full action log."""
        print(f"\n📜 Action Log ({len(self.action_log)} entries)")
        print("-" * 50)
        for entry in self.action_log:
            emoji = AGENT_PROMPTS.get(entry["agent"], {}).get("emoji", "🔧")
            print(f"  {entry['timestamp'][:19]} {emoji} {entry['action']}")


# ── CLI Entry Point ──────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Trading Orchestrator")
    parser.add_argument("--symbol", default="BTCUSDT", help="Binance symbol")
    parser.add_argument("--yf-symbol", default="BTC-USD", help="Yahoo Finance symbol")
    parser.add_argument("--strategy", default="sma", choices=["sma", "rsi", "random_forest", "xgboost"])
    parser.add_argument("--amount", type=float, default=10.0, help="Trade amount (USD)")
    parser.add_argument("--start", default="2024-01-01", help="Data start date")
    parser.add_argument("--end", default="2025-01-01", help="Data end date")
    args = parser.parse_args()

    orchestrator = TradingOrchestrator()
    result = orchestrator.run_full_cycle(
        symbol_binance=args.symbol,
        symbol_yf=args.yf_symbol,
        strategy=args.strategy,
        amount_usd=args.amount,
        start=args.start,
        end=args.end,
    )
    orchestrator.print_action_log()


if __name__ == "__main__":
    main()
