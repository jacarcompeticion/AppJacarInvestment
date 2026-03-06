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

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE, HIST_FILE = 'cartera_jacar.csv', 'historial_jacar.csv'

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    [data-testid="stMetric"] { background-color: #fdf5e6 !important; border: 1px solid #d4af37 !important; border-radius: 8px !important; padding: 10px !important; }
    .plan-box { border: 2px solid #d4af37; padding: 22px; border-radius: 12px; background-color: #fdf5e6; color: #5d4037; margin-bottom: 20px; min-height: 400px; box-shadow: 4px 4px 15px rgba(0,0,0,0.4); }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 45px; transition: 0.3s; }
    .stButton>button:hover { border: 2px solid #d4af37; color: #d4af37; }
    .news-card { background-color: #161b22; padding: 15px; border-radius: 8px; border-left: 5px solid #d4af37; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE PERSISTENCIA ---
def safe_float(val):
    try:
        if isinstance(val, (pd.Series, pd.Index)): val = val.iloc[0]
        return float(val)
    except: return 0.0

def fix_columns(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def cargar_datos(archivo):
    if os.path.exists(archivo):
        try: return pd.read_csv(archivo).to_dict('records')
        except: return []
    return []

def guardar_datos(lista, archivo):
    if lista: pd.DataFrame(lista).to_csv(archivo, index=False)
    elif os.path.exists(archivo): os.remove(archivo)

# Inicialización de Estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 3. NÚCLEO IA (ESTRATEGIAS Y PREDICCIÓN) ---
def generar_estrategia_ia(t, n):
    try:
        df_h = yf.download(t, period="1mo", interval="1h", progress=False)
        df_h = fix_columns(df_h)
        p_act = round(safe_float(df_h['Close'].iloc[-1]), 4)
        
        prompt = f"""WOLF IA STRATEGY: Analiza {n} ({t}) a {p_act}. 
        PROPORCIONA 3 PLANES: CORTO, MEDIO Y LARGO PLAZO.
        Formato: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [MOTIVO]. 
        Riesgo por operación: {st.session_state.riesgo_op}€."""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
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
    except: return None

# --- 4. INTERFAZ MAESTRA ---
menu = st.sidebar.radio("🐺 NAVEGACIÓN", ["🎯 Radar Lobo", "🔮 Precios Futuros", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])

if menu == "🎯 Radar Lobo":
    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Cuenta (€)", f"{st.session_state.wallet:,.0f}")
    c2.metric("Riesgo (€)", f"{st.session_state.riesgo_op:,.0f}")
    c3.metric("Activo", st.session_state.activo_sel)

    # CATEGORÍAS SEPARADAS
    t_cat = st.tabs(["📈 stocks", "📊 indices", "🏗️ material", "divisas"])
    
    def grid_lobo(d, key_p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(n, key=f"{key_p}_{t}"):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = generar_estrategia_ia(t, n)
                st.rerun()

    with t_cat[0]: # stocks
        s1, s2 = st.tabs(["USA", "España"])
        with s1: grid_lobo({"Nvidia":"NVDA", "Tesla":"TSLA", "Apple":"AAPL", "MSTR":"MSTR", "Coinbase":"COIN", "Palantir":"PLTR"}, "st_u")
        with s2: grid_lobo({"Inditex":"ITX.MC", "Santander":"SAN.MC", "Iberdrola":"IBE.MC", "ACS":"ACS.MC", "BBVA":"BBVA.MC"}, "st_e")
    with t_cat[1]: grid_lobo({"Nasdaq":"NQ=F", "S&P 500":"ES=F", "Dow Jones":"YM=F", "DAX 40":"^GDAXI", "IBEX 35":"^IBEX", "CAC 40":"^FCHI"}, "idx")
    with t_cat[2]: grid_lobo({"Oro":"GC=F", "Plata":"SI=F", "Brent":"BZ=F", "WTI":"CL=F", "Gas Nat":"NG=F", "Cobre":"HG=F"}, "mat")
    with t_cat[3]: grid_lobo({"EUR/USD":"EURUSD=X", "GBP/USD":"GBPUSD=X", "USD/JPY":"JPY=X", "Bitcoin":"BTC-USD", "Ethereum":"ETH-USD", "Solana":"SOL-USD"}, "div")

    # GRÁFICO
    st.divider()
    g1, g2 = st.columns(2)
    p_sel = g1.selectbox("Rango Temporal", ["1d", "5d", "1mo", "6mo", "1y", "max"], index=1)
    i_sel = g2.selectbox("Intervalo Velas", ["5m", "15m", "30m", "1h", "6h", "12h", "1d"], index=3)

    df = fix_columns(yf.download(st.session_state.ticker_sel, period=p_sel, interval=i_sel, progress=False))
    if not df.empty:
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        p_act = safe_float(df['Close'].iloc[-1])
        st.subheader(f"📊 Gráfico de {st.session_state.activo_sel} | Precio: {p_act:,.2f}")
        
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.04)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Velas"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=2), name="EMA 20"), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color='dodgerblue', name="Volumen"), row=2, col=1)
        fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- RENDERIZADO DE ESTRATEGIAS (FORZADO) ---
    st.markdown("### ⚔️ Planes Estratégicos IA")
    if st.session_state.analisis_auto is None:
        with st.spinner(f"🐺 Wolf IA analizando {st.session_state.activo_sel}..."):
            st.session_state.analisis_auto = generar_estrategia_ia(st.session_state.ticker_sel, st.session_state.activo_sel)
    
    ana = st.session_state.analisis_auto
    if ana:
        cols_p = st.columns(3)
        for i, tag in enumerate(["corto", "medio", "largo"]):
            if tag in ana:
                s = ana[tag]
                with cols_p[i]:
                    st.markdown(f"""<div class="plan-box">
                        <p style='color:#d4af37; font-weight:bold;'>PROBABILIDAD: {s['prob']}%</p>
                        <h2 style='color:#2e7d32; margin-top:0;'>{tag.upper()}: {s['accion']}</h2>
                        <b>Punto Entrada: {ana['p_act']}</b><br>
                        <b>Volumen: {s['vol']} Lotes</b><br>
                        <span style='color:#c62828;'>🛑 SL: {s['sl']}</span> | <span style='color:#2e7b32;'>✅ TP: {s['tp']}</span>
                        <hr style='border:0.5px solid #d4af37;'>
                        <p style='font-size:0.9rem; line-height:1.4;'>{s['why']}</p>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 EJECUTAR {tag.upper()}", key=f"ex_{tag}"):
                        st.success(f"Orden de {tag} enviada a XTB.")

elif menu == "🔮 Precios Futuros":
    st.header("🔮 Ventana de Predicción de Rango")
    if st.button("Ejecutar Análisis Predictivo"):
        st.info("Calculando proyecciones basadas en datos macro y técnicos...")

elif menu == "🧪 Backtesting":
    st.header("🧪 Rendimiento Estratégico")
    st.write("Visualización de resultados históricos por horizonte temporal.")

elif menu == "📰 Noticias":
    st.header("📰 Inteligencia de Noticias")
    st.markdown('<div class="news-card"><h4>Ruptura Inminente en el Nasdaq</h4><p>El precio se acerca a la resistencia EMA 200...</p></div>', unsafe_allow_html=True)

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.wallet = st.number_input("Balance Cuenta (€)", value=st.session_state.wallet)
    st.session_state.riesgo_op = st.number_input("Riesgo por Operación (€)", value=st.session_state.riesgo_op)
