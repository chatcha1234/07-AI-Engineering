"""
app.py — AI Algo Trading Dashboard (Streamlit)

Run:  streamlit run app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from src.features import prepare_features
from strategies.sma_crossover import generate_signals as sma_signals
from strategies.rsi_mean_reversion import generate_signals as rsi_signals
from strategies.ml_strategy import generate_signals as ml_signals
from backtest.engine import run_backtest, print_metrics

# ── Page Config ────────────────────────────────────────────
st.set_page_config(
    page_title="AI Algo Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .main-header p {
        color: #a8a8d8;
        font-size: 1rem;
    }
    
    .metric-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1.4rem;
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); }
    .metric-card .label {
        color: #8888aa;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0.3rem 0;
    }
    .positive { color: #00e676; }
    .negative { color: #ff5252; }
    .neutral  { color: #64b5f6; }
    
    .strategy-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    .badge-sma      { background: rgba(33, 150, 243, 0.2); color: #42a5f5; border: 1px solid rgba(33, 150, 243, 0.3); }
    .badge-rsi      { background: rgba(156, 39, 176, 0.2); color: #ba68c8; border: 1px solid rgba(156, 39, 176, 0.3); }
    .badge-rf       { background: rgba(76, 175, 80, 0.2);  color: #66bb6a; border: 1px solid rgba(76, 175, 80, 0.3); }
    .badge-xgb      { background: rgba(255, 152, 0, 0.2);  color: #ffa726; border: 1px solid rgba(255, 152, 0, 0.3); }
    
    .comparison-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        margin: 1rem 0;
    }
    .comparison-table th {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        color: #8888cc;
        padding: 0.8rem 1rem;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .comparison-table td {
        padding: 0.8rem 1rem;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        font-size: 0.95rem;
    }
    .comparison-table tr:hover td { background: rgba(255,255,255,0.03); }
    
    .winner-row { background: rgba(0, 230, 118, 0.08) !important; }
    
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #1a1a2e);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
    }
    
    .live-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-connected {
        background: rgba(0,230,118,0.15);
        color: #00e676;
        border: 1px solid rgba(0,230,118,0.3);
    }
    .status-disconnected {
        background: rgba(255,82,82,0.15);
        color: #ff5252;
        border: 1px solid rgba(255,82,82,0.3);
    }
    .status-testnet {
        background: rgba(255,193,7,0.15);
        color: #ffc107;
        border: 1px solid rgba(255,193,7,0.3);
    }
    
    .balance-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 14px;
        padding: 1.5rem;
        text-align: center;
    }
    .balance-card .asset-name {
        color: #8888aa;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .balance-card .asset-value {
        font-size: 2rem;
        font-weight: 700;
        color: #00d2ff;
        margin: 0.3rem 0;
    }
    .balance-card .asset-usd {
        color: #66bb6a;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📈 AI Algo Trading Dashboard</h1>
    <p>Feature Engineering • Strategy Backtesting • ML Signal Prediction</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar Controls ───────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")
    
    symbol = st.text_input("🪙 Symbol", value="BTC-USD", help="e.g. BTC-USD, ETH-USD, AAPL, TSLA")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 Start", value=pd.Timestamp("2022-01-01"))
    with col2:
        end_date = st.date_input("📅 End", value=pd.Timestamp("2024-01-01"))
    
    init_cash = st.number_input("💰 Initial Cash ($)", value=10_000, step=1000, min_value=100)
    fees = st.slider("📊 Trading Fees (%)", min_value=0.0, max_value=1.0, value=0.1, step=0.05) / 100
    
    st.markdown("---")
    st.markdown("### 🎯 Strategies")
    run_sma = st.checkbox("SMA Crossover (20/50)", value=True)
    run_rsi = st.checkbox("RSI Mean Reversion", value=True)
    run_rf = st.checkbox("ML — Random Forest", value=True)
    run_xgb = st.checkbox("ML — XGBoost", value=True)
    
    st.markdown("---")
    run_button = st.button("🚀 Run Backtest", use_container_width=True, type="primary")


# ── Helper Functions ───────────────────────────────────────
def get_color_class(value, invert=False):
    if invert:
        return "positive" if value <= 0 else "negative"
    return "positive" if value > 0 else "negative"


def create_metric_card(label, value, fmt=".2f", suffix="%", invert=False):
    color_class = get_color_class(value, invert)
    return f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value {color_class}">{value:{fmt}}{suffix}</div>
    </div>
    """


