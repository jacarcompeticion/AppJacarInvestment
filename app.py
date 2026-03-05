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
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'historial' not in st.session_state: st.session_state.historial = []
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
# Nuevo estado para controlar la selección desde los botones
if 'activo_seleccionado' not in st.session_state: st.session_state.activo_seleccionado = "Oro"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Definición de activos (para usar en varios sitios)
activos_dict = {"Oro": "GC=F", "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", "Brent": "BZ=F", "Bitcoin": "BTC-USD"}

# --- PUNTO 1: PANEL DE OPORTUNIDADES FUNCIONAL ---
st.subheader("🚀 Acceso Rápido y Oportunidades")
cols_top = st.columns(len(activos_dict))

for i, nombre in enumerate(activos_dict.keys()):
    # Al hacer clic, actualizamos el estado y recargamos
    if cols_top[i].button(f"📊 {nombre}", key=f"top_{nombre}", use_container_width=True):
        st.session_state.activo_seleccionado = nombre
        st.rerun()

# 2. PANEL LATERAL (Sidebar conectado al estado)
with st.sidebar:
    st.title(f"💰 Balance: {st.session_state.wallet:,.2f} USD")
    st.divider()
    obj_diario = st.number_input("Objetivo Diario ($)", value=200.0)
    perfil = st.radio("Estrategia", ["Scalping", "Swing"])
    tf_visual = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "1d"], index=2)
    st.divider()
    
    # El selectbox ahora se sincroniza con los botones superiores
    seleccion = st.selectbox("Seleccionar Activo", list(activos_dict.keys()), 
                             index=list(activos_dict.keys()).index(st.session_state.activo_seleccionado))
    # Actualizamos el estado si el usuario cambia el selectbox manualmente
    st.session_state.activo_seleccionado = seleccion

# 3. OBTENCIÓN DE DATOS
ajuste_temp = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "1d": "max"}
df = yf.download(activos[seleccion], period=ajuste_temp.get(tf_visual, "5d"), interval=tf_visual)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    precio_act = float(df['Close'].iloc[-1])
    resistencia = float(df['High'].tail(40).max())
    soporte = float(df['Low'].tail(40).min())
    
    # 4. GRÁFICO PROFESIONAL
    colors_vol = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name="Volumen"), row=2, col=1)
    
    fig.add_hline(y=resistencia, line_dash="dash", line_color="cyan", opacity=0.3, row=1, col=1)
    fig.add_hline(y=soporte, line_dash="dash", line_color="orange", opacity=0.3, row=1, col=1)

    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=30, b=10), showlegend=False)
    fig.update_yaxes(autorange=True, fixedrange=False, side="right", row=1, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # 5. GENERADOR DE SEÑALES (IA MEJORADA)
    if st.button("🧠 GENERAR ANÁLISIS DE MERCADO"):
        with st.spinner('Escaneando indicadores y contexto...'):
            prompt = f"""Activo: {seleccion} a {precio_act}. Resistencia: {resistencia}, Soporte: {soporte}. Perfil: {perfil}.
            Responde estrictamente con estas etiquetas:
            TIPO: [A MERCADO o PENDIENTE]
            ACCIÓN: [COMPRA o VENTA]
            PRECIO: [Valor numérico]
            SL: [Valor numérico]
            TP: [Valor numérico]
            LOTES: [Valor numérico]
            MOTIVO: [Análisis corto]"""
            
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Eres un ejecutor de trading. No des explicaciones, solo las etiquetas."}, {"role": "user", "content": prompt}]
            )
            res = resp.choices[0].message.content
            
            # LECTOR ROBUSTO DE NÚMEROS (Punto 6)
            def extraer_numero(tag, texto):
                match = re.search(rf"{tag}:\s*([\d\.]+)", texto, re.IGNORECASE)
                return float(match.group(1)) if match else 0.0

            try:
                st.session_state.señal_actual = {
                    "texto": res,
                    "entrada": extraer_numero("PRECIO", res),
                    "sl": extraer_numero("SL", res),
                    "tp": extraer_numero("TP", res),
                    "lotes": extraer_numero("LOTES", res),
                    "tipo": "COMPRA" if "COMPRA" in res.upper() else "VENTA"
                }
                st.rerun()
            except Exception as e:
                st.error(f"Error interpretando la señal: {e}")

    # --- FLUJO DE CARTERA ---
    if st.session_state.señal_actual:
        with st.container(border=True):
            st.info("### 📡 Señal Recibida")
            st.code(st.session_state.señal_actual['texto'])
            col_a, col_b = st.columns(2)
            ent_real = col_a.number_input("Confirmar Entrada", value=st.session_state.señal_actual['entrada'], format="%.4f")
            lot_real = col_b.number_input("Confirmar Lotes", value=st.session_state.señal_actual['lotes'])
            
            if st.button("🚀 ACEPTAR Y ABRIR POSICIÓN"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"),
                    "activo": seleccion,
                    "entrada": ent_real,
                    "lotes": lot_real,
                    "tipo": st.session_state.señal_actual['tipo'],
                    "hora": datetime.now().strftime("%H:%M")
                })
                st.session_state.señal_actual = None
                st.rerun()

    # POSICIONES ACTIVAS (Multitarea)
    if st.session_state.cartera_abierta:
        st.divider()
        st.subheader("💼 Posiciones en Curso (Independientes)")
        for i, pos in enumerate(st.session_state.cartera_abierta):
            with st.expander(f"🟢 {pos['tipo']} {pos['activo']} (In: {pos['entrada']})", expanded=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                precio_salida = c1.number_input(f"Precio Salida {pos['id']}", value=precio_act if seleccion == pos['activo'] else pos['entrada'], format="%.4f")
                pnl_real = c2.number_input(f"Profit/Loss Final ($) {pos['id']}", value=0.0)
                if c3.button(f"Cerrar {pos['id']}", use_container_width=True):
                    st.session_state.wallet += pnl_real
                    st.session_state.historial.append({"Activo": pos['activo'], "PnL": pnl_real, "Fecha": pos['hora']})
                    st.session_state.cartera_abierta.pop(i)
                    st.rerun()

    if st.session_state.historial:
        st.divider()
        st.subheader("📊 Historial Semanal")
        st.table(pd.DataFrame(st.session_state.historial).tail(5))
