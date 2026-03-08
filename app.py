import streamlit as st

# 1. Configuración básica
st.set_page_config(page_title="Wolf Reset", layout="wide")

# 2. Inicializar el estado de la vista si no existe
if 'view' not in st.session_state:
    st.session_state.view = "Lobo"

# 3. Estética mínima para ver los botones
st.markdown("### 🐺 Wolf Sovereign - Modo Reset")

# 4. Barra de Navegación (Botones que cambian el estado)
col1, col2, col3, col4 = st.columns(4)

if col1.button("🏠 LOBO"):
    st.session_state.view = "Lobo"

if col2.button("💼 XTB"):
    st.session_state.view = "XTB"

if col3.button("📈 RATIOS"):
    st.session_state.view = "Ratios"

if col4.button("⚙️ AJUSTES"):
    st.session_state.view = "Ajustes"

st.divider()

# 5. Renderizado de Ventanas según el estado
if st.session_state.view == "Lobo":
    st.header("Ventana: LOBO")
    st.write("Estado actual: Visualizando Dashboard Principal")

elif st.session_state.view == "XTB":
    st.header("Ventana: XTB")
    st.write("Estado actual: Conectando con Broker")

elif st.session_state.view == "Ratios":
    st.header("Ventana: RATIOS")
    st.write("Estado actual: Análisis de Métricas")

elif st.session_state.view == "Ajustes":
    st.header("Ventana: AJUSTES")
    st.write("Estado actual: Configuración de Capital")
