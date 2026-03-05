import streamlit as st
import yfinance as yf 
import pandas as pd
import plotly.graph_objects as go
from openai import OpenAI
import os

# 1. Configuración de página
st.set_page_config(page_title="AppJacarInvestment", layout="wide", initial_sidebar_state="expanded")
st.title("🛡️ AppJacarInvestment: Terminal de Ejecución")

# 2. Conexión con OpenAI (Secrets de Streamlit)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 3. Panel Lateral (Sidebar)
with st.sidebar:
    st.header("💰 Gestión de Capital")
    capital = st.number_input("Capital en Cuenta (USD)", value=18000.0)
    riesgo_per = st.slider("Riesgo por operación (%)", 0.1, 5.0, 1.0)
    st.divider()
    st.header("🔍 Selección de Activo")
    activos = {
        "Oro": "GC=F",
        "Petróleo Brent": "BZ=F",
        "Nasdaq 100": "^IXIC",
        "DAX 40": "^GDAXI",
        "EUR/USD": "EURUSD=X"
    }
    seleccion = st.selectbox("Activo a analizar", list(activos.keys()))

# 4. Descarga de datos de Yahoo Finance
ticker = activos[seleccion]
df = yf.download(ticker, period="5d", interval="15m")

if not df.empty:
    # Limpieza de datos para evitar errores en el gráfico
    df = df.dropna()
    
    # Precios clave (convertidos a float para evitar errores de formato)
    precio_act = float(df['Close'].iloc[-1])
    high_recent = float(df['High'].max())
    low_recent = float(df['Low'].min())

    # Indicadores visuales rápidos
    col1, col2, col3 = st.columns(3)
    col1.metric("Precio Actual", f"{precio_act:.4f}")
    col2.metric("Máximo Reciente", f"{high_recent:.4f}")
    col3.metric("Mínimo Reciente", f"{low_recent:.4f}")

    # 5. Gráfico de Velas Japonesas con Auto-Ajuste de Escala
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'], 
        high=df['High'],
        low=df['Low'], 
        close=df['Close'],
        name="Precio",
        increasing_line_color='#00ff00', # Verde neón
        decreasing_line_color='#ff0000'  # Rojo neón
    )])
    
    # Forzamos a que el eje Y se ajuste solo al precio actual (Zoom automático)
    fig.update_layout(
        title=f"Gráfico de Velas - {seleccion} (15 min)",
        xaxis_rangeslider_visible=False, 
        template="plotly_dark",
        height=600,
        margin=dict(l=50, r=50, t=50, b=50),
        yaxis=dict(
            autorange=True,      # <--- Esto fuerza el zoom al precio
            fixedrange=False,    # Permite que tú muevas el gráfico arriba/abajo
            side="right",        # El precio a la derecha, como en MetaTrader
            tickformat=".4f"     # Muestra 4 decimales en el eje
        ),
        xaxis=dict(type='date')
    )
    
    # Este comando es vital para que se renderice en Streamlit
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})

    # 6. Lógica de la IA Ejecutora
    if st.button("🚀 OBTENER ORDEN DE MERCADO DIRECTA"):
        with st.spinner('IA analizando tendencia y calculando pips...'):
            # Enviamos los últimos 15 cierres para que la IA vea la tendencia
            ultimos_precios = df['Close'].tail(15).tolist()
            
            prompt = f"""
            Actúa como un TRADER ALGORÍTMICO PROFESIONAL.
            ACTIVO: {seleccion} (Precio actual: {precio_act:.4f})
            CONTEXTO: Máximo reciente {high_recent:.4f}, Mínimo reciente {low_recent:.4f}.
            HISTORIAL RECIENTE (15 min): {ultimos_precios}
            CAPITAL: {capital} USD. RIESGO: {riesgo_per}%.

            ORDEN DIRECTA REQUERIDA:
            1. Decide: COMPRA, VENTA o ESPERAR.
            2. Si es OPERAR, dame:
               - Punto de entrada exacto.
               - Volumen en LOTES (basado en el riesgo y un SL técnico).
               - Stop Loss (SL) y Take Profit (TP) como precios exactos.
            3. Si es ESPERAR, dame el precio para una orden PENDIENTE (Buy/Sell Limit).
            Sé extremadamente directo y preciso.
            """
            
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": "Eres un ejecutor de señales de trading. No das consejos, das órdenes exactas."},
                              {"role": "user", "content": prompt}]
                )
                st.markdown("### 📋 ORDEN DE OPERACIÓN")
                st.info(resp.choices[0].message.content)
            except Exception as e:
                st.error(f"Error en la IA: {e}")

else:
    st.error("No se han podido cargar los datos. Verifica el mercado o el activo seleccionado.")
