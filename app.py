import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Wolf Sovereign V94", layout="wide", page_icon="🐺")

# 2. INICIALIZACIÓN DE ESTADOS
if 'view' not in st.session_state: st.session_state.view = "Lobo"
if 'active_cat' not in st.session_state: st.session_state.active_cat = "indices"
if 'active_sub' not in st.session_state: st.session_state.active_sub = None
if 'ticker' not in st.session_state: st.session_state.ticker = "NQ=F"

# 3. ESTILO AVANZADO (Botones compactos y logos integrados)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    
    /* Botones de Navegación Superior */
    div.stButton > button {
        background-color: #161b22; color: #d4af37;           
        border: 1px solid #333; border-radius: 8px;
        height: 3em; font-weight: bold; font-size: 0.9rem;
    }
    div.stButton > button:hover { border-color: #d4af37; background-color: #1c2128; }

    /* Estilo para los botones de activos (más pequeños) */
    .asset-btn-container {
        display: flex;
        align-items: center;
        background-color: #161b22;
        border: 1px solid #333;
        border-radius: 5px;
        padding: 5px 10px;
        margin-bottom: 5px;
        cursor: pointer;
    }
    .asset-btn-container:hover { border-color: #d4af37; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS ESTRUCTURADA (Mapeo XTB -> Yahoo) ---
# Hemos actualizado las imágenes a iconos de alta disponibilidad
DATABASE = {
    "indices": {
        "EEUU": {
            "US100": ["NQ=F", "🇺🇸"],
            "US500": ["ES=F", "🇺🇸"]
        },
        "EUROPA": {
            "DE40": ["^GDAXI", "🇩🇪"],
            "SPA35": ["^IBEX", "🇪🇸"]
        }
    },
    "acciones": {
        "TECNOLOGÍA": {
            "NVDA.US": ["NVDA", "🟢"],
            "TSLA.US": ["TSLA", "🔴"],
            "AAPL.US": ["AAPL", "⚪"]
        },
        "BANCA ESPAÑA": {
            "SAN.MC": ["SAN.MC", "🔴"],
            "BBVA.MC": ["BBVA.MC", "🔵"]
        }
    },
    "material": {
        "METALES": {
            "GOLD": ["GC=F", "🟡"],
            "SILVER": ["SI=F", "⚪"]
        },
        "ENERGÍA": {
            "OIL.WTI": ["CL=F", "🛢️"],
            "OIL.BRENT": ["BZ=F", "🌍"],
            "NATGAS": ["NG=F", "🔥"]
        }
    },
    "divisas": {
        "MAJORS": {
            "EURUSD": ["EURUSD=X", "🇪🇺"],
            "GBPUSD": ["GBPUSD=X", "🇬🇧"]
        },
        "CRYPTO": {
            "BITCOIN": ["BTC-USD", "₿"]
        }
    }
}

st.title("🐺 JACAR INVESTMENT SOVEREIGN")

# 4. BARRA DE NAVEGACIÓN PRINCIPAL
nav_cols = st.columns(6)
titles = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
views = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]

for i, col in enumerate(nav_cols):
    if col.button(titles[i], use_container_width=True):
        st.session_state.view = views[i]
        st.session_state.active_sub = None

st.divider()

# 5. LÓGICA DE VENTANA LOBO
if st.session_state.view == "Lobo":
    # A. Categorías Principales
    c_cat = st.columns(4)
    cats = ["indices", "acciones", "material", "divisas"]
    icons = ["🏛️", "📈", "🏗️", "💱"]
    
    for i, cat in enumerate(cats):
        if c_cat[i].button(f"{icons[i]} {cat.upper()}", use_container_width=True):
            st.session_state.active_cat = cat
            st.session_state.active_sub = None

    # B. Subcategorías
    st.markdown(f"#### 📂 {st.session_state.active_cat.upper()}")
    subcats = list(DATABASE[st.session_state.active_cat].keys())
    c_sub = st.columns(max(len(subcats), 4))
    
    for i, sub in enumerate(subcats):
        if c_sub[i].button(sub, key=f"sub_{sub}", use_container_width=True):
            st.session_state.active_sub = sub

    # C. Activos Finales (Logo e Imagen dentro del texto del botón)
    if st.session_state.active_sub:
        st.divider()
        st.markdown(f"#### 💎 Selecciona Activo ({st.session_state.active_sub})")
        activos_dict = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
        
        # Mostramos los activos en columnas más pequeñas (5 por fila)
        cols_act = st.columns(5)
        for idx, (nombre_xtb, datos) in enumerate(activos_dict.items()):
            # El logo ahora va dentro del string del botón para asegurar que carga
            label = f"{datos[1]} {nombre_xtb}"
            if cols_act[idx % 5].button(label, key=f"f_{nombre_xtb}", use_container_width=True):
                st.session_state.ticker = datos[0]
                st.toast(f"Cargando {nombre_xtb}...")

    st.markdown("---")
    st.subheader(f"📊 Monitor: {st.session_state.ticker}")
    st.info("Estructura de activos compacta y Brent añadido correctamente.")

# Otras ventanas...
elif st.session_state.view == "Ajustes":
    st.header("⚙️ CONFIGURACIÓN")
    st.session_state.wallet = st.number_input("Wallet Inicial (€)", value=18850.0)
