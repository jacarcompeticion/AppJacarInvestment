import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime

# 1. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="Jacar Pro Terminal", layout="wide")

# Estados de memoria persistentes
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'historial' not in st.session_state: st.session_state.historial = []
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 2. PANEL LATERAL (Sidebar)
with st.sidebar:
    st.title(f"💰 Balance: {st.session_state.wallet:,.2f} USD")
    st.divider()
    obj_diario = st.number_input("Objetivo Diario ($)", value=200.0)
    perfil = st.radio("Estrategia", ["Scalping", "Swing"])
    tf_visual = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "1d"], index=2)
    st.divider()
    activos = {"Oro": "GC=F", "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", "Brent": "BZ=F", "Bitcoin": "BTC-USD"}
    seleccion = st.selectbox("Seleccionar Activo", list(activos.keys()))

# 3. OBTENCIÓN DE DATOS
ajuste_temp = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "1d": "max"}
df = yf.download(activos[seleccion], period=ajuste_temp.get(tf_visual, "5d"), interval=tf_visual)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    precio_act = float(df['Close'].iloc[-1])
    resistencia = float(df['High'].tail(40).max())
    soporte = float(df['Low'].tail(40).min())
    
    # 4. GRÁFICO PROFESIONAL CON VOLUMEN
    colors_vol = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name="Volumen"), row=2, col=1)
    
    # Soportes y Resistencias
    fig.add_hline(y=resistencia, line_dash="dash", line_color="cyan", opacity=0.3, row=1, col=1)
    fig.add_hline(y=soporte, line_dash="dash", line_color="orange", opacity=0.3, row=1, col=1)

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=30, b=10), showlegend=False)
    fig.update_yaxes(autorange=True, fixedrange=False, side="right", row=1, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # 5. GENERADOR DE SEÑALES (IA)
    if st.button("🧠 GENERAR ANÁLISIS"):
        with st.spinner('IA analizando mercado...'):
            prompt = f"Trader pro. Activo: {seleccion} a {precio_act}. Res: {resistencia}, Sop: {soporte}. Formato: TIPO (MERCADO/PENDIENTE), ACCIÓN (COMPRA/VENTA), PRECIO, SL, TP, LOTES, MOTIVO."
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Responde solo con etiquetas técnicas."}, {"role": "user", "content": prompt}]
            )
            res = resp.choices[0].message.content
            import re
            try:
                st.session_state.señal_actual = {
                    "texto": res,
                    "entrada": float(re.findall(r"PRECIO: ([\d\.]+)", res)[0]),
                    "sl": float(re.findall(r"SL: ([\d\.]+)", res)[0]),
                    "tp": float(re.findall(r"TP: ([\d\.]+)", res)[0]),
                    "lotes": float(re.findall(r"LOTES: ([\d\.]+)", res)[0]),
                    "tipo": "COMPRA" if "COMPRA" in res.upper() else "VENTA"
                }
                st.rerun()
            except: st.error("Error al leer la señal. Intenta de nuevo.")

    # --- FLUJO DE TRABAJO ---

    # PASO 1: PROPUESTA
    if st.session_state.señal_actual:
        st.info("### 📡 Propuesta de la IA")
        st.code(st.session_state.señal_actual['texto'])
        with st.expander("⚡ CONFIGURAR Y EJECUTAR", expanded=True):
            col_a, col_b = st.columns(2)
            ent_real = col_a.number_input("Entrada Real", value=st.session_state.señal_actual['entrada'], format="%.4f")
            lot_real = col_b.number_input("Lotes Reales", value=st.session_state.señal_actual['lotes'])
            
            if st.button("🚀 CONFIRMAR APERTURA Y GUARDAR"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"),
                    "activo": seleccion,
                    "entrada": ent_real,
                    "lotes": lot_real,
                    "tipo": st.session_state.señal_actual['tipo'],
                    "hora": datetime.now().strftime("%H:%M")
                })
                st.session_state.señal_actual = None
                st.success("Posición guardada en cartera activa.")
                st.rerun()

    # PASO 2 Y 3: CARTERA DE POSICIONES
    if st.session_state.cartera_abierta:
        st.divider()
        st.subheader("💼 Posiciones en Curso (Cartera)")
        for i, pos in enumerate(st.session_state.cartera_abierta):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])
                c1.write(f"**{pos['activo']}**")
                c2.write(f"ID: {pos['id']}")
                c3.write(f"{pos['tipo']}")
                c4.write(f"In: {pos['entrada']}")
                
                with c5:
                    with st.popover(f"Finalizar {pos['activo']}"):
                        res_usd = st.number_input("Ganancia/Pérdida ($)", value=0.0, key=f"pnl_{pos['id']}")
                        if st.button("Cerrar y Registrar", key=f"btn_{pos['id']}"):
                            st.session_state.wallet += res_usd
                            st.session_state.historial.append({
                                "Fecha": pos['hora'], "Activo": pos['activo'], "PnL": res_usd
                            })
                            st.session_state.cartera_abierta.pop(i)
                            st.rerun()

    # HISTORIAL
    if st.session_state.historial:
        st.divider()
        st.subheader("📊 Historial de Cierre")
        st.table(pd.DataFrame(st.session_state.historial).tail(5))
