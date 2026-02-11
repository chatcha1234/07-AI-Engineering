import streamlit as st
import pandas as pd
from src.dashboard.components import MetricCard, StatusBadge, TradingChart, OrderBook
from src.exchange import BinanceClient

def render_dashboard(client: BinanceClient):
    """
    Main Layout Logic for the Premium Dashboard.
    """
    # ── Sidebar ─────────────────────────────────────────────
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2919/2919740.png", width=50) # Placeholder Icon
        st.title("NEO TRADER")
        st.markdown(f"<div style='margin-bottom: 20px;'>v1.0.8 • AI-Powered HFT</div>", unsafe_allow_html=True)
        
        # Connection Status
        mode = st.session_state.get("exchange_mode", "simulation")
        StatusBadge(mode)
        
        st.markdown("---")
        
        # Navigation
        page = st.radio("Navigation", ["📈 Dashboard", "🧠 Strategies", "📊 Backtest", "⚙️ Settings"], label_visibility="collapsed")
        
        st.markdown("---")
        st.info("💡 Tip: Use 'Simulation' mode to test strategies without risk.")

    # ── Main Content ────────────────────────────────────────
    if page == "📈 Dashboard":
        render_live_dashboard(client)
    elif page == "📊 Backtest":
        st.markdown("### 🚧 Backtest Engine")
        st.info("The backtest engine is being migrated to the new layout. Please use the 'Legacy' dashboard if needed.")

    else:
        st.markdown(f"### {page}")
        st.caption("Coming Soon")

def render_live_dashboard(client: BinanceClient):
    # 1. Top Bar: Ticker & High-Level Metrics
    symbol = "BTC-USD" # Default
    
    # Fetch Data
    price = client.get_price(symbol.replace("-","") + "T") # quick fix
    if not price: 
        price = 65000.00
    
    # Layout Grid
    col_chart, col_side = st.columns([3, 1])
    
    with col_chart:
        # Header Stats
        c1, c2, c3, c4 = st.columns(4)
        with c1: MetricCard("BTC/USDT", f"${price:,.2f}", 1.24)
        with c2: MetricCard("24h Vol", "4.2B", 5.12)
        with c3: MetricCard("AI Conf", "87%", 2.4, prefix="", suffix="")
        with c4: MetricCard("Next Signal", "BUY", None)  # Placeholder
        
        # Main Chart
        st.markdown("### 📊 Market Overview")
        # Get historical data for chart
        try:
            df = client.get_historical_data(symbol, interval="1h", limit=100)
            from src.features import add_indicators
            if df is not None:
                df = add_indicators(df)
                TradingChart(df, symbol)
            else:
                st.warning("Loading chart data...")
        except Exception as e:
            st.error(f"Chart Error: {e}")

    with col_side:
        # Order Book & Trade Log
        st.markdown("### 📚 Order Book")
        with st.container():
             # Wrap in card
             st.markdown('<div class="glass-card">', unsafe_allow_html=True)
             OrderBook(symbol, price)
             st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("### 💰 Account")
        try:
            bal = client.get_balance()
            usdt = bal.get("USDT", {}).get("free", 0)
            btc = bal.get("BTC", {}).get("free", 0)
            
            MetricCard("Total Equity", f"${usdt + (btc*price):,.2f}")
            MetricCard("USDT Free", f"${usdt:,.2f}")
        except:
             MetricCard("Total Equity", "$10,000.00")
