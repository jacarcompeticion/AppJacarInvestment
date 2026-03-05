import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re

# 1. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="Jacar Pro Terminal | Institutional Grade", layout="wide")

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'historial' not in st.session_state: st.session_state.historial = []
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: st.session_state.activo_sel = "Oro"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

activos = {
    "Oro": "GC=F", 
    "Nasdaq": "^IXIC", 
    "EUR/USD": "EURUSD=X", 
    "Brent": "BZ=F", 
    "Bitcoin": "BTC-USD"
}

# --- FUNCIÓN DE INTELIGENCIA DE MERCADO (Punto 9) ---
def obtener_flujo_noticias(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news[:5] 
        info_relevante = ""
        for n in news:
            info_relevante += f"- {n['title']} (Fuente: {n.get('publisher', 'Medio Económico')})\n"
        return info_relevante
    except:
        return "Fuentes Bloomberg/Reuters: Estabilidad relativa en el flujo de noticias."

# --- UI: PANEL SUPERIOR ---
st.subheader("🚀 Terminal de Alta Frecuencia & Análisis Macro")
cols_top = st.columns(len(activos))
for i, nombre in enumerate(activos.keys()):
    if cols_top[i].button(f"📊 {nombre}", key=f"btn_top_{nombre}", use_container_width=True):
        st.session_state.activo_sel = nombre
        st.rerun()

# 2. PANEL LATERAL
with st.sidebar:
    st.title(f"💰 Equity: {st.session_state.wallet:,.2f} USD")
    st.divider()
    perfil = st.selectbox("Perfil de Inversor", ["Institucional (Conservador)", "Hedge Fund (Agresivo)", "Retail Scalper"])
    tf_visual = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "1d"], index=2)
    st.divider()
    lista_nombres = list(activos.keys())
    indice_act = lista_nombres.index(st.session_state.activo_sel)
    seleccion = st.selectbox("Activo", lista_nombres, index=indice_act)
    st.session_state.activo_sel = seleccion

# 3. DATOS TÉCNICOS AVANZADOS
df = yf.download(activos[seleccion], period="5d", interval=tf_visual)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    precio_act = float(df['Close'].iloc[-1])
    rsi_act = float(df['RSI'].iloc[-1])
    
    # 4. GRÁFICO PROFESIONAL
    
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1), name="EMA 20"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color='gray', opacity=0.5, name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1.5), name="RSI"), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 5. EL ANALISTA MACRO (IA CON CONTRASTE DE FUENTES)
    if st.button("⚖️ CONTRASTAR NOTICIAS Y GENERAR ORDEN"):
        with st.spinner('Comparando fuentes institucionales y flujos de capital...'):
            noticias = obtener_flujo_noticias(activos[seleccion])
            
            prompt = f"""
            Actúa como un Comité de Inversión Senior. 
            ACTIVO: {seleccion} | PRECIO: {precio_act} | RSI: {rsi_act:.2f}.
            
            FLUJO DE NOTICIAS (Yahoo, Bloomberg, Reuters):
            {noticias}
            
            TAREA:
            1. Compara estas noticias con el comportamiento de los grandes inversores (Smart Money).
            2. Identifica si hay una "Trampa de Noticias" o si el movimiento tiene respaldo institucional.
            3. Analiza el impacto macroeconómico global (Geopolítica).
            
            FORMATO DE RESPUESTA:
            ORDEN: [COMPRA/VENTA/ESPERAR]
            EJECUCIÓN: [MERCADO/PENDIENTE]
            NIVELES: Precio: {precio_act}, SL: [Valor], TP: [Valor]
            SENTIMIENTO INSTITUCIONAL: [¿Qué están haciendo los grandes inversores?]
            ANÁLISIS DE PRENSA: [Contraste entre noticias y realidad técnica]
            LOTES: [Cálculo según riesgo]
            """
            
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Eres un analista de Wall Street experto en flujos de capital y geopolítica."}, {"role": "user", "content": prompt}]
            )
            res_ia = resp.choices[0].message.content
            
            try:
                st.session_state.señal_actual = {
                    "texto": res_ia,
                    "entrada": precio_act,
                    "lotes": 0.10, # Valor base para edición
                    "tipo": "COMPRA" if "COMPRA" in res_ia.upper() else "VENTA"
                }
                st.rerun()
            except: st.error("Error en el procesado de la orden de alta frecuencia.")

    # --- PANEL DE GESTIÓN (IDEM ANTERIOR PERO MÁS LIMPIO) ---
    if st.session_state.señal_actual:
        with st.container(border=True):
            st.info("### 📡 Informe de Inversión Contrastado")
            st.write(st.session_state.señal_actual['texto'])
            col_a, col_b = st.columns(2)
            if col_a.button("🚀 EJECUTAR OPERACIÓN"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": seleccion, 
                    "entrada": precio_act, "tipo": st.session_state.señal_actual['tipo'], "hora": datetime.now().strftime("%H:%M")
                })
                st.session_state.señal_actual = None
                st.rerun()
            if col_b.button("🗑️ DESCARTAR"):
                st.session_state.señal_actual = None
                st.rerun()

    # CARTERA ACTIVA
    if st.session_state.cartera_abierta:
        st.divider()
        st.subheader("💼 Posiciones en Cartera")
        for i, pos in enumerate(st.session_state.cartera_abierta):
            with st.expander(f"🟢 {pos['activo']} | {pos['tipo']} | In: {pos['entrada']}"):
                res_pnl = st.number_input(f"Profit/Loss Final ($)", value=0.0, key=f"p_{pos['id']}")
                if st.button(f"Liquidar Posición", key=f"b_{pos['id']}"):
                    st.session_state.wallet += res_pnl
                    st.session_state.historial.append({"Activo": pos['activo'], "PnL": res_pnl, "Fecha": pos['hora']})
                    st.session_state.cartera_abierta.pop(i)
                    st.rerun()
