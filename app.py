import streamlit as st
import yfinance as yf
import pandas as pd

# =========================================================
# BLOQUE 1: CONFIGURACIÓN E IDENTIDAD (ESTILOS Y CONTRASTE)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    
    /* BLOQUE 3: Ticker Animado Estilo Bolsa Antigua */
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #000; 
        border-bottom: 2px solid #d4af37; padding: 12px 0;
    }
    .ticker-move {
        display: flex; width: fit-content;
        animation: ticker 60s linear infinite;
    }
    .ticker-item {
        display: flex; align-items: center; gap: 10px;
        padding: 0 60px; white-space: nowrap; font-family: monospace; font-size: 1.2rem;
        cursor: pointer; color: #ffffff;
    }
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    /* ESTILO DE BOTONES: CONTRASTE REAL FONDO VS TEXTO */
    /* 1. Botón de Ventanas (Gris Oscuro / Texto Blanco) */
    .nav-btn > div > button {
        background-color: #1c2128 !important; color: #ffffff !important;
        border: 1px solid #444 !important; height: 3.2em;
    }

    /* 2. Botón Categoría (Negro Sólido / Texto Dorado) */
    .cat-btn > div > button {
        background-color: #000000 !important; color: #d4af37 !important;
        border: 1px solid #d4af37 !important; height: 3.5em; font-weight: bold;
    }
    
    /* 3. Botón ACTIVO (Fondo Dorado / Texto Negro) */
    .active-btn > div > button {
        background-color: #d4af37 !important; color: #000000 !important;
        font-weight: 900 !important; border: 1px solid #ffffff !important;
    }

    /* Eliminar espacios de los expanders para que parezcan ventanas limpias */
    .stExpander { border: none !important; background: transparent !important; }
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
# BLOQUE 3: HEADER (KPIs Y TICKER FLOTANTE)
# =========================================================
pnl_color = "#00ff41" if st.session_state.pnl >= 0 else "#ff3131"
st.markdown(f"""
    <div style="background-color:#0d1117; padding:10px; display:flex; justify-content:space-around; border-bottom:1px solid #333;">
        <span>CAPITAL: <span style="color:#d4af37; font-weight:bold;">{st.session_state.wallet:,.2f}€</span></span>
        <span>MARGEN: <span style="color:#d4af37; font-weight:bold;">{st.session_state.margen:,.2f}€</span></span>
        <span>PnL: <span style="color:{pnl_color}; font-weight:bold;">{st.session_state.pnl:,.2f}€</span></span>
    </div>
    """, unsafe_allow_html=True)

# Ticker interactivo
hot_list = [("NQ=F", "US100", "🇺🇸", "COMPRAR"), ("GC=F", "GOLD", "🟡", "COMPRAR"), ("BTC-USD", "BITCOIN", "₿", "VENDER")]
content = "".join([f'<div class="ticker-item">{i} {n} <span style="color:{"#00ff41" if s=="COMPRAR" else "#ff3131"};">[{s}]</span></div>' for t, n, i, s in hot_list * 8])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# Ventana Flotante de Acción (Trigger)
with st.expander("🐺 ACCIÓN RECOMENDADA SENTINEL (Pulsa para desplegar)"):
    st.write("Selecciona el activo del ticker para ver la orden:")
    cols_flot = st.columns(len(hot_list))
    for idx, (t, n, i, s) in enumerate(hot_list):
        if cols_flot[idx].button(f"{i} Ver {n}", key=f"alert_{n}", use_container_width=True):
            st.session_state.ticker = t
            st.session_state.ticker_name = n
            st.warning(f"⚠️ ORDEN SENTINEL: {s} en {n}. Ejecución inmediata sugerida.")

# =========================================================
# BLOQUE 4: NAVEGACIÓN SUPERIOR (VENTANAS)
# =========================================================
nav = st.columns(6)
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]

for i, col in enumerate(nav):
    is_active = st.session_state.view == v_list[i]
    style = "active-btn" if is_active else "nav-btn"
    with col:
        st.markdown(f'<div class="{style}">', unsafe_allow_html=True)
        if st.button(btns[i], key=f"nav_{v_list[i]}", use_container_width=True):
            st.session_state.view = v_list[i]
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 5: VENTANA LOBO (CASCADA LIMPIA SIN MENSAJES)
# =========================================================
if st.session_state.view == "Lobo":
    st.write("") # Separación estándar
    
    # 5.1 - CATEGORÍAS
    c_cat = st.columns(4)
    cats = ["indices", "acciones", "material", "divisas"]
    icons = ["🏛️", "📈", "🏗️", "💱"]
    for i, cat in enumerate(cats):
        is_active = st.session_state.active_cat == cat
        style = "active-btn" if is_active else "cat-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{style}">', unsafe_allow_html=True)
            if st.button(f"{icons[i]} {cat.upper()}", key=f"c_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = None
            st.markdown('</div>', unsafe_allow_html=True)

    # 5.2 - SUBCATEGORÍAS (Solo si hay categoría)
    if st.session_state.active_cat:
        st.write("") # Separación idéntica
        sub_list = list(DATABASE[st.session_state.active_cat].keys())
        c_sub = st.columns(max(len(sub_list), 4))
        for i, sub in enumerate(sub_list):
            is_active = st.session_state.active_sub == sub
            style = "active-btn" if is_active else "nav-btn"
            with c_sub[i]:
                st.markdown(f'<div class="{style}">', unsafe_allow_html=True)
                if st.button(sub, key=f"s_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                st.markdown('</div>', unsafe_allow_html=True)

        # 5.3 - ACTIVOS (Solo si hay subcategoría)
        if st.session_state.active_sub:
            st.write("") # Separación idéntica
            items = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
            cols_act = st.columns(6)
            for idx, (name, data) in enumerate(items.items()):
                is_active = st.session_state.ticker_name == name
                style = "active-btn" if is_active else "nav-btn"
                with cols_act[idx % 6]:
                    st.markdown(f'<div class="{style}">', unsafe_allow_html=True)
                    if st.button(f"{data[1]} {name}", key=f"f_{name}", use_container_width=True):
                        st.session_state.ticker = data[0]
                        st.session_state.ticker_name = name
                    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 7: MONITOR FINAL
# =========================================================
st.markdown("---")
st.subheader(f"📊 MONITOR: {st.session_state.ticker_name}")
