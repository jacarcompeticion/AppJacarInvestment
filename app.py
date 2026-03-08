import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Wolf Sovereign V94", layout="wide", page_icon="🐺")

# 2. INICIALIZACIÓN DE ESTADOS (Persistencia)
if 'view' not in st.session_state:
    st.session_state.view = "Lobo"
if 'active_cat' not in st.session_state:
    st.session_state.active_cat = "indices"
if 'ticker' not in st.session_state:
    st.session_state.ticker = "US100"

# 3. ESTILO DE BOTONES Y FONDO
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    
    /* Estilo botones navegación superior */
    div.stButton > button {
        background-color: #161b22; 
        color: #d4af37;           
        border: 1px solid #d4af37;
        border-radius: 8px;
        height: 3.5em;
        font-weight: bold;
    }
    
    div.stButton > button:hover {
        background-color: #d4af37;
        color: #05070a;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🐺 JACAR INVESTMENT SOVEREIGN")

# 4. BARRA DE NAVEGACIÓN PRINCIPAL (6 Apartados)
nav_cols = st.columns(6)

if nav_cols[0].button("🐺 LOBO", use_container_width=True):
    st.session_state.view = "Lobo"
if nav_cols[1].button("💼 XTB", use_container_width=True):
    st.session_state.view = "XTB"
if nav_cols[2].button("📈 RATIOS", use_container_width=True):
    st.session_state.view = "Ratios"
if nav_cols[3].button("🔮 PREDICCIONES", use_container_width=True):
    st.session_state.view = "Predicciones"
if nav_cols[4].button("📰 NOTICIAS", use_container_width=True):
    st.session_state.view = "Noticias"
if nav_cols[5].button("⚙️ AJUSTES", use_container_width=True):
    st.session_state.view = "Ajustes"

st.divider()

# 5. LÓGICA DE RENDERIZADO
if st.session_state.view == "Lobo":
    st.header("🐺 PANEL LOBO")

    # Mapeo de Activos XTB
    xtb_assets = {
        "indices": ["US100", "US500", "DE40", "SPA35", "UK100"],
        "stocks": ["NVDA.US", "TSLA.US", "AAPL.US", "MSFT.US", "SAN.MC", "BBVA.MC"],
        "material": ["GOLD", "SILVER", "OIL.WTI", "NATGAS"],
        "divisas": ["EURUSD", "GBPUSD", "USDJPY", "BITCOIN"]
    }

    # Selector de Categorías
    st.markdown("### 🗂️ Categorías")
    c_cat = st.columns(4)
    if c_cat[0].button("🏛️ INDICES", use_container_width=True): st.session_state.active_cat = "indices"
    if c_cat[1].button("📈 STOCKS", use_container_width=True): st.session_state.active_cat = "stocks"
    if c_cat[2].button("🏗️ MATERIAL", use_container_width=True): st.session_state.active_cat = "material"
    if c_cat[3].button("💱 DIVISAS", use_container_width=True): st.session_state.active_cat = "divisas"

    st.write(f"Categoría seleccionada: **{st.session_state.active_cat.upper()}**")
    st.divider()

    # Selector de Activos
    activos = xtb_assets[st.session_state.active_cat]
    c_act = st.columns(len(activos))
    for i, activo in enumerate(activos):
        if c_act[i].button(activo, key=f"btn_{activo}", use_container_width=True):
            st.session_state.ticker = activo

    st.markdown("---")
    st.subheader(f"📊 Activo seleccionado: {st.session_state.ticker}")
    st.info("Estructura de Ventana Lobo lista y limpia de errores.")

elif st.session_state.view == "XTB":
    st.header("💼 GESTIÓN XTB")

elif st.session_state.view == "Ratios":
    st.header("📈 RATIOS IA")

elif st.session_state.view == "Predicciones":
    st.header("🔮 PREDICCIONES")

elif st.session_state.view == "Noticias":
    st.header("📰 NOTICIAS")

elif st.session_state.view == "Ajustes":
    st.header("⚙️ AJUSTES")
