import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from openai import OpenAI
import os

st.set_page_config(page_title="AppJacarInvestment", layout="wide")
st.title("🛡️ AppJacarInvestment: Terminal de Ejecución")

# --- CONEXIÓN IA ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración de Cuenta")
    capital = st.number_input("Capital en Cuenta (USD)", value=18000.0)
    riesgo_per = st.slider("Riesgo por operación (%)", 0.1, 5.0, 1.0)
    st.divider()
    activos = {
        "Oro": "GC=F",
        "Petróleo Brent": "BZ=F",
        "Nasdaq 100": "^IXIC",
        "DAX 40": "^GDAXI",
        "EUR/USD": "EURUSD=X"
    }
    seleccion = st.selectbox("Activo a analizar", list(activos.keys()))

# --- OBTENCIÓN DE DATOS ---
ticker = activos[seleccion]
# Traemos datos de 15 min para precisión intradía
data = yf.download(ticker, period="3d", interval="15m")

if not data.empty:
    # Último precio y variaciones
    precio_act = data['Close'].iloc[-1].item()
    high_24h = data['High'].max()
    low_24h = data['Low'].min()

    col1, col2, col3 = st.columns(3)
    col1.metric("Precio Actual", f"{float(precio_act):.4f}")
    col2.metric("Máximo Reciente", f"{float(high_24h):.4f}")
    col3.metric("Mínimo Reciente", f"{float(low_24h):.4f}")

    # --- GRÁFICO DE VELAS PROFESIONAL ---
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                open=data['Open'], high=data['High'],
                low=data['Low'], close=data['Close'],
                name="Velas")])
    fig.update_layout(title=f"Gráfico de Velas - {seleccion}", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

    # --- BOTÓN DE EJECUCIÓN IA ---
    if st.button("🚀 OBTENER ORDEN DE MERCADO DIRECTA"):
        with st.spinner('IA analizando tendencia y calculando pips...'):
            # Enviamos a la IA los últimos 10 cierres para que vea la dirección
            ultimos_precios = data['Close'].tail(10).tolist()
            
            prompt = f"""
            Eres un trader algorítmico profesional. 
            ACTIVO: {seleccion} (Precio actual: {precio_act:.4f})
            CONTEXTO: Máximo reciente {high_24h:.4f}, Mínimo reciente {low_24h:.4f}.
            ÚLTIMOS CIERRES (15min): {ultimos_precios}
            CAPITAL: {capital} USD. RIESGO: {riesgo_per}%.

            REGLAS:
            1. No des consejos genéricos. 
            2. Decide: COMPRA, VENTA o ESPERAR.
            3. Si decides operar, dame:
               - Punto de entrada exacto.
               - Volumen en LOTES (calculado con un SL técnico).
               - Stop Loss (SL) y Take Profit (TP) con valores de precio exactos.
            4. Si decides ESPERAR, dime el precio exacto donde pondrías una orden PENDIENTE (Buy Limit/Sell Limit).
            """
            
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Actúa como un ejecutor de señales de trading preciso y directo."},
                          {"role": "user", "content": prompt}]
            )
            
            st.markdown("### 📋 ORDEN DE OPERACIÓN")
            st.info(resp.choices[0].message.content)

else:
    st.error("Error al cargar datos de Yahoo Finance.")
