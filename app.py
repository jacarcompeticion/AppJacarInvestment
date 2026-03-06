import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re
import os
import requests

# --- 1. CONFIGURACIÓN Y ESTILO MODERN DARK (LOBO) ---
st.set_page_config(page_title="Jacar Pro V60 - Lobo Edition", layout="wide", page_icon="🐺")

# Configuración Telegram
TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"

CSV_FILE = 'cartera_jacar.csv'
HIST_FILE = 'historial_jacar.csv'

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    div[data-testid="stExpander"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #238636; color: white; border: none; font-weight: bold; }
    .alerta-agresiva {
        background: linear-gradient(90deg, #941111 0%, #4a0808 100%);
        padding: 20px; border-radius: 10px; border-left: 10px solid #ff0000;
        animation: pulse 2s infinite; color: white; margin-bottom: 20px;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PERSISTENCIA Y FUNCIONES DE CÁLCULO ---
def limpiar_numero(valor):
    if isinstance(valor, (int, float)): return float(valor)
    clean = re.sub(r'[^\d.]', '', str(valor).replace(',', '.'))
    try: return float(clean) if clean else 0.0
    except: return 0.0

def cargar_datos(archivo):
    if os.path.exists(archivo):
        try: return pd.read_csv(archivo).to_dict('records')
        except: return []
    return []

def guardar_datos(lista, archivo):
    if lista: pd.DataFrame(lista).to_csv(archivo, index=False)
    elif os.path.exists(archivo): os.remove(archivo)

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'activo_sel' not in st.session_state: st.session_state.activo_sel, st.session_state.ticker_sel = "US100", "NQ=F"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

def calcular_lotes_lobo(p_entrada, p_sl):
    riesgo_fijo = 90.0 # 0.5% de 18,000
    distancia = abs(p_entrada - p_sl)
    if distancia == 0: return 0.1
    # Cálculo para Forex/Índices (ajustable según multiplicador de XTB)
    return round(riesgo_fijo / (distancia * 100), 2)

# --- 3. MOTOR DE TELEGRAM + XTB ---
def enviar_alerta_lobo(activo, tipo, precio, sl, tp, lotes, probabilidad):
    xtb_map = {"Oro": "GOLD", "US100": "US100", "Bitcoin": "BITCOIN", "S&P 500": "US500", "EUR/USD": "EURUSD"}
    symbol = xtb_map.get(activo, activo)
    header = "🚨 ALERTA LOBO AGRESIVA 🚨" if probabilidad >= 85 else "🐺 Sugerencia Lobo"
    mensaje = (
        f"{header}\n📊 Probabilidad: {probabilidad}%\n📈 Activo: {activo}\n"
        f"⚡ Acción: {tipo}\n\n🎯 Entrada: {precio:,.2f}\n🛑 SL: {sl:,.2f}\n✅ TP: {tp:,.2f}\n"
        f"💰 Lotes: {lotes}\n⚠️ Riesgo: 90€"
    )
    url_xtb = f"https://xstation5.xtb.com/#/market/{symbol}"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": [[{"text": "🚀 EJECUTAR EN XTB", "url": url_xtb}]]}
    }
    return requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=payload)

# --- 4. IA Y DATOS TÉCNICOS ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

@st.cache_data(ttl=60)
def obtener_datos(ticker, periodo, intervalo):
    try:
        df = yf.download(ticker, period=periodo, interval=intervalo, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df
    except: return pd.DataFrame()

def auto_analizar_lobo(t, n):
    try:
        df_t = obtener_datos(t, "1mo", "1h")
        p_act = round(float(df_t['Close'].iloc[-1]), 2)
        prompt = f"""Analiza {n} a {p_act}. Diferencia 3 horizontes:
        INTRA (Scalping 15m), MEDIO (Swing 4h), LARGO (Trend 1d).
        Formato: TAG: [Prob]% | [ACCION] | [SL] | [TP] | [FUNDAMENTO]"""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.7)
        lineas = resp.choices[0].message.content.split('\n')
        
        res = {"p_act": p_act}
        for tag in ["INTRA", "MEDIO", "LARGO"]:
            for line in lineas:
                if tag in line.upper() and '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    res[tag.lower()] = {"prob": prob, "accion": parts[1], "sl": limpiar_numero(parts[2]), "tp": limpiar_numero(parts[3]), "why": parts[4]}
        return res
    except: return None

# --- 5. INTERFAZ SUPERIOR Y RADAR ---
col_w1, col_w2, col_w3, col_w4 = st.columns(4)
col_w1.metric("Balance Lobo", f"{st.session_state.wallet:,.2f} €")
col_w2.metric("Riesgo Fijo", "90.00 €", "0.5%")
col_w3.metric("Salud Deuda", "OK", "Filtro Pasado")
col_w4.metric("Status", "HÍBRIDO", "Telegram Activo")

st.write("### 🐺 Radar de Activos")
t_main = st.tabs(["📊 Indices", "🏗️ Material", "💱 Divisas", "📈 Stocks"])

def grid_lobo(d, pref):
    cols = st.columns(len(d))
    for i, (n, t) in enumerate(d.items()):
        if cols[i].button(n, key=f"{pref}_{t}"):
            st.session_state.activo_sel, st.session_state.ticker_sel = n, t
            st.session_state.analisis_auto = auto_analizar_lobo(t, n)
            st.rerun()

with t_main[0]: grid_lobo({"US100":"NQ=F", "S&P 500":"ES=F", "DAX 40":"^GDAXI", "IBEX 35":"^IBEX"}, "idx")
with t_main[1]: grid_lobo({"Oro":"GC=F", "Plata":"SI=F", "Brent":"BZ=F", "Gas Nat":"NG=F"}, "mat")
with t_main[2]: grid_lobo({"EUR/USD":"EURUSD=X", "GBP/USD":"GBPUSD=X", "USD/JPY":"JPY=X", "Bitcoin":"BTC-USD"}, "div")
with t_main[3]: grid_lobo({"Nvidia":"NVDA", "Tesla":"TSLA", "Apple":"AAPL", "MSTR":"MSTR"}, "stk")

# --- 6. VISUALIZACIÓN TÉCNICA Y ESTRATEGIA ---
st.divider()
c_chart, c_strat = st.columns([2, 1])

with c_chart:
    st.write(f"#### 📈 {st.session_state.activo_sel} (Temporalidad Actual)")
    col_t1, col_t2 = st.columns(2)
    with col_t1: per = st.selectbox("Rango", ["1d", "5d", "1mo", "6mo"], index=1)
    with col_t2: intv = st.selectbox("Velas", ["1m", "5m", "15m", "1h", "1d"], index=2)
    
    df = obtener_datos(st.session_state.ticker_sel, per, intv)
    if not df.empty:
        sop, res_v = df['Low'].tail(30).min(), df['High'].tail(30).max()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"), row=1, col=1)
        fig.add_hline(y=res_v, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=sop, line_dash="dash", line_color="green", row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=2, col=1)
        fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

with c_strat:
    if st.session_state.analisis_auto:
        ana = st.session_state.analisis_auto
        st.write("### 🛡️ Plan Táctico")
        for tag in ["intra", "medio", "largo"]:
            s = ana[tag]
            lotes = calcular_lotes_lobo(ana['p_act'], s['sl'])
            if s['prob'] >= 85:
                st.markdown(f'<div class="alerta-agresiva"><b>🚨 {tag.upper()} ALTA PROBABILIDAD ({s["prob"]}%)</b></div>', unsafe_allow_html=True)
            
            with st.expander(f"{tag.upper()} - {s['accion']} ({s['prob']}%)", expanded=(tag=="intra")):
                st.write(f"💡 *Por qué:* {s['why']}")
                st.write(f"🎯 Entrada: **{ana['p_act']}** | Lotes: **{lotes}**")
                st.write(f"🛑 SL: {s['sl']} | ✅ TP: {s['tp']}")
                if st.button(f"🚀 ENVIAR {tag.upper()} AL MÓVIL", key=f"btn_{tag}"):
                    enviar_alerta_lobo(st.session_state.activo_sel, s['accion'], ana['p_act'], s['sl'], s['tp'], lotes, s['prob'])
                    st.toast(f"Alerta {tag} enviada!")

# --- 7. SIDEBAR GESTIÓN ---
with st.sidebar:
    st.header("🐺 Terminal Lobo")
    st.write("#### Posiciones Abiertas")
    pnl_t = 0
    for i, pos in enumerate(list(st.session_state.cartera_abierta)):
        with st.expander(f"📌 {pos['activo']}"):
            p_c = st.number_input("Precio Cierre", value=float(pos['entrada']), key=f"c_{pos['id']}")
            pnl = (p_c - float(pos['entrada'])) * float(pos['lotes']) * 100 if "COMPRA" in str(pos['tipo']).upper() else (float(pos['entrada']) - p_c) * float(pos['lotes']) * 100
            pnl_t += pnl
            if st.button("Cerrar Op", key=f"cl_{pos['id']}"):
                st.session_state.historial.append({"fecha": datetime.now().strftime("%H:%M"), "activo": pos['activo'], "pnl": pnl})
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                guardar_datos(st.session_state.cartera_abierta, CSV_FILE); guardar_datos(st.session_state.historial, HIST_FILE); st.rerun()
    st.divider()
    st.markdown(f"**PnL Total:** `{pnl_t:,.2f} €`")
