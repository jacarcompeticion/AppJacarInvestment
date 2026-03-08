import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="Wolf Sovereign V94", layout="wide", page_icon="🐺")

# CSS para mantener la estética Bloomberg/Lobo
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    .kpi-header { 
        background: #0d1117; border-bottom: 2px solid #d4af37; 
        padding: 20px; margin-bottom: 20px; text-align: center;
    }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INICIALIZACIÓN DE ESTADOS (Persistencia) ---
if 'view' not in st.session_state: st.session_state.view = "Dashboard"
if 'ticker' not in st.session_state: st.session_state.ticker = "NQ=F" # Nasdaq por defecto

# --- 3. BARRA DE NAVEGACIÓN ---
st.markdown('<div class="kpi-header"><h1>🐺 JACAR INVESTMENT SOVEREIGN</h1></div>', unsafe_allow_html=True)

col_nav = st.columns(4)
if col_nav[0].button("🏠 LOBO"): st.session_state.view = "Lobo"
if col_nav[1].button("💼 XTB"): st.session_state.view = "XTB"
if col_nav[2].button("📈 RATIOS"): st.session_state.view = "Ratios"
if col_nav[3].button("⚙️ AJUSTES"): st.session_state.view = "Ajustes"

st.divider()

# --- 4. LÓGICA DE VENTANAS ---

# VENTANA: LOBO (Gráficos Base)
if st.session_state.view == "Lobo":
    st.subheader(f"Monitor de Mercado: {st.session_state.ticker}")
    
    # Selector rápido para probar que el cambio de datos funciona
    c1, c2, c3 = st.columns(3)
    if c1.button("NASDAQ (US100)"): st.session_state.ticker = "NQ=F"
    if c2.button("ORO (GOLD)"): st.session_state.ticker = "GC=F"
    if c3.button("BITCOIN"): st.session_state.ticker = "BTC-USD"

    # Descarga limpia
    df = yf.download(st.session_state.ticker, period="2d", interval="15m", progress=False)
    
    if not df.empty:
        # Limpieza de columnas MultiIndex (Vital para evitar errores)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        st.write("✅ Datos cargados correctamente.")
        st.dataframe(df.tail(5), use_container_width=True)
    else:
        st.error("No se han podido recuperar datos. Revisa la conexión.")

# VENTANA: XTB (Simulación)
elif st.session_state.view == "XTB":
    st.subheader("💼 Terminal de Órdenes XTB")
    st.info("Módulo de conexión xAPI preparado para el Paso 3.")

# VENTANA: AJUSTES
elif st.session_state.view == "Ajustes":
    st.subheader("⚙️ Configuración del Sistema")
    st.number_input("Capital de la cuenta", value=18850.0)
    st.success("Ajustes detectados correctamente.")
