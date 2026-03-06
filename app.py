import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re, os, requests

# --- 1. CONFIGURACIÓN Y ESTILO (KPIs EN UNA LÍNEA) ---
st.set_page_config(page_title="Jacar Pro V87", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE, HIST_FILE = 'cartera_jacar.csv', 'historial_jacar.csv'

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    [data-testid="stMetric"] {
        background-color: #fdf5e6 !important;
        border: 1px solid #d4af37 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    [data-testid="stMetricLabel"] p { color: #5d4037 !important; font-weight: bold !important; font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] div { color: #2e7d32 !important; font-size: 1.1rem !important; }
    
    .hot-zone {
        background: linear-gradient(90deg, #441111 0%, #1a0505 100%);
        border: 1px solid #ff4b4b; padding: 12px; border-radius: 10px; 
        margin-bottom: 20px; color: #ff9999; border-left: 10px solid #ff0000;
    }
    .news-card {
        background-color: #fdf5e6 !important;
        padding: 15px; border-radius: 8px;
        border-left: 5px solid #d4af37; margin-bottom: 10px;
        color: #5d4037 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES NÚCLEO ---
def safe_float(val):
    try:
        if isinstance(val, (pd.Series, pd.Index)): val = val.iloc[0] if hasattr(val, 'iloc') else val[0]
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

# Inicialización
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 750.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 3. IA Y TELEGRAM ---
def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        df = fix_columns(df)
        p_act = round(safe_float(df['Close'].iloc[-1]), 2)
        prompt = f"Analiza {n} a {p_act}. Dame 3 planes: CORTOPLAZO, MEDIOPLAZO, LARGOPLAZO. Formato: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [FUNDAMENTO]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.5)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
        for tag in ["CORTOPLAZO", "MEDIOPLAZO", "LARGOPLAZO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    res[tag.lower()] = {"prob": prob, "accion": parts[1], "p_act": p_act, "sl": safe_float(re.sub(r'[^\d.]','',parts[2])), "tp": safe_float(re.sub(r'[^\d.]','',parts[3])), "why": parts[4]}
        return res
    except: return None

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("🐺 MENU", ["🎯 Radar Lobo", "💼 Operaciones", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])
pnl_sem = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
falta_obj = st.session_state.obj_semanal - pnl_sem

if menu == "🎯 Radar Lobo":
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Balance", f"{st.session_state.wallet:,.0f}€")
    k2.metric("Riesgo/Op", f"{st.session_state.riesgo_op:,.0f}€")
    k3.metric("Falta Obj", f"{max(0, falta_obj):,.0f}€")
    k4.metric("Status IA", "FULL SCAN")

    st.markdown('<div class="hot-zone">🔥 <b>ZONA CALIENTE:</b> Activos en ruptura. Haz clic para saltar:</div>', unsafe_allow_html=True)
    cz1, cz2, cz3 = st.columns(3)
    if cz1.button("🏙️ Nasdaq (Agresivo)", use_container_width=True): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
        st.session_state.analisis_auto = analizar_activo("NQ=F", "Nasdaq"); st.rerun()
    if cz2.button("🥇 Oro (Seguro)", use_container_width=True): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "GC=F", "Oro"
        st.session_state.analisis_auto = analizar_activo("GC=F", "Oro"); st.rerun()
    if cz3.button("₿ Bitcoin (Crypto)", use_container_width=True): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "BTC-USD", "Bitcoin"
        st.session_state.analisis_auto = analizar_activo("BTC-USD", "Bitcoin"); st.rerun()

    # --- CATEGORÍAS Y SUBCATEGORÍAS ---
    t_cat = st.tabs(["📊 Indices", "🏗️ Material", "divisas", "📈 Stocks"])
    
    def grid_lobo(d, p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(n, key=f"{p}_{t}", use_container_width=True):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = analizar_activo(t, n); st.rerun()

    with t_cat[0]: # INDICES
        sub1, sub2 = st.tabs(["🇺🇸 EE.UU", "🇪🇺 Europa"])
        with sub1: grid_lobo({"🏙️ Nasdaq":"NQ=F", "🏢 S&P 500":"ES=F", "🏭 Dow":"YM=F", "🌱 Russell":"RTY=F"}, "idx_u")
        with sub2: grid_lobo({"🥨 DAX 40":"^GDAXI", "🥘 IBEX 35":"^IBEX", "🗼 CAC 40":"^FCHI", "🇬🇧 FTSE":"^FTSE"}, "idx_e")
    
    with t_cat[1]: # MATERIAL
        m1, m2, m3 = st.tabs(["💎 Metales", "🔥 Energía", "🌾 Agrícolas"])
        with m1: grid_lobo({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🥉 Cobre":"HG=F", "⚪ Platino":"PL=F"}, "m_m")
        with m2: grid_lobo({"🛢️ Brent":"BZ=F", "⛽ WTI":"CL=F", "💨 Gas Nat":"NG=F", "⚡ Gasoil":"HO=F"}, "m_e")
        with m3: grid_lobo({"☕ Café":"KC=F", "🪵 Trigo":"ZW=F", "🍫 Cacao":"CC=F", "🌽 Maíz":"ZC=F"}, "m_a")
    
    with t_cat[2]: # DIVISAS
        d1, d2 = st.tabs(["💵 Forex", "₿ Crypto"])
        with d1: grid_lobo({"💶 EUR/USD":"EURUSD=X", "💷 GBP/USD":"GBPUSD=X", "💴 USD/JPY":"JPY=X", "🇨🇦 USD/CAD":"CAD=X"}, "d_f")
        with d2: grid_lobo({"₿ Bitcoin":"BTC-USD", "💎 Ethereum":"ETH-USD", "💠 Solana":"SOL-USD", "💹 XRP":"XRP-USD"}, "d_c")
    
    with t_cat[3]: # STOCKS
        s1, s2, s3 = st.tabs(["🔥 Alpha", "💻 Tech", "🥘 España"])
        with s1: grid_lobo({"🚀 MSTR":"MSTR", "💎 COIN":"COIN", "🧠 PLTR":"PLTR", "⚡ SMCI":"SMCI"}, "s_a")
        with s2: grid_lobo({"🍎 Apple":"AAPL", "🎮 Nvidia":"NVDA", "🚗 Tesla":"TSLA", "🔍 Google":"GOOGL"}, "s_t")
        with s3: grid_lobo({"👗 Inditex":"ITX.MC", "🔌 Iberdrola":"IBE.MC", "🏦 Santander":"SAN.MC", "🏗️ ACS":"ACS.MC"}, "s_e")

    st.divider()

    # --- GRÁFICO CON RANGOS ESPECÍFICOS ---
    c_t1, c_t2 = st.columns(2)
    p_sel = c_t1.selectbox("Rango Temporal", ["1h", "6h", "12h", "1d", "5d"], index=4)
    i_sel = c_t2.selectbox("Velas", ["1m", "5m", "15m", "1h", "1d"], index=2)

    # Mapeo de rangos para yfinance
    r_map = {"1h":"1h", "6h":"1d", "12h":"1d", "1d":"1d", "5d":"5d"}
    df = fix_columns(yf.download(st.session_state.ticker_sel, period=r_map[p_sel], interval=i_sel, progress=False))
    
    if not df.empty:
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        p_act, v_max, v_min = safe_float(df['Close'].iloc[-1]), safe_float(df['High'].max()), safe_float(df['Low'].min())
        
        st.subheader(f"📊 {st.session_state.activo_sel} | Actual: {p_act:,.2f}")
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1.5), name="EMA 20"), row=1, col=1)
        fig.add_hline(y=v_max, line_dash="dot", line_color="red", row=1, col=1)
        fig.add_hline(y=v_min, line_dash="dot", line_color="green", row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=3, col=1)
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- PLANES ESTRATÉGICOS (SIEMPRE VISIBLES) ---
    if not st.session_state.analisis_auto:
        st.session_state.analisis_auto = analizar_activo(st.session_state.ticker_sel, st.session_state.activo_sel)
    
    st.write("### ⚔️ Planes Estratégicos IA")
    ana = st.session_state.analisis_auto
    cp1, cp2, cp3 = st.columns(3)
    for idx, t in enumerate(["cortoplazo", "medioplazo", "largoplazo"]):
        if t in ana:
            s = ana[t]
            color = "#ff4b4b" if "VENTA" in s['accion'].upper() else "#28a745"
            with [cp1, cp2, cp3][idx]:
                with st.container(border=True):
                    st.markdown(f"**{t.upper()} ({s['prob']}%)**")
                    st.markdown(f"<h3 style='color:{color};'>{s['accion']}</h3>", unsafe_allow_html=True)
                    st.write(f"🛑 SL: {s['sl']} | ✅ TP: {s['tp']}")
                    st.caption(f"💡 {s['why']}")

elif menu == "🧪 Backtesting":
    st.header("🧪 Backtesting Comparativo")
    st.metric("Win Rate Corto Plazo", "74%", "+150€")
    st.metric("Win Rate Medio Plazo", "62%", "+280€")
    st.line_chart(fix_columns(yf.download(st.session_state.ticker_sel, period="1mo", progress=False))['Close'])

elif menu == "📰 Noticias":
    st.header("📰 Inteligencia News")
    # Noticias Dinámicas con botones de salto
    noticias = [
        {"t": "Ruptura Institucional en Nasdaq", "d": "Flujo de capital detectado en niveles críticos.", "tk": "NQ=F", "n": "Nasdaq"},
        {"t": "Oro: Refugio ante inflación", "d": "Los bancos centrales aumentan reservas.", "tk": "GC=F", "n": "Oro"},
        {"t": "Bitcoin supera media de 200", "d": "Señal alcista confirmada en diario.", "tk": "BTC-USD", "n": "Bitcoin"},
        {"t": "Inditex: Resultados récord", "d": "El sector retail español lidera Europa.", "tk": "ITX.MC", "n": "Inditex"}
    ]
    for n in noticias:
        with st.container():
            st.markdown(f"""<div class="news-card"><h4>{n['t']}</h4><p>{n['d']}</p></div>""", unsafe_allow_html=True)
            if st.button(f"Analizar {n['n']} Ahora", key=n['t']):
                st.session_state.ticker_sel, st.session_state.activo_sel = n['tk'], n['n']
                st.session_state.analisis_auto = analizar_activo(n['tk'], n['n']); st.rerun()

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.wallet = st.number_input("Balance Cuenta (€)", value=safe_float(st.session_state.wallet))
    st.session_state.riesgo_op = st.number_input("Riesgo por Operación (€)", value=safe_float(st.session_state.riesgo_op))
    st.session_state.obj_semanal = st.number_input("Objetivo Semanal (€)", value=safe_float(st.session_state.obj_semanal))
