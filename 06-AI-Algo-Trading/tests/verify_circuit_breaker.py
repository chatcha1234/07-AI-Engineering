import sys
import os
import time

# Add root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Mock FastMCP ───────────────────────────────────────────
# We mock FastMCP to bypass the decorator and access functions directly
class FakeMCP:
    def __init__(self, *args, **kwargs): pass
    def tool(self, *args, **kwargs):
        def decorator(f):
            return f
        return decorator
    def resource(self, *args, **kwargs):
        def decorator(f):
            return f
        return decorator
    def run(self): pass

# Inject fake module
import types
fake_fastmcp = types.ModuleType("fastmcp")
fake_fastmcp.FastMCP = FakeMCP
sys.modules["fastmcp"] = fake_fastmcp
# ───────────────────────────────────────────────────────────

from src.exchange import BinanceClient

try:
    import mcp_server.trading_mcp_server as server_module
except ImportError as e:
    print(f"❌ Could not import mcp_server.trading_mcp_server: {e}")
    sys.exit(1)

def main():
    print("🚀 Verifying Circuit Breaker Safety Feature...")
    
    # Initialize client in Simulation mode
    client = BinanceClient(mode="simulation", initial_usdt=10000.0)
    
    # Ensure limit is set
    client.max_daily_loss_pct = 5.0
    print(f"💰 Initial Equity: ${client.initial_equity_usd:,.2f}")
    print(f"🛑 Max Daily Loss: {client.max_daily_loss_pct}%")
    
    # Inject into MCP server module
    server_module._client = client
    server_module._client_mode = "simulation"
    
    # Check initial status via tool
    # Now check_safety should be the raw function
    status = server_module.check_safety()
    print(f"\nPhase 1: Initial Check")
    print(f"  Tool Status: Loss={status.get('current_loss_pct', 'N/A')}%, Triggered={status.get('circuit_breaker_triggered', 'N/A')}")
    
    if status.get('circuit_breaker_triggered'):
        print("❌ FAILED: Circuit breaker triggered on start!")
        return

    # Simulate catastrophic loss
    # Lose $600 (6% of $10,000)
    print("\n📉 Simulating $600 loss (6%)...")
    
    # Hack simulation internals
    if client.simulation:
        client.client.balances["USDT"]["free"] -= 600.0
    
    current_equity = client.get_total_equity_usd()
    loss = client.initial_equity_usd - current_equity
    loss_pct = (loss / client.initial_equity_usd) * 100
    
    print(f"💰 Current Equity: ${current_equity:,.2f}")
    print(f"📉 Calculated Loss: {loss_pct:.2f}%")
    
    # Check again via tool
    print("\nPhase 2: Post-Loss Check")
    status = server_module.check_safety()
    print(f"  Tool Status: Loss={status.get('current_loss_pct')}%, Triggered={status.get('circuit_breaker_triggered')}")
    
    if not status.get('circuit_breaker_triggered'):
        print("❌ FAILED: Circuit breaker DID NOT trigger!")
        return
        
    if status.get('can_trade'):
        print("❌ FAILED: Tool says 'can_trade=True' despite trigger!")
        return

    # Try to execute a trade
    print("\nPhase 3: Attempting Trade (Should Fail)")
    result = server_module.buy_crypto(symbol="BTCUSDT", amount_usd=10.0)
    if result.get("success"):
        print("❌ FAILED: Trade succeeded despite circuit breaker!")
    else:
        print(f"✅ Trade blocked: {result.get('error')}")

    print("\n✅ VERIFICATION COMPLETE: Circuit Breaker Works!")

if __name__ == "__main__":
    main()
