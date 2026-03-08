import streamlit as st

# 1. Configuración de página (Única)
st.set_page_config(page_title="Wolf Sovereign V94", layout="wide")

# 2. Inicialización del Estado (Para que no se pierda la ventana al hacer clic)
if 'view' not in st.session_state:
    st.session_state.view = "Lobo"

# 3. Identidad Visual (CSS Mínimo)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    .nav-button { border: 1px solid #d4af37 !important; color: #d4af37 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🐺 JACAR INVESTMENT SOVEREIGN")

# 4. Barra de Navegación con Botones
col1, col2, col3, col4 = st.columns(4)

if col1.button("🏠 LOBO", use_container_width=True):
    st.session_state.view = "Lobo"

if col2.button("💼 XTB", use_container_width=True):
    st.session_state.view = "XTB"

if col3.button("📈 RATIOS", use_container_width=True):
    st.session_state.view = "Ratios"

if col4.button("⚙️ AJUSTES", use_container_width=True):
    st.session_state.view = "Ajustes"

st.divider()

# 5. Renderizado de Contenido
if st.session_state.view == "Lobo":
    st.header("📍 VENTANA: LOBO")
    st.info("Listo para el siguiente paso. ¿Qué ponemos aquí primero?")

elif st.session_state.view == "XTB":
    st.header("📍 VENTANA: XTB")
    st.write("Control de posiciones reales.")

elif st.session_state.view == "Ratios":
    st.header("📍 VENTANA: RATIOS")
    st.write("Métricas de rendimiento IA.")

elif st.session_state.view == "Ajustes":
    st.header("📍 VENTANA: AJUSTES")
    st.write("Configuración de Capital y Riesgo.")
