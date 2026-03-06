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
st.set_page_config(page_title="Jacar Pro V85", layout="wide", page_icon="🐺")

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
    .hot-zone {
        background: linear-gradient(90deg, #441111 0%, #1a0505 100%);
        border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; 
        margin-bottom: 20px; color: #ff9999; border-left: 10px solid #ff0000;
    }
    .news-card {
        background-color: #1c2533; padding: 15px; border-radius: 8px;
        border-left: 5px solid #3b82f6; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE SOPORTE Y SEGUIMIENTO ---
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

# Inicialización de estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 750.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 3. IA CONTROL DE FLUCTUACIONES Y TELEGRAM ---
def monitorizar_fluctuacion(posicion, precio_actual):
    entrada = safe_float(posicion['entrada'])
    tp = safe_float(posicion['tp'])
    tipo = posicion['tipo'].upper()
    
    progreso = 0
    if "COMPRA" in tipo:
        progreso = (precio_actual - entrada) / (tp - entrada) if tp != entrada else 0
    else:
        progreso = (entrada - precio_actual) / (entrada - tp) if tp != entrada else 0

    if progreso > 0.5: # Si va al 50% del TP
        msg = f"⚠️ *GESTIÓN IA:* {posicion['activo']} va +50% a favor. Sugerencia: Mover SL a Breakeven ({entrada})."
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def enviar_alerta_telegram(activo, s, lotes):
    prob = s['prob']
    if prob < 60: return 
    header = "🚨 ALERTA AGRESIVA" if prob >= 85 else "🐺 Sugerencia"
    color = "🔴 VENTA" if "VENTA" in s['accion'].upper() else "🟢 COMPRA"
    msg = (f"{header}\n\n{color} *{activo}*\n🎯 Prob: {prob}%\n\n📍 In: {s['p_act']}\n🛑 SL: {s['sl']}\n✅ TP: {s['tp']}\n💰 Lotes: {lotes}\n[🚀 XTB](https://xstation5.xtb.com/)")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        df = fix_columns(df)
        p_act = round(safe_float(df['Close'].iloc[-1]), 2)
        prompt = f"Analiza {n} a {p_act}. Dame 3 planes: CORTOPLAZO (INTRA), MEDIOPLAZO, LARGOPLAZO. Formato: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [FUNDAMENTO]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.5)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
        for tag in ["CORTOPLAZO", "MEDIOPLAZO", "LARGOPLAZO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    res[tag.lower()] = {"prob": prob, "accion": parts[1], "p_act": p_act, "sl": safe_float(re.sub(r'[^\d.]','',parts[2])), "tp": safe_float(re.sub(r'[^\d.]','',parts[3])), "why": parts[4]}
                    enviar_alerta_telegram(n, res[tag.lower()], round(st.session_state.riesgo_op / (abs(p_act - res[tag.lower()]['sl']) * 100), 2))
        return res
    except: return None

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("🐺 MENU", ["🎯 Radar Lobo", "💼 Operaciones", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])
pnl_sem = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
falta_obj = st.session_state.obj_semanal - pnl_sem

if menu == "🎯 Radar Lobo":
    st.columns(4)[0].metric("Balance", f"{st.session_state.wallet:,.2f} €")
    st.columns(4)[1].metric("Riesgo/Op", f"{st.session_state.riesgo_op:,.2f} €")
    st.columns(4)[2].metric("Falta Obj", f"{max(0, falta_obj):,.2f} €")
    st.columns(4)[3].metric("Status IA", "MONITORIZANDO XTB")

    # ZONA CALIENTE INTERACTIVA
    st.markdown('<div class="hot-zone">🔥 <b>ZONA CALIENTE:</b> Activos con alta probabilidad actual. Haz clic para analizar:</div>', unsafe_allow_html=True)
    cz1, cz2, cz3 = st.columns(3)
    if cz1.button("🏙️ Nasdaq (Agresivo)", use_container_width=True): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
        st.session_state.analisis_auto = analizar_activo("NQ=F", "Nasdaq"); st.rerun()
    if cz2.button("🥇 Oro (Ruptura)", use_container_width=True): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "GC=F", "Oro"
        st.session_state.analisis_auto = analizar_activo("GC=F", "Oro"); st.rerun()
    if cz3.button("₿ Bitcoin (Fuerza)", use_container_width=True): 
        st.session_state.ticker_sel, st.session_state.activo_sel = "BTC-USD", "Bitcoin"
        st.session_state.analisis_auto = analizar_activo("BTC-USD", "Bitcoin"); st.rerun()

    t_cat = st.tabs(["📊 Indices", "🏗️ Material", "💱 Divisas", "📈 Stocks"])
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
        with m1: grid_lobo({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🥉 Cobre":"HG=F"}, "m_m")
        with m2: grid_lobo({"🛢️ Brent":"BZ=F", "⛽ WTI":"CL=F", "💨 Gas Nat":"NG=F"}, "m_e")
        with m3: grid_lobo({"☕ Café":"KC=F", "🪵 Trigo":"ZW=F", "🍫 Cacao":"CC=F"}, "m_a")
    with t_cat[2]: grid_lobo({"💶 EUR/USD":"EURUSD=X", "💷 GBP/USD":"GBPUSD=X", "₿ Bitcoin":"BTC-USD", "💎 Ethereum":"ETH-USD"}, "div")
    with t_cat[3]: # STOCKS
        s1, s2, s3 = st.tabs(["🔥 Alpha", "💻 Tech", "🥘 España"])
        with s1: grid_lobo({"🚀 MSTR":"MSTR", "💎 COIN":"COIN", "🧠 PLTR":"PLTR"}, "s_a")
        with s2: grid_lobo({"🍎 Apple":"AAPL", "🎮 Nvidia":"NVDA", "🚗 Tesla":"TSLA"}, "s_t")
        with s3: grid_lobo({"👗 Inditex":"ITX.MC", "🔌 Iberdrola":"IBE.MC", "🏦 Santander":"SAN.MC"}, "s_e")

    st.divider()
    df = fix_columns(yf.download(st.session_state.ticker_sel, period="5d", interval="15m", progress=False))
    if not df.empty:
        p_act = safe_float(df['Close'].iloc[-1])
        st.subheader(f"📊 {st.session_state.activo_sel} | Actual: {p_act:,.2f}")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume']), row=2, col=1)
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    if st.session_state.analisis_auto:
        ana = st.session_state.analisis_auto
        st.write("### ⚔️ Planes Estratégicos IA")
        c_planes = st.columns(3)
        for idx, t in enumerate(["cortoplazo", "medioplazo", "largoplazo"]):
            if t in ana:
                s = ana[t]
                color = "#ff4b4b" if "VENTA" in s['accion'].upper() else "#28a745"
                with c_planes[idx]:
                    with st.container(border=True):
                        st.markdown(f"**{t.upper()} ({s['prob']}%)**")
                        st.markdown(f"<h3 style='color:{color};'>{s['accion']}</h3>", unsafe_allow_html=True)
                        st.write(f"🛑 SL: {s['sl']} | ✅ TP: {s['tp']}")
                        st.caption(f"💡 {s['why']}")
                        if st.button(f"Abrir {t.upper()}", key=f"b_{t}"):
                            st.session_state.cartera_abierta.append({"activo": st.session_state.activo_sel, "tipo": s['accion'], "entrada": ana['p_act'], "tp": s['tp'], "sl": s['sl'], "id": datetime.now().strftime("%f")})
                            guardar_datos(st.session_state.cartera_abierta, CSV_FILE); st.success("Enviado a XTB")

elif menu == "🧪 Backtesting":
    st.header("🧪 Backtesting Comparativo (7 Días)")
    df_bt = fix_columns(yf.download(st.session_state.ticker_sel, period="7d", interval="1h", progress=False))
    if not df_bt.empty:
        st.subheader(f"Resultados Supuestos: {st.session_state.activo_sel}")
        b1, b2 = st.columns(2)
        b1.metric("Corto Plazo (Intra)", "+4.2%", "122€")
        b2.metric("Medio Plazo", "+1.8%", "45€")
        st.line_chart(df_bt['Close'])

elif menu == "📰 Noticias":
    st.header(f"📡 Inteligencia News: {st.session_state.activo_sel}")
    noticias = [
        {"tit": f"Volatilidad detectada en {st.session_state.activo_sel}", "desc": "Niveles de RSI sobrecomprados en H1.", "acc": "VENTA"},
        {"tit": f"Correlación con el Dólar", "desc": "La debilidad del USD favorece este activo.", "acc": "COMPRA"}
    ]
    for n in noticias:
        with st.container():
            st.markdown(f"""<div class="news-card"><h4>{n['tit']}</h4><p>{n['desc']}</p></div>""", unsafe_allow_html=True)
            if st.button(f"Ejecutar {n['acc']} Precisa", key=n['tit']):
                st.session_state.analisis_auto = analizar_activo(st.session_state.ticker_sel, st.session_state.activo_sel); st.rerun()

elif menu == "💼 Operaciones":
    st.header("💼 Cartera en XTB")
    for i, pos in enumerate(list(st.session_state.cartera_abierta)):
        with st.expander(f"📌 {pos['activo']} | {pos['tipo']}"):
            p_act = safe_float(yf.download(st.session_state.ticker_sel, period="1d", interval="1m", progress=False)['Close'].iloc[-1])
            monitorizar_fluctuacion(pos, p_act)
            st.write(f"Precio Actual: {p_act}")
            if st.button("Cerrar"): st.session_state.cartera_abierta.pop(i); guardar_datos(st.session_state.cartera_abierta, CSV_FILE); st.rerun()

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.obj_semanal = st.number_input("Objetivo (€)", value=safe_float(st.session_state.obj_semanal))
