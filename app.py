import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# 1. Configuración de Página
st.set_page_config(page_title="Wolf v94 - Step 1", layout="wide")

# 2. Persistencia de Ventanas (El corazón de la navegación)
if 'view' not in st.session_state: st.session_state.view = "Lobo"
if 'ticker' not in st.session_state: st.session_state.ticker = "NQ=F" # US100

# 3. Estilos CSS Básicos (Bloomberg Style)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    .nav-bar { display: flex; gap: 10px; margin-bottom: 20px; }
    .kpi-header { background: #0d1117; border-bottom: 2px solid #d4af37; padding: 15px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 4. Header de Control
st.markdown('<div class="kpi-header"><h2>🐺 Wolf Sovereign Terminal</h2></div>', unsafe_allow_html=True)

# 5. Barra de Navegación Real (Paso a paso)
col_nav = st.columns(4)
if col_nav[0].button("🏠 LOBO (Gráficos)", use_container_width=True): st.session_state.view = "Lobo"
if col_nav[1].button("💼 XTB (Órdenes)", use_container_width=True): st.session_state.view = "XTB"
if col_nav[2].button("⚙️ AJUSTES", use_container_width=True): st.session_state.view = "Ajustes"
if col_nav[3].button("🧪 AUDITORÍA", use_container_width=True): st.session_state.view = "Audit"

# ==========================================
# VISTA 1: LOBO (EL MOTOR GRÁFICO)
# ==========================================
if st.session_state.view == "Lobo":
    st.subheader(f"Análisis en Vivo: {st.session_state.ticker}")
    
    # Selector rápido de activos
    c1, c2, c3 = st.columns(3)
    if c1.button("Nasdaq (US100)"): st.session_state.ticker = "NQ=F"
    if c2.button("Oro (GOLD)"): st.session_state.ticker = "GC=F"
    if c3.button("Bitcoin"): st.session_state.ticker = "BTC-USD"

    # Descarga de datos con LIMPIEZA TOTAL
    df = yf.download(st.session_state.ticker, period="5d", interval="15m", progress=False)
    
    if not df.empty:
        # Aplanar MultiIndex (Esto evita que el gráfico salga en blanco)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Gráfico de Velas
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name="Velas Reales"
        )])
        
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error("Error cargando datos de Yahoo Finance. Reintenta en unos segundos.")

# ==========================================
# VISTA 2: XTB (SIMULACIÓN DE ÓRDENES)
# ==========================================
elif st.session_state.view == "XTB":
    st.subheader("💼 Gestión de Cartera XTB")
    st.info("Aquí conectaremos la xAPI de XTB en el siguiente paso.")
    st.table(pd.DataFrame({"Activo": ["US100"], "Estado": ["Protegido"], "PnL": ["+240€"]}))

# ==========================================
# VISTA 3: AJUSTES
# ==========================================
elif st.session_state.view == "Ajustes":
    st.subheader("⚙️ Configuración de Capital")
    st.number_input("Capital Inicial (€)", value=18850.0)
    st.slider("Riesgo por Operación (%)", 0.1, 5.0, 1.5)

# ==========================================
# VISTA 4: AUDITORÍA
# ==========================================
elif st.session_state.view == "Audit":
    st.subheader("🧪 Logs del Sistema")
    st.code(f"[{datetime.now()}] Sistema iniciado correctamente.\n[{datetime.now()}] Vista actual: {st.session_state.view}")
