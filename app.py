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
st.set_page_config(page_title="Jacar Pro V16", layout="wide", page_icon="⚖️")

st.markdown("""
    <style>
    .buy-card { border-left: 5px solid #00ff00; padding-left: 15px; background-color: #1a1c23; border-radius: 0 10px 10px 0; }
    .sell-card { border-left: 5px solid #ff4b4b; padding-left: 15px; background-color: #1a1c23; border-radius: 0 10px 10px 0; }
    .stMetric { background-color: #0e1117; border: 1px solid #333; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: st.session_state.activo_sel = "Oro"
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel = "GC=F"
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

activos_dict = {
    "💻 Tecnología (USD)": {"NVDA": "NVDA", "Apple": "AAPL", "MSFT": "MSFT", "Tesla": "TSLA"},
    "⚡ Energía": {"Iberdrola": "IBE.MC", "Repsol": "REP.MC", "Exxon": "XOM", "Chevron": "CVX"},
    "⚱️ Materias Primas (USD)": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F", "Gas Nat": "NG=F"},
    "💵 Divisas": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X", "Bitcoin": "BTC-USD"},
    "📈 Índices": {"Nasdaq 100": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"}
}

# --- 2. MENU VISUAL ---
st.title("🏛️ Jacar Global Institutional Terminal")
tabs = st.tabs(list(activos_dict.keys()))
for i, (categoria, lista) in enumerate(activos_dict.items()):
    with tabs[i]:
        cols = st.columns(len(lista))
        for j, (nombre, ticker) in enumerate(lista.items()):
            if cols[j].button(f"{nombre}", key=f"btn_{ticker}"):
                st.session_state.activo_sel = nombre
                st.session_state.ticker_sel = ticker
                st.rerun()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🏢 Gestión de Capital")
    st.metric("Balance Cuenta", f"{st.session_state.wallet:,.2f} €")
    st.divider()
    if st.button("🚀 COPILOTO: ANALIZAR RIESGO", use_container_width=True):
        if not st.session_state.cartera_abierta:
            st.warning("Sin posiciones activas.")
        else:
            for pos in st.session_state.cartera_abierta:
                t = yf.Ticker(pos['ticker'])
                p_actual = t.history(period="1d")['Close'].iloc[-1]
                p_gestion = f"Soy analista. Posición {pos['tipo']} en {pos['activo']}. Entrada: {pos['entrada']}, SL: {pos['sl']}, TP: {pos['tp']}. Precio Actual: {p_actual}. Indica si asegurar beneficios o prolongar. Breve."
                r = client.chat.completions.create(model="gpt-4o", messages=[{"role":"user", "content":p_gestion}])
                st.info(f"**{pos['activo']}**: {r.choices[0].message.content}")

# --- 4. GRÁFICA ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h")
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    precio_act = float(df['Close'].iloc[-1])
    moneda = "€" if any(x in st.session_state.ticker_sel for x in [".MC", "GDAXI", "IBEX"]) else "$"
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=f"{st.session_state.activo_sel}"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1.5), name="EMA 20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1, dash='dot'), name="RSI", opacity=0.4), row=1, col=1, secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    if st.button(f"⚖️ ANALIZAR {st.session_state.activo_sel.upper()} ({moneda})"):
        with st.spinner('Procesando datos...'):
            ticker_obj = yf.Ticker(st.session_state.ticker_sel)
            news_list = ticker_obj.news[:5]
            news_text = "\n".join([n.get('title', '') for n in news_list])
            
            prompt = f"""Analista XTB. Activo: {st.session_state.activo_sel}. Precio: {precio_act} {moneda}. RSI: {df['RSI'].iloc[-1]:.1f}. Capital: {st.session_state.wallet} EUR. Noticias: {news_text}.
            Genera 3 opciones (INTRA, MEDIO, LARGO) con Probabilidad, Acción (COMPRA/VENTA), Lotes (Riesgo 1% Bank en EUR), Entrada, TP y SL. 
            IMPORTANTE: Entrada, TP y SL en {moneda}. Lotes calculados para bank en EUR.
            Formato: TAG: [Prob]|[Accion]|[Lotes]|[Entrada]|[TP]|[SL]"""
            
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
            res_ia = resp.choices[0].message.content

            def parse_tag(tag):
                m = re.search(rf"{tag}:\s*(.*)", res_ia)
                if m:
                    parts = m.group(1).split('|')
                    return [p.strip() for p in parts]
                return ["---"]*6

            st.session_state.señal_actual = {"intra": parse_tag("INTRA"), "medio": parse_tag("MEDIO"), "largo": parse_tag("LARGO"), "moneda": moneda}
            st.rerun()

# --- 5. RESULTADOS ---
if st.session_state.señal_actual:
    st.divider()
    cols_res = st.columns(3)
    mon = st.session_state.señal_actual["moneda"]
    for i, (name, tag) in enumerate([("INTRADÍA", "intra"), ("MEDIO PLAZO", "medio"), ("LARGO PLAZO", "largo")]):
        s = st.session_state.señal_actual[tag]
        tipo = s[1].upper()
        card_style = "buy-card" if "COMPRA" in tipo else "sell-card"
        with cols_res[i].container():
            st.markdown(f"<div class='{card_style}'><h3>{name}</h3>", unsafe_allow_html=True)
            st.metric("Éxito", s[0])
            st.write(f"**{tipo}** | **{s[2]} lotes**")
            st.write(f"In: {s[3]} {mon} | TP: {s[4]} {mon}")
            if st.button(f"Ejecutar {name}", key=f"exe_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "ticker": st.session_state.ticker_sel, "tipo": tipo, "lotes": s[2],
                    "entrada": s[3], "tp": s[4], "sl": s[5], "moneda": mon
                })
                st.session_state.señal_actual = None
                st.rerun()

# --- 6. CARTERA ---
st.divider()
st.subheader("💼 Posiciones Abiertas")
if st.session_state.cartera_abierta:
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            pref = "🟢" if "COMPRA" in pos['tipo'] else "🔴"
            c1.markdown(f"**{pref} {pos['activo']}** ({pos['tipo']})")
            c1.write(f"Entrada: {pos['entrada']} {pos['moneda']}")
            pos['sl'] = c2.text_input(f"SL ({pos['moneda']})", value=pos['sl'], key=f"sl_{pos['id']}")
            pos['tp'] = c2.text_input(f"TP ({pos['moneda']})", value=pos['tp'], key=f"tp_{pos['id']}")
            pnl = c3.number_input("PnL (€)", key=f"pnl_{pos['id']}")
            if c3.button("Cerrar Posición", key=f"c_{pos['id']}"):
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                st.rerun()
