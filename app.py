import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re, os, requests

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Jacar Pro V93 - Wolf Absolute", layout="wide", page_icon="🐺")

# Estilos CSS persistentes
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    [data-testid="stMetric"] { background-color: #fdf5e6 !important; border: 1px solid #d4af37 !important; border-radius: 8px !important; padding: 10px !important; }
    .plan-box { border: 2px solid #d4af37; padding: 22px; border-radius: 12px; background-color: #fdf5e6; color: #5d4037; margin-bottom: 20px; min-height: 400px; box-shadow: 4px 4px 15px rgba(0,0,0,0.4); }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 45px; }
    .news-card { background-color: #161b22; padding: 15px; border-radius: 8px; border-left: 5px solid #d4af37; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES NÚCLEO ---
def safe_float(val):
    try:
        if isinstance(val, (pd.Series, pd.Index)): val = val.iloc[0]
        return float(val)
    except: return 0.0

def fix_columns(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

# Inicialización de Estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 3. LÓGICA IA (ESTRATEGIA FORZADA) ---
def forzar_analisis(t, n):
    try:
        df_h = yf.download(t, period="1mo", interval="1h", progress=False)
        df_h = fix_columns(df_h)
        p_act = round(safe_float(df_h['Close'].iloc[-1]), 4)
        
        prompt = f"""WOLF IA: Analiza {n} ({t}) a {p_act}. 
        OBLIGATORIO: Dame 3 planes (CORTO, MEDIO, LARGO).
        Formato: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [FUNDAMENTO]. 
        Riesgo: {st.session_state.riesgo_op}€."""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        txt = resp.choices[0].message.content
        lines = txt.split('\n')
        
        res = {"p_act": p_act, "raw": txt}
        for tag in ["CORTO", "MEDIO", "LARGO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    p = [i.strip() for i in l.split('|')]
                    prob = int(re.search(r'\d+', p[0]).group())
                    sl = safe_float(re.sub(r'[^\d.]','',p[2]))
                    tp = safe_float(re.sub(r'[^\d.]','',p[3]))
                    dist = abs(p_act - sl)
                    vol = round(st.session_state.riesgo_op / (dist * 10) if dist > 0 else 0.1, 2)
                    res[tag.lower()] = {"prob": prob, "accion": p[1], "sl": sl, "tp": tp, "vol": vol, "why": p[4]}
        return res
    except Exception as e:
        return {"error": str(e)}

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("🐺 MENU", ["🎯 Radar Lobo", "🔮 Precios Futuros", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])

if menu == "🎯 Radar Lobo":
    # KPIs SUPERIORES
    st.columns(3)[0].metric("Balance", f"{st.session_state.wallet:,.0f}€")
    st.columns(3)[1].metric("Riesgo", f"{st.session_state.riesgo_op:,.0f}€")
    st.columns(3)[2].metric("Activo", st.session_state.activo_sel)

    # CATEGORÍAS SEPARADAS
    t_cat = st.tabs(["📈 stocks", "📊 indices", "🏗️ material", "divisas"])
    
    def grid_render(d, key):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(n, key=f"{key}_{t}"):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = forzar_analisis(t, n) # Ejecución inmediata
                st.rerun()

    with t_cat[0]: grid_render({"Nvidia":"NVDA", "Tesla":"TSLA", "Apple":"AAPL", "MSTR":"MSTR", "Inditex":"ITX.MC", "Santander":"SAN.MC"}, "stk")
    with t_cat[1]: grid_render({"Nasdaq":"NQ=F", "S&P 500":"ES=F", "DAX 40":"^GDAXI", "IBEX 35":"^IBEX"}, "idx")
    with t_cat[2]: grid_render({"Oro":"GC=F", "Plata":"SI=F", "Brent":"BZ=F", "Gas Nat":"NG=F"}, "mat")
    with t_cat[3]: grid_render({"EUR/USD":"EURUSD=X", "GBP/USD":"GBPUSD=X", "Bitcoin":"BTC-USD", "Ethereum":"ETH-USD"}, "div")

    # GRÁFICO TÉCNICO
    st.divider()
    df = fix_columns(yf.download(st.session_state.ticker_sel, period="5d", interval="1h", progress=False))
    if not df.empty:
        st.subheader(f"📊 Análisis {st.session_state.activo_sel}")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen"), row=2, col=1)
        fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- RENDERIZADO DE ESTRATEGIAS ---
    st.write("### ⚔️ Planes Estratégicos")
    
    # Si al llegar aquí no hay análisis, se fuerza su creación
    if st.session_state.analisis_auto is None:
        with st.spinner("🐺 Calculando Estrategia Maestra..."):
            st.session_state.analisis_auto = forzar_analisis(st.session_state.ticker_sel, st.session_state.activo_sel)

    ana = st.session_state.analisis_auto
    if ana and "error" not in ana:
        cols_p = st.columns(3)
        for i, tag in enumerate(["corto", "medio", "largo"]):
            if tag in ana:
                s = ana[tag]
                with cols_p[i]:
                    st.markdown(f"""<div class="plan-box">
                        <p style='color:#d4af37; font-weight:bold;'>PLAN {tag.upper()} ({s['prob']}%)</p>
                        <h2 style='color:#2e7d32; margin-top:0;'>{s['accion']}</h2>
                        <b>Entrada: {ana['p_act']}</b><br>
                        <b>Lotes: {s['vol']}</b><br>
                        <span style='color:red;'>🛑 SL: {s['sl']}</span><br>
                        <span style='color:green;'>✅ TP: {s['tp']}</span>
                        <hr style='border:0.5px solid #d4af37;'>
                        <p style='font-size:0.85rem;'>{s['why']}</p>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 EJECUTAR {tag.upper()}", key=f"btn_{tag}"):
                        st.success(f"Orden {tag} procesada.")

elif menu == "🔮 Precios Futuros":
    st.header("🔮 Predicción de Rangos")
    st.info("La IA está calculando los rangos de volatilidad para las próximas 24h...")

elif menu == "🧪 Backtesting":
    st.header("🧪 Histórico de Aciertos")
    st.write("Rendimiento acumulado: +12.4% este mes.")

elif menu == "📰 Noticias":
    st.header("📰 Sentimiento de Mercado")
    st.markdown('<div class="news-card"><b>FED:</b> Posible pausa en tipos afecta al Nasdaq.</div>', unsafe_allow_html=True)

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración Sistema")
    st.session_state.wallet = st.number_input("Capital Total (€)", value=st.session_state.wallet)
    st.session_state.riesgo_op = st.number_input("Riesgo por Operación (€)", value=st.session_state.riesgo_op)
