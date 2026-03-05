import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Jacar Pro - Institutional Terminal", layout="wide", page_icon="📈")

# Estilo CSS para mejorar la UI (Logos y Tarjetas)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #262730; color: white; border: 1px solid #4a4a4a; }
    .stButton>button:hover { border-color: #00ff00; color: #00ff00; }
    .asset-card { padding: 10px; border-radius: 10px; border: 1px solid #333; background-color: #1a1c23; text-align: center; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Inicialización segura de Session State
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: st.session_state.activo_sel = "Oro"
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel = "GC=F"
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# DICCIONARIO DE ACTIVOS CATEGORIZADOS
activos_dict = {
    "🚀 Tecnología": {"NVDA": "NVDA", "Apple": "AAPL", "Microsoft": "MSFT", "Google": "GOOGL", "Tesla": "TSLA"},
    "⚡ Energía": {"Iberdrola": "IBE.MC", "Repsol": "REP.MC", "Exxon": "XOM", "Chevron": "CVX"},
    "💰 Materias Primas": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F", "Gas Natural": "NG=F"},
    "💱 Divisas": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X", "Bitcoin": "BTC-USD"},
    "📊 Índices": {"Nasdaq 100": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"}
}

# --- 2. MENU VISUAL DE ACTIVOS ---
st.title("Jacar Investment Terminal")

tabs = st.tabs(list(activos_dict.keys()))

for i, (categoria, lista) in enumerate(activos_dict.items()):
    with tabs[i]:
        cols = st.columns(len(lista))
        for j, (nombre, ticker) in enumerate(lista.items()):
            with cols[j]:
                if st.button(f"{nombre}", key=f"btn_{ticker}"):
                    st.session_state.activo_sel = nombre
                    st.session_state.ticker_sel = ticker
                    st.rerun()

# --- 3. SIDEBAR (COPILOTO) ---
with st.sidebar:
    st.header("🏢 Wallet Management")
    st.metric("Equity (EUR)", f"{st.session_state.wallet:,.2f} €", delta="XTB Sync")
    st.divider()
    
    if st.button("🚀 COPILOTO: MONITORIZAR", use_container_width=True, type="primary"):
        if not st.session_state.cartera_abierta:
            st.warning("No hay posiciones para auditar.")
        else:
            for pos in st.session_state.cartera_abierta:
                t = yf.Ticker(pos['ticker'])
                p_actual = t.history(period="1d")['Close'].iloc[-1]
                n_act = "\n".join([n.get('title','') for n in t.news[:2]])
                p_gestion = f"Analiza: {pos['activo']} ({pos['tipo']}). In: {pos['entrada']}, SL: {pos['sl']}, TP: {pos['tp']}. Actual: {p_actual}. Noticias: {n_act}. ¿Subir SL o Prolongar TP? Breve."
                r = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":p_gestion}])
                st.info(f"**{pos['activo']}**: {r.choices[0].message.content}")

# --- 4. GRÁFICA PROFESIONAL (OVERLAY RSI/EMA) ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h")
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    precio_act = float(df['Close'].iloc[-1])
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], 
                        vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=st.session_state.activo_sel), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1.5), name="EMA 20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1, dash='dot'), name="RSI", opacity=0.4), row=1, col=1, secondary_y=True)
    
    colors_vol = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name="Volumen"), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=50, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. ANÁLISIS ---
    if st.button(f"⚖️ ANALIZAR {st.session_state.activo_sel.upper()}"):
        with st.spinner('Procesando matriz de confluencia...'):
            ticker_obj = yf.Ticker(st.session_state.ticker_sel)
            news_text = "\n".join([n.get('title', '') for n in ticker_obj.news[:5]])
            prompt = f"Analista XTB. Activo: {st.session_state.activo_sel}. Precio: {precio_act}. RSI: {df['RSI'].iloc[-1]:.1f}. Capital: {st.session_state.wallet} EUR. Noticias: {news_text}. Genera opciones INTRA, MEDIO, LARGO con Probabilidad, Acción, Lotes(1% riesgo), Entrada, TP y SL. Formato: TAG: [Prob]|[Accion]|[Lotes]|[Entrada]|[TP]|[SL]"
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
            res_ia = resp.choices[0].message.content

            def parse_tag(tag):
                m = re.search(rf"{tag}:\s*(.*)", res_ia)
                return [p.strip() for p in m.group(1).split('|')] if m else ["---"]*6

            st.session_state.señal_actual = {"intra": parse_tag("INTRA"), "medio": parse_tag("MEDIO"), "largo": parse_tag("LARGO")}
            st.rerun()

# --- 6. TARJETAS DE SEÑAL ---
if st.session_state.señal_actual:
    st.divider()
    cols_res = st.columns(3)
    for i, (name, tag) in enumerate([("INTRADÍA", "intra"), ("MEDIO PLAZO", "medio"), ("LARGO PLAZO", "largo")]):
        s = st.session_state.señal_actual[tag]
        with cols_res[i].container(border=True):
            st.subheader(name)
            st.metric("Probabilidad", s[0])
            st.markdown(f"**{s[1]}** | {s[2]} lotes")
            st.markdown(f"**Entrada:** {s[3]}\n\n**TP:** {s[4]} | **SL:** {s[5]}")
            if st.button(f"Aceptar {name}", key=f"exe_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "ticker": st.session_state.ticker_sel, "tipo": s[1], "lotes": s[2],
                    "entrada": s[3], "tp": s[4], "sl": s[5], "prob": s[0]
                })
                st.session_state.señal_actual = None
                st.rerun()

# --- 7. CARTERA ACTIVA ---
st.divider()
st.subheader("💼 Posiciones Abiertas (XTB)")
if st.session_state.cartera_abierta:
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.markdown(f"### {pos['activo']} ({pos['tipo']})")
            c1.write(f"In: {pos['entrada']} | SL: {pos['sl']} | TP: {pos['tp']}")
            
            # Gestión dinámica
            pos['sl'] = c2.text_input("Ajustar SL", value=pos['sl'], key=f"sl_{pos['id']}")
            pos['tp'] = c2.text_input("Ajustar TP", value=pos['tp'], key=f"tp_{pos['id']}")
            
            pnl_val = c3.number_input("PnL (€)", key=f"p_{pos['id']}")
            if c3.button("Cerrar", key=f"c_{pos['id']}"):
                st.session_state.wallet += pnl_val
                st.session_state.cartera_abierta.pop(i)
                st.rerun()
else:
    st.info("Terminal lista. Selecciona un activo para empezar.")
