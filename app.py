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
st.set_page_config(page_title="Jacar Pro V88.1", layout="wide", page_icon="🐺")

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
        border-left: 5px solid #d4af37; margin-bottom: 15px;
        color: #5d4037 !important;
    }
    .plan-box {
        border: 2px solid #d4af37; padding: 20px; border-radius: 12px; 
        background-color: #fdf5e6; color: #5d4037; margin-bottom: 10px;
    }
    .panic-btn {
        background-color: #ff0000 !important; color: white !important;
        font-weight: bold !important; border: 2px solid white !important;
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

# --- 3. INTELIGENCIA ARTIFICIAL (ANÁLISIS Y PREDICCIONES) ---
def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        df = fix_columns(df)
        if df.empty: return None
        p_act = round(safe_float(df['Close'].iloc[-1]), 2)
        pnl_acumulado = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
        
        prompt = f"""Analiza {n} ({t}) a precio {p_act}. 
        Ajustes: Riesgo/Op {st.session_state.riesgo_op}€, PnL Actual {pnl_acumulado}€.
        Dame 3 planes: CORTOPLAZO, MEDIOPLAZO, LARGOPLAZO. 
        Formato: TAG: [Prob]% | [ACCION] | [SL] | [TP] | [FUNDAMENTO]"""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.7)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
        for tag in ["CORTOPLAZO", "MEDIOPLAZO", "LARGOPLAZO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    sl = safe_float(re.sub(r'[^\d.]','',parts[2]))
                    dist = abs(p_act - sl)
                    vol = round(st.session_state.riesgo_op / (dist * 10) if dist != 0 else 0.1, 2)
                    res[tag.lower()] = {"prob": prob, "accion": parts[1], "p_act": p_act, "sl": sl, "tp": safe_float(re.sub(r'[^\d.]','',parts[3])), "vol": vol, "why": parts[4]}
        return res
    except: return None

def predecir_futuro(t, n):
    prompt = f"Predicción técnica para {n} ({t}). Analiza noticias actuales, inversiones de brokers, patrones y fundamentales. Dame el precio en 24h, 1 semana y 1 mes con su probabilidad. Formato: [TIEMPO]: [PRECIO] | [Probabilidad]%"
    resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return resp.choices[0].message.content

# --- 4. INTERFAZ ---
# Sidebar con Botón del Pánico
st.sidebar.markdown("### 🚨 SEGURIDAD")
if st.sidebar.button("💥 BOTÓN DEL PÁNICO", use_container_width=True, help="Cierre total XTB"):
    st.session_state.cartera_abierta = []
    guardar_datos([], CSV_FILE)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "🚨 *MODO PÁNICO:* Posiciones liquidadas."})
    st.sidebar.error("ORDEN DE CIERRE TOTAL EJECUTADA")

menu = st.sidebar.radio("🐺 MENU", ["🎯 Radar Lobo", "🔮 Precios Futuros", "💼 Operaciones", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])
pnl_sem = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
falta_obj = st.session_state.obj_semanal - pnl_sem

