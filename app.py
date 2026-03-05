import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime

# 1. CONFIGURACIÓN E INICIO
st.set_page_config(page_title="Jacar Pro Terminal", layout="wide")

# Inicializar estados de memoria
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'historial' not in st.session_state: st.session_state.historial = []
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None
if 'posicion_abierta' not in st.session_state: st.session_state.posicion_abierta = None

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
df = yf.download(activos[seleccion], period="5d", interval=tf_visual)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    precio_act = float(df['Close'].iloc[-1])
    resistencia = float(df['High'].tail(40).max())
    soporte = float(df['Low'].tail(40).min())

    # 4. GRÁFICO (Simplificado para visualización)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    
    # Dibujar niveles de la posición abierta si existe
    if st.session_state.posicion_abierta:
        pos = st.session_state.posicion_abierta
        fig.add_hline(y=pos['entrada'], line_color="white", line_dash="solid", annotation_text="ENTRADA REAL", row=1, col=1)
        fig.add_hline(y=pos['tp'], line_color="green", line_dash="dot", row=1, col=1)
        fig.add_hline(y=pos['sl'], line_color="red", line_dash="dot", row=1, col=1)

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=30, b=10))
    fig.update_yaxes(side="right", row=1, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # 5. GENERACIÓN DE SEÑAL
    if st.button("🧠 GENERAR ANÁLISIS"):
        with st.spinner('IA analizando mercado...'):
            prompt = f"""Activo: {seleccion} a {precio_act}. Res: {resistencia}, Sop: {soporte}.
            Responde con este formato:
            TIPO: [A MERCADO / ORDEN PENDIENTE]
            ACCIÓN: [COMPRA / VENTA]
            PRECIO: [Valor]
            SL: [Valor]
            TP: [Valor]
            LOTES: [Valor]
            MOTIVO: [Texto corto]"""
            
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Eres un trader ejecutor."}, {"role": "user", "content": prompt}]
            )
            
            res = resp.choices[0].message.content
            # Extracción de datos para la sesión
            import re
            def extraer(tag):
                try: return re.findall(rf"{tag}: (.+)", res)[0]
                except: return "0"
            
            st.session_state.señal_actual = {
                "texto": res,
                "entrada": float(re.findall(r"PRECIO: ([\d\.]+)", res)[0]),
                "sl": float(re.findall(r"SL: ([\d\.]+)", res)[0]),
                "tp": float(re.findall(r"TP: ([\d\.]+)", res)[0]),
                "lotes": float(re.findall(r"LOTES: ([\d\.]+)", res)[0]),
                "tipo": extraer("ACCIÓN")
            }
            st.rerun()

    # --- FLUJO DE TRABAJO (PASOS 1, 2, 3) ---
    
    # PASO 1: SEÑAL RECIBIDA
    if st.session_state.señal_actual and not st.session_state.posicion_abierta:
        st.info("### 📡 Nueva Señal Detectada")
        st.code(st.session_state.señal_actual['texto'])
        col1, col2 = st.columns(2)
        if col1.button("✅ ACEPTAR E INDICAR APERTURA"):
            # Pasamos a posición abierta con los datos de la IA por defecto
            st.session_state.posicion_abierta = {
                "activo": seleccion,
                "entrada": st.session_state.señal_actual['entrada'],
                "lotes": st.session_state.señal_actual['lotes'],
                "sl": st.session_state.señal_actual['sl'],
                "tp": st.session_state.señal_actual['tp'],
                "tipo": st.session_state.señal_actual['tipo']
            }
            st.session_state.señal_actual = None
            st.rerun()
        if col2.button("❌ RECHAZAR"):
            st.session_state.señal_actual = None
            st.rerun()

    # PASO 2: POSICIÓN ABIERTA (Edición)
    if st.session_state.posicion_abierta:
        st.success(f"### 🔓 POSICIÓN ABIERTA: {st.session_state.posicion_abierta['activo']}")
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            # El usuario puede modificar los valores que vinieron por defecto
            st.session_state.posicion_abierta['entrada'] = c1.number_input("Precio Entrada Real", value=st.session_state.posicion_abierta['entrada'], format="%.4f")
            st.session_state.posicion_abierta['lotes'] = c2.number_input("Volumen (Lotes)", value=st.session_state.posicion_abierta['lotes'])
            
            # PASO 3: CIERRE
            st.divider()
            st.write("#### Finalizar Operación")
            cc1, cc2 = st.columns(2)
            precio_cierre = cc1.number_input("Precio de Salida / Cierre", value=precio_act, format="%.4f")
            
            if cc2.button("🏁 CERRAR Y CALCULAR RESULTADO"):
                # Cálculo simple de PnL (para Oro/Forex/Nasdaq varía, aquí usamos una base estándar)
                tipo = 1 if "COMPRA" in st.session_state.posicion_abierta['tipo'].upper() else -1
                pips = (precio_cierre - st.session_state.posicion_abierta['entrada']) * tipo
                # Multiplicador genérico (ajustar según activo)
                resultado_final = pips * st.session_state.posicion_abierta['lotes'] * 1000 
                
                # Guardar en historial
                st.session_state.wallet += resultado_final
                st.session_state.historial.append({
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Activo": st.session_state.posicion_abierta['activo'],
                    "Entrada": st.session_state.posicion_abierta['entrada'],
                    "Salida": precio_cierre,
                    "Resultado": round(resultado_final, 2)
                })
                st.session_state.posicion_abierta = None
                st.balloons()
                st.rerun()

    # HISTORIAL FINAL
    if st.session_state.historial:
        st.divider()
        st.subheader("📊 Resumen de Operaciones")
        st.table(pd.DataFrame(st.session_state.historial).tail(10))
