import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from openai import OpenAI
import os
from streamlit_autorefresh import st_autorefresh

# Refrescar la app automáticamente cada 60 segundos
count = st_autorefresh(interval=60000, limit=100, key="framer")


# 1. Configuración de página
st.set_page_config(page_title="AppJacarInvestment", layout="wide")
st.title("🛡️ AppJacarInvestment: Terminal Pro")

# 2. Conexión con OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 3. Panel Lateral
with st.sidebar:
    st.header("💰 Cuenta")
    capital = st.number_input("Capital (USD)", value=18000.0)
    riesgo_per = st.slider("Riesgo (%)", 0.1, 5.0, 1.0)
    st.divider()
    activos = {
        "Oro": "GC=F",
        "Petróleo Brent": "BZ=F",
        "Nasdaq 100": "^IXIC",
        "DAX 40": "^GDAXI",
        "EUR/USD": "EURUSD=X"
    }
    seleccion = st.selectbox("Activo", list(activos.keys()))

# 4. Descarga y Limpieza de Datos (IMPORTANTE)
ticker = activos[seleccion]
df = yf.download(ticker, period="5d", interval="15m")

if not df.empty:
    # --- TRUCO PARA ARREGLAR LAS COLUMNAS ---
    # Si Yahoo manda columnas dobles, esto las aplana a nombres simples: 'Open', 'Close', etc.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.dropna()

    # Precios clave
    precio_act = float(df['Close'].iloc[-1])
    high_recent = float(df['High'].max())
    low_recent = float(df['Low'].min())

    col1, col2, col3 = st.columns(3)
    col1.metric("Precio Actual", f"{precio_act:.4f}")
    col2.metric("Máximo", f"{high_recent:.4f}")
    col3.metric("Mínimo", f"{low_recent:.4f}")

    # 5. Gráfico de Velas con Auto-Zoom
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    )])
    
    fig.update_layout(
        template="plotly_dark",
        height=500,
        xaxis_rangeslider_visible=False,
        yaxis=dict(autorange=True, fixedrange=False, side="right", tickformat=".4f"),
        margin=dict(l=20, r=50, t=30, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 6. Orden Directa de la IA
    if st.button("🚀 OBTENER ORDEN DE MERCADO DIRECTA"):
        with st.spinner('Analizando tendencia...'):
            # Tomamos los últimos 20 cierres para que la IA vea la acción del precio
            precios_lista = df['Close'].tail(20).tolist()
            
            prompt = f"""
            Eres un TRADER EJECUTOR. No des consejos, da una ORDEN DE TRADING.
            ACTIVO: {seleccion} a {precio_act:.4f}.
            Contexto: Max {high_recent:.4f}, Min {low_recent:.4f}.
            Últimos cierres: {precios_lista}
            Capital: {capital} USD. Riesgo: {riesgo_per}%.

            RESPONDE CON ESTE FORMATO:
            - ACCIÓN: [COMPRA / VENTA / ESPERAR]
            - ENTRADA: [Precio]
            - LOTES: [Cálculo exacto]
            - STOP LOSS: [Precio]
            - TAKE PROFIT: [Precio]
            - MOTIVO: [Breve frase técnica]
            """
            
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": "Solo das órdenes directas de trading basadas en datos técnicos."},
                              {"role": "user", "content": prompt}]
            )
                st.info(resp.choices[0].message.content)
            except Exception as e:
                st.error(f"Error IA: {e}")
else:
    st.warning("Mercado cerrado o sin datos. Prueba con el Oro.")
