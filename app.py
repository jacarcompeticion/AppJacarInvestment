import streamlit as st
import yfinance as yf
from openai import OpenAI
import os

# Título y Configuración
st.set_page_config(page_title="AppJacarInvestment", layout="wide")
st.title("🛡️ AppJacarInvestment: Estratega Pro")

# --- CONEXIÓN IA ---
# Aquí no usamos Secrets de Replit, usaremos los de Streamlit
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Tu Capital")
    capital = st.number_input("Saldo Bróker (USD)", value=1000.0)
    riesgo_per = st.slider("Riesgo por operación (%)", 0.5, 5.0, 1.0)
    st.divider()
    activos = {
        "Oro": "GC=F",
        "Petróleo Brent": "BZ=F",
        "Nasdaq 100": "^IXIC",
        "DAX 40": "^GDAXI",
        "EUR/USD": "EURUSD=X"
    }
    seleccion = st.selectbox("Activo a analizar", list(activos.keys()))

# --- PROCESO ---
ticker = activos[seleccion]
data = yf.download(ticker, period="2d", interval="15m")

if not data.empty:
    precio_act = data['Close'].iloc[-1].item()
    st.metric(f"Precio Actual {seleccion}", f"{precio_act:.2f}")

    if st.button("🧠 GENERAR ESTRATEGIA"):
        with st.spinner('Analizando...'):
            prompt = f"Activo: {seleccion}. Precio: {precio_act}. Capital: {capital}. Riesgo: {riesgo_per}%. Dame señal de Compra/Venta, LOTES exactos, Stop Loss y Take Profit."
            
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Eres un estratega de trading."},
                          {"role": "user", "content": prompt}]
            )
            st.success(resp.choices[0].message.content)
    
    st.line_chart(data['Close'])
