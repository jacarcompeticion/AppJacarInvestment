import streamlit as st
import yfinance as yf

# =========================================================
# BLOQUE 1: MOTOR DE ESTILOS (COLORES FIJOS Y ESPACIADO 0)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    /* Fondo General */
    .stApp { background-color: #05070a; }
    
    /* ELIMINAR GAPS ENTRE FILAS PARA CASCADA PEGADA */
    [data-testid="stVerticalBlock"] { gap: 0rem !important; }
    div[data-testid="stColumn"] { padding: 0px !important; margin: 0px !important; }

    /* --- 1. VENTANAS (NAV SUPERIOR): MARRÓN -> BLANCO (FIJADO) --- */
    div.nav-btn button {
        background-color: #A67B5B !important; color: #000000 !important;
        border: 1px solid #000 !important; border-radius: 0px !important; height: 3.5em !important;
    }
    div.nav-active button {
        background-color: #FFFFFF !important; color: #000000 !important;
        border: 2px solid #000000 !important; border-radius: 0px !important; height: 3.5em !important; font-weight: 900 !important;
    }

    /* --- 2. MENÚ LOBO (CATEGORÍAS/SUB/ACTIVOS): BLANCO -> NEGRO (FIJADO) --- */
    div.menu-btn button {
        background-color: #FFFFFF !important; color: #000000 !important;
        border: 1px solid #333333 !important; border-radius: 0px !important; height: 3em !important;
    }
    div.menu-active button {
        background-color: #000000 !important; color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important; border-radius: 0px !important; height: 3em !important; font-weight: bold !important;
    }

    /* --- 3. ACCIÓN SENTINEL: FONDO ROJO / LETRAS NEGRAS --- */
    div.sentinel-btn button {
        background-color: #FF0000 !important; color: #000000 !important;
        border: 2px solid #000000 !important; font-weight: 900 !important; height: 4em !important;
        margin-bottom: 10px !important;
    }

    /* Espaciado para evitar solapamiento */
    .sentinel-space { margin-top: 60px !important; margin-bottom: 20px !important; }

    /* Ticker Animado */
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #000; border-bottom: 2px solid #A67B5B; padding: 10px 0;
    }
    .ticker-move { display: flex; width: fit-content; animation: ticker 60s linear infinite; }
    .ticker-item { padding: 0 50px; white-space: nowrap; font-family: monospace; font-size: 1.1rem; color: #fff; }
    @keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# BLOQUE 2: BASE DE DATOS (3 SUBS / 10 ACTIVOS POR SUB)
# =========================================================
if 'setup' not in st.session_state:
    st.session_state.update({
        'view': "Lobo", 'active_cat': None, 'active_sub': None,
        'ticker': "NQ=F", 'ticker_name': "US100",
        'wallet': 18850.00, 'margen': 15200.00, 'pnl': 420.50, 'setup': True
    })

# Generador dinámico para rellenar los 10 activos solicitados
def gen_assets(cat_name, sub_name):
    return {f"{cat_name}.{sub_name}.{i}": [f"TICK{i}", "📊"] for i in range(1, 11)}

DATABASE = {
    "stocks": {
        "TECNOLOGÍA": gen_assets("STK", "TECH"),
        "BANCA": gen_assets("STK", "BANK"),
        "ENERGÍA": gen_assets("STK", "ENER")
    },
    "indices": {
        "EEUU": gen_assets("IDX", "USA"),
        "EUROPA": gen_assets("IDX", "EU"),
        "ASIA": gen_assets("IDX", "ASIA")
    },
    "material": {
        "METALES": gen_assets("MAT", "MET"),
        "GRANOS": gen_assets("MAT", "GRA"),
        "SOFT": gen_assets("MAT", "SOFT")
    },
    "divisas": {
        "MAJORS": gen_assets("DIV", "MAJ"),
        "MINORS": gen_assets("DIV", "MIN"),
        "CRYPTO": gen_assets("DIV", "CRYP")
    }
}

# =========================================================
# BLOQUE 3: HEADER Y TICKER
# =========================================================
st.markdown(f'<div style="background-color:#0d1117; padding:8px; display:flex; justify-content:space-around; border-bottom:1px solid #333; color:#A67B5B; font-weight:bold;">'
            f'<span>CAPITAL: {st.session_state.wallet:,.2f}€</span>'
            f'<span>MARGEN: {st.session_state.margen:,.2f}€</span>'
            f'<span>PnL: {st.session_state.pnl:,.2f}€</span></div>', unsafe_allow_html=True)

hot_list = [("NQ=F", "US100", "🇺🇸", "COMPRAR"), ("GC=F", "GOLD", "🟡", "COMPRAR")]
content = "".join([f'<div class="ticker-item">{i} {n} <span style="color:{"#00ff41" if s=="COMPRAR" else "#ff3131"};">[{s}]</span></div>' for t, n, i, s in hot_list * 10])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# ESPACIADO Y ACCIÓN SENTINEL (FONDO ROJO)
st.markdown('<div class="sentinel-space"></div>', unsafe_allow_html=True)
with st.expander("🚨 ALERTAS CRÍTICAS SENTINEL (Click para Acción)"):
    c_sen = st.columns(len(hot_list))
    for idx, (t, n, i, s) in enumerate(hot_list):
        with c_sen[idx]:
            st.markdown('<div class="sentinel-btn">', unsafe_allow_html=True)
            if st.button(f"EJECUTAR {s}: {n}", key=f"sen_{n}"):
                st.warning(f"ORDEN SENTINEL LANZADA: {s} EN {n}")
            st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 4: NAVEGACIÓN (VENTANAS) - FIJADO MARRÓN/BLANCO
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
# BLOQUE 5: VENTANA LOBO (CASCADA PEGADA - FIJADO BLANCO/NEGRO)
# =========================================================
if st.session_state.view == "Lobo":
    # 5.1 - CATEGORÍAS (Stocks, Indices, Material, Divisas)
    cats = list(DATABASE.keys())
    c_cat = st.columns(len(cats))
    for i, cat in enumerate(cats):
        is_active = st.session_state.active_cat == cat
        tag = "menu-active" if is_active else "menu-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(cat.upper(), key=f"c_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = None # Limpiar sub al cambiar cat
            st.markdown('</div>', unsafe_allow_html=True)

    # 5.2 - SUBCATEGORÍAS (Solo aparecen si hay categoría)
    if st.session_state.active_cat:
        sub_dict = DATABASE[st.session_state.active_cat]
        sub_list = list(sub_dict.keys())
        c_sub = st.columns(len(sub_list))
        for i, sub in enumerate(sub_list):
            is_active = st.session_state.active_sub == sub
            tag = "menu-active" if is_active else "menu-btn"
            with c_sub[i]:
                st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                if st.button(sub, key=f"s_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                st.markdown('</div>', unsafe_allow_html=True)

        # 5.3 - ACTIVOS (10 por subcategoría en rejilla pegada)
        if st.session_state.active_sub:
            items = sub_dict[st.session_state.active_sub]
            # Usamos 5 columnas para que los 10 activos queden en 2 filas exactas
            cols_act = st.columns(5)
            for idx, (name, data) in enumerate(items.items()):
                is_active = st.session_state.ticker_name == name
                tag = "menu-active" if is_active else "menu-btn"
                with cols_act[idx % 5]:
                    st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                    if st.button(name, key=f"f_{name}", use_container_width=True):
                        st.session_state.ticker = data[0]
                        st.session_state.ticker_name = name
                    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 7: MONITOR FINAL
# =========================================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.subheader(f"📊 MONITOR: {st.session_state.ticker_name}")