STRATEGY_COLORS = {
    "SMA Crossover (20/50)": "#42a5f5",
    "RSI Mean Reversion (30/70)": "#ba68c8",
    "ML (random_forest)": "#66bb6a",
    "ML (xgboost)": "#ffa726",
}


# ── Main Logic ─────────────────────────────────────────────
if run_button:
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # --- Download & Features ---
    with st.spinner(f"🔄 Downloading {symbol} data & computing indicators..."):
        try:
            df = prepare_features(symbol, start=start_str, end=end_str)
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.stop()
    
    st.success(f"✅ Data ready — {len(df)} trading days, {len(df.columns)} features")
    
    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["📊 Price & Indicators", "🏆 Strategy Comparison", "📈 Equity Curves"])
    
    # ── Tab 1: Price Chart ──────────────────────────────────
    with tab1:
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.55, 0.25, 0.20],
            subplot_titles=("Price & Moving Averages", "RSI (14)", "MACD"),
        )
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Price",
            increasing_line_color="#00e676", decreasing_line_color="#ff5252",
        ), row=1, col=1)
        
        # Moving Averages
        for col, color, name in [
            ("SMA_20", "#42a5f5", "SMA 20"),
            ("SMA_50", "#ffa726", "SMA 50"),
            ("EMA_12", "#80deea", "EMA 12"),
        ]:
            if col in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[col], name=name,
                    line=dict(color=color, width=1.5),
                ), row=1, col=1)
        
        # Bollinger Bands
        bb_upper = [c for c in df.columns if c.startswith("BBU_")]
        bb_lower = [c for c in df.columns if c.startswith("BBL_")]
        if bb_upper and bb_lower:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[bb_upper[0]], name="BB Upper",
                line=dict(color="rgba(128,128,128,0.3)", dash="dot"),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df[bb_lower[0]], name="BB Lower",
                line=dict(color="rgba(128,128,128,0.3)", dash="dot"),
                fill="tonexty", fillcolor="rgba(128,128,128,0.05)",
            ), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI_14"], name="RSI 14",
            line=dict(color="#ba68c8", width=1.5),
        ), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,82,82,0.5)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,230,118,0.5)", row=2, col=1)
        
        # MACD
        macd_col = "MACD_12_26_9"
        macds_col = "MACDs_12_26_9"
        macdh_col = "MACDh_12_26_9"
        if macd_col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[macd_col], name="MACD",
                line=dict(color="#42a5f5", width=1.5),
            ), row=3, col=1)
            fig.add_trace(go.Scatter(
                x=df.index, y=df[macds_col], name="Signal",
                line=dict(color="#ffa726", width=1.5),
            ), row=3, col=1)
            colors = ["#00e676" if v >= 0 else "#ff5252" for v in df[macdh_col]]
            fig.add_trace(go.Bar(
                x=df.index, y=df[macdh_col], name="Histogram",
                marker_color=colors, opacity=0.6,
            ), row=3, col=1)
        
        fig.update_layout(
            template="plotly_dark",
            height=800,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_rangeslider_visible=False,
            margin=dict(t=50, b=30, l=50, r=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,12,41,0.8)",
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # ── Tab 2: Strategy Comparison ──────────────────────────
    with tab2:
        all_results = []
        all_portfolios = {}
        all_dfs = {}
        
        strategies_to_run = []
        if run_sma:
            strategies_to_run.append(("SMA Crossover (20/50)", "traditional", sma_signals, {}))
        if run_rsi:
            strategies_to_run.append(("RSI Mean Reversion (30/70)", "traditional", rsi_signals, {}))
        if run_rf:
            strategies_to_run.append(("ML (random_forest)", "ml", ml_signals, {"model_type": "random_forest"}))
        if run_xgb:
            strategies_to_run.append(("ML (xgboost)", "ml", ml_signals, {"model_type": "xgboost"}))
        
        progress = st.progress(0, text="Running strategies...")
        
        for i, (name, stype, signal_fn, kwargs) in enumerate(strategies_to_run):
            progress.progress((i + 1) / len(strategies_to_run), text=f"Running {name}...")
            
            try:
                if stype == "traditional":
                    df_strat = signal_fn(df.copy())
                else:
                    df_strat = signal_fn(df.copy(), **kwargs)
                
                portfolio = run_backtest(df_strat, init_cash=init_cash, fees=fees)
                metrics = print_metrics(portfolio, strategy_name=name)
                all_results.append(metrics)
                all_portfolios[name] = portfolio
                all_dfs[name] = df_strat
            except Exception as e:
                st.warning(f"⚠️ {name} failed: {e}")
        
        progress.empty()
        
        if all_results:
            results_df = pd.DataFrame(all_results).set_index("strategy")
            
            # Find winner
            best_return_strategy = results_df["total_return_pct"].idxmax()
            best_sharpe_strategy = results_df["sharpe_ratio"].idxmax()
            
            # Metric Cards for winner
            winner = results_df.loc[best_return_strategy]
            st.markdown(f"### 🏆 Best Strategy: **{best_return_strategy}**")
            
            mcols = st.columns(5)
            with mcols[0]:
                st.markdown(create_metric_card("Total Return", winner["total_return_pct"]), unsafe_allow_html=True)
            with mcols[1]:
                st.markdown(create_metric_card("Sharpe Ratio", winner["sharpe_ratio"], suffix=""), unsafe_allow_html=True)
            with mcols[2]:
                st.markdown(create_metric_card("Max Drawdown", winner["max_drawdown_pct"], invert=True), unsafe_allow_html=True)
            with mcols[3]:
                st.markdown(create_metric_card("Total Trades", winner["total_trades"], fmt=".0f", suffix=""), unsafe_allow_html=True)
            with mcols[4]:
                st.markdown(create_metric_card("Win Rate", winner["win_rate_pct"]), unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Comparison Table
            st.markdown("### 📊 Full Comparison")
            
            display_df = results_df.copy()
            display_df.columns = ["Return (%)", "Sharpe", "Max DD (%)", "Trades", "Win Rate (%)"]
            st.dataframe(
                display_df.style
                    .highlight_max(subset=["Return (%)", "Sharpe", "Win Rate (%)"], color="rgba(0,230,118,0.2)")
                    .highlight_min(subset=["Max DD (%)"], color="rgba(0,230,118,0.2)")
                    .format({
                        "Return (%)": "{:.2f}%",
                        "Sharpe": "{:.4f}",
                        "Max DD (%)": "{:.2f}%",
                        "Trades": "{:.0f}",
                        "Win Rate (%)": "{:.2f}%",
                    }),
                use_container_width=True,
                height=220,
            )
            
            # Bar Chart Comparison
            st.markdown("### 📊 Visual Comparison")
            bar_fig = make_subplots(rows=1, cols=3, subplot_titles=("Return (%)", "Sharpe Ratio", "Max Drawdown (%)"))
            
            names = results_df.index.tolist()
            colors = [STRATEGY_COLORS.get(n, "#888") for n in names]
            
            bar_fig.add_trace(go.Bar(x=names, y=results_df["total_return_pct"], marker_color=colors, showlegend=False), row=1, col=1)
            bar_fig.add_trace(go.Bar(x=names, y=results_df["sharpe_ratio"], marker_color=colors, showlegend=False), row=1, col=2)
            bar_fig.add_trace(go.Bar(x=names, y=results_df["max_drawdown_pct"], marker_color=colors, showlegend=False), row=1, col=3)
            
            bar_fig.update_layout(
                template="plotly_dark", height=350,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,12,41,0.5)",
                margin=dict(t=40, b=30),
            )
            st.plotly_chart(bar_fig, use_container_width=True)
    
    # ── Tab 3: Equity Curves ────────────────────────────────
    with tab3:
        if all_portfolios:
            eq_fig = go.Figure()
            
            for name, portfolio in all_portfolios.items():
                cum_returns = portfolio.cumulative_returns() * 100
                eq_fig.add_trace(go.Scatter(
                    x=cum_returns.index, y=cum_returns.values,
                    name=name, line=dict(color=STRATEGY_COLORS.get(name, "#888"), width=2.5),
                    fill="tozeroy", fillcolor=f"rgba({','.join(str(int(STRATEGY_COLORS.get(name, '#888').lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.05)",
                ))
            
            eq_fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
            
            eq_fig.update_layout(
                title="Cumulative Returns (%)",
                template="plotly_dark", height=500,
                yaxis_title="Return (%)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,12,41,0.8)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=60, b=30),
            )
            st.plotly_chart(eq_fig, use_container_width=True)
            
            # Drawdown chart
            dd_fig = go.Figure()
            for name, portfolio in all_portfolios.items():
                dd = portfolio.drawdown() * 100
                dd_fig.add_trace(go.Scatter(
                    x=dd.index, y=dd.values, name=name,
                    line=dict(color=STRATEGY_COLORS.get(name, "#888"), width=1.5),
                    fill="tozeroy",
                ))
            
            dd_fig.update_layout(
                title="Drawdown (%)",
                template="plotly_dark", height=350,
                yaxis_title="Drawdown (%)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,12,41,0.8)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=60, b=30),
            )
            st.plotly_chart(dd_fig, use_container_width=True)
        else:
            st.info("Run a backtest to see equity curves.")

else:
    # Landing state
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem; color: #8888aa;">
        <h2 style="color: #a8a8d8;">👈 Configure & Click <span style="color: #00d2ff;">Run Backtest</span></h2>
        <p style="font-size: 1.1rem;">Choose a symbol, date range, and strategies from the sidebar to get started.</p>
        <div style="margin-top: 2rem; display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
            <span class="strategy-badge badge-sma">SMA Crossover</span>
            <span class="strategy-badge badge-rsi">RSI Mean Reversion</span>
            <span class="strategy-badge badge-rf">ML Random Forest</span>
            <span class="strategy-badge badge-xgb">ML XGBoost</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Tab/Section: Live Trading ──────────────────────────────
st.markdown("---")
st.markdown("### 🔗 Live Trading")

# Try to connect
try:
    from src.exchange import BinanceClient
    EXCHANGE_AVAILABLE = True
except ImportError:
    EXCHANGE_AVAILABLE = False

if EXCHANGE_AVAILABLE:
    live_col1, live_col2 = st.columns([3, 1])

    with live_col2:
        trade_mode = st.radio(
            "Mode",
            ["🎮 Simulation", "🧪 Testnet", "🔴 Live"],
            index=0,
            help="Simulation: ไม่ต้องใช้ API key, ราคาจริง, order จำลอง\nTestnet: ต้องมี Binance API key\nLive: เงินจริง!"
        )
        mode_map = {"🎮 Simulation": "simulation", "🧪 Testnet": "testnet", "🔴 Live": "live"}
        selected_mode = mode_map[trade_mode]

        connect_btn = st.button("🔌 Connect", use_container_width=True, type="secondary")

    if connect_btn or st.session_state.get("exchange_connected"):
        # Reconnect if mode changed
        prev_mode = st.session_state.get("exchange_mode")
        needs_reconnect = connect_btn or prev_mode != selected_mode

        if needs_reconnect:
            with st.spinner("Connecting..."):
                try:
                    client = BinanceClient(mode=selected_mode)
                    st.session_state["exchange_connected"] = True
                    st.session_state["exchange_mode"] = selected_mode
                    st.session_state["exchange_client"] = client
                except Exception as e:
                    st.error(f"❌ Connection failed: {e}")
                    st.session_state["exchange_connected"] = False

    if st.session_state.get("exchange_connected"):
        client = st.session_state.get("exchange_client")
        current_mode = st.session_state.get("exchange_mode", "simulation")

        with live_col1:
            if current_mode == "simulation":
                st.markdown('<span class="live-status status-testnet">🎮 SIMULATION — Paper Trading (Real Prices)</span>', unsafe_allow_html=True)
            elif current_mode == "testnet":
                st.markdown('<span class="live-status status-testnet">🧪 TESTNET — Binance Paper Trading</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="live-status status-connected">🟢 LIVE — Real Money</span>', unsafe_allow_html=True)

        # ── Account Overview ──
        try:
            status = client.status()
            balances = client.get_balance()

            # Show key balances
            st.markdown("#### 💰 Account Balances")
            bal_cols = st.columns(4)

            priority_assets = ["USDT", "BTC", "ETH", "BNB"]
            shown = 0
            for asset in priority_assets:
                if asset in balances and shown < 4:
                    bal = balances[asset]
                    if bal["free"] > 0 or bal["locked"] > 0:
                        with bal_cols[shown]:
                            usd_str = ""
                            if asset != "USDT":
                                try:
                                    price = client.get_price(f"{asset}USDT")
                                    usd_val = bal["free"] * price
                                    usd_str = f'<div class="asset-usd">≈ ${usd_val:,.2f}</div>'
                                except Exception:
                                    pass
                            else:
                                usd_str = f'<div class="asset-usd">Available</div>'

                            st.markdown(f"""
                            <div class="balance-card">
                                <div class="asset-name">{asset}</div>
                                <div class="asset-value">{bal["free"]:,.8g}</div>
                                {usd_str}
                            </div>
                            """, unsafe_allow_html=True)
                        shown += 1

            st.markdown("")

            # ── Live Prices ──
            st.markdown("#### 📈 Live Prices")
            price_cols = st.columns(3)
            for i, sym in enumerate(["BTCUSDT", "ETHUSDT", "BNBUSDT"]):
                try:
                    p = client.get_price(sym)
                    with price_cols[i]:
                        name = sym.replace("USDT", "")
                        st.metric(f"{name}/USDT", f"${p:,.2f}")
                except Exception:
                    pass

            st.markdown("---")

            # ── Manual Trading ──
            st.markdown("#### 🎮 Manual Trading")
            trade_cols = st.columns([2, 1, 1, 1])

            with trade_cols[0]:
                trade_symbol = st.selectbox("Trading Pair", ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"])
            with trade_cols[1]:
                trade_amount = st.number_input("Amount (USDT)", value=10.0, min_value=1.0, max_value=100.0, step=1.0)
            with trade_cols[2]:
                buy_btn = st.button("🟢 BUY", use_container_width=True, type="primary")
            with trade_cols[3]:
                sell_btn = st.button("🔴 SELL ALL", use_container_width=True)

            if buy_btn:
                try:
                    order = client.buy(trade_symbol, usd_amount=trade_amount)
                    st.success(f"✅ Bought ${trade_amount} of {trade_symbol} — Order #{order.get('orderId')}")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Buy failed: {e}")

            if sell_btn:
                try:
                    base_asset = trade_symbol.replace("USDT", "")
                    bal = client.get_balance(base_asset)
                    qty = bal.get(base_asset, {}).get("free", 0)
                    if qty > 0:
                        import math
                        info = client.client.get_symbol_info(trade_symbol)
                        step = float([f for f in info["filters"] if f["filterType"] == "LOT_SIZE"][0]["stepSize"])
                        precision = int(round(-math.log(step, 10), 0))
                        qty = math.floor(qty * 10**precision) / 10**precision
                        if qty > 0:
                            order = client.sell(trade_symbol, quantity=qty)
                            st.success(f"✅ Sold {qty} {base_asset} — Order #{order.get('orderId')}")
                        else:
                            st.warning("No balance to sell.")
                    else:
                        st.warning(f"No {base_asset} balance to sell.")
                except Exception as e:
                    st.error(f"❌ Sell failed: {e}")

            # ── Trade Log ──
            st.markdown("---")
            st.markdown("#### 📋 Trade History")

            if client.trade_log:
                log_df = pd.DataFrame(client.trade_log)
                st.dataframe(log_df, use_container_width=True)
            else:
                log_path = "data/trade_log.csv"
                if os.path.exists(log_path):
                    log_df = pd.read_csv(log_path)
                    st.dataframe(log_df.tail(20), use_container_width=True)
                else:
                    st.info("No trades yet. Use the controls above to place your first trade!")

            # ── Safety Info ──
            st.markdown("---")
            with st.expander("⚙️ Safety Settings"):
                mode_label = {"simulation": "🎮 Simulation", "testnet": "🧪 Testnet", "live": "🔴 Live"}
                st.markdown(f"""
                - **Max Position Size:** ${status.get('max_position_usd', 50)}
                - **Max Daily Trades:** {status.get('max_daily_trades', 10)}
                - **Trades Today:** {status.get('daily_trades', 0)}
                - **Mode:** {mode_label.get(current_mode, current_mode)}
                
                > Adjust limits in `.env` file.
                """)

        except Exception as e:
            st.error(f"❌ Error: {e}")
            if current_mode != "simulation":
                st.info("Make sure your API keys are set in `.env` file. Or try **Simulation** mode.")

    else:
        st.info("""
        **👆 Click Connect** to start paper trading!
        
        - **Simulation**: ใช้ได้ทันที ไม่ต้อง API key (ราคาจริง, order จำลอง)
        - **Testnet**: ต้องสมัคร API key จาก [Binance Testnet](https://testnet.binance.vision/)
        - **Live**: เงินจริง — ใช้หลังทดสอบจน confident แล้วเท่านั้น
        """)

else:
    st.warning("Install `python-binance`: `pip install python-binance python-dotenv`")
