import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from openai import OpenAI
from datetime import datetime

# 1. CONFIGURACIÓN E INICIO (Puntos 5 y 8)
st.set_page_config(page_title="Jacar Pro Terminal", layout="wide")

# Inicializar estados de memoria (Para que no se borren al interactuar)
if 'wallet' not in st.session_state:
    st.session_state.wallet = 18000.0
if 'historial' not in st.session_state:
    st.session_state.historial = []

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 2. PANEL LATERAL (Puntos 5, 8, 9, 10)
with st.sidebar:
    st.title(f"💰 Balance: {st.session_state.wallet:,.2f} USD")
    st.divider()
    st.header("⚙️ Estrategia")
    obj_diario = st.number_input("Objetivo Diario ($)", value=200.0)
    perfil = st.radio("Frecuencia (Punto 9)", ["Scalping (Muchas/Poco)", "Swing (Pocas/Mucho)"])
    tf_visual = st.selectbox("Temporalidad (Punto 10)", ["1m", "5m", "15m", "1h", "1d"], index=2)
    
    st.divider()
    activos = {"Oro": "GC=F", "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", "Brent": "BZ=F", "Bitcoin": "BTC-USD"}
    seleccion = st.selectbox("Activo a analizar", list(activos.keys()))

# 3. OBTENCIÓN Y ANÁLISIS DE DATOS (Puntos 2, 6, 7 corregidos)
ticker = activos[seleccion]

# Lógica de ajuste automático de temporalidad
ajuste_temporal = {
    "1m": "1d",    # Si quieres velas de 1m, bajamos solo 1 día
    "5m": "5d",    # Si quieres velas de 5m, bajamos 5 días
    "15m": "5d",
    "1h": "1mo",   # Si quieres velas de 1h, bajamos 1 mes
    "1d": "max"    # Si quieres velas diarias, bajamos todo el historial
}

periodo_ajustado = ajuste_temporal.get(tf_visual, "5d")

# Descarga con el ajuste dinámico
df = yf.download(ticker, period=periodo_ajustado, interval=tf_visual)

if isinstance(df.columns, pd.MultiIndex): 
    df.columns = df.columns.get_level_values(0)

df = df.dropna()

if not df.empty:
    # Recalcular indicadores con los nuevos datos
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # Soportes y resistencias basados en la temporalidad visible
    resistencia = float(df['High'].tail(40).max())
    soporte = float(df['Low'].tail(40).min())
    precio_act = float(df['Close'].iloc[-1])

    # 4. PANEL DE OPORTUNIDADES (Punto 1)
    st.subheader("🚀 Monitor de Oportunidades")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Precio {seleccion}", f"{precio_act:.4f}")
    c2.metric("RSI (Fuerza)", f"{df['RSI'].iloc[-1]:.2f}")
    c3.metric("Resistencia", f"{resistencia:.4f}")
    c4.metric("Soporte", f"{soporte:.4f}")

  # 5. GRÁFICO PROFESIONAL (Busca esta sección en tu app.py)
    fig.update_layout(
        template="plotly_dark", 
        height=600, # He subido un poco la altura para que se vea mejor
        xaxis_rangeslider_visible=False,
        yaxis=dict(
            autorange=True,      # <--- ESTE ES EL TRUCO: Auto-zoom al precio
            fixedrange=False,     # Permite que tú muevas el eje Y con el ratón
            side="right", 
            gridcolor='rgba(255,255,255,0.1)'
        ),
        margin=dict(l=10, r=50, t=30, b=20)
    )
    # 6. GENERACIÓN DE ORDEN Y REGISTRO (Puntos 3, 4)
    if st.button("🧠 ANALIZAR Y GENERAR ORDEN"):
        with st.spinner('IA Calculando rangos basándose en contexto geopolítico y técnico...'):
            prompt = f"""
            Analiza {seleccion}. Precio: {precio_act}. RSI: {df['RSI'].iloc[-1]:.2f}. 
            Soporte: {soporte}, Resistencia: {resistencia}. Estilo: {perfil}. Objetivo: {obj_diario}.
            Dame una orden DIRECTA: Acción, Entrada, Lotes, SL y TP. 
            Ten en cuenta patrones históricos y situación de mercado actual.
            """
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Eres un ejecutor de trading preciso."}, {"role": "user", "content": prompt}]
            )
            st.session_state.ultima_orden = resp.choices[0].message.content
            st.session_state.precio_sugerido = precio_act

    if 'ultima_orden' in st.session_state:
        st.markdown("---")
        st.subheader("📋 Orden Detectada")
        st.info(st.session_state.ultima_orden)
        
        with st.expander("✅ REGISTRAR EJECUCIÓN (Journaling)", expanded=True):
            col_reg1, col_reg2, col_reg3 = st.columns(3)
            p_entrada = col_reg1.number_input("Precio Real de Entrada", value=st.session_state.precio_sugerido)
            lotes_real = col_reg2.number_input("Lotes Finales", value=0.1)
            pnl = col_reg3.number_input("Resultado Final ($)", value=0.0)
            
            if st.button("💾 Guardar en Historial y Actualizar Bankroll"):
                st.session_state.wallet += pnl
                st.session_state.historial.append({
                    "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                    "Activo": seleccion,
                    "Entrada": p_entrada,
                    "Resultado": pnl
                })
                st.success("¡Operación registrada! El balance se ha actualizado.")
                # Limpiar orden actual para la siguiente
                del st.session_state.ultima_orden
                st.rerun()

    # 7. RESUMEN SEMANAL/MENSUAL (Punto 4)
    st.divider()
    st.subheader("📊 Historial de Operaciones")
    if st.session_state.historial:
        st.table(pd.DataFrame(st.session_state.historial))
    else:
        st.write("No hay operaciones registradas este mes.")
else:
    st.warning("No hay datos disponibles. Verifica la conexión o el mercado.")
