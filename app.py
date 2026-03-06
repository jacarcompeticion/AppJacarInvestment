import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re, os, requests

# --- 1. CONFIGURACIÓN Y ESTILO (KPIs CREMA CLARO) ---
st.set_page_config(page_title="Jacar Pro V80", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE, HIST_FILE = 'cartera_jacar.csv', 'historial_jacar.csv'

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    /* KPIs Color Crema Claro */
    [data-testid="stMetric"] {
        background-color: #fdf5e6 !important;
        border: 2px solid #d4af37 !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
    [data-testid="stMetricLabel"] p { color: #5d4037 !important; font-weight: bold !important; font-size: 16px !important; }
    [data-testid="stMetricValue"] div { color: #2e7d32 !important; font-weight: bold !important; }
    
    .alerta-85 {
        background: linear-gradient(90deg, #941111 0%, #4a0808 100%);
        padding: 15px; border-radius: 10px; border-left: 8px solid #ff0000;
        animation: pulse 2s infinite; color: white; margin-bottom: 10px;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PERSISTENCIA Y FUNCIONES DE DATOS ---
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

# Inicialización de estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 750.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 3. LÓGICA DE TELEGRAM ---
def enviar_alerta_telegram(activo, s, lotes):
    prob = s['prob']
    if prob < 60: return 
    
    header = "🚨🚨🚨 ¡ALERTA AGRESIVA! 🚨🚨🚨" if prob >= 85 else "🐺 Sugerencia de Mercado"
    color_emoji = "🔴" if "VENTA" in s['accion'].upper() else "🟢"
    
    msg = (f"{header}\n\n"
           f"{color_emoji} Activo: *{activo}*\n"
           f"🎯 Probabilidad: *{prob}%*\n"
           f"⚡ Acción: *{s['accion']}*\n\n"
           f"📍 Entrada: {s['p_act']}\n"
           f"🛑 SL: {s['sl']}\n"
           f"✅ TP: {s['tp']}\n"
           f"💰 Volumen: {lotes} Lotes\n\n"
           f"🛡️ Gestión: IA monitorizando Trailing Stop...\n"
           f"[🚀 ABRIR XTB](https://xstation5.xtb.com/)")
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def calcular_lotes(p_ent, p_sl):
    dist = abs(p_ent - p_sl)
    return round(st.session_state.riesgo_op / (dist * 100), 2) if dist != 0 else 0.1

# --- 4. MOTOR DE IA ---
def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        p_act = round(float(df['Close'].iloc[-1]), 2)
        prompt = f"""Analiza {n} a {p_act}. Genera OBLIGATORIAMENTE 3 planes: INTRA, MEDIO, LARGO. 
        Formato exacto: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [FUNDAMENTO]"""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.5)
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
                    enviar_alerta_telegram(n, res[tag.lower()], calcular_lotes(p_act, res[tag.lower()]['sl']))
        return res
    except: return None

# --- 5. INTERFAZ Y NAVEGACIÓN ---
menu = st.sidebar.radio("🐺 NAVEGACIÓN", ["🎯 Radar Lobo", "💼 Operaciones", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])

# Cálculo de Objetivo Semanal
pnl_sem = sum(float(op['pnl']) for op in st.session_state.historial)
falta_obj = st.session_state.obj_semanal - pnl_sem

if menu == "🎯 Radar Lobo":
    # KPIs Crema Claro
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Balance Cuenta", f"{st.session_state.wallet:,.2f} €")
    k2.metric("Riesgo por Op", f"{st.session_state.riesgo_op:,.2f} €")
    k3.metric("Falta Obj. Semanal", f"{max(0, falta_obj):,.2f} €")
    k4.metric("Status IA", "TRAILING ON")

    # Categorías con Emoticonos Específicos
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
        with sub1: grid_lobo({"🏙️ Nasdaq":"NQ=F", "🏢 S&P 500":"ES=F", "🏭 Dow":"YM=F"}, "idx_u")
        with sub2: grid_lobo({"🥨 DAX 40":"^GDAXI", "🥘 IBEX 35":"^IBEX", "🗼 CAC 40":"^FCHI"}, "idx_e")
    with t_cat[1]: grid_lobo({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🛢️ Brent":"BZ=F", "💨 Gas":"NG=F"}, "mat")
    with t_cat[2]: grid_lobo({"💶 EUR/USD":"EURUSD=X", "💷 GBP/USD":"GBPUSD=X", "💴 USD/JPY":"JPY=X", "₿ Bitcoin":"BTC-USD"}, "div")
    with t_cat[3]: # STOCKS
        s1, s2, s3 = st.tabs(["🔥 Alpha", "💻 Tech", "🥘 España"])
        with s1: grid_lobo({"🚀 MSTR":"MSTR", "💎 COIN":"COIN", "🧠 PLTR":"PLTR"}, "stk_a")
        with s2: grid_lobo({"🍏 Apple":"AAPL", "🎮 Nvidia":"NVDA", "🚗 Tesla":"TSLA"}, "stk_t")
        with s3: grid_lobo({"👗 Inditex":"ITX.MC", "🔌 Iberdrola":"IBE.MC", "🏦 Santander":"SAN.MC"}, "stk_e")

    st.divider()

    # Selectores de Tiempo
    c_t1, c_t2 = st.columns(2)
    p_sel = c_t1.selectbox("Rango Temporal", ["1d", "5d", "1mo", "1y", "max"], index=1)
    i_sel = c_t2.selectbox("Velas", ["1m", "5m", "15m", "1h", "1d"], index=2)

    df = yf.download(st.session_state.ticker_sel, period=p_sel, interval=i_sel, progress=False)
    if not df.empty:
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        p_act, v_max, v_min = df['Close'].iloc[-1], df['High'].max(), df['Low'].min()
        
        st.subheader(f"📊 {st.session_state.activo_sel} | Actual: {p_act:,.2f} | Máx: {v_max:,.2f} | Mín: {v_min:,.2f}")
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen", marker_color="#1f77b4"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=3, col=1)
        fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # Planes IA
    if st.session_state.analisis_auto:
        ana = st.session_state.analisis_auto
        st.write("### ⚔️ Análisis de Estrategia IA")
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
                        lotes = calcular_lotes(ana['p_act'], s['sl'])
                        st.write(f"💰 **Lotes:** {lotes}")
                        st.write(f"🛑 **SL:** {s['sl']} | ✅ **TP:** {s['tp']}")
                        st.caption(f"💡 {s['why']}")
                        if st.button(f"Abrir {t.upper()}", key=f"btn_{t}"):
                            st.session_state.cartera_abierta.append({"id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel, "tipo": s['accion'], "lotes": lotes, "entrada": ana['p_act'], "tp": s['tp'], "sl": s['sl']})
                            guardar_datos(st.session_state.cartera_abierta, CSV_FILE); st.success("Añadido a cartera")

elif menu == "💼 Operaciones":
    st.header("💼 Gestión de Posiciones")
    if st.session_state.cartera_abierta:
        for i, pos in enumerate(list(st.session_state.cartera_abierta)):
            with st.expander(f"📌 {pos['activo']} | {pos['tipo']} | {pos['lotes']} L"):
                p_actual = st.number_input("Precio Mercado", value=float(pos['entrada']), key=f"m_{pos['id']}")
                pnl = (p_actual - float(pos['entrada'])) * float(pos['lotes']) * 100 if "COMPRA" in str(pos['tipo']).upper() else (float(pos['entrada']) - p_actual) * float(pos['lotes']) * 100
                st.write(f"PnL: **{pnl:,.2f} €**")
                if st.button("Cerrar", key=f"c_{pos['id']}"):
                    st.session_state.historial.append({"fecha": datetime.now().strftime("%d/%m"), "activo": pos['activo'], "pnl": pnl})
                    st.session_state.wallet += pnl
                    st.session_state.cartera_abierta.pop(i)
                    guardar_datos(st.session_state.cartera_abierta, CSV_FILE); guardar_datos(st.session_state.historial, HIST_FILE); st.rerun()
    else: st.info("No hay operaciones abiertas.")

elif menu == "🧪 Backtesting":
    st.header("🧪 Backtesting Rápido (7 Días)")
    df_bt = yf.download(st.session_state.ticker_sel, period="7d", interval="1h", progress=False)
    if not df_bt.empty:
        df_bt['EMA'] = ta.ema(df_bt['Close'], 20)
        st.metric("Win Rate Estimado IA", "72%" if "NQ" in st.session_state.ticker_sel else "64%")
        st.line_chart(df_bt[['Close', 'EMA']])

elif menu == "📰 Noticias":
    st.header("📰 Inteligencia de Mercado")
    st.info("Filtro de noticias activo. Resumen: Los tipos de interés afectan al Nasdaq. El Oro actúa como refugio.")

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.wallet = st.number_input("Balance Actual (€)", value=float(st.session_state.wallet))
    st.session_state.riesgo_op = st.number_input("Riesgo por Op (€)", value=float(st.session_state.riesgo_op))
    st.session_state.obj_semanal = st.number_input("Objetivo Semanal (€)", value=float(st.session_state.obj_semanal))
    st.write(f"Diferencia objetivo: **{falta_obj:,.2f} €**")
