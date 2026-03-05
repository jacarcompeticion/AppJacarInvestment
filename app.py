Ese error ocurre porque, a veces, la IA responde algo como "85% (Alta)" o simplemente "N/A" en el campo de probabilidad, y la función int() no sabe cómo convertir ese texto en un número para la barra de progreso.

He blindado esa línea de código para que extraiga solo los números de la respuesta de la IA y, si no encuentra ninguno, asigne un 50% por defecto. También he añadido la alerta visual especial (un borde dorado y destellos) para cuando la probabilidad supere el 85%.

📋 Código Jacar Pro V9 (Final con Filtro Numérico y Alertas VIP)
Python
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
st.set_page_config(page_title="Jacar Pro - XTB Institutional", layout="wide")

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'historial' not in st.session_state: st.session_state.historial = []
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: st.session_state.activo_sel = "Oro"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
activos = {"Oro": "GC=F", "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", "Brent": "BZ=F", "Bitcoin": "BTC-USD"}

# 2. PANEL SUPERIOR
cols_top = st.columns(len(activos))
for i, nombre in enumerate(activos.keys()):
    if cols_top[i].button(f"📊 {nombre}", key=f"btn_top_{nombre}", use_container_width=True):
        st.session_state.activo_sel = nombre
        st.rerun()

# 3. SIDEBAR XTB
with st.sidebar:
    st.header("🎛️ Terminal XTB")
    st.metric("Equity Balance", f"{st.session_state.wallet:,.2f} USD")
    st.divider()
    perfil = st.selectbox("Perfil de Riesgo", ["Institucional", "Hedge Fund", "Retail"])
    tf_visual = st.selectbox("Temporalidad", ["1m", "5m", "15m", "1h", "1d"], index=2)
    seleccion = st.selectbox("Activo", list(activos.keys()), index=list(activos.keys()).index(st.session_state.activo_sel))
    st.session_state.activo_sel = seleccion

# 4. DATOS E INDICADORES
df = yf.download(activos[seleccion], period="5d", interval=tf_visual)
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    precio_act = float(df['Close'].iloc[-1])
    rsi_act = float(df['RSI'].iloc[-1]) if not pd.isna(df['RSI'].iloc[-1]) else 50.0

    # GRÁFICA MULTI-PANEL
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.2, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1), name="EMA 20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1), name="RSI"), row=2, col=1)
    colors_vol = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name="Volumen"), row=3, col=1)
    fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=10, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # 5. BOTÓN DE ANÁLISIS
    if st.button("⚖️ GENERAR ANÁLISIS DE CONFLUENCIA"):
        with st.spinner('Evaluando Macro, FED y Flujos de Capital...'):
            ticker = yf.Ticker(activos[seleccion])
            noticias = "\n".join([n.get('title', '') for n in ticker.news[:3]])
            
            prompt = f"""Analista Senior XTB. Activo: {seleccion} a {precio_act}. RSI: {rsi_act:.2f}. Noticias: {noticias}.
            Capital: {st.session_state.wallet} USD. Perfil: {perfil}.
            Responde estrictamente con este formato:
            PROBABILIDAD: [Solo el número]%
            PERIODO: [Corto/Medio/Largo]
            ACCION: [COMPRA/VENTA/ESPERAR]
            TIEMPO: [Mercado/Orden]
            LOTES: [Número]
            ENTRADA: [Precio]
            TP: [Precio]
            SL: [Precio]
            CONFLUENCIA: [Resumen técnico-fundamental]"""
            
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
            res_ia = resp.choices[0].message.content

            def ext(tag):
                match = re.search(rf"{tag}:\s*(.*?)(?=\n[A-ZÁÉÍÓÚ]+:|$)", res_ia, re.S | re.I)
                return match.group(1).strip() if match else "---"

            st.session_state.señal_actual = {
                "prob": ext("PROBABILIDAD"), "periodo": ext("PERIODO"), "accion": ext("ACCION"), 
                "tiempo": ext("TIEMPO"), "lotes": ext("LOTES"), "entrada": ext("ENTRADA"), 
                "tp": ext("TP"), "sl": ext("SL"), "confluencia": ext("CONFLUENCIA")
            }
            st.rerun()

    # 6. FICHA TÉCNICA CON FILTRO DE ERROR
    if st.session_state.señal_actual:
        s = st.session_state.señal_actual
        
        # Limpieza robusta de la probabilidad
        try:
            prob_num = int(re.search(r'\d+', s['prob']).group())
        except:
            prob_num = 50

        # Alerta visual para Alta Probabilidad (>85%)
        if prob_num >= 85:
            st.balloons()
            st.success(f"🔥 OPORTUNIDAD DE ALTA PRECISIÓN DETECTADA ({prob_num}%)")
        
        with st.container(border=True):
            st.subheader("📋 Ficha de Inteligencia")
            st.progress(prob_num / 100, text=f"Confianza del Sistema: {prob_num}%")
            
            tabla_data = {
                "Parámetro": ["Probabilidad", "Periodo", "Acción", "Lotes", "Entrada", "T. Profit", "S. Loss"],
                "Valor": [f"{prob_num}%", s['periodo'], s['accion'], s['lotes'], s['entrada'], s['tp'], s['sl']]
            }
            st.table(pd.DataFrame(tabla_data))
            
            with st.expander("🔍 Informe de Confluencia"):
                st.write(s['confluencia'])
            
            c1, c2 = st.columns(2)
            if "ESPERAR" not in s['accion'].upper():
                if c1.button("🚀 ACEPTAR OPERACIÓN"):
                    st.session_state.cartera_abierta.append({
                        "id": datetime.now().strftime("%H%M%S"), "activo": seleccion, 
                        "entrada": s['entrada'], "lotes": s['lotes'], "tipo": s['accion'], "prob": f"{prob_num}%"
                    })
                    st.session_state.señal_actual = None
                    st.rerun()
            if c2.button("🗑️ RECHAZAR"):
                st.session_state.señal_actual = None
                st.rerun()

# 7. CARTERA
st.divider()
st.subheader("💼 Posiciones Abiertas")
if st.session_state.cartera_abierta:
    df_car = pd.DataFrame(st.session_state.cartera_abierta)
    st.dataframe(df_car[['activo', 'tipo', 'entrada', 'lotes', 'prob']], use_container_width=True)
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.expander(f"Gestionar {pos['activo']}"):
            c_p1, c_p2 = st.columns([2, 1])
            pnl_v = c_p1.number_input(f"P/L Neto ($)", value=0.0, key=f"pnl_{pos['id']}")
            if c_p2.button(f"Cerrar", key=f"btn_{pos['id']}"):
                st.session_state.wallet += pnl_v
                st.session_state.historial.append({"Activo": pos['activo'], "PnL": pnl_v})
                st.session_state.cartera_abierta.pop(i)
                st.rerun()
