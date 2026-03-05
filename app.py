import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Jacar Pro - Copiloto de Gestión", layout="wide")

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: 
    st.session_state.activo_sel = "Oro"
    st.session_state.ticker_sel = "GC=F"

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ACTIVOS POR GRUPOS
activos_dict = {
    "Tecnología": {"NVDA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Google": "GOOGL", "Tesla": "TSLA"},
    "Energía": {"Iberdrola": "IBE.MC", "Repsol": "REP.MC", "Exxon": "XOM", "Chevron": "CVX"},
    "Materias Primas": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F", "Gas Natural": "NG=F"},
    "Divisas": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X", "Bitcoin": "BTC-USD"},
    "Índices": {"Nasdaq 100": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"}
}

# --- 2. PANEL SUPERIOR ---
st.write("### 🔍 Radar Sectorial")
for grupo, lista in activos_dict.items():
    exp = st.expander(f"📂 {grupo}", expanded=(grupo == "Tecnología"))
    cols = exp.columns(len(lista))
    for i, (nombre, ticker) in enumerate(lista.items()):
        if cols[i].button(nombre, key=f"btn_{ticker}", use_container_width=True):
            st.session_state.activo_sel = nombre
            st.session_state.ticker_sel = ticker
            st.rerun()

# --- 3. SIDEBAR CON COPILOTO ---
with st.sidebar:
    st.header("🎛️ Gestión de Riesgo")
    st.metric("Bankroll (EUR)", f"{st.session_state.wallet:,.2f} €")
    st.divider()
    
    # COPILOTO DE GESTIÓN DINÁMICA
    if st.button("🚀 COPILOTO: ANALIZAR GESTIÓN", use_container_width=True, type="primary"):
        if not st.session_state.cartera_abierta:
            st.warning("Sin posiciones abiertas.")
        else:
            with st.spinner("Analizando fuerza de tendencia y noticias..."):
                for pos in st.session_state.cartera_abierta:
                    t = yf.Ticker(pos['ticker'])
                    hist = t.history(period="1d", interval="15m")
                    p_actual = hist['Close'].iloc[-1]
                    n_act = "\n".join([n.get('title','') for n in t.news[:3]])
                    
                    # Prompt de gestión proactiva
                    p_gestion = f"""Analista Senior. Posición {pos['tipo']} en {pos['activo']}. 
                    Entrada: {pos['entrada']}, SL: {pos['sl']}, TP: {pos['tp']}. 
                    Precio Actual: {p_actual}. Noticias: {n_act}.
                    TAREA: Si va ganando, indica si debemos SUBIR SL para asegurar o PROLONGAR TP para maximizar. 
                    Si hay noticias malas, indica CERRAR. 
                    Responde breve: [ACCIÓN RECOMENDADA] + [MOTIVO]."""
                    
                    r = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":p_gestion}])
                    msg = r.choices[0].message.content
                    st.info(f"**{pos['activo']}**: {msg}")

# --- 4. GRÁFICA ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h")
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    precio_act = float(df['Close'].iloc[-1])
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], 
                        vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1.5), name="EMA 20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1, dash='dot'), name="RSI", opacity=0.4), row=1, col=1, secondary_y=True)
    
    colors_vol = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name="Volumen"), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. ANÁLISIS ---
    if st.button("⚖️ GENERAR MATRIZ DE CONFLUENCIA"):
        ticker_obj = yf.Ticker(st.session_state.ticker_sel)
        news_text = "\n".join([n.get('title', '') for n in ticker_obj.news[:5]])
        prompt = f"Analista XTB. Activo: {st.session_state.activo_sel}. Precio: {precio_act}. RSI: {df['RSI'].iloc[-1]:.1f}. Capital: {st.session_state.wallet} EUR. Noticias: {news_text}. Genera 3 opciones claras: INTRA, MEDIO, LARGO con Probabilidad, Acción, Lotes(1% riesgo), Entrada, TP y SL. Formato: TAG: [Prob]|[Accion]|[Lotes]|[Entrada]|[TP]|[SL]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        res_ia = resp.choices[0].message.content

        def parse_tag(tag):
            m = re.search(rf"{tag}:\s*(.*)", res_ia)
            return [p.strip() for p in m.group(1).split('|')] if m else ["---"]*6

        st.session_state.señal_actual = {"intra": parse_tag("INTRA"), "medio": parse_tag("MEDIO"), "largo": parse_tag("LARGO")}
        st.rerun()

# --- 6. RESULTADOS ---
if st.session_state.señal_actual:
    cols_res = st.columns(3)
    for i, (name, tag) in enumerate([("INTRADÍA", "intra"), ("MEDIO PLAZO", "medio"), ("LARGO PLAZO", "largo")]):
        s = st.session_state.señal_actual[tag]
        with cols_res[i].container(border=True):
            st.write(f"**{name}** ({s[0]})")
            st.write(f"**{s[1]}** | {s[2]} lotes")
            st.write(f"In: {s[3]} | TP: {s[4]}")
            if st.button(f"Ejecutar {name}", key=f"exe_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "ticker": st.session_state.ticker_sel, "tipo": s[1], "lotes": s[2],
                    "entrada": s[3], "tp": s[4], "sl": s[5], "prob": s[0]
                })
                st.rerun()

# --- 7. CARTERA DINÁMICA ---
st.divider()
st.subheader("💼 Gestión Activa de Posiciones")
if st.session_state.cartera_abierta:
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([1.5, 2, 1.5, 1])
            c1.write(f"**{pos['activo']}** | {pos['tipo']}")
            
            # Campos editables para seguir las sugerencias de la IA
            new_sl = c2.text_input("Ajustar SL", value=pos['sl'], key=f"sl_mod_{pos['id']}")
            new_tp = c2.text_input("Ajustar TP", value=pos['tp'], key=f"tp_mod_{pos['id']}")
            pos['sl'], pos['tp'] = new_sl, new_tp # Actualización dinámica
            
            c3.write(f"Lotes: {pos['lotes']}")
            pnl_v = c4.number_input("PnL (€)", key=f"pnl_{pos['id']}")
            if c4.button("Cerrar", key=f"close_{pos['id']}"):
                st.session_state.wallet += pnl_v
                st.session_state.cartera_abierta.pop(i)
                st.rerun()
