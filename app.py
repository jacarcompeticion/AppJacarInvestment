import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re, os, requests

# --- 1. CONFIGURACIÓN, PERSISTENCIA Y ESTILO ---
st.set_page_config(page_title="Jacar Pro V75 - Lobo Alpha", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE, HIST_FILE = 'cartera_jacar.csv', 'historial_jacar.csv'

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
    elif os.path.exists(archivo): 
        try: os.remove(archivo)
        except: pass

# --- ESTADO DE SESIÓN ---
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "US100"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    /* KPIs Profesionales en Azul/Gris */
    [data-testid="stMetric"] {
        background-color: #1c2533 !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
    .hot-zone {
        background: linear-gradient(90deg, #441111 0%, #1a0505 100%);
        border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-bottom: 20px; color: #ff9999;
    }
    .alerta-85 {
        background: linear-gradient(90deg, #941111 0%, #4a0808 100%);
        padding: 15px; border-radius: 10px; border-left: 8px solid #ff0000;
        animation: pulse 2s infinite; color: white; margin-bottom: 10px;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. LÓGICA DE TELEGRAM Y CÁLCULOS ---
def enviar_alerta_telegram(activo, s, lotes):
    prob = s['prob']
    if prob < 60: return 
    
    if prob >= 85:
        header = "🚨🚨🚨 ¡ALERTA AGRESIVA LOBO! 🚨🚨🚨"
        emoji = "🔥"
    else:
        header = "🐺 Sugerencia de Mercado"
        emoji = "📊"
        
    msg = (f"{header}\n\n{emoji} Activo: *{activo}*\n🎯 Probabilidad: *{prob}%*\n⚡ Acción: *{s['accion']}*\n\n"
           f"📍 Entrada: {s['p_act']}\n🛑 SL: {s['sl']}\n✅ TP: {s['tp']}\n💰 Lotes: {lotes}\n\n"
           f"⚠️ Riesgo: {st.session_state.riesgo_op}€\n[🚀 EJECUTAR EN XTB](https://xstation5.xtb.com/)")
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def calcular_lotes(p_ent, p_sl):
    dist = abs(p_ent - p_sl)
    return round(st.session_state.riesgo_op / (dist * 100), 2) if dist != 0 else 0.1

# --- 3. MOTOR DE IA ---
@st.cache_data(ttl=2)
def obtener_datos(ticker, periodo, intervalo):
    try:
        df = yf.download(ticker, period=periodo, interval=intervalo, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df
    except: return pd.DataFrame()

def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        p_act = round(float(df['Close'].iloc[-1]), 2)
        prompt = f"Analiza {n} a {p_act}. Dame 3 planes: INTRA, MEDIO, LARGO. Formato: TAG: [Prob]% | [ACCION] | [SL] | [TP] | [FUNDAMENTO]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.6)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
        for tag in ["INTRA", "MEDIO", "LARGO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    res[tag.lower()] = {
                        "prob": prob, "accion": parts[1], "p_act": p_act,
                        "sl": limpiar_numero(parts[2]), "tp": limpiar_numero(parts[3]), "why": parts[4]
                    }
                    # Disparo automático si cumple >60%
                    enviar_alerta_telegram(n, res[tag.lower()], calcular_lotes(p_act, res[tag.lower()]['sl']))
        return res
    except: return None

# --- 4. NAVEGACIÓN Y VENTANAS ---
menu = st.sidebar.radio("🐺 NAVEGACIÓN", ["🎯 Radar Lobo", "💼 Operaciones", "📰 Noticias", "⚙️ Ajustes"])

if menu == "🎯 Radar Lobo":
    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Balance Total", f"{st.session_state.wallet:,.2f} €")
    c2.metric("Riesgo por Op", f"{st.session_state.riesgo_op:,.2f} €")
    c3.metric("Activo", st.session_state.activo_sel)

    # Activos Calientes
    st.markdown('<div class="hot-zone">🔥 <b>ZONA CALIENTE:</b> Movimiento agresivo detectado en Nasdaq y Oro. Correlación de Deuda OK.</div>', unsafe_allow_html=True)

    # Categorías y Subcategorías
    t_cat = st.tabs(["📊 Indices", "🏗️ Material", "💱 Divisas", "📈 Stocks"])
    
    def grid_lobo(d, p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(f"🐺 {n}", key=f"{p}_{t}", use_container_width=True):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = analizar_activo(t, n)
                st.rerun()

    with t_cat[0]: # INDICES
        sub1, sub2 = st.tabs(["🇺🇸 EE.UU", "🇪🇺 Europa"])
        with sub1: grid_lobo({"Nasdaq":"NQ=F", "S&P 500":"ES=F", "Dow Jones":"YM=F"}, "idx_u")
        with sub2: grid_lobo({"DAX 40":"^GDAXI", "IBEX 35":"^IBEX", "CAC 40":"^FCHI"}, "idx_e")
    with t_cat[1]: grid_lobo({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🛢️ Brent":"BZ=F", "🔥 Gas Nat":"NG=F"}, "mat")
    with t_cat[2]: grid_lobo({"EUR/USD":"EURUSD=X", "GBP/USD":"GBPUSD=X", "USD/JPY":"JPY=X", "₿ Bitcoin":"BTC-USD"}, "div")
    with t_cat[3]: # STOCKS
        s1, s2, s3 = st.tabs(["🔥 Alpha", "💻 Tech", "🇪🇸 España"])
        with s1: grid_lobo({"MSTR":"MSTR", "COIN":"COIN", "PLTR":"PLTR", "SMCI":"SMCI"}, "stk_a")
        with s2: grid_lobo({"Apple":"AAPL", "Nvidia":"NVDA", "Tesla":"TSLA", "Google":"GOOGL"}, "stk_t")
        with s3: grid_lobo({"Inditex":"ITX.MC", "Iberdrola":"IBE.MC", "Santander":"SAN.MC", "BBVA":"BBVA.MC"}, "stk_e")

    st.divider()
    
    # Gráfico y Estrategia
    col_chart, col_strat = st.columns([2, 1])
    with col_chart:
        df = obtener_datos(st.session_state.ticker_sel, "5d", "15m")
        if not df.empty:
            sop, res = df['Low'].tail(30).min(), df['High'].tail(30).max()
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Velas"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"), row=1, col=1)
            fig.add_hline(y=res, line_dash="dash", line_color="red", row=1, col=1)
            fig.add_hline(y=sop, line_dash="dash", line_color="green", row=1, col=1)
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen", marker_color="#1f77b4"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=3, col=1)
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)

    with col_strat:
        if st.session_state.analisis_auto:
            ana = st.session_state.analisis_auto
            st.write("### ⚔️ Planes Lobo")
            for t in ["intra", "medio", "largo"]:
                if t in ana:
                    s = ana[t]
                    if s['prob'] >= 85: st.markdown(f'<div class="alerta-85">🚨 <b>{t.upper()} ALTA ({s["prob"]}%)</b></div>', unsafe_allow_html=True)
                    with st.expander(f"{t.upper()} - {s['accion']}", expanded=(t=="intra")):
                        lotes = calcular_lotes(ana['p_act'], s['sl'])
                        st.write(f"💡 {s['why']}")
                        st.write(f"📍 Entrada: **{ana['p_act']}** | Lotes: **{lotes}**")
                        st.write(f"🛑 SL: {s['sl']} | ✅ TP: {s['tp']}")
                        if st.button(f"💼 Abrir Carpeta {t.upper()}", key=f"abrir_{t}"):
                            st.session_state.cartera_abierta.append({"id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel, "tipo": s['accion'], "lotes": lotes, "entrada": ana['p_act'], "tp": s['tp'], "sl": s['sl']})
                            guardar_datos(st.session_state.cartera_abierta, CSV_FILE); st.rerun()

# --- VENTANA: OPERACIONES ---
elif menu == "💼 Operaciones":
    st.header("🏢 Gestión de Cartera")
    tab_p, tab_h = st.tabs(["💼 Posiciones Abiertas", "📜 Historial"])
    with tab_p:
        if st.session_state.cartera_abierta:
            for i, pos in enumerate(list(st.session_state.cartera_abierta)):
                with st.expander(f"📌 {pos['activo']} | {pos['tipo']} | {pos['lotes']} L"):
                    p_c = st.number_input("Precio Actual", value=float(pos['entrada']), key=f"c_{pos['id']}")
                    pnl = (p_c - float(pos['entrada'])) * float(pos['lotes']) * 100 if "COMPRA" in str(pos['tipo']).upper() else (float(pos['entrada']) - p_c) * float(pos['lotes']) * 100
                    st.write(f"PnL: **{pnl:,.2f} €**")
                    if st.button("Cerrar Op", key=f"btn_c_{pos['id']}"):
                        st.session_state.historial.append({"fecha": datetime.now().strftime("%d/%m %H:%M"), "activo": pos['activo'], "pnl": pnl})
                        st.session_state.wallet += pnl
                        st.session_state.cartera_abierta.pop(i)
                        guardar_datos(st.session_state.cartera_abierta, CSV_FILE); guardar_datos(st.session_state.historial, HIST_FILE); st.rerun()
        else: st.info("Sin posiciones.")
    with tab_h:
        if st.session_state.historial: st.table(pd.DataFrame(st.session_state.historial).iloc[::-1])

# --- VENTANA: NOTICIAS ---
elif menu == "📰 Noticias":
    st.header("📡 Feed de Inteligencia Lobo")
    st.info("🔴 **GEOPOLÍTICA:** Tensión en el Mar Rojo afecta al Brent.")
    st.warning("🟡 **MACRO:** FED mantiene tipos, el Nasdaq busca nuevos máximos.")

# --- VENTANA: AJUSTES ---
elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.wallet = st.number_input("Balance Total (€)", value=float(st.session_state.wallet))
    st.session_state.riesgo_op = st.number_input("Riesgo por Operación (€)", value=float(st.session_state.riesgo_op))
    if st.button("Guardar Cambios"): st.success("Actualizado.")
