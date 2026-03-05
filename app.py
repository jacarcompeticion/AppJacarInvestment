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
st.set_page_config(page_title="Jacar Pro Terminal | Global Macro", layout="wide")

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'historial' not in st.session_state: st.session_state.historial = []
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: st.session_state.activo_sel = "Oro"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

activos = {
    "Oro": "GC=F", "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", 
    "Brent": "BZ=F", "Bitcoin": "BTC-USD"
}

# --- FUNCIÓN DE NOTICIAS ---
def obtener_flujo_noticias(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news[:5] 
        return "\n".join([f"- {n['title']}" for n in news])
    except:
        return "Flujo de noticias estable en Bloomberg/Reuters."

# --- UI: PANEL SUPERIOR ---
st.subheader("🚀 Monitor de Oportunidades")
cols_top = st.columns(len(activos))
for i, nombre in enumerate(activos.keys()):
    if cols_top[i].button(f"📊 {nombre}", key=f"btn_top_{nombre}", use_container_width=True):
        st.session_state.activo_sel = nombre
        st.rerun()

# 2. PANEL LATERAL
with st.sidebar:
    st.title(f"💰 Equity: {st.session_state.wallet:,.2f} USD")
    st.divider()
    perfil = st.selectbox("Perfil", ["Institucional", "Hedge Fund", "Retail"])
    tf_visual = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "1d"], index=2)
    st.divider()
    seleccion = st.selectbox("Activo", list(activos.keys()), index=list(activos.keys()).index(st.session_state.activo_sel))
    st.session_state.activo_sel = seleccion

# 3. OBTENCIÓN DE DATOS
df = yf.download(activos[seleccion], period="5d", interval=tf_visual)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    precio_act = float(df['Close'].iloc[-1])
    rsi_act = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0
    
    # 4. GRÁFICO (Simplificado para esta versión)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1), name="EMA 20"), row=1, col=1)
    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 5. IA: ANÁLISIS CONTRASTADO
    if st.button("⚖️ ANALIZAR Y CONTRASTAR FUENTES"):
        with st.spinner('Procesando datos institucionales...'):
            noticias = obtener_flujo_noticias(activos[seleccion])
            prompt = f"""
            Comité de Inversión. ACTIVO: {seleccion} | PRECIO: {precio_act} | RSI: {rsi_act:.2f}.
            NOTICIAS: {noticias}
            Responde estrictamente así:
            RESUMEN: [Una frase de 15 palabras máximo sobre la decisión]
            ORDEN: [COMPRA, VENTA o ESPERAR]
            NIVELES: Entrada: {precio_act}, SL: [Valor], TP: [Valor]
            DETALLE INSTITUCIONAL: [Análisis largo sobre Smart Money]
            DETALLE PRENSA: [Contraste noticias vs técnica]
            DETALLE MACRO: [Geopolítica]
            LOTES: [Valor]
            """
            
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Analista Senior de Wall Street."}, {"role": "user", "content": prompt}]
            )
            res_ia = resp.choices[0].message.content
            
            # Extractor Inteligente
            def ext(tag):
                try: return re.search(rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)", res_ia, re.S).group(1).strip()
                except: return "N/A"

            st.session_state.señal_actual = {
                "resumen": ext("RESUMEN"),
                "orden": ext("ORDEN"),
                "niveles": ext("NIVELES"),
                "inst": ext("DETALLE INSTITUCIONAL"),
                "prensa": ext("DETALLE PRENSA"),
                "macro": ext("DETALLE MACRO"),
                "lotes": ext("LOTES"),
                "full": res_ia
            }
            st.rerun()

    # 6. INFORME RESUMIDO CON OPCIÓN DE AMPLIAR (Punto 9)
    if st.session_state.señal_actual:
        s = st.session_state.señal_actual
        color = "green" if "COMPRA" in s['orden'].upper() else "red" if "VENTA" in s['orden'].upper() else "orange"
        
        with st.container(border=True):
            st.markdown(f"### 🛡️ Decisión: :{color}[{s['orden']}]")
            st.markdown(f"**💡 {s['resumen']}**")
            
            # Botones de acción rápida
            c1, c2 = st.columns(2)
            if "ESPERAR" not in s['orden'].upper():
                if c1.button("🚀 EJECUTAR AHORA"):
                    st.session_state.cartera_abierta.append({
                        "id": datetime.now().strftime("%H%M%S"), "activo": seleccion, 
                        "entrada": precio_act, "tipo": s['orden'], "hora": datetime.now().strftime("%H:%M")
                    })
                    st.session_state.señal_actual = None
                    st.rerun()
            
            if c2.button("🗑️ DESCARTAR"):
                st.session_state.señal_actual = None
                st.rerun()

            # AMPLIAR INFORMACIÓN (Punto 9)
            with st.expander("🔍 Ver Informe de Inteligencia Completo"):
                st.write(f"**📍 Niveles Proyectados:** {s['niveles']}")
                st.write(f"**📊 Lotes sugeridos:** {s['lotes']}")
                st.divider()
                st.write("**💼 Sentimiento Institucional (Smart Money):**")
                st.write(s['inst'])
                st.write("**📰 Análisis de Prensa (Contraste):**")
                st.write(s['prensa'])
                st.write("**🌍 Impacto Geopolítico:**")
                st.write(s['macro'])

    # CARTERA ACTIVA
    if st.session_state.cartera_abierta:
        st.divider()
        st.subheader("💼 Operaciones en Curso")
        for i, pos in enumerate(st.session_state.cartera_abierta):
            with st.expander(f"🟢 {pos['activo']} | {pos['tipo']} | In: {pos['entrada']}"):
                pnl = st.number_input(f"PnL Final ($)", value=0.0, key=f"p_{pos['id']}")
                if st.button(f"Liquidar", key=f"b_{pos['id']}"):
                    st.session_state.wallet += pnl
                    st.session_state.historial.append({"Activo": pos['activo'], "PnL": pnl, "Fecha": pos['hora']})
                    st.session_state.cartera_abierta.pop(i)
                    st.rerun()
