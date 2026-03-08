import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# BLOQUE 1: CONFIGURACIÓN E IDENTIDAD (ESTILOS)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    /* Estilo KPIs Superiores */
    .kpi-row {
        background-color: #0d1117; padding: 12px; border-bottom: 2px solid #d4af37;
        display: flex; justify-content: space-around; font-family: monospace; font-size: 1rem;
    }
    .kpi-val { color: #d4af37; font-weight: bold; }
    /* Estilo Botones Navegación */
    div.stButton > button {
        background-color: #161b22; color: #d4af37; border: 1px solid #333;
        border-radius: 6px; height: 3em; font-weight: bold;
    }
    div.stButton > button:hover { border-color: #d4af37; background: #1c2128; }
    /* Ticker Hot Assets */
    .hot-label { font-size: 0.8rem; margin-bottom: 5px; color: #888; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# BLOQUE 2: ESTADOS Y PERSISTENCIA (DATOS)
# =========================================================
if 'setup' not in st.session_state:
    st.session_state.update({
        'view': "Lobo", 'active_cat': "indices", 'active_sub': None,
        'ticker': "NQ=F", 'ticker_name': "US100",
        'wallet': 18850.00, 'margen': 15200.00, 'objetivo': 2500.00, 'pnl': 420.50,
        'setup': True
    })

# Base de Datos (Mapeo XTB -> Yahoo)
DATABASE = {
    "indices": {
        "EEUU": {"US100": ["NQ=F", "🇺🇸"], "US500": ["ES=F", "🇺🇸"]},
        "EUROPA": {"DE40": ["^GDAXI", "🇩🇪"], "SPA35": ["^IBEX", "🇪🇸"]}
    },
    "acciones": {
        "TECNOLOGÍA": {"NVDA.US": ["NVDA", "🟢"], "TSLA.US": ["TSLA", "🔴"], "AAPL.US": ["AAPL", "⚪"]},
        "BANCA ESPAÑA": {"SAN.MC": ["SAN.MC", "🔴"], "BBVA.MC": ["BBVA.MC", "🔵"]}
    },
    "material": {
        "METALES": {"GOLD": ["GC=F", "🟡"], "SILVER": ["SI=F", "⚪"]},
        "ENERGÍA": {"OIL.WTI": ["CL=F", "🛢️"], "OIL.BRENT": ["BZ=F", "🌍"], "NATGAS": ["NG=F", "🔥"]}
    },
    "divisas": {
        "MAJORS": {"EURUSD": ["EURUSD=X", "🇪🇺"], "GBPUSD": ["GBPUSD=X", "🇬🇧"]},
        "CRYPTO": {"BITCOIN": ["BTC-USD", "₿"]}
    }
}

# =========================================================
# BLOQUE 3: HEADER FIJO (CAPITAL Y TICKER CALIENTE)
# =========================================================
# 3.1 - Línea de Capital
pnl_color = "#00ff41" if st.session_state.pnl >= 0 else "#ff3131"
st.markdown(f"""
    <div class="kpi-row">
        <span>Capital: <span class="kpi-val">{st.session_state.wallet:,.2f}€</span></span>
        <span>| Margen: <span class="kpi-val">{st.session_state.margen:,.2f}€</span></span>
        <span>| Objetivo: <span class="kpi-val">{st.session_state.objetivo:,.2f}€</span></span>
        <span>| PnL Abierto: <span style="color:{pnl_color}; font-weight:bold;">{st.session_state.pnl:,.2f}€</span></span>
    </div>
    """, unsafe_allow_html=True)

# 3.2 - Ticker de Activos Calientes (Clicables)
st.markdown("<div class='hot-label'>🔥 ACTIVOS CALIENTES (SENTINEL SIGNALS)</div>", unsafe_allow_html=True)
hot_list = [
    {"n": "US100", "i": "🇺🇸", "s": "BUY", "t": "NQ=F", "c": "#00ff41"},
    {"n": "GOLD", "i": "🟡", "s": "BUY", "t": "GC=F", "c": "#00ff41"},
    {"n": "BITCOIN", "i": "₿", "s": "SELL", "t": "BTC-USD", "c": "#ff3131"},
    {"n": "NVDA.US", "i": "🟢", "s": "BUY", "t": "NVDA", "c": "#00ff41"},
    {"n": "OIL.BRENT", "i": "🌍", "s": "BUY", "t": "BZ=F", "c": "#00ff41"}
]
h_cols = st.columns(len(hot_list))
for idx, h in enumerate(hot_list):
    st.markdown(f"<style>div[data-testid='stColumn']:nth-of-type({idx+1}) button {{ border-left: 5px solid {h['c']} !important; }}</style>", unsafe_allow_html=True)
    if h_cols[idx].button(f"{h['i']} {h['n']}\n{h['s']}", key=f"h_{h['n']}", use_container_width=True):
        st.session_state.ticker = h['t']
        st.session_state.ticker_name = h['n']
        st.toast(f"Cargando señal de {h['s']} para {h['n']}")

# =========================================================
# BLOQUE 4: NAVEGACIÓN PRINCIPAL
# =========================================================
st.divider()
nav = st.columns(6)
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDIC.", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]
for i, col in enumerate(nav):
    if col.button(btns[i], use_container_width=True):
        st.session_state.view = v_list[i]
st.divider()

# =========================================================
# BLOQUE 5: VENTANA LOBO (CATEGORÍAS Y ACTIVOS)
# =========================================================
if st.session_state.view == "Lobo":
    # 5.1 - Categorías
    c_cat = st.columns(4)
    cats = ["indices", "acciones", "material", "divisas"]
    icons = ["🏛️", "📈", "🏗️", "💱"]
    for i, cat in enumerate(cats):
        if c_cat[i].button(f"{icons[i]} {cat.upper()}", use_container_width=True):
            st.session_state.active_cat = cat
            st.session_state.active_sub = None

    # 5.2 - Subcategorías
    st.markdown(f"#### 📂 {st.session_state.active_cat.upper()}")
    sub_list = list(DATABASE[st.session_state.active_cat].keys())
    c_sub = st.columns(max(len(sub_list), 4))
    for i, sub in enumerate(sub_list):
        if c_sub[i].button(sub, key=f"s_{sub}", use_container_width=True):
            st.session_state.active_sub = sub

    # 5.3 - Activos Finales
    if st.session_state.active_sub:
        st.divider()
        items = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
        cols_act = st.columns(5)
        for idx, (name, data) in enumerate(items.items()):
            if cols_act[idx % 5].button(f"{data[1]} {name}", key=f"f_{name}", use_container_width=True):
                st.session_state.ticker = data[0]
                st.session_state.ticker_name = name

# =========================================================
# BLOQUE 6: VENTANA AJUSTES
# =========================================================
elif st.session_state.view == "Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.wallet = st.number_input("Capital Inicial (€)", value=st.session_state.wallet)
    st.session_state.objetivo = st.number_input("Meta Mensual (€)", value=st.session_state.objetivo)

# =========================================================
# BLOQUE 7: EL GRÁFICO (PRÓXIMO PASO)
# =========================================================
st.markdown("---")
st.subheader(f"📊 Análisis: {st.session_state.ticker_name} ({st.session_state.ticker})")
st.info("Bloques configurados. ¿Inyectamos el motor de velas en el Bloque 7?")
