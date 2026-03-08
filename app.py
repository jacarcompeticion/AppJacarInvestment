import streamlit as st

# 1. Configuración de página (Mantenemos la base sólida)
st.set_page_config(page_title="Wolf Sovereign V94", layout="wide")

# 2. Inicialización del Estado de Navegación (Ahora con 6 secciones)
if 'active_cat' not in st.session_state: st.session_state.active_cat = "indices"
if 'ticker' not in st.session_state: st.session_state.ticker = "US100"

# 3. Identidad Visual y Estilo de Botones (Fondo diferente a las letras)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    
    /* Estilo para los botones de navegación */
    div.stButton > button {
        background-color: #161b22; /* Fondo oscuro grisáceo */
        color: #d4af37;           /* Letras doradas */
        border: 1px solid #d4af37;
        border-radius: 8px;
        height: 3.5em;
        font-weight: bold;
        transition: 0.3s;
    }
    
    div.stButton > button:hover {
        background-color: #d4af37; /* Fondo dorado al pasar el ratón */
        color: #05070a;           /* Letras negras al pasar el ratón */
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🐺 JACAR INVESTMENT SOVEREIGN")

# 4. Barra de Navegación (6 Apartados)
# Dividimos en 6 columnas para los nuevos apartados
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

# 5. Renderizado de Contenido según la selección
if st.session_state.view == "Lobo":
    st.header("🐺 PANEL LOBO")
    st.info("Estructura visual lista. ¿Pasamos a colocar el gráfico aquí?")if st.session_state.view == "Lobo":
    st.header("🐺 PANEL LOBO")

    # Mapeo de Activos (Requisito 9: XTB Names)
    # Nota: He configurado los nombres tal cual aparecen en XTB
    xtb_assets = {
        "indices": ["US100", "US500", "DE40", "SPA35", "UK100"],
        "stocks": ["NVDA.US", "TSLA.US", "AAPL.US", "MSFT.US", "SAN.MC", "BBVA.MC"],
        "material": ["GOLD", "SILVER", "OIL.WTI", "NATGAS"],
        "divisas": ["EURUSD", "GBPUSD", "USDJPY", "BITCOIN"]
    }

    # 1. Selector de Categorías (Separadas por completo)
    # Usamos un contenedor con fondo diferente para resaltar
    st.markdown("### 🗂️ Selecciona Categoría")
    c_cat = st.columns(4)
    if c_cat[0].button("🏛️ INDICES", use_container_width=True): st.session_state.active_cat = "indices"
    if c_cat[1].button("📈 STOCKS", use_container_width=True): st.session_state.active_cat = "stocks"
    if c_cat[2].button("🏗️ MATERIAL", use_container_width=True): st.session_state.active_cat = "material"
    if c_cat[3].button("💱 DIVISAS", use_container_width=True): st.session_state.active_cat = "divisas"

    st.markdown(f"**Categoría activa:** `{st.session_state.active_cat.upper()}`")
    st.divider()

    # 2. Selector de Activos (Aparece según la categoría elegida)
    st.markdown(f"### 🔎 Activos en {st.session_state.active_cat.upper()}")
    activos = xtb_assets[st.session_state.active_cat]
    
    # Creamos columnas dinámicas según el número de activos
    c_act = st.columns(len(activos))
    for i, activo in enumerate(activos):
        if c_act[i].button(activo, key=f"btn_{activo}", use_container_width=True):
            st.session_state.ticker = activo

    # 3. Espacio para el Gráfico (Paso siguiente)
    st.markdown("---")
    st.subheader(f"📊 Análisis Actual: {st.session_state.ticker}")
    st.info(f"Sistema preparado para cargar el gráfico de {st.session_state.ticker}. ¿Lo inyectamos ahora?")

elif st.session_state.view == "XTB":
    st.header("💼 GESTIÓN XTB")
    st.write("Estado de la cuenta y posiciones en tiempo real.")

elif st.session_state.view == "Ratios":
    st.header("📈 RATIOS IA")
    st.write("Análisis avanzado de métricas y rendimiento.")

elif st.session_state.view == "Predicciones":
    st.header("🔮 PREDICCIONES")
    st.write("Modelos predictivos de Sentinel para los próximos movimientos.")

elif st.session_state.view == "Noticias":
    st.header("📰 NOTICIAS")
    st.write("Feed de noticias geopolíticas y económicas.")

elif st.session_state.view == "Ajustes":
    st.header("⚙️ AJUSTES")
    st.write("Configuración de capital, riesgo y API keys.")
