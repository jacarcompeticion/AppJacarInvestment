import streamlit as st
import yfinance as yf
import pandas as pd

# =========================================================
# BLOQUE 1: CONFIGURACIÓN E IDENTIDAD (COLORES Y ESPACIADO 0)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    
    /* ELIMINAR ESPACIOS ENTRE FILAS (Padding y Gap) */
    [data-testid="stVerticalBlock"] > div {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        margin-top: -5px !important;
    }

    /* 1. VENTANAS (Navegación Superior): Marrón Claro / Letras Negras */
    .nav-btn > div > button {
        background-color: #A67B5B !important; color: #000000 !important;
        border: 1px solid #8B4513 !important; height: 3em; font-weight: bold;
    }
    .nav-active > div > button {
        background-color: #FFFFFF !important; color: #000000 !important;
        border: 1px solid #000000 !important; height: 3em; font-weight: 900;
    }

    /* 2. CATEGORÍAS/SUB/ACTIVOS: Blanco / Letras Negras */
    .menu-btn > div > button {
        background-color: #FFFFFF !important; color: #000000 !important;
        border: 1px solid #CCCCCC !important; height: 3.2em; border-radius: 0px !important;
    }
    .menu-active > div > button {
        background-color: #000000 !important; color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important; height: 3.2em; font-weight: bold; border-radius: 0px !important;
    }

    /* Ticker Animado */
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #000; 
        border-bottom: 2px solid #A67B5B; padding: 10px 0;
    }
    .ticker-move {
        display: flex; width: fit-content;
        animation: ticker 60s linear infinite;
    }
    .ticker-item {
        display: flex; align-items: center; gap: 10px;
        padding: 0 50px; white-space: nowrap; font-family: monospace; font-size: 1.1rem;
    }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# BLOQUE 2: ESTADOS Y BASE DE DATOS
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
# BLOQUE 3: HEADER (KPIs Y TICKER)
# =========================================================
pnl_color = "#00ff41" if st.session_state.pnl >= 0 else "#ff3131"
st.markdown(f"""
    <div style="background-color:#0d1117; padding:8px; display:flex; justify-content:space-around; border-bottom:1px solid #333; font-size:0.8rem;">
        <span>CAPITAL: <b style="color:#A67B5B">{st.session_state.wallet:,.2f}€</b></span>
        <span>MARGEN: <b style="color:#A67B5B">{st.session_state.margen:,.2f}€</b></span>
        <span>PnL: <b style="color:{pnl_color}">{st.session_state.pnl:,.2f}€</b></span>
    </div>
    """, unsafe_allow_html=True)

hot_list = [("NQ=F", "US100", "🇺🇸", "COMPRAR"), ("GC=F", "GOLD", "🟡", "COMPRAR")]
content = "".join([f'<div class="ticker-item">{i} {n} <span style="color:{"#00ff41" if s=="COMPRAR" else "#ff3131"};">[{s}]</span></div>' for t, n, i, s in hot_list * 10])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 4: NAVEGACIÓN (VENTANAS) - MARRÓN/BLANCO
# =========================================================
nav_cols = st.columns(6)
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]

for i, col in enumerate(nav_cols):
    is_active = st.session_state.view == v_list[i]
    style = "nav-active" if is_active else "nav-btn"
    with col:
        st.markdown(f'<div class="{style}">', unsafe_allow_html=True)
        if st.button(btns[i], key=f"v_{i}", use_container_width=True):
            st.session_state.view = v_list[i]
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 5: VENTANA LOBO (CASCADA PEGADA - BLANCO/NEGRO)
# =========================================================
if st.session_state.view == "Lobo":
    # 5.1 - CATEGORÍAS
    c_cat = st.columns(4)
    cats = ["indices", "acciones", "material", "divisas"]
    icons = ["🏛️", "📈", "🏗️", "💱"]
    for i, cat in enumerate(cats):
        is_active = st.session_state.active_cat == cat
        style = "menu-active" if is_active else "menu-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{style}">', unsafe_allow_html=True)
            if st.button(f"{icons[i]} {cat.upper()}", key=f"c_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = None
            st.markdown('</div>', unsafe_allow_html=True)

    # 5.2 - SUBCATEGORÍAS (Aparecen pegadas si hay categoría)
    if st.session_state.active_cat:
        sub_list = list(DATABASE[st.session_state.active_cat].keys())
        c_sub = st.columns(max(len(sub_list), 4))
        for i, sub in enumerate(sub_list):
            is_active = st.session_state.active_sub == sub
            style = "menu-active" if is_active else "menu-btn"
            with c_sub[i]:
                st.markdown(f'<div class="{style}">', unsafe_allow_html=True)
                if st.button(sub, key=f"s_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                st.markdown('</div>', unsafe_allow_html=True)

        # 5.3 - ACTIVOS (Aparecen pegados si hay subcategoría)
        if st.session_state.active_sub:
            items = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
            cols_act = st.columns(6)
            for idx, (name, data) in enumerate(items.items()):
                is_active = st.session_state.ticker_name == name
                style = "menu-active" if is_active else "menu-btn"
                with cols_act[idx % 6]:
                    st.markdown(f'<div class="{style}">', unsafe_allow_html=True)
                    if st.button(f"{data[1]} {name}", key=f"f_{name}", use_container_width=True):
                        st.session_state.ticker = data[0]
                        st.session_state.ticker_name = name
                    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 7: MONITOR
# =========================================================
st.markdown("<br>", unsafe_allow_html=True)
st.subheader(f"📊 MONITOR: {st.session_state.ticker_name}")
