import streamlit as st
import yfinance as yf

# =========================================================
# BLOQUE 1: CONFIGURACIÓN E IDENTIDAD (ESTILOS FORZADOS)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95", layout="wide", page_icon="🐺")

# CSS para forzar colores y eliminar espacios
st.markdown("""
    <style>
    /* Fondo y Reset de espacios */
    .stApp { background-color: #05070a; }
    [data-testid="stVerticalBlock"] { gap: 0rem !important; }
    div[data-testid="stColumn"] { padding: 0px !important; margin: 0px !important; }

    /* --- 1. VENTANAS (NAV SUPERIOR): MARRÓN CLARO (#D2B48C) --- */
    /* Botón Normal */
    div.nav-btn button {
        background-color: #D2B48C !important;
        color: #000000 !important;
        border: 1px solid #8B4513 !important;
        border-radius: 0px !important;
        height: 3.5em !important;
        font-weight: bold !important;
    }
    /* Botón Activo (Blanco) */
    div.nav-active button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 0px !important;
        height: 3.5em !important;
        font-weight: 900 !important;
    }

    /* --- 2. MENÚ LOBO (CATEGORÍAS/SUB/ACTIVOS): BLANCO -> NEGRO --- */
    /* Botón Normal (Blanco) */
    div.menu-btn button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #333333 !important;
        border-radius: 0px !important;
        height: 3.2em !important;
    }
    /* Botón Activo (Negro) */
    div.menu-active button {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 0px !important;
        height: 3.2em !important;
        font-weight: bold !important;
    }

    /* Ticker Animado */
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #000; 
        border-bottom: 2px solid #D2B48C; padding: 10px 0;
    }
    .ticker-move {
        display: flex; width: fit-content;
        animation: ticker 60s linear infinite;
    }
    .ticker-item {
        padding: 0 50px; white-space: nowrap; font-family: monospace; font-size: 1.1rem; color: #fff;
    }
    @keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# BLOQUE 2: ESTADOS Y BASE DE DATOS
# =========================================================
if 'setup' not in st.session_state:
    st.session_state.update({
        'view': "Lobo", 'active_cat': None, 'active_sub': None,
        'ticker': "NQ=F", 'ticker_name': "US100",
        'wallet': 18850.00, 'margen': 15200.00, 'pnl': 420.50, 'setup': True
    })

DATABASE = {
    "indices": {
        "EEUU": {"US100": ["NQ=F", "🇺🇸"], "US500": ["ES=F", "🇺🇸"]},
        "EUROPA": {"DE40": ["^GDAXI", "🇩🇪"], "SPA35": ["^IBEX", "🇪🇸"]}
    },
    "acciones": {
        "TECNOLOGÍA": {"NVDA.US": ["NVDA", "🟢"], "TSLA.US": ["TSLA", "🔴"]},
        "material": {"METALES": {"GOLD": ["GC=F", "🟡"]}, "ENERGÍA": {"OIL": ["CL=F", "🛢️"]}},
        "divisas": {"MAJORS": {"EURUSD": ["EURUSD=X", "🇪🇺"]}, "CRYPTO": {"BITCOIN": ["BTC-USD", "₿"]}}
    }
}

# =========================================================
# BLOQUE 3: HEADER (KPIs Y TICKER CON MODAL)
# =========================================================
st.markdown(f'<div style="background-color:#0d1117; padding:8px; display:flex; justify-content:space-around; border-bottom:1px solid #333; color:#D2B48C; font-weight:bold;">'
            f'<span>CAPITAL: {st.session_state.wallet:,.2f}€</span>'
            f'<span>MARGEN: {st.session_state.margen:,.2f}€</span>'
            f'<span>PnL: {st.session_state.pnl:,.2f}€</span></div>', unsafe_allow_html=True)

hot_list = [("NQ=F", "US100", "🇺🇸", "COMPRAR"), ("GC=F", "GOLD", "🟡", "COMPRAR")]
content = "".join([f'<div class="ticker-item">{i} {n} <span style="color:{"#00ff41" if s=="COMPRAR" else "#ff3131"};">[{s}]</span></div>' for t, n, i, s in hot_list * 10])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

with st.expander("🐺 ACCIÓN SENTINEL"):
    for t, n, i, s in hot_list:
        if st.button(f"VER ACCIÓN {n}", key=f"alert_{n}"):
            st.warning(f"ORDEN: {s} en {n}")

# =========================================================
# BLOQUE 4: NAVEGACIÓN (VENTANAS) - MARRÓN -> BLANCO
# =========================================================
nav_cols = st.columns(6)
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]

for i, col in enumerate(nav_cols):
    is_active = st.session_state.view == v_list[i]
    tag = "nav-active" if is_active else "nav-btn"
    with col:
        st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
        if st.button(btns[i], key=f"v_{i}", use_container_width=True):
            st.session_state.view = v_list[i]
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 5: VENTANA LOBO (CASCADA PEGADA - BLANCO -> NEGRO)
# =========================================================
if st.session_state.view == "Lobo":
    # 5.1 - CATEGORÍAS
    c_cat = st.columns(4)
    cats = ["indices", "acciones", "material", "divisas"]
    for i, cat in enumerate(cats):
        is_active = st.session_state.active_cat == cat
        tag = "menu-active" if is_active else "menu-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(cat.upper(), key=f"c_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = None
            st.markdown('</div>', unsafe_allow_html=True)

    # 5.2 - SUBCATEGORÍAS (Solo si hay categoría)
    if st.session_state.active_cat:
        sub_dict = DATABASE.get(st.session_state.active_cat, {})
        sub_list = list(sub_dict.keys())
        c_sub = st.columns(max(len(sub_list), 4))
        for i, sub in enumerate(sub_list):
            is_active = st.session_state.active_sub == sub
            tag = "menu-active" if is_active else "menu-btn"
            with c_sub[i]:
                st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                if st.button(sub, key=f"s_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                st.markdown('</div>', unsafe_allow_html=True)

        # 5.3 - ACTIVOS (Solo si hay subcategoría)
        if st.session_state.active_sub:
            items = sub_dict[st.session_state.active_sub]
            cols_act = st.columns(6)
            for idx, (name, data) in enumerate(items.items()):
                is_active = st.session_state.ticker_name == name
                tag = "menu-active" if is_active else "menu-btn"
                with cols_act[idx % 6]:
                    st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                    if st.button(name, key=f"f_{name}", use_container_width=True):
                        st.session_state.ticker = data[0]
                        st.session_state.ticker_name = name
                    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 7: MONITOR
# =========================================================
st.markdown("<br>", unsafe_allow_html=True)
st.subheader(f"📊 MONITOR: {st.session_state.ticker_name}")
