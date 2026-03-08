import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# =========================================================
# BLOQUE 1: CONFIGURACIÓN E IDENTIDAD (ESTILOS Y COLORES)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    
    /* BLOQUE 3.1: Estilo de KPIs */
    .kpi-row {
        background-color: #0d1117; padding: 10px; border-bottom: 1px solid #333;
        display: flex; justify-content: space-around; font-family: monospace;
    }

    /* BLOQUE 3.2: Ticker Animado (Bolsa Antigua) */
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #000; 
        border-bottom: 2px solid #d4af37; padding: 10px 0;
    }
    .ticker-move {
        display: flex; width: fit-content;
        animation: ticker 50s linear infinite;
    }
    .ticker-item {
        display: flex; align-items: center; gap: 10px;
        padding: 0 50px; white-space: nowrap; font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
    }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    /* BLOQUE 4: Navegación Superior (Gris Oscuro) */
    .nav-btn > div > button {
        background-color: #1c2128 !important; color: #ffffff !important;
        border: 1px solid #444 !important; height: 3em;
    }

    /* BLOQUE 5: Menú Lobo (Dorado/Negro - Diferente al superior) */
    .cat-btn > div > button {
        background-color: #2b2101 !important; color: #d4af37 !important;
        border: 1px solid #d4af37 !important; height: 3.5em;
    }
    
    /* Estado ACTIVO (Resaltado Dorado Brillante) */
    .active-btn > div > button {
        background-color: #d4af37 !important; color: #000 !important;
        font-weight: 900 !important; border: 1px solid #fff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# BLOQUE 2: ESTADOS Y BASE DE DATOS (MAPEO XTB -> YAHOO)
# =========================================================
if 'setup' not in st.session_state:
    st.session_state.update({
        'view': "Lobo", 'active_cat': None, 'active_sub': None,
        'ticker': "NQ=F", 'ticker_name': "US100",
        'wallet': 18850.00, 'margen': 15200.00, 'pnl': 420.50,
        'setup': True
    })

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
# BLOQUE 3: HEADER FIJO (CAPITAL Y TICKER ANIMADO)
# =========================================================
# 3.1 - KPIs Superiores
pnl_color = "#00ff41" if st.session_state.pnl >= 0 else "#ff3131"
st.markdown(f"""
    <div class="kpi-row">
        <span>CAPITAL: <span style="color:#d4af37">{st.session_state.wallet:,.2f}€</span></span>
        <span>MARGEN: <span style="color:#d4af37">{st.session_state.margen:,.2f}€</span></span>
        <span>PnL ABIERTO: <span style="color:{pnl_color}">{st.session_state.pnl:,.2f}€</span></span>
    </div>
    """, unsafe_allow_html=True)

# 3.2 - Ticker de Bolsa Antigua (Movimiento Continuo)
hot_items = [
    ("NQ=F", "US100", "🇺🇸", "BUY"), ("GC=F", "GOLD", "🟡", "BUY"),
    ("BTC-USD", "BITCOIN", "₿", "SELL"), ("NVDA", "NVDA.US", "🟢", "BUY"),
    ("BZ=F", "OIL.BRENT", "🌍", "BUY")
]

content = ""
for t, n, i, s in hot_items * 5:
    color = "#00ff41" if s == "BUY" else "#ff3131"
    content += f'<div class="ticker-item">{i} {n} <span style="color:{color};">[{s}]</span></div>'
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# 3.3 - Ventana Flotante de Acción (Expander para Alertas)
with st.expander("⚡ ALERTAS SENTINEL (Click para ver recomendación)"):
    t_cols = st.columns(len(hot_items))
    for idx, (t, n, i, s) in enumerate(hot_items):
        if t_cols[idx].button(f"INFO {n}", key=f"alert_{n}"):
            st.session_state.ticker = t
            st.session_state.ticker_name = n
            st.info(f"📍 SEÑAL SENTINEL: {s} en {n}. Objetivo +2%, Riesgo -1%.")

# =========================================================
# BLOQUE 4: NAVEGACIÓN PRINCIPAL (Selector de Ventanas)
# =========================================================
nav = st.columns(6)
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]

for i, col in enumerate(nav):
    is_active = st.session_state.view == v_list[i]
    style_class = "active-btn" if is_active else "nav-btn"
    with col:
        st.markdown(f'<div class="{style_class}">', unsafe_allow_html=True)
        if st.button(btns[i], key=f"view_{i}", use_container_width=True):
            st.session_state.view = v_list[i]
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 5: VENTANA LOBO (MENÚ EN CASCADA REAL)
# =========================================================
if st.session_state.view == "Lobo":
    st.divider()
    # 5.1 - Categorías (Dorado/Negro)
    c_cat = st.columns(4)
    cats = ["indices", "acciones", "material", "divisas"]
    icons = ["🏛️", "📈", "🏗️", "💱"]
    
    for i, cat in enumerate(cats):
        is_active = st.session_state.active_cat == cat
        style_class = "active-btn" if is_active else "cat-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{style_class}">', unsafe_allow_html=True)
            if st.button(f"{icons[i]} {cat.upper()}", key=f"btn_cat_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = None # Reset sub al cambiar
            st.markdown('</div>', unsafe_allow_html=True)

    # 5.2 - Subcategorías (Ocultas hasta que hagas clic en Categoría)
    if st.session_state.active_cat:
        st.write(f"📂 Selecciona Subcategoría de **{st.session_state.active_cat.upper()}**:")
        sub_list = list(DATABASE[st.session_state.active_cat].keys())
        c_sub = st.columns(max(len(sub_list), 4))
        for i, sub in enumerate(sub_list):
            is_active = st.session_state.active_sub == sub
            style_class = "active-btn" if is_active else "nav-btn"
            with c_sub[i]:
                st.markdown(f'<div class="{style_class}">', unsafe_allow_html=True)
                if st.button(sub, key=f"btn_sub_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                st.markdown('</div>', unsafe_allow_html=True)

    # 5.3 - Activos (Ocultos hasta que hagas clic en Subcategoría)
    if st.session_state.active_sub:
        st.write(f"💎 Activos en **{st.session_state.active_sub}**:")
        items = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
        cols_act = st.columns(6)
        for idx, (name, data) in enumerate(items.items()):
            is_active = st.session_state.ticker_name == name
            style_class = "active-btn" if is_active else "nav-btn"
            with cols_act[idx % 6]:
                st.markdown(f'<div class="{style_class}">', unsafe_allow_html=True)
                if st.button(f"{data[1]} {name}", key=f"btn_act_{name}", use_container_width=True):
                    st.session_state.ticker = data[0]
                    st.session_state.ticker_name = name
                st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 7: ESPACIO PARA GRÁFICO
# =========================================================
st.markdown("---")
st.subheader(f"📊 MONITOR ACTIVO: {st.session_state.ticker_name} | {st.session_state.ticker}")
st.info("Estructura de cascada y ticker de bolsa antigua verificados. ¿Inyectamos el gráfico de velas ahora?")
