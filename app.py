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
st.set_page_config(page_title="Jacar Pro Terminal", layout="wide")

# Estados de memoria persistentes
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'historial' not in st.session_state: st.session_state.historial = []
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: st.session_state.activo_sel = "Oro"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Diccionario maestro de activos (Punto 1)
activos = {
    "Oro": "GC=F", 
    "Nasdaq": "^IXIC", 
    "EUR/USD": "EURUSD=X", 
    "Brent": "BZ=F", 
    "Bitcoin": "BTC-USD"
}

# --- PUNTO 1: PANEL DE OPORTUNIDADES INTERACTIVO ---
st.subheader("🚀 Monitor de Oportunidades (Top Profit)")
cols_top = st.columns(len(activos))

for i, nombre in enumerate(activos.keys()):
    # Hacemos que el botón cambie el activo seleccionado
    if cols_top[i].button(f"📊 {nombre}", key=f"btn_top_{nombre}", use_container_width=True):
        st.session_state.activo_sel = nombre
        st.rerun()

# 2. PANEL LATERAL (Sincronizado)
with st.sidebar:
    st.title(f"💰 Balance: {st.session_state.wallet:,.2f} USD")
    st.divider()
    obj_diario = st.number_input("Objetivo Diario ($)", value=200.0)
    perfil = st.radio("Estrategia", ["Scalping", "Swing"])
    tf_visual = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "1d"], index=2)
    st.divider()
    
    # El selectbox manda sobre el estado, pero el estado puede ser cambiado por los botones
    lista_nombres = list(activos.keys())
    indice_act = lista_nombres.index(st.session_state.activo_sel)
    seleccion = st.selectbox("Activo Actual", lista_nombres, index=indice_act)
    st.session_state.activo_sel = seleccion

# 3. OBTENCIÓN DE DATOS (Punto 6: Precisión)
ajuste_temp = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "1d": "max"}
df = yf.download(activos[seleccion], period=ajuste_temp.get(tf_visual, "5d"), interval=tf_visual)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    precio_act = float(df['Close'].iloc[-1])
    # Punto 7: Soportes y Resistencias última hora (aprox 60 velas si es 1m o últimas 40)
    resistencia = float(df['High'].tail(40).max())
    soporte = float(df['Low'].tail(40).min())
    
    # 4. GRÁFICO (Punto 11: Visualización clara)
    colors_vol = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name="Volumen"), row=2, col=1)
    
    # Dibujar niveles proyectados (Punto 11)
    fig.add_hline(y=resistencia, line_dash="dash", line_color="cyan", opacity=0.3, row=1, col=1)
    fig.add_hline(y=soporte, line_dash="dash", line_color="orange", opacity=0.3, row=1, col=1)

    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=30, b=10), showlegend=False)
    fig.update_yaxes(autorange=True, fixedrange=False, side="right", row=1, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # 5. GENERADOR DE SEÑALES (Punto 2 y 9)
    if st.button("🧠 ANALIZAR OPORTUNIDAD DE MERCADO"):
        with st.spinner('IA analizando soportes, resistencias y contexto geopolítico...'):
            prompt = f"Trader pro. Activo: {seleccion} a {precio_act}. Res: {resistencia}, Sop: {soporte}. Estilo: {perfil}. Responde con: TIPO (MERCADO/PENDIENTE), ACCIÓN (COMPRA/VENTA), PRECIO, SL, TP, LOTES, MOTIVO."
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Eres un ejecutor de trading preciso."}, {"role": "user", "content": prompt}]
            )
            res = resp.choices[0].message.content
            
            # Extractor robusto
            def ext(tag):
                try: return re.search(rf"{tag}:\s*([\d\.\w\s/]+)", res, re.I).group(1).strip()
                except: return "N/A"

            st.session_state.señal_actual = {
                "texto": res,
                "entrada": float(re.search(r"PRECIO:\s*([\d\.]+)", res, re.I).group(1)),
                "lotes": float(re.search(r"LOTES:\s*([\d\.]+)", res, re.I).group(1)),
                "tipo": "COMPRA" if "COMPRA" in res.upper() else "VENTA"
            }
            st.rerun()

    # --- FLUJO DE TRABAJO (Punto 3 y 4) ---
    if st.session_state.señal_actual:
        with st.container(border=True):
            st.info(f"### 📡 Señal para {seleccion}")
            st.write(st.session_state.señal_actual['texto'])
            c1, c2 = st.columns(2)
            e_real = c1.number_input("Precio Real In", value=st.session_state.señal_actual['entrada'], format="%.4f")
            l_real = c2.number_input("Lotes Reales", value=st.session_state.señal_actual['lotes'])
            if st.button("🚀 ACEPTAR POSICIÓN"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"),
                    "activo": seleccion, "entrada": e_real, "lotes": l_real,
                    "tipo": st.session_state.señal_actual['tipo'], "hora": datetime.now().strftime("%H:%M")
                })
                st.session_state.señal_actual = None
                st.rerun()

    # POSICIONES ACTIVAS (Punto 3, 4, 5)
    if st.session_state.cartera_abierta:
        st.divider()
        st.subheader("💼 Operaciones en Curso")
        for i, pos in enumerate(st.session_state.cartera_abierta):
            with st.expander(f"🔹 {pos['activo']} | {pos['tipo']} | In: {pos['entrada']}", expanded=True):
                colx, coly, colz = st.columns([2, 2, 1])
                p_salida = colx.number_input(f"Precio Salida", value=precio_act if seleccion == pos['activo'] else pos['entrada'], format="%.4f", key=f"s_{pos['id']}")
                pnl = coly.number_input(f"PnL Final ($)", value=0.0, key=f"p_{pos['id']}")
                if colz.button(f"Cerrar", key=f"b_{pos['id']}"):
                    st.session_state.wallet += pnl
                    st.session_state.historial.append({"Activo": pos['activo'], "PnL": pnl, "Fecha": pos['hora']})
                    st.session_state.cartera_abierta.pop(i)
                    st.rerun()

    if st.session_state.historial:
        st.divider()
        st.subheader("📊 Historial y Resumen (Punto 4)")
        st.table(pd.DataFrame(st.session_state.historial).tail(10))
