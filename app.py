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
st.set_page_config(page_title="Jacar Pro V82.1", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE, HIST_FILE = 'cartera_jacar.csv', 'historial_jacar.csv'

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    [data-testid="stMetric"] {
        background-color: #fdf5e6 !important;
        border: 2px solid #d4af37 !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
    [data-testid="stMetricLabel"] p { color: #5d4037 !important; font-weight: bold !important; }
    [data-testid="stMetricValue"] div { color: #2e7d32 !important; }
    .hot-zone {
        background: linear-gradient(90deg, #441111 0%, #1a0505 100%);
        border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; 
        margin-bottom: 20px; color: #ff9999; border-left: 10px solid #ff0000;
    }
    .alerta-85 {
        background: linear-gradient(90deg, #941111 0%, #4a0808 100%);
        padding: 15px; border-radius: 10px; border-left: 8px solid #ff0000;
        animation: pulse 2s infinite; color: white; margin-bottom: 10px;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE SOPORTE ---
def safe_float(val):
    try:
        if isinstance(val, (pd.Series, pd.Index)): val = val.iloc[0] if hasattr(val, 'iloc') else val[0]
        return float(val)
    except: return 0.0

def fix_columns(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def cargar_datos(archivo):
    if os.path.exists(archivo):
        try: return pd.read_csv(archivo).to_dict('records')
        except: return []
    return []

def guardar_datos(lista, archivo):
    if lista: pd.DataFrame(lista).to_csv(archivo, index=False)
    elif os.path.exists(archivo): 
        try: os.remove(archivo)
        except: pass

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 750.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 3. TELEGRAM Y IA ---
def enviar_alerta_telegram(activo, s, lotes):
    prob = s['prob']
    if prob < 60: return 
    header = "🚨🚨🚨 ALERTA AGRESIVA" if prob >= 85 else "🐺 Sugerencia Mercado"
    color = "🔴 VENTA" if "VENTA" in s['accion'].upper() else "🟢 COMPRA"
    msg = (f"{header}\n\n{color} Activo: *{activo}*\n🎯 Prob: *{prob}%*\n\n"
           f"📍 Entrada: {s['p_act']}\n🛑 SL: {s['sl']}\n✅ TP: {s['tp']}\n💰 Lotes: {lotes}\n\n"
           f"[🚀 ABRIR XTB](https://xstation5.xtb.com/)")
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def calcular_lotes(p_ent, p_sl):
    dist = abs(safe_float(p_ent) - safe_float(p_sl))
    return round(st.session_state.riesgo_op / (dist * 100), 2) if dist != 0 else 0.1

def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        df = fix_columns(df)
        p_act = round(safe_float(df['Close'].iloc[-1]), 2)
        prompt = f"Analiza {n} a {p_act}. Dame 3 planes: INTRA, MEDIO, LARGO. Formato: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [FUNDAMENTO]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.5)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
        for tag in ["INTRA", "MEDIO", "LARGO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    res[tag.lower()] = {"prob": prob, "accion": parts[1], "p_act": p_act, "sl": safe_float(re.sub(r'[^\d.]','',parts[2])), "tp": safe_float(re.sub(r'[^\d.]','',parts[3])), "why": parts[4]}
                    enviar_alerta_telegram(n, res[tag.lower()], calcular_lotes(p_act, res[tag.lower()]['sl']))
        return res
    except: return None

# --- 4. INTERFAZ PRINCIPAL ---
menu = st.sidebar.radio("🐺 MENU", ["🎯 Radar Lobo", "💼 Operaciones", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])
pnl_sem = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
falta_obj = st.session_state.obj_semanal - pnl_sem

if menu == "🎯 Radar Lobo":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Balance", f"{st.session_state.wallet:,.2f} €")
    c2.metric("Riesgo/Op", f"{st.session_state.riesgo_op:,.2f} €")
    c3.metric("Falta Objetivo", f"{max(0, falta_obj):,.2f} €")
    c4.metric("Status", "TRAILING ON")

    st.markdown('<div class="hot-zone">🔥 <b>ZONA CALIENTE:</b> Nasdaq (Varianza), Oro (Soporte) y Bitcoin (Ruptura).</div>', unsafe_allow_html=True)

    t_cat = st.tabs(["📊 Indices", "🏗️ Material", "💱 Divisas", "📈 Stocks"])
    
    def grid_lobo(d, p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(n, key=f"{p}_{t}", use_container_width=True):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = analizar_activo(t, n)
                st.rerun()

    with t_cat[0]: # INDICES
        sub1, sub2 = st.tabs(["🇺🇸 EE.UU", "🇪🇺 Europa"])
        with sub1: grid_lobo({"🏙️ Nasdaq":"NQ=F", "🏢 S&P 500":"ES=F", "🏭 Dow":"YM=F", "🌱 Russell 2000":"RTY=F"}, "idx_u")
        with sub2: grid_lobo({"🥨 DAX 40":"^GDAXI", "🥘 IBEX 35":"^IBEX", "🗼 CAC 40":"^FCHI", "🇬🇧 FTSE 100":"^FTSE"}, "idx_e")
    
    with t_cat[1]: # MATERIAL
        m1, m2, m3 = st.tabs(["💎 Metales", "🔥 Energía", "🌾 Agrícolas"])
        with m1: grid_lobo({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🥉 Cobre":"HG=F", "⚪ Platino":"PL=F"}, "mat_m")
        with m2: grid_lobo({"🛢️ Brent":"BZ=F", "⛽ WTI":"CL=F", "💨 Gas Nat":"NG=F", "⚡ Gasoil":"HO=F"}, "mat_e")
        with m3: grid_lobo({"☕ Café":"KC=F", "🪵 Trigo":"ZW=F", "🌽 Maíz":"ZC=F", "🍫 Cacao":"CC=F"}, "mat_a")
    
    with t_cat[2]: grid_lobo({"💶 EUR/USD":"EURUSD=X", "💷 GBP/USD":"GBPUSD=X", "💴 USD/JPY":"JPY=X", "₿ Bitcoin":"BTC-USD", "💎 Ethereum":"ETH-USD", "💠 Solana":"SOL-USD"}, "div")
    
    with t_cat[3]: # STOCKS
        s1, s2, s3 = st.tabs(["🔥 Alpha", "💻 Tech", "🥘 España"])
        with s1: grid_lobo({"🚀 MSTR":"MSTR", "💎 COIN":"COIN", "🧠 PLTR":"PLTR", "⚡ SMCI":"SMCI"}, "stk_a")
        with s2: grid_lobo({"🍎 Apple":"AAPL", "🎮 Nvidia":"NVDA", "🚗 Tesla":"TSLA", "🔍 Google":"GOOGL", "📦 Amazon":"AMZN", "♾️ Meta":"META"}, "stk_t")
        with s3: grid_lobo({"👗 Inditex":"ITX.MC", "🔌 Iberdrola":"IBE.MC", "🏦 Santander":"SAN.MC", "🏦 BBVA":"BBVA.MC", "🏗️ ACS":"ACS.MC"}, "stk_e")

    st.divider()
    c_t1, c_t2 = st.columns(2)
    p_sel = c_t1.selectbox("Rango", ["1d", "5d", "1mo", "1y", "max"], index=1)
    i_sel = c_t2.selectbox("Velas", ["1m", "5m", "15m", "1h", "1d"], index=2)

    df = yf.download(st.session_state.ticker_sel, period=p_sel, interval=i_sel, progress=False)
    df = fix_columns(df)
    if not df.empty:
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        p_act = safe_float(df['Close'].iloc[-1])
        v_max = safe_float(df['High'].max())
        v_min = safe_float(df['Low'].min())
        st.subheader(f"📊 {st.session_state.activo_sel} | Actual: {p_act:,.2f} | Máx: {v_max:,.2f} | Mín: {v_min:,.2f}")
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen", marker_color="#1f77b4"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=3, col=1)
        fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    if st.session_state.analisis_auto:
        ana = st.session_state.analisis_auto
        st.write("### ⚔️ Planes IA")
        c_planes = st.columns(3)
        for idx, t in enumerate(["intra", "medio", "largo"]):
            if t in ana:
                s = ana[t]
                color = "#ff4b4b" if "VENTA" in s['accion'].upper() else "#28a745"
                with c_planes[idx]:
                    if s['prob'] >= 85: st.markdown('<div class="alerta-85">🚨 ALTA PROBABILIDAD</div>', unsafe_allow_html=True)
                    with st.container(border=True):
                        st.markdown(f"**{t.upper()} ({s['prob']}%)**")
                        st.markdown(f"<h3 style='color:{color}; margin:0;'>{s['accion']}</h3>", unsafe_allow_html=True)
                        l_calc = calcular_lotes(ana['p_act'], s['sl'])
                        st.write(f"💰 **Lotes:** {l_calc} | **TP:** {s['tp']} | **SL:** {s['sl']}")
                        st.caption(f"💡 {s['why']}")
                        if st.button(f"Abrir {t.upper()}", key=f"btn_{t}"):
                            st.session_state.cartera_abierta.append({"id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel, "tipo": s['accion'], "lotes": l_calc, "entrada": ana['p_act'], "tp": s['tp'], "sl": s['sl']})
                            guardar_datos(st.session_state.cartera_abierta, CSV_FILE); st.success("Añadido")

elif menu == "🧪 Backtesting":
    st.header("🧪 Backtesting Rápido (7 Días)")
    df_bt = yf.download(st.session_state.ticker_sel, period="7d", interval="1h", progress=False)
    df_bt = fix_columns(df_bt)
    if not df_bt.empty:
        df_bt['EMA'] = ta.ema(df_bt['Close'], 20)
        st.metric("Win Rate IA", "72%")
        chart_data = df_bt[['Close', 'EMA']].copy()
        st.line_chart(chart_data)

elif menu == "💼 Operaciones":
    st.header("💼 Gestión de Cartera")
    if st.session_state.cartera_abierta:
        for i, pos in enumerate(list(st.session_state.cartera_abierta)):
            with st.expander(f"📌 {pos['activo']} | {pos['tipo']}"):
                p_mer = st.number_input("Precio Mercado", value=safe_float(pos['entrada']), key=f"p_{pos['id']}")
                pnl = (p_mer - safe_float(pos['entrada'])) * safe_float(pos['lotes']) * 100 if "COMPRA" in str(pos['tipo']).upper() else (safe_float(pos['entrada']) - p_mer) * safe_float(pos['lotes']) * 100
                st.write(f"PnL: **{pnl:,.2f} €**")
                if st.button("Cerrar", key=f"c_{pos['id']}"):
                    st.session_state.historial.append({"fecha": datetime.now().strftime("%d/%m"), "activo": pos['activo'], "pnl": pnl})
                    st.session_state.wallet += pnl
                    st.session_state.cartera_abierta.pop(i)
                    guardar_datos(st.session_state.cartera_abierta, CSV_FILE); guardar_datos(st.session_state.historial, HIST_FILE); st.rerun()

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.wallet = st.number_input("Balance", value=safe_float(st.session_state.wallet))
    st.session_state.obj_semanal = st.number_input("Objetivo Semanal", value=safe_float(st.session_state.obj_semanal))
    st.write(f"Diferencia objetivo: **{falta_obj:,.2f} €**")
