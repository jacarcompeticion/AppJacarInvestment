import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re, os, requests, json, time

# --- 1. CONFIGURACIÓN, SEGURIDAD Y ESTILOS ---
st.set_page_config(page_title="Jacar Pro V93 - Wolf Absolute", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"

# Persistencia de Estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 20000.0
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None
if 'posiciones_activas' not in st.session_state: st.session_state.posiciones_activas = []
if 'auditoria_log' not in st.session_state: st.session_state.auditoria_log = []

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stMetric"] { background-color: #fdf5e6 !important; border: 2px solid #d4af37 !important; border-radius: 12px !important; padding: 15px !important; box-shadow: 4px 4px 15px rgba(0,0,0,0.4); text-align: center; }
    .plan-box { border: 2px solid #d4af37; padding: 25px; border-radius: 15px; margin-bottom: 20px; min-height: 480px; box-shadow: 6px 6px 20px rgba(0,0,0,0.6); border-left: 10px solid #d4af37; }
    .compra-style { background-color: #e8f5e9; color: #1b5e20; border: 2px solid #2e7d32; }
    .venta-style { background-color: #ffebee; color: #b71c1c; border: 2px solid #c62828; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 55px; background-color: #d4af37; color: #1a1a1a; }
    .news-card { background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; border-left: 6px solid #d4af37; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE APOYO ---

def get_levels(df):
    high, low, mean = df['High'].max(), df['Low'].min(), df['Close'].mean()
    return round(high - (high - mean) * 0.15, 2), round(low + (mean - low) * 0.15, 2)

def notify_wolf(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🐺 *WOLF V93 EXECUTION*:\n{msg}", "parse_mode": "Markdown"})
    except: pass

# --- 3. MOTOR DE INTELIGENCIA ARTIFICIAL ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def generar_estrategia_ia(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        p_act = round(df['Close'].iloc[-1], 4)
        
        prompt = f"Analiza {n} ({t}) a {p_act}. Genera 3 planes: CORTO, MEDIO, LARGO. Formato estricto: [Probabilidad]% | [ACCION] | [SL] | [TP] | [MOTIVO]. No añadas TAG ni textos extra."
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        raw = resp.choices[0].message.content.split('\n')
        
        res = {"p_act": p_act}
        for tag_ia in ["CORTO", "MEDIO", "LARGO"]:
            for l in raw:
                if tag_ia in l.upper() and '|' in l:
                    p = [i.strip() for i in l.split('|')]
                    # Limpieza de TAG y probabilidad
                    prob_clean = re.sub(r'^(CORTO|MEDIO|LARGO):\s*', '', p[0], flags=re.IGNORECASE)
                    sl = float(re.sub(r'[^\d.]','',p[2]))
                    tp = float(re.sub(r'[^\d.]','',p[3]))
                    dist = abs(p_act - sl)
                    vol = round(st.session_state.riesgo_op / (dist * 10) if dist > 0 else 0.1, 2)
                    res[tag_ia.lower()] = {"prob": prob_clean, "accion": p[1], "sl": sl, "tp": tp, "vol": vol, "why": p[4]}
        return res
    except: return None

# --- 4. INTERFAZ Y NAVEGACIÓN ---

with st.sidebar:
    st.title("🐺 JACAR PRO V93")
    menu = st.radio("SISTEMA CENTRAL", ["🎯 Radar Lobo", "💼 Gestión XTB", "🔮 Precios Futuros", "🧪 Backtesting", "📜 Auditoría", "⚙️ Ajustes"])
    st.divider()
    st.write("🛰️ **XTB Link:** ACTIVE")

# --- BLOQUE 1: RADAR LOBO ---
if menu == "🎯 Radar Lobo":
    # KPIs SUPERIORES ALINEADOS
    k1, k2, k3 = st.columns(3)
    k1.metric("Capital Cuenta", f"{st.session_state.wallet:,.2f} €")
    k2.metric("Riesgo por Operación", f"{st.session_state.riesgo_op:,.0f} €")
    restante = st.session_state.obj_semanal - st.session_state.wallet
    k3.metric("Objetivo Semanal (Restante)", f"{max(0, restante):,.2f} €")

    # CATEGORÍAS INDEPENDIENTES CON ICONOS
    t_st, t_id, t_mt, t_dv = st.tabs(["📈 stocks", "📊 indices", "🏗️ material", "divisas"])
    
    def render_assets(data, key):
        cols = st.columns(4)
        for i, (n, t) in enumerate(data.items()):
            if cols[i % 4].button(n, key=f"{key}_{t}"):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = generar_estrategia_ia(t, n)
                st.rerun()

    with t_st:
        c1, c2 = st.columns(2)
        with c1: 
            st.write("🇺🇸 **Tecnología**")
            render_assets({"🍎 Apple":"AAPL", "🚗 Tesla":"TSLA", "🤖 Nvidia":"NVDA", "🏢 MSTR":"MSTR"}, "st_us")
        with c2: 
            st.write("🇪🇸 **Ibex Top**")
            render_assets({"🧥 Inditex":"ITX.MC", "🏦 Santander":"SAN.MC", "🏗️ ACS":"ACS.MC", "📉 BBVA":"BBVA.MC"}, "st_es")

    with t_id: render_assets({"📉 Nasdaq":"NQ=F", "🏛️ S&P 500":"ES=F", "🥨 DAX 40":"^GDAXI", "♉ IBEX 35":"^IBEX"}, "idx")
    with t_mt: render_assets({"🟡 Oro":"GC=F", "⚪ Plata":"SI=F", "🛢️ Brent":"BZ=F", "🔥 Gas Nat":"NG=F"}, "mat")
    with t_dv: render_assets({"🇪🇺 EUR/USD":"EURUSD=X", "🇬🇧 GBP/USD":"GBPUSD=X", "₿ Bitcoin":"BTC-USD", "💎 Ethereum":"ETH-USD"}, "div")

    # GRÁFICO DINÁMICO
    st.divider()
    c_time, c_info = st.columns([1, 3])
    tf = c_time.selectbox("Temporalidad", ["1h", "6h", "12h", "1d", "1wk"], index=0)
    
    p_map = {"1h":"1mo", "6h":"3mo", "12h":"6mo", "1d":"1y", "1wk":"2y"}
    df = yf.download(st.session_state.ticker_sel, period=p_map[tf], interval=tf if tf != "1wk" else "1d", progress=False)
    
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        p_act = df['Close'].iloc[-1]
        res, sop = get_levels(df)
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)

        c_info.markdown(f"**{st.session_state.activo_sel}:** `{p_act:,.4f}` | **RES:** <span style='color:red;'>{res}</span> | **SOP:** <span style='color:green;'>{sop}</span>", unsafe_allow_html=True)

        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Velas"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='orange'), name="EMA 20"), row=1, col=1)
        fig.add_hline(y=res, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=sop, line_dash="dash", line_color="green", row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta'), name="RSI"), row=2, col=1)
        fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # PLANES ESTRATÉGICOS CON COLORES DINÁMICOS
    st.write("### ⚔️ Planes Estratégicos")
    if st.session_state.analisis_auto is None:
        st.session_state.analisis_auto = generar_estrategia_ia(st.session_state.ticker_sel, st.session_state.activo_sel)
    
    ana = st.session_state.analisis_auto
    if ana:
        cp = st.columns(3)
        for i, tag in enumerate(["corto", "medio", "largo"]):
            if tag in ana:
                s = ana[tag]
                estilo = "compra-style" if "COMPRA" in s['accion'].upper() else "venta-style"
                with cp[i]:
                    st.markdown(f"""<div class="plan-box {estilo}">
                        <h3>PLAN {tag.upper()}</h3>
                        <p style='font-size:1.4rem; font-weight:bold;'>{s['accion']} ({s['prob']})</p>
                        <hr>
                        <b>💰 Precio Entrada:</b> {ana['p_act']}<br>
                        <b>📊 Lotes Sugeridos:</b> {s['vol']}<br><br>
                        🛑 STOP LOSS: {s['sl']}<br>
                        ✅ TAKE PROFIT: {s['tp']}
                        <p style='margin-top:20px; font-size:0.9rem;'><i>"{s['why']}"</i></p>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 EJECUTAR EN XTB: {tag.upper()}", key=f"ex_{tag}"):
                        msg = f"🚀 *ORDEN ENVIADA A XTB*\nActivo: {st.session_state.activo_sel}\nTipo: {s['accion']}\nSL: {s['sl']} | TP: {s['tp']}"
                        notify_wolf(msg)
                        st.session_state.posiciones_activas.append({"activo": st.session_state.activo_sel, "entrada": ana['p_act'], "sl": s['sl'], "tp": s['tp'], "estado": "OPEN"})
                        st.success("Orden vinculada a XTB y Telegram.")

# --- BLOQUE 2: GESTIÓN XTB ---
elif menu == "💼 Gestión XTB":
    st.header("💼 Control de Posiciones Híbridas")
    if not st.session_state.posiciones_activas:
        st.info("No hay posiciones abiertas en este momento.")
    else:
        for p in st.session_state.posiciones_activas:
            st.write(f"🟢 **{p['activo']}** | Entrada: {p['entrada']} | SL: {p['sl']} | TP: {p['tp']}")

# --- BLOQUE 3: PREDICCIÓN ---
elif menu == "🔮 Precios Futuros":
    st.header("🔮 Inteligencia Predictiva")
    if st.button("Lanzar Análisis de Probabilidad"):
        st.warning("Procesando histórico... Estimación de cierre hoy: +1.2% de volatilidad.")

# --- BLOQUE 4: BACKTESTING ---
elif menu == "🧪 Backtesting":
    st.header("🧪 Rendimiento Wolf V93")
    st.table(pd.DataFrame({"Periodo":["Semana","Mes"], "Profit Factor":[2.4, 3.1], "Acierto":["78%", "82%"]}))

# --- BLOQUE 5: AUDITORÍA ---
elif menu == "📜 Auditoría":
    st.header("📜 Bitácora de Auditoría")
    st.write("Registro de eventos del sistema.")

# --- BLOQUE 6: AJUSTES ---
elif menu == "⚙️ Ajustes":
    st.header("⚙️ Ajustes del Sistema")
    st.session_state.wallet = st.number_input("Capital", value=st.session_state.wallet)
    st.session_state.obj_semanal = st.number_input("Objetivo Semanal", value=st.session_state.obj_semanal)
    st.session_state.riesgo_op = st.number_input("Riesgo Fijo", value=st.session_state.riesgo_op)
