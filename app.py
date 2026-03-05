import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime

# 1. INICIO Y ESTADO DE SESIÓN
st.set_page_config(page_title="Jacar Pro Terminal", layout="wide")

if 'wallet' not in st.session_state:
    st.session_state.wallet = 18000.0
if 'historial' not in st.session_state:
    st.session_state.historial = []
if 'ultima_orden' not in st.session_state:
    st.session_state.ultima_orden = None
if 'trade_coords' not in st.session_state:
    st.session_state.trade_coords = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 2. PANEL LATERAL
with st.sidebar:
    st.title(f"💰 Balance: {st.session_state.wallet:,.2f} USD")
    st.divider()
    obj_diario = st.number_input("Objetivo Diario ($)", value=200.0)
    perfil = st.radio("Estrategia", ["Scalping", "Swing"])
    tf_visual = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "1d"], index=2)
    st.divider()
    activos = {"Oro": "GC=F", "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", "Brent": "BZ=F"}
    seleccion = st.selectbox("Activo", list(activos.keys()))

# 3. DATOS E INDICADORES
ajuste_temp = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "1d": "max"}
df = yf.download(activos[seleccion], period=ajuste_temp.get(tf_visual, "5d"), interval=tf_visual)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    resistencia = float(df['High'].tail(40).max())
    soporte = float(df['Low'].tail(40).min())
    precio_act = float(df['Close'].iloc[-1])

  # 4. GRÁFICO CON VOLUMEN DINÁMICO (Puntos 10 y 11)
    from plotly.subplots import make_subplots

    # Creamos colores para el volumen basados en el cierre vs apertura
    colors_vol = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]

    # Subplots con escala independiente para el volumen
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_heights=[0.7, 0.3]) # 70% precio, 30% volumen

    # Añadir Velas
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name="Precio"
    ), row=1, col=1)

    # Añadir Volumen con Colores
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'], 
        name="Volumen", 
        marker_color=colors_vol,
        opacity=0.8
    ), row=2, col=1)
    
    # Soportes y Resistencias
    fig.add_hline(y=resistencia, line_dash="dash", line_color="cyan", opacity=0.3, row=1, col=1)
    fig.add_hline(y=soporte, line_dash="dash", line_color="orange", opacity=0.3, row=1, col=1)

    # Dibujar Orden de la IA si existe
    if st.session_state.trade_coords:
        tc = st.session_state.trade_coords
        color_zona = "rgba(0, 255, 0, 0.15)" if "COMPRA" in tc['tipo'].upper() else "rgba(255, 0, 0, 0.15)"
        fig.add_hrect(y0=tc['entrada'], y1=tc['tp'], fillcolor=color_zona, line_width=0, row=1, col=1)
        fig.add_hline(y=tc['sl'], line_color="#ff5252", line_width=2, line_dash="dot", row=1, col=1)

    # --- CONFIGURACIÓN DE ESCALAS (Auto-ajuste total) ---
    fig.update_layout(
        template="plotly_dark", 
        height=700, 
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=50, t=30, b=10),
        showlegend=False
    )

    # Ajuste eje Y Precio (Lado derecho)
    fig.update_yaxes(autorange=True, fixedrange=False, side="right", row=1, col=1)
    
    # Ajuste eje Y Volumen (Escalable y visible)
    fig.update_yaxes(autorange=True, showgrid=False, row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # 5. BOTÓN E IA
    if st.button("🧠 ANALIZAR Y GENERAR ORDEN"):
        with st.spinner('Procesando...'):
            prompt = f"Activo: {seleccion} a {precio_act}. RSI: {df['RSI'].iloc[-1]:.2f}. Res: {resistencia}, Sop: {soporte}. Formato: ACCIÓN, ENTRADA, SL, TP, LOTES, MOTIVO."
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Eres un trader experto. Responde solo con los datos solicitados en formato de lista de etiquetas."}, {"role": "user", "content": prompt}]
            )
            respuesta = resp.choices[0].message.content
            st.session_state.ultima_orden = respuesta
            
            try:
                # Extractor numérico
                def get_val(tag, txt):
                    import re
                    linea = [l for l in txt.split('\n') if tag in l.upper()][0]
                    num = re.findall(r"[-+]?\d*\.\d+|\d+", linea)
                    return float(num[0]) if num else 0.0

                st.session_state.trade_coords = {
                    "entrada": get_val("ENTRADA", respuesta),
                    "sl": get_val("SL", respuesta),
                    "tp": get_val("TP", respuesta),
                    "tipo": "COMPRA" if "COMPRA" in respuesta.upper() else "VENTA"
                }
                st.rerun()
            except:
                st.session_state.trade_coords = None

    # 6. REGISTRO Y RESULTADOS
    if st.session_state.ultima_orden:
        st.info(st.session_state.ultima_orden)
        with st.expander("📝 REGISTRAR OPERACIÓN", expanded=True):
            col_r1, col_r2 = st.columns(2)
            pnl = col_r1.number_input("Resultado Final ($)", value=0.0)
            if col_r2.button("💾 Guardar y Actualizar"):
                st.session_state.wallet += pnl
                st.session_state.historial.append({"Fecha": datetime.now().strftime("%H:%M"), "Activo": seleccion, "PnL": pnl})
                st.session_state.ultima_orden = None
                st.session_state.trade_coords = None
                st.rerun()

    if st.session_state.historial:
        st.divider()
        st.subheader("📊 Historial Reciente")
        st.table(pd.DataFrame(st.session_state.historial).tail(5))
