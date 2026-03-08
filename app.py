import streamlit as st

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Wolf Sovereign V94", layout="wide", page_icon="🐺")

# 2. INICIALIZACIÓN DE ESTADOS
if 'view' not in st.session_state: st.session_state.view = "Lobo"
if 'active_cat' not in st.session_state: st.session_state.active_cat = "indices"
if 'active_sub' not in st.session_state: st.session_state.active_sub = None
if 'ticker' not in st.session_state: st.session_state.ticker = "US100"

# 3. ESTILO DE BOTONES
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    div.stButton > button {
        background-color: #161b22; color: #d4af37;           
        border: 1px solid #333; border-radius: 8px;
        height: 3.5em; font-weight: bold;
    }
    div.stButton > button:hover { border-color: #d4af37; background-color: #1c2128; }
    .asset-card { display: flex; align-items: center; gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS ESTRUCTURADA (Mapeo XTB -> Yahoo) ---
# Formato: "Nombre XTB": ["Ticker Yahoo", "URL Logo"]
DATABASE = {
    "indices": {
        "EEUU": {
            "US100": ["NQ=F", "https://cryptologos.cc/logos/usd-coin-usdc-logo.png"],
            "US500": ["ES=F", "https://cryptologos.cc/logos/usd-coin-usdc-logo.png"]
        },
        "EUROPA": {
            "DE40": ["^GDAXI", "https://flagcdn.com/w40/de.png"],
            "SPA35": ["^IBEX", "https://flagcdn.com/w40/es.png"]
        }
    },
    "acciones": {
        "TECNOLOGÍA": {
            "NVDA.US": ["NVDA", "https://logo.clearbit.com/nvidia.com"],
            "TSLA.US": ["TSLA", "https://logo.clearbit.com/tesla.com"],
            "AAPL.US": ["AAPL", "https://logo.clearbit.com/apple.com"]
        },
        "BANCA ESPAÑA": {
            "SAN.MC": ["SAN.MC", "https://logo.clearbit.com/santander.com"],
            "BBVA.MC": ["BBVA.MC", "https://logo.clearbit.com/bbva.com"]
        }
    },
    "material": {
        "METALES": {
            "GOLD": ["GC=F", "https://cdn-icons-png.flaticon.com/512/272/272530.png"],
            "SILVER": ["SI=F", "https://cdn-icons-png.flaticon.com/512/4343/4343033.png"]
        },
        "ENERGÍA": {
            "OIL.WTI": ["CL=F", "https://cdn-icons-png.flaticon.com/512/2967/2967562.png"],
            "NATGAS": ["NG=F", "https://cdn-icons-png.flaticon.com/512/1500/1500465.png"]
        }
    },
    "divisas": {
        "MAJORS": {
            "EURUSD": ["EURUSD=X", "https://flagcdn.com/w40/eu.png"],
            "GBPUSD": ["GBPUSD=X", "https://flagcdn.com/w40/gb.png"]
        },
        "CRYPTO": {
            "BITCOIN": ["BTC-USD", "https://cryptologos.cc/logos/bitcoin-btc-logo.png"]
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
        st.session_state.active_sub = None # Reset subcat al cambiar de vista

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
            st.session_state.active_sub = None # Reset subcat al elegir nueva categoría

    # B. Subcategorías (Solo aparecen si hay una categoría elegida)
    st.markdown(f"#### 📂 Subcategorías en {st.session_state.active_cat.upper()}")
    subcats = list(DATABASE[st.session_state.active_cat].keys())
    c_sub = st.columns(len(subcats))
    
    for i, sub in enumerate(subcats):
        if c_sub[i].button(sub, key=f"sub_{sub}", use_container_width=True):
            st.session_state.active_sub = sub

    # C. Activos Finales (Con Logo y Nombre XTB)
    if st.session_state.active_sub:
        st.divider()
        st.markdown(f"#### 💎 Activos en {st.session_state.active_sub}")
        activos_dict = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
        
        # Mostramos los activos como botones con imagen al lado
        for nombre_xtb, datos in activos_dict.items():
            col_img, col_btn = st.columns([0.1, 0.9])
            col_img.image(datos[1], width=35)
            if col_btn.button(nombre_xtb, key=f"final_{nombre_xtb}", use_container_width=True):
                st.session_state.ticker = datos[0] # Aquí guardamos el ticker de Yahoo para el gráfico
                st.success(f"Seleccionado: {nombre_xtb} (Yahoo: {datos[0]})")

    st.markdown("---")
    st.info(f"Sistema listo para graficar **{st.session_state.ticker}**")

# Otras ventanas vacías por ahora...
elif st.session_state.view == "XTB": st.header("💼 GESTIÓN XTB")
elif st.session_state.view == "Ratios": st.header("📈 RATIOS IA")
elif st.session_state.view == "Predicciones": st.header("🔮 PREDICCIONES")
elif st.session_state.view == "Noticias": st.header("📰 NOTICIAS")
elif st.session_state.view == "Ajustes": st.header("⚙️ AJUSTES")
