import streamlit as st

# 1. Configuración de página (Solo puede haber una en todo el código)
st.set_page_config(page_title="Wolf Reset V1", layout="wide")

# 2. Inicializar el estado de la vista (Si no existe, la creamos)
if 'view' not in st.session_state:
    st.session_state.view = "Lobo"

# 3. Título del Proyecto
st.title("🐺 Wolf Sovereign - Start from Zero")

# 4. Los Botones de Navegación
# Usamos columnas para que queden en fila
c1, c2, c3, c4 = st.columns(4)

if c1.button("🏠 LOBO", use_container_width=True):
    st.session_state.view = "Lobo"

if c2.button("💼 XTB", use_container_width=True):
    st.session_state.view = "XTB"

if c3.button("📈 RATIOS", use_container_width=True):
    st.session_state.view = "Ratios"

if c4.button("⚙️ AJUSTES", use_container_width=True):
    st.session_state.view = "Ajustes"

st.divider()

# 5. El "Cuerpo" que cambia según el botón pulsado
if st.session_state.view == "Lobo":
    st.header("📍 Estás en: VENTANA LOBO")
    st.write("Aquí irá el gráfico y el Sentinel.")

elif st.session_state.view == "XTB":
    st.header("📍 Estás en: VENTANA XTB")
    st.write("Aquí irán tus posiciones abiertas.")

elif st.session_state.view == "Ratios":
    st.header("📍 Estás en: VENTANA RATIOS")
    st.write("Aquí irán las métricas de rendimiento.")

elif st.session_state.view == "Ajustes":
    st.header("📍 Estás en: VENTANA AJUSTES")
    st.write("Aquí configurarás tu capital y riesgo.")
