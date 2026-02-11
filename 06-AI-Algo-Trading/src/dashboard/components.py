import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ── Metric Components ───────────────────────────────────────
def MetricCard(label, value, delta=None, prefix="", suffix=""):
    """
    Renders a glassmorphism metric card via HTML.
    """
    delta_html = ""
    if delta is not None:
        color = "#00e676" if delta >= 0 else "#ff5252"
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f'<span style="color: {color}; font-size: 0.8rem; font-weight: 600; margin-left: 6px;">{arrow} {abs(delta):.2f}%</span>'
    
    html = f"""
    <div class="glass-card" style="padding: 1.2rem 1rem; text-align: center; height: 100%;">
        <div class="metric-label">{label}</div>
        <div class="metric-value">
            {prefix}{value}{suffix}
            {delta_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def StatusBadge(mode):
    """
    Renders the connection status badge.
    """
    badges = {
        "simulation": ('#ffca28', 'CTRL'),
        "testnet": ('#29b6f6', 'TEST'),
        "live": ('#00e676', 'LIVE'),
    }
    color, text = badges.get(mode, ('#9e9e9e', 'OFF'))
    
    html = f"""
    <div style="
        display: inline-flex; align-items: center; gap: 8px;
        padding: 4px 12px; border-radius: 20px;
        background: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15);
        border: 1px solid {color};
        color: {color}; font-weight: 700; font-size: 0.75rem;
        letter-spacing: 1px;
    ">
        <span style="width: 8px; height: 8px; background: {color}; border-radius: 50%; box-shadow: 0 0 8px {color};"></span>
        {text}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ── Charts ─────────────────────────────────────────────────
def TradingChart(df, symbol):
    """
    Creates a high-performance Plotly candlestick chart with indicators.
    """
    if df is None or df.empty:
        st.warning("No data to display")
        return

    # Create Subplots: Main (Price), RSI, MACD
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("", "", "")
    )

    # 1. Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name='Price',
        increasing_line_color='#00e676', decreasing_line_color='#ff5252',
        increasing_fillcolor='rgba(0, 230, 118, 0.1)', decreasing_fillcolor='rgba(255, 82, 82, 0.1)',
    ), row=1, col=1)

    # Moving Averages (Neon Style)
    if 'SMA_20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name='SMA 20', line=dict(color='#00d2ff', width=1.5)), row=1, col=1)
    if 'SMA_50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='SMA 50', line=dict(color='#d500f9', width=1.5)), row=1, col=1)

    # Bollinger Bands
    if 'BBU_20_2.0' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], name='BB Upper', line=dict(color='rgba(255,255,255,0.2)', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['BBL_20_2.0'], name='BB Lower',
            line=dict(color='rgba(255,255,255,0.2)', dash='dot'),
            fill='tonexty', fillcolor='rgba(255,255,255,0.02)'
        ), row=1, col=1)

    # 2. RSI
    if 'RSI_14' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name='RSI', line=dict(color='#29b6f6', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,82,82,0.5)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,230,118,0.5)", row=2, col=1)

    # 3. MACD
    if 'MACD_12_26_9' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], name='MACD', line=dict(color='#00d2ff', width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], name='Signal', line=dict(color='#ffea00', width=1.5)), row=3, col=1)
        # Histogram with color based on value
        colors = ['#00e676' if v >= 0 else '#ff5252' for v in df['MACDh_12_26_9']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name='Hist', marker_color=colors, opacity=0.8), row=3, col=1)

    # Layout Styling
    fig.update_layout(
        template="plotly_dark",
        height=700,
        margin=dict(t=30, b=30, l=40, r=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(15, 12, 41, 0.4)',
        xaxis_rangeslider_visible=False,
        showlegend=False,
        hovermode='x unified'
    )
    
    # Grid lines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)')

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ── Order Book (Simulated) ─────────────────────────────────
def OrderBook(symbol, price):
    """
    Renders a simulated Order Book visualization.
    """
    st.markdown('<div class="metric-label" style="text-align:center; margin-bottom:10px;">ORDER BOOK</div>', unsafe_allow_html=True)
    
    # Generate fake depth
    asks =  [ (price * (1 + i*0.0005), 1000 - i*50) for i in range(1, 6) ]
    bids =  [ (price * (1 - i*0.0005), 1000 - i*50) for i in range(1, 6) ]
    
    # Render Asks (Red) - Top down
    for p, v in reversed(asks):
        width = min(v/10, 100)
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono'; font-size: 0.8rem; margin-bottom: 2px; position: relative;">
            <div style="position: absolute; right: 0; top: 0; bottom: 0; width: {width}%; background: rgba(255, 82, 82, 0.15);"></div>
            <span style="color: #ff5252; z-index: 1;">{p:,.2f}</span>
            <span style="color: #aaa; z-index: 1;">{v:.4f}</span>
        </div>
        """, unsafe_allow_html=True)
        
    # Current Price
    st.markdown(f"""
    <div style="text-align: center; font-family: 'JetBrains Mono'; font-size: 1.1rem; font-weight: 700; color: #fff; margin: 8px 0; border-top: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); padding: 4px;">
        {price:,.2f}
    </div>
    """, unsafe_allow_html=True)

    # Render Bids (Green)
    for p, v in bids:
        width = min(v/10, 100)
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; font-family: 'JetBrains Mono'; font-size: 0.8rem; margin-bottom: 2px; position: relative;">
            <div style="position: absolute; right: 0; top: 0; bottom: 0; width: {width}%; background: rgba(0, 230, 118, 0.15);"></div>
            <span style="color: #00e676; z-index: 1;">{p:,.2f}</span>
            <span style="color: #aaa; z-index: 1;">{v:.4f}</span>
        </div>
        """, unsafe_allow_html=True)
