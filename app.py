import streamlit as st

# RESET ABSOLUTO - BORRA TODO LO ANTERIOR
st.set_page_config(page_title="Reset", layout="wide")

st.title("⚠️ ESTADO: RESET TOTAL")
st.write("Si ves este mensaje, hemos limpiado el código 'basura'.")

# Un selector ultra simple para comprobar que la web responde
menu = st.sidebar.radio("MENÚ DE EMERGENCIA", ["LIMPIEZA", "PASO 1"])

if menu == "LIMPIEZA":
    st.success("Caché y código viejo eliminados.")
    st.info("Dime 'ESTAMOS LIMPIOS' para meter la primera pieza real.")

if menu == "PASO 1":
    st.header("Esperando instrucciones...")
    st.write("Tú dime qué es lo primero que quieres ver (¿Velas? ¿Botones? ¿Capital?)")
