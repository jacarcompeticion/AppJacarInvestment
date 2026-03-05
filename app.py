import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Jacar Pro V15 - Multi-Currency", layout="wide", page_icon="⚖️")

# CSS para diferenciar COMPRA/VENTA y símbolos de moneda
st.markdown("""
    <style>
    .buy-card { border-left: 5px solid #00ff00; padding-left: 10px; }
    .sell-card { border-left: 5px solid #ff4b4b; padding-left: 10px; }
    .usd-price { color: #85bb65; font-weight: bold; }
    .eur-price { color: #3b82f6; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: 
    st.session_state.activo_sel = "Oro"
    st.session_state.ticker_sel = "GC=F"
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# DICCIONARIO CON MONEDA DE COTIZACIÓN
activos_dict = {
    "💻 Tecnología (USD)": {"NVDA": "NVDA", "Apple": "AAPL", "MSFT": "MSFT", "Tesla": "TSLA"},
    "⚡ Energía (EUR/USD)": {"Iberdrola": "IBE.MC", "Repsol": "REP.MC", "Exxon": "XOM", "Chevron": "CVX"},
    "⚱️ Materias Primas (USD)": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F", "Gas Nat": "NG=F"},
    "💵 Divisas": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X", "Bitcoin": "BTC-USD"},
    "📈 Índices": {"Nasdaq 100": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"}
}

# --- 2. MENU VISUAL ---
st.title("🏛️ Jacar Global Terminal")
tabs = st.tabs(list(activos_dict.keys()))
for i, (categoria, lista) in enumerate(activos_dict.items()):
    with tabs[i]:
        cols = st.columns(len(lista))
        for j, (nombre, ticker) in enumerate(lista.items()):
            if cols[j].button(f"{nombre}", key=f"btn_{ticker}"):
                st.session_state.activo_sel = nombre
                st.session_state.ticker_sel = ticker
                st.rerun()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🏢 Gestión de Capital")
    st.metric("Balance Cuenta", f"{st.session_state.wallet:,.2f} €")
    st.caption("Cálculo de riesgo basado en 1% del Equity en EUR.")
    st.divider()
    if st.button("🚀 COPILOTO: AUDITAR GESTIÓN", use_container_width=True):
        if not st.session_state.cartera_abierta:
            st.warning("No hay posiciones activas.")
        else:
            for pos in st.session_state.cartera_abierta:
                t = yf.Ticker(pos['ticker'])
                p_actual = t.history(period="1d")['Close'].iloc[-1]
                p_gestion = f"Analista. {pos['activo']} ({pos['tipo']}). Entrada: {pos['entrada']}, SL: {pos['sl']}, TP: {pos['tp']}. Precio Actual: {p_actual}. Indica si asegurar beneficios o prolongar. Breve."
                r = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":p_gestion}])
                st.info(f"**{pos['activo']}**: {r.choices[0].message.content}")

# --- 4. GRÁFICA ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h")
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    precio_act = float(df['Close'].iloc[-1])
    # Identificar moneda (simplificado: si tiene .MC o .GDAXI o ^IBEX es EUR, si no es USD mayormente)
    moneda = "€" if any(x in st.session_state.ticker_sel for x in [".MC", "GDAXI", "IBEX"]) else "$"
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=f"{st.session_state.activo_sel} ({moneda})"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1.5), name="EMA 20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1, dash='dot'), name="RSI", opacity=0.4), row=1, col=1, secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    if st.button(f"⚖️ ANALIZAR {st.session_state.activo_sel.upper()} EN {moneda}"):
        with st.spinner('Analizando confluencia multidivisa...'):
            ticker_obj = yf.Ticker(st.session_state.ticker_sel)
            news_text = "\n".join([n.get('title', '') for n in ticker_
