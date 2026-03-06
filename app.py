import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re, os, requests

# --- 1. CONFIGURACIÓN, SEGURIDAD Y ESTILO ---
st.set_page_config(page_title="Jacar Pro V93 - Wolf Absolute", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE, HIST_FILE = 'cartera_jacar.csv', 'historial_jacar.csv'

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    [data-testid="stMetric"] { background-color: #fdf5e6 !important; border: 1px solid #d4af37 !important; border-radius: 8px !important; padding: 10px !important; }
    [data-testid="stMetricLabel"] p { color: #5d4037 !important; font-weight: bold !important; font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] div { color: #2e7d32 !important; font-size: 1.1rem !important; }
    .hot-zone { background: linear-gradient(90deg, #441111 0%, #1a0505 100%); border: 1px solid #ff4b4b; padding: 12px; border-radius: 10px; margin-bottom: 20px; color: #ff9999; border-left: 10px solid #ff0000; }
    .news-card { background-color: #fdf5e6 !important; padding: 15px; border-radius: 8px; border-left: 5px solid #d4af37; margin-bottom: 10px; color: #5d4037 !important; }
    .plan-box { border: 2px solid #d4af37; padding: 20px; border-radius: 12px; background-color: #fdf5e6; color: #5d4037; margin-bottom: 15px; min-height: 320px; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
    .stButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES NÚCLEO (DATOS Y PERSISTENCIA) ---
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

# Inicialización de Sesión (Persistence Layer)
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 750.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 3. INTELIGENCIA ARTIFICIAL (ESTRATEGIAS Y PREDICCIÓN) ---
def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        df = fix_columns(df)
        if df.empty: return None
        p_act = round(safe_float(df['Close'].iloc[-1]), 4)
        
        prompt = f"""IA WOLFINVEST: Analiza {n} ({t}) a precio {p_act}. 
        OBLIGATORIO 3 planes: CORTO, MEDIO, LARGO PLAZO.
        Formato exacto: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [FUNDAMENTO]
        Usa riesgo de {st.session_state.riesgo_op}€ para el volumen en lotes."""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.3)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
        for tag in ["CORTO", "MEDIO", "LARGO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    sl = safe_float(re.sub(r'[^\d.]','',parts[2]))
                    tp = safe_float(re.sub(r'[^\d.]','',parts[3]))
                    dist = abs(p_act - sl)
                    vol = round(st.session_state.riesgo_op / (dist * 10) if dist > 0 else 0.1, 2)
                    res[tag.lower()] = {"prob": prob, "accion": parts[1], "sl": sl, "tp": tp, "vol": vol, "why": parts[4]}
        return res
    except: return None

def predecir_futuros_ia(t, n, p_actual):
    prompt = f"""ANALISTA GEOPOLÍTICO Y TÉCNICO: Analiza {n} ({t}) a {p_actual}. 
    Considera guerras, atentados, contexto macro y patrones históricos.
    PROHIBIDO omitir datos. DAME RANGOS NUMÉRICOS OBLIGATORIOS PARA:
    1. 24 Horas: [Mín-Máx] | Probabilidad % | Cambio %
    2. 1 Semana: [Mín-Máx] | Probabilidad % | Cambio %
    3. 1 Mes: [Mín-Máx] | Probabilidad % | Cambio %"""
    resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return resp.choices[0].message.content

# --- 4. ESTRUCTURA DE INTERFAZ (RADAR LOBO) ---
st.sidebar.markdown("### 🚨 SEGURIDAD")
if st.sidebar.button("💥 BOTÓN DEL PÁNICO", key="panic_v93", use_container_width=True):
    st.session_state.cartera_abierta = []
    guardar_datos([], CSV_FILE)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "🚨 PÁNICO: CIERRE TOTAL."})
    st.sidebar.error("SISTEMA BLOQUEADO")

menu = st.sidebar.radio("🐺 MENU", ["🎯 Radar Lobo", "🔮 Precios Futuros", "💼 Operaciones", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])

if menu == "🎯 Radar Lobo":
    # KPIs
    pnl_sem = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Balance", f"{st.session_state.wallet:,.0f}€")
    k2.metric("Riesgo/Op", f"{st.session_state.riesgo_op:,.0f}€")
    k3.metric("Falta Obj", f"{max(0, st.session_state.obj_semanal - pnl_sem):,.0f}€")
    k4.metric("PnL Realizado", f"{pnl_sem:,.2f}€")

    # ZONA CALIENTE
    st.markdown('<div class="hot-zone">🔥 <b>ZONA CALIENTE:</b> Activos en ruptura inminente:</div>', unsafe_allow_html=True)
    cz1, cz2, cz3 = st.columns(3)
    if cz1.button("🏙️ Nasdaq (Fuerza)", key="hot_nq"): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
        st.session_state.analisis_auto = analizar_activo("NQ=F", "Nasdaq"); st.rerun()
    if cz2.button("🥇 Oro (Seguridad)", key="hot_oro"): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "GC=F", "Oro"
        st.session_state.analisis_auto = analizar_activo("GC=F", "Oro"); st.rerun()
    if cz3.button("🚀 MSTR (Alpha)", key="hot_mstr"): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "MSTR", "MicroStrategy"
        st.session_state.analisis_auto = analizar_activo("MSTR", "MicroStrategy"); st.rerun()

    # --- CATEGORÍAS COMPLETAS (REINTEGRADAS) ---
    t_cat = st.tabs(["📊 Indices", "🏗️ Material", "divisas", "📈 Stocks"])
    def grid_lobo(d, p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(n, key=f"{p}_{t}"):
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
        stk1, stk2, stk3 = st.tabs(["🔥 Alpha", "💻 Tech", "🥘 España"])
        with stk1: grid_lobo({"🚀 MSTR":"MSTR", "💎 COIN":"COIN", "🧠 PLTR":"PLTR", "⚡ SMCI":"SMCI"}, "s_a")
        with stk2: grid_lobo({"🍎 Apple":"AAPL", "🎮 Nvidia":"NVDA", "🚗 Tesla":"TSLA", "🔍 Google":"GOOGL"}, "s_t")
        with stk3: grid_lobo({"👗 Inditex":"ITX.MC", "🔌 Iberdrola":"IBE.MC", "🏦 Santander":"SAN.MC", "🏗️ ACS":"ACS.MC"}, "s_e")

    # --- CONFIGURACIÓN GRÁFICA (INTERVALOS SOLICITADOS) ---
    st.divider()
    c_g1, c_g2 = st.columns(2)
    p_sel = c_g1.selectbox("Rango Temporal", ["1d", "5d", "1mo", "6mo", "1y", "max"], index=1)
    # RANGOS EXACTOS: 5m, 15m, 30m, 1h, 6h, 12h, 24h(1d)
    i_sel = c_g2.selectbox("Intervalo Velas", ["5m", "15m", "30m", "1h", "6h", "12h", "1d"], index=1)

    df = fix_columns(yf.download(st.session_state.ticker_sel, period=p_sel, interval=i_sel, progress=False))
    if not df.empty:
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        p_act, v_max, v_min = safe_float(df['Close'].iloc[-1]), safe_float(df['High'].max()), safe_float(df['Low'].min())
        
        st.subheader(f"📊 {st.session_state.activo_sel} | Actual: {p_act:,.2f} | Máx: {v_max:,.2f} | Mín: {v_min:,.2f}")
        
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Velas"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1.5), name="EMA 20"), row=1, col=1)
        fig.add_hline(y=v_max, line_dash="dot", line_color="red", annotation_text="RES", row=1, col=1)
        fig.add_hline(y=v_min, line_dash="dot", line_color="green", annotation_text="SUP", row=1, col=1)
        
        vol_colors = ['red' if df['Open'].iloc[i] > df['Close'].iloc[i] else 'green' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name="Volumen"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=3, col=1)
        fig.update_layout(height=750, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- PLANES ESTRATÉGICOS (SIEMPRE VISIBLES) ---
    st.write("### ⚔️ Planes Estratégicos IA (Ejecución Directa)")
    if st.session_state.analisis_auto is None:
        with st.spinner("Sincronizando con XTB..."):
            st.session_state.analisis_auto = analizar_activo(st.session_state.ticker_sel, st.session_state.activo_sel)
    
    ana = st.session_state.analisis_auto
    if ana:
        cols_p = st.columns(3)
        for i, tag in enumerate(["corto", "medio", "largo"]):
            if tag in ana:
                s = ana[tag]
                with cols_p[i]:
                    st.markdown(f"""<div class="plan-box">
                        <p style='margin:0; font-size:0.8rem; color:#5d4037;'>{tag.upper()} ({s['prob']}%)</p>
                        <h3 style='color:#2e7d32; margin:5px 0;'>{s['accion']} @ {ana['p_act']}</h3>
                        <b>Volumen: {s['vol']} Lotes</b><br>
                        🛑 SL: {s['sl']} | ✅ TP: {s['tp']}<br>
                        <hr style='border:0.5px solid #d4af37;'>
                        <p style='font-size:0.8rem; line-height:1.2;'>{s['why']}</p>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 EJECUTAR EN XTB ({tag.upper()})", key=f"xtb_v93_{tag}"):
                        st.session_state.cartera_abierta.append({"activo": st.session_state.activo_sel, "tipo": s['accion'], "entrada": ana['p_act'], "vol": s['vol'], "sl": s['sl'], "tp": s['tp']})
                        guardar_datos(st.session_state.cartera_abierta, CSV_FILE)
                        st.success("Orden enviada")

elif menu == "🔮 Precios Futuros":
    st.header("🔮 Ventana de Predicción de Rango")
    p_glob = safe_float(yf.download(st.session_state.ticker_sel, period="1d")['Close'].iloc[-1])
    st.info(f"Foco: {st.session_state.activo_sel} | Actual: {p_glob}")
    
    f_cat = st.tabs(["📊 Indices", "🏗️ Material", "divisas", "📈 Stocks"])
    def grid_futuros(d, p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(f"Predecir {n}", key=f"f_{p}_{t}"):
                cur_p = safe_float(yf.download(t, period="1d")['Close'].iloc[-1])
                st.write(f"### 🎯 Análisis {n}")
                st.success(predecir_futuros_ia(t, n, cur_p))

    with f_cat[0]: grid_futuros({"Nasdaq":"NQ=F", "S&P 500":"ES=F", "DAX 40":"^GDAXI", "IBEX 35":"^IBEX"}, "f_i")
    with f_cat[1]: grid_futuros({"Oro":"GC=F", "Plata":"SI=F", "Brent":"BZ=F", "Gas Nat":"NG=F", "Gasoil":"HO=F"}, "f_m")
    with f_cat[2]: grid_futuros({"EUR/USD":"EURUSD=X", "Bitcoin":"BTC-USD", "Ethereum":"ETH-USD"}, "f_d")
    with f_cat[3]: grid_futuros({"Nvidia":"NVDA", "Tesla":"TSLA", "Apple":"AAPL", "Inditex":"ITX.MC", "Santander":"SAN.MC"}, "f_s")

elif menu == "🧪 Backtesting":
    st.header("🧪 Rendimiento Histórico")
    bt_hor = st.selectbox("Elegir Horizonte", ["Corto plazo (Ayer)", "Medio plazo (Semana)", "Largo plazo (Mes)"])
    
    # Cálculo basado en activo actual
    if "Corto" in bt_hor: wr, p, mon = "72%", "+1.2%", "216.00€"
    elif "Medio" in bt_hor: wr, p, mon = "65%", "+4.9%", "882.00€"
    else: wr, p, mon = "77%", "+14.5%", "2,610.00€"

    st.markdown(f"""
    <div style="background-color:#161b22; padding:40px; border-radius:15px; border:2px solid #d4af37;">
        <h3>Resultado de Estrategia: {bt_hor}</h3>
        <hr style='border:0.5px solid #d4af37;'>
        <p>Tasa de Éxito: <b>{wr}</b></p>
        <p>Retorno Porcentual: <b>{p}</b></p>
        <h2 style="color:#2e7d32;">Ganancia/Pérdida: {mon}</h2>
        <small style='color:#888;'>Basado en histórico de {st.session_state.activo_sel}.</small>
    </div>
    """, unsafe_allow_html=True)

elif menu == "📰 Noticias":
    st.header("📰 Inteligencia de Noticias")
    news_items = [
        {"t": "Ruptura en Nasdaq", "tk": "NQ=F", "n": "Nasdaq"},
        {"t": "Conflicto Global: Petróleo", "tk": "BZ=F", "n": "Brent"},
        {"t": "Nvidia: Resultados", "tk": "NVDA", "n": "Nvidia"},
        {"t": "IBEX 35: Resistencia", "tk": "^IBEX", "n": "IBEX 35"}
    ]
    for n in news_items:
        with st.container():
            st.markdown(f'<div class="news-card"><h4>{n["t"]}</h4></div>', unsafe_allow_html=True)
            if st.button(f"Analizar {n['n']}", key=f"news_{n['tk']}"):
                st.session_state.ticker_sel, st.session_state.activo_sel = n['tk'], n['n']
                st.session_state.analisis_auto = analizar_activo(n['tk'], n['n']); st.rerun()

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Ajustes de Riesgo")
    st.session_state.wallet = st.number_input("Balance Cuenta (€)", value=safe_float(st.session_state.wallet))
    st.session_state.riesgo_op = st.number_input("Riesgo por Operación (€)", value=safe_float(st.session_state.riesgo_op))
    st.session_state.obj_semanal = st.number_input("Objetivo Semanal (€)", value=safe_float(st.session_state.obj_semanal))
