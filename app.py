import streamlit as st
import yfinance as yf
import pandas as pd

# =========================================================
# BLOQUE 1: CONFIGURACIÓN E IDENTIDAD (CSS AVANZADO)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    
    /* BLOQUE 3.1: KPIs Superiores */
    .kpi-row {
        background-color: #0d1117; padding: 10px; border-bottom: 1px solid #333;
        display: flex; justify-content: space-around; font-family: monospace; font-size: 0.9rem;
    }
    .kpi-val { color: #d4af37; font-weight: bold; }

    /* BLOQUE 3.2: Ticker Animado (Bolsa Antigua) */
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #000; 
        border-bottom: 1px solid #d4af37; padding: 5px 0;
    }
    .ticker-move {
        display: flex; width: fit-content;
        animation: ticker 40s linear infinite;
    }
    .ticker-item {
        display: flex; align-items: center; gap: 8px;
        padding: 0 30px; white-space: nowrap; font-family: monospace; font-size: 1rem;
    }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    /* BLOQUE 5: Estilo Menú (Categorías y Subcategorías) */
    /* Botón estándar de menú */
    div.stButton > button {
        background-color: #1a1e23; color: #ffffff; border: 1px solid #444;
        border-radius: 4px; transition: 0.3s;
    }
    /* Botón Activo (Cuando estás dentro de la categoría/subcategoría) */
    .active-btn > div > button {
        background-color: #d4af37 !important; color: #000 !important;
        border: 1px solid #fff !important; font-weight: 800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# BLOQUE 2: ESTADOS Y BASE DE DATOS
# =========================================================
if 'setup' not in st.session_state:
    st.session_state.update({
        'view': "Lobo", 'active_cat': "indices", 'active_sub': None,
        'ticker': "NQ=F", 'ticker_name': "US100",
        'wallet': 18850.00, 'margen': 15200.00, 'objetivo': 2500.00, 'pnl': 420.50,
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
# 3.1 - KPIs
pnl_color = "#00ff41" if st.session_state.pnl >= 0 else "#ff3131"
st.markdown(f"""
    <div class="kpi-row">
        <span>CAPITAL: <span class="kpi-val">{st.session_state.wallet:,.2f}€</span></span>
        <span>MARGEN: <span class="kpi-val">{st.session_state.margen:,.2f}€</span></span>
        <span>OBJETIVO: <span class="kpi-val">{st.session_state.objetivo:,.2f}€</span></span>
        <span>PnL: <span style="color:{pnl_color}; font-weight:bold;">{st.session_state.pnl:,.2f}€</span></span>
    </div>
    """, unsafe_allow_html=True)

# 3.2 - Ticker Animado (Activos Calientes)
hot_items = [
    ("NQ=F", "US100", "🇺🇸", "BUY", "#00ff41"), ("GC=F", "GOLD", "🟡", "BUY", "#00ff41"),
    ("BTC-USD", "BITCOIN", "₿", "SELL", "#ff3131"), ("NVDA", "NVDA.US", "🟢", "BUY", "#00ff41"),
    ("BZ=F", "OIL.BRENT", "🌍", "BUY", "#00ff41")
]
# Duplicamos la lista para efecto infinito suave
content = ""
for t, n, i, s, c in hot_items * 3:
    content += f'<div class="ticker-item">{i} {n} <span style="color:{c};">[{s}]</span></div>'

st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# Acciones del Ticker (Botones discretos debajo para interactuar)
t_cols = st.columns(len(hot_items))
for idx, (t, n, i, s, c) in enumerate(hot_items):
    if t_cols[idx].button(f"Analyze {n}", key=f"h_{n}", use_container_width=True):
        st.session_state.ticker = t
        st.session_state.ticker_name = n

# =========================================================
# BLOQUE 4: NAVEGACIÓN PRINCIPAL
# =========================================================
nav = st.columns(6)
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]
for i, col in enumerate(nav):
    # Marcamos el botón activo con clase CSS especial
    if st.session_state.view == v_list[i]:
        st.markdown('<div class="active-btn">', unsafe_allow_html=True)
        if col.button(btns[i], key=f"nav_{i}", use_container_width=True): pass
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        if col.button(btns[i], key=f"nav_{i}", use_container_width=True):
            st.session_state.view = v_list[i]

# =========================================================
# BLOQUE 5: VENTANA LOBO (MENÚ LIMPIO)
# =========================================================
if st.session_state.view == "Lobo":
    # 5.1 - Categorías
    c_cat = st.columns(4)
    cats = ["indices", "acciones", "material", "divisas"]
    icons = ["🏛️", "📈", "🏗️", "💱"]
    for i, cat in enumerate(cats):
        if st.session_state.active_cat == cat:
            st.markdown('<div class="active-btn">', unsafe_allow_html=True)
            c_cat[i].button(f"{icons[i]} {cat.upper()}", key=f"cat_{cat}", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            if c_cat[i].button(f"{icons[i]} {cat.upper()}", key=f"cat_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = None

    # 5.2 - Subcategorías (Sin nombres de carpetas, solo botones con color de estado)
    sub_list = list(DATABASE[st.session_state.active_cat].keys())
    c_sub = st.columns(max(len(sub_list), 4))
    for i, sub in enumerate(sub_list):
        if st.session_state.active_sub == sub:
            st.markdown('<div class="active-btn">', unsafe_allow_html=True)
            c_sub[i].button(sub, key=f"s_{sub}", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            if c_sub[i].button(sub, key=f"s_{sub}", use_container_width=True):
                st.session_state.active_sub = sub

    # 5.3 - Activos Finales (Botones pequeños y limpios)
    if st.session_state.active_sub:
        items = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
        cols_act = st.columns(6)
        for idx, (name, data) in enumerate(items.items()):
            # Si es el activo seleccionado, resaltar en dorado
            if st.session_state.ticker_name == name:
                st.markdown('<div class="active-btn">', unsafe_allow_html=True)
                cols_act[idx % 6].button(f"{data[1]} {name}", key=f"f_{name}", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                if cols_act[idx % 6].button(f"{data[1]} {name}", key=f"f_{name}", use_container_width=True):
                    st.session_state.ticker = data[0]
                    st.session_state.ticker_name = name

# =========================================================
# BLOQUE 7: EL GRÁFICO (LISTO PARA INYECTAR)
# =========================================================
st.markdown("---")
st.subheader(f"📊 {st.session_state.ticker_name} | {st.session_state.ticker}")
