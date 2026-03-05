import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Jacar Pro Terminal", layout="wide")

# Estados de memoria
for key, val in {
    'wallet': 18000.0, 'historial': [], 'señal_actual': None, 
    'cartera_abierta': [], 'activo_sel': "Oro"
}.items():
    if key not in st.session_state: st.session_state[key] = val

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
activos = {"Oro": "GC=F", "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", "Brent": "BZ=F", "Bitcoin": "BTC-USD"}

# 2. PANEL SUPERIOR
st.subheader("🚀 Monitor de Oportunidades")
cols_top = st.columns(len(activos))
for i, nombre in enumerate(activos.keys()):
    if cols_top[i].button(f"📊 {nombre}", key=f"btn_top_{nombre}", use_container_width=True):
        st.session_state.activo_sel = nombre
        st.rerun()

# 3. SIDEBAR
with st.sidebar:
    st.title(f"💰 Equity: {st.session_state.wallet:,.2f} USD")
    st.divider()
    perfil = st.selectbox("Perfil", ["Institucional", "Hedge Fund", "Retail"])
    tf_visual = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "1d"], index=2)
    seleccion = st.selectbox("Activo", list(activos.keys()), index=list(activos.keys()).index(st.session_state.activo_sel))
    st.session_state.activo_sel = seleccion

# 4. DATOS
df = yf.download(activos[seleccion], period="5d", interval=tf_visual)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    precio_act = float(df['Close'].iloc[-1])
    rsi_act = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0

    # Gráfico
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1), name="EMA 20"), row=1, col=1)
    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 5. ANÁLISIS IA
    if st.button("⚖️ ANALIZAR Y CONTRASTAR FUENTES"):
        with st.spinner('Contrastando Bloomberg, Reuters y Flujos de Capital...'):
            ticker = yf.Ticker(activos[seleccion])
            noticias = "\n".join([n['title'] for n in ticker.news[:5]]) if ticker.news else "Sin noticias relevantes."
            
            prompt = f"""Comité Inversión. Activo: {seleccion} a {precio_act}. RSI: {rsi_act:.2f}. Noticias: {noticias}.
            Responde con este formato exacto:
            RESUMEN: [Breve]
            ORDEN: [COMPRA, VENTA o ESPERAR]
            NIVELES: [Entrada, SL, TP]
            DETALLE INSTITUCIONAL: [Smart Money]
            DETALLE PRENSA: [Contraste]
            DETALLE MACRO: [Geopolítica]
            LOTES: [Sugerencia]"""
            
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Analista Wall Street."}, {"role": "user", "content": prompt}]
            )
            res_ia = resp.choices[0].message.content

            def ext(tag):
                match = re.search(rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)", res_ia, re.S | re.I)
                return match.group(1).strip() if match else "N/A"

            st.session_state.señal_actual = {
                "resumen": ext("RESUMEN"), "orden": ext("ORDEN"), "niveles": ext("NIVELES"),
                "inst": ext("DETALLE INSTITUCIONAL"), "prensa": ext("DETALLE PRENSA"),
                "macro": ext("DETALLE MACRO"), "lotes": ext("LOTES")
            }
            st.rerun()

    # 6. INFORME (Fix del KeyError)
    if st.session_state.señal_actual:
        s = st.session_state.señal_actual
        orden_txt = s.get('orden', 'ESPERAR').upper()
        color = "green" if "COMPRA" in orden_txt else "red" if "VENTA" in orden_txt else "orange"
        
        with st.container(border=True):
            st.markdown(f"### 🛡️ Decisión: :{color}[{orden_txt}]")
            st.markdown(f"**💡 {s.get('resumen', 'Sin resumen disponible')}**")
            
            c1, c2 = st.columns(2)
            if "ESPERAR" not in orden_txt:
                if c1.button("🚀 EJECUTAR OPERACIÓN"):
                    st.session_state.cartera_abierta.append({
                        "id": datetime.now().strftime("%H%M%S"), "activo": seleccion, 
                        "entrada": precio_act, "tipo": orden_txt, "hora": datetime.now().strftime("%H:%M")
                    })
                    st.session_state.señal_actual = None
                    st.rerun()
            if c2.button("🗑️ DESCARTAR"):
                st.session_state.señal_actual = None
                st.rerun()

            with st.expander("🔍 Informe de Inteligencia Detallado"):
                st.markdown(f"**📍 Niveles:** {s.get('niveles')}")
                st.markdown(f"**💼 Smart Money:** {s.get('inst')}")
                st.markdown(f"**📰 Prensa vs Técnica:** {s.get('prensa')}")
                st.markdown(f"**🌍 Geopolítica:** {s.get('macro')}")

    # CARTERA
    if st.session_state.cartera_abierta:
        st.divider()
        st.subheader("💼 Posiciones en Curso")
        for i, pos in enumerate(st.session_state.cartera_abierta):
            with st.expander(f"🟢 {pos['activo']} | {pos['tipo']} | In: {pos['entrada']}", expanded=True):
                pnl = st.number_input(f"Profit/Loss Final ($)", value=0.0, key=f"p_{pos['id']}")
                if st.button(f"Liquidar {pos['id']}", key=f"b_{pos['id']}"):
                    st.session_state.wallet += pnl
                    st.session_state.historial.append({"Activo": pos['activo'], "PnL": pnl, "Fecha": pos['hora']})
                    st.session_state.cartera_abierta.pop(i)
                    st.rerun()