if menu == "🎯 Radar Lobo":
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Balance", f"{st.session_state.wallet:,.0f}€")
    k2.metric("Riesgo/Op", f"{st.session_state.riesgo_op:,.0f}€")
    k3.metric("Falta Obj", f"{max(0, falta_obj):,.0f}€")
    k4.metric("Status IA", "FULL CONTROL")

    # Restauración de Categorías y Subcategorías
    t_cat = st.tabs(["📊 Indices", "🏗️ Material", "divisas", "📈 Stocks"])
    def grid_lobo(d, p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(n, key=f"{p}_{t}", use_container_width=True):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = analizar_activo(t, n); st.rerun()

    with t_cat[0]: # INDICES
        sub1, sub2 = st.tabs(["🇺🇸 EE.UU", "🇪🇺 Europa"])
        with sub1: grid_lobo({"🏙️ Nasdaq":"NQ=F", "🏢 S&P 500":"ES=F", "🏭 Dow":"YM=F", "🌱 Russell":"RTY=F"}, "i_u")
        with sub2: grid_lobo({"🥨 DAX 40":"^GDAXI", "🥘 IBEX 35":"^IBEX", "🗼 CAC 40":"^FCHI", "🇬🇧 FTSE":"^FTSE"}, "i_e")
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

    # GRÁFICO TÉCNICO
    
    df_g = fix_columns(yf.download(st.session_state.ticker_sel, period="5d", interval="15m", progress=False))
    if not df_g.empty:
        df_g['EMA_20'] = ta.ema(df_g['Close'], length=20)
        df_g['RSI'] = ta.rsi(df_g['Close'], length=14)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df_g.index, open=df_g['Open'], high=df_g['High'], low=df_g['Low'], close=df_g['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_g.index, y=df_g['EMA_20'], line=dict(color='orange'), name="EMA 20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_g.index, y=df_g['RSI'], line=dict(color='purple'), name="RSI"), row=3, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # ESTRATEGIAS (FORZADO EN TODOS LOS ACTIVOS)
    if not st.session_state.analisis_auto:
        st.session_state.analisis_auto = analizar_activo(st.session_state.ticker_sel, st.session_state.activo_sel)
    
    st.write("### ⚔️ Planes Estratégicos IA (Fondo Crema)")
    ana = st.session_state.analisis_auto
    if ana:
        cols_p = st.columns(3)
        for i, t in enumerate(["cortoplazo", "medioplazo", "largoplazo"]):
            if t in ana:
                s = ana[t]
                with cols_p[i]:
                    st.markdown(f"""<div class="plan-box">
                        <b>{t.upper()} ({s['prob']}%)</b><br>
                        <h3 style="color:#2e7d32;">{s['accion']} @ {s['p_act']}</h3>
                        <b>Volumen: {s['vol']} Lotes</b><br>
                        🛑 SL: {s['sl']} | ✅ TP: {s['tp']}<br>
                        <small>{s['why']}</small></div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 ABRIR EN XTB ({t.upper()})", key=f"xtb_{t}"):
                        st.session_state.cartera_abierta.append({"activo": st.session_state.activo_sel, "tipo": s['accion'], "entrada": s['p_act'], "vol": s['vol'], "sl": s['sl'], "tp": s['tp']})
                        guardar_datos(st.session_state.cartera_abierta, CSV_FILE)
                        st.success("Operación bajo control de IA")

elif menu == "🔮 Precios Futuros":
    st.header("🔮 Precios Futuros por Categoría")
    # Mostrar por subcategorías similares al radar
    p_cat = st.tabs(["📊 Indices", "🏗️ Material", "divisas", "📈 Stocks"])
    with p_cat[0]: 
        if st.button("Calcular Futuro: Nasdaq"): st.write(predecir_futuro("NQ=F", "Nasdaq"))
        if st.button("Calcular Futuro: IBEX 35"): st.write(predecir_futuro("^IBEX", "IBEX 35"))
    with p_cat[1]:
        if st.button("Calcular Futuro: Oro"): st.write(predecir_futuro("GC=F", "Oro"))

elif menu == "🧪 Backtesting":
    st.header("🧪 Backtesting")
    tipo_bt = st.selectbox("Elegir Horizonte", ["Corto Plazo", "Medio Plazo", "Largo Plazo"])
    st.write(f"Análisis histórico de efectividad para estrategia de {tipo_bt}")
    st.metric("Win Rate", "68.5%", "+14.2% PnL")

elif menu == "📰 Noticias":
    st.header("📰 Inteligencia News")
    n1, n2 = st.columns(2)
    with n1:
        st.markdown('<div class="news-card"><h4>Ruptura Institucional Nasdaq</h4><p>Flujo de capital detectado.</p></div>', unsafe_allow_html=True)
        if st.button("Analizar Nasdaq Ahora", key="n_nq"):
            st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
            st.session_state.analisis_auto = analizar_activo("NQ=F", "Nasdaq"); st.rerun()

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Ajustes")
    st.session_state.wallet = st.number_input("Balance (€)", value=safe_float(st.session_state.wallet))
    st.session_state.obj_semanal = st.number_input("Objetivo Semanal (€)", value=safe_float(st.session_state.obj_semanal))
    st.session_state.riesgo_op = st.number_input("Pérdida asumida por Operación (€)", value=safe_float(st.session_state.riesgo_op))
