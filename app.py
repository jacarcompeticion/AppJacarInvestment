import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from streamlit_autorefresh import st_autorefresh

# =========================================================
# 1. ARRANQUE DEL NÚCLEO (Única llamada permitida)
# =========================================================
st.set_page_config(
    page_title="WOLF SOVEREIGN v.95", 
    layout="wide", 
    initial_sidebar_state="collapsed", 
    page_icon="🐺"
)

# Refresco global estable
st_autorefresh(interval=15000, key="wolf_global_refresh")

# =========================================================
# 2. ESTADO DE SESIÓN Y SANEAMIENTO
# =========================================================
if 'setup' not in st.session_state:
    st.session_state.update({
        'setup': True,
        'view': 'Lobo',
        'active_cat': 'indices',
        'active_sub': 'EEUU',
        'ticker': 'NQ=F',
        'ticker_name': 'US100 (Nasdaq) 🇺🇸',
        'wallet': 18850.0,
        'pnl': 420.0,
        'int_top': '1h'
    })

# =========================================================
# 3. BASE DE DATOS ESTRUCTURADA
# =========================================================
DATABASE = {
    "stocks": {
        "TECNOLOGÍA": {
            "APPLE (AAPL) 🍎": ["AAPL", "123"], "TESLA (TSLA) ⚡": ["TSLA", "124"],
            "NVIDIA (NVDA) 🟢": ["NVDA", "125"]
        }
    },
    "indices": {
        "EEUU": { "US100 (Nasdaq) 🇺🇸": ["NQ=F", "100"], "US500 (S&P500) 🇺🇸": ["ES=F", "500"] },
        "EUROPA": { "DE40 (DAX) 🇩🇪": ["^GDAXI", "40"], "SPA35 (IBEX) 🇪🇸": ["^IBEX", "35"] }
    },
    "divisas": {
        "MAJORS": { "EURUSD 🇪🇺🇺🇸": ["EURUSD=X", "501"], "GBPUSD 🇬🇧🇺🇸": ["GBPUSD=X", "502"] }
    },
    "material": {
        "METALES": { "GOLD (Oro) 🟡": ["GC=F", "003"], "SILVER (Plata) ⚪": ["SI=F", "004"] }
    }
}

# =========================================================
# 4. FUNCIONES DE APOYO
# =========================================================
def get_data(ticker, interval):
    try:
        df = yf.download(ticker, period='5d', interval=interval, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df['Close'], df['Open'])]
        return df.dropna(subset=['Close'])
    except: return None

# =========================================================
# 5. UI Y NAVEGACIÓN
# =========================================================
st.markdown("""<style> .stApp { background-color: #05070a; color: white; } </style>""", unsafe_allow_html=True)

# Cabecera
st.markdown(f"""
<div style="background:#0d1117; padding:10px; border-bottom:2px solid #A67B5B; display:flex; justify-content:space-around; color:#A67B5B; font-weight:bold;">
    <span>CAPITAL: {st.session_state.wallet:,.2f}€</span>
    <span>SISTEMA: V95 SOVEREIGN</span>
    <span>PnL: {st.session_state.pnl:,.2f}€</span>
</div>
""", unsafe_allow_html=True)

# Menú de Vistas
c1, c2, c3, c4 = st.columns(4)
vistas = {"🐺 LOBO": "Lobo", "📰 NOTICIAS": "Noticias", "⚙️ AJUSTES": "Ajustes", "🧹 RESET": "Reset"}
for i, (label, key) in enumerate(vistas.items()):
    with [c1, c2, c3, c4][i]:
        if st.button(label, key=f"v_{key}", use_container_width=True):
            if key == "Reset":
                st.session_state.clear()
                st.rerun()
            st.session_state.view = key
            st.rerun()

# --- VISTA PRINCIPAL (LOBO) ---
if st.session_state.view == "Lobo":
    # Categorías
    cats = list(DATABASE.keys())
    c_cols = st.columns(len(cats))
    for i, cat in enumerate(cats):
        if c_cols[i].button(cat.upper(), key=f"c_{cat}", use_container_width=True):
            st.session_state.active_cat = cat
            st.session_state.active_sub = list(DATABASE[cat].keys())[0]
            st.rerun()

    # Subcategorías
    subs = list(DATABASE[st.session_state.active_cat].keys())
    s_cols = st.columns(len(subs))
    for i, sub in enumerate(subs):
        if s_cols[i].button(sub, key=f"s_{sub}", use_container_width=True):
            st.session_state.active_sub = sub
            st.rerun()

    # Activos
    activos = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
    a_cols = st.columns(4)
    for i, (name, val) in enumerate(activos.items()):
        if a_cols[i % 4].button(name, key=f"a_{name}", use_container_width=True):
            st.session_state.ticker = val[0]
            st.session_state.ticker_name = name
            st.rerun()

    # --- RENDERIZADO DE DATOS ---
    df = get_data(st.session_state.ticker, st.session_state.int_top)
    if df is not None:
        # Gráfico
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_width=[0.3, 0.7], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#FFD700')), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Vol_Color']), row=2, col=1)
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{st.session_state.ticker}_{len(df)}")
        
        # Estrategia rápida
        st.info(f"Análisis en vivo: {st.session_state.ticker_name} | {df['Close'].iloc[-1]:,.2f}")
    else:
        st.error("Error de conexión con el proveedor de datos.")

elif st.session_state.view == "Ajustes":
    st.title("Configuración")
    st.session_state.wallet = st.number_input("Capital", value=float(st.session_state.wallet))
    st.success("Ajustes activos.")

else:
    st.info("Sección en construcción.")
