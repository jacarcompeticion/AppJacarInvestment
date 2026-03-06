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
st.set_page_config(page_title="Jacar Pro V71 - Lobo Alpha", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE = 'cartera_jacar.csv'
HIST_FILE = 'historial_jacar.csv'

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
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 10px; }
    .alerta-agresiva {
        background: linear-gradient(90deg, #941111 0%, #4a0808 100%);
        padding: 15px; border-radius: 10px; border-left: 10px solid #ff0000;
        animation: pulse 2s infinite; color: white; margin-bottom: 15px;
    }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. MOTOR DE DATOS E IA ---
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

def auto_analizar_lobo(t, n):
    try:
        df_t = obtener_datos(t, "1mo", "1h")
        p_act = round(float(df_t['Close'].iloc[-1]), 2)
        prompt = f"Analiza {n} a {p_act}. Dame 3 planes DISTINTOS: INTRA, MEDIO, LARGO. Formato: TAG: [Prob]% | [ACCION] | [SL] | [TP] | [FUNDAMENTO]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.7)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act, "moneda": "€" if ".MC" in t or "GDAXI" in t else "$"}
        for tag in ["INTRA", "MEDIO", "LARGO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group()) if re.search(r'\d+', parts[0]) else 50
                    res[tag.lower()] = {"prob": prob, "accion": parts[1], "sl": limpiar_numero(parts[2]), "tp": limpiar_numero(parts[3]), "why": parts[4]}
        return res
    except: return None

# --- 3. NAVEGACIÓN ---
menu = st.sidebar.radio("🐺 NAVEGACIÓN", ["🎯 Radar Lobo", "💼 Operaciones", "📰 Noticias", "⚙️ Ajustes"])

# --- VENTANA: RADAR ---
if menu == "🎯 Radar Lobo":
    # KPIs Superiores
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Balance", f"{st.session_state.wallet:,.2f} €")
    c2.metric("Riesgo/Op", f"{st.session_state.riesgo_op} €")
    c3.metric("Activo", st.session_state.activo_sel)
    c4.metric("Precio", f"{obtener_datos(st.session_state.ticker_sel, '1d', '1m')['Close'].iloc[-1]:,.2f}" if not st.session_state.ticker_sel=="" else "0")

    # Sistema de Categorías
    st.write("### 🔍 Selección de Mercado")
    t_cat = st.tabs(["📊 Indices", "🏗️ Material", "💱 Divisas", "📈 Stocks"])
    
    def grid_v(d, p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(n, key=f"{p}_{t}", use_container_width=True):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = auto_analizar_lobo(t, n)
                st.rerun()

    with t_cat[0]: # INDICES
        i1, i2 = st.tabs(["🇺🇸 EE.UU", "🇪🇺 Europa"])
        with i1: grid_v({"🇺🇸 US100":"NQ=F", "📈 S&P 500":"ES=F", "🏭 Dow Jones":"YM=F"}, "idx_u")
        with i2: grid_v({"🇩🇪 DAX 40":"^GDAXI", "🇪🇸 IBEX 35":"^IBEX", "🇫🇷 CAC 40":"^FCHI"}, "idx_e")
    with t_cat[1]: grid_v({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🛢️ Brent":"BZ=F", "🔥 Gas Nat":"NG=F"}, "mat")
    with t_cat[2]: grid_v({"🇪🇺 EUR/USD":"EURUSD=X", "🇬🇧 GBP/USD":"GBPUSD=X", "🇯🇵 USD/JPY":"JPY=X", "₿ Bitcoin":"BTC-USD"}, "div")
    with t_cat[3]: # STOCKS
        s1, s2, s3 = st.tabs(["🔥 Alpha", "💻 Tech", "🇪🇸 España"])
        with s1: grid_v({"🚀 MSTR":"MSTR", "🪙 COIN":"COIN", "🧠 PLTR":"PLTR", "⚡ SMCI":"SMCI"}, "stk_a")
        with s2: grid_v({"🍏 Apple":"AAPL", "🤖 NVDA":"NVDA", "🚗 Tesla":"TSLA", "🔍 Google":"GOOGL"}, "stk_t")
        with s3: grid_v({"👕 Inditex":"ITX.MC", "⚡ Iberdrola":"IBE.MC", "🏦 Santander":"SAN.MC", "🏦 BBVA":"BBVA.MC"}, "stk_e")

    st.divider()
    
    # Gráfico y Estrategia
    c_chart, c_strat = st.columns([2, 1])
    with c_chart:
        c_p1, c_p2 = st.columns(2)
        p_sel = c_p1.selectbox("Rango", ["1d", "5d", "1mo", "1y"], index=1)
        i_sel = c_p2.selectbox("Velas", ["1m", "5m", "15m", "1h", "1d"], index=2)
        df = obtener_datos(st.session_state.ticker_sel, p_sel, i_sel)
        if not df.empty:
            sop, res = df['Low'].tail(30).min(), df['High'].tail(30).max()
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Velas"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"), row=1, col=1)
            fig.add_hline(y=res, line_dash="dash", line_color="red", annotation_text=f"RES: {res:,.2f}", row=1, col=1)
            fig.add_hline(y=sop, line_dash="dash", line_color="green", annotation_text=f"SOP: {sop:,.2f}", row=1, col=1)
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen", marker_color="#1f77b4"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=3, col=1)
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)
            

    with c_strat:
        if st.session_state.analisis_auto:
            ana = st.session_state.analisis_auto
            st.write("### ⚔️ Planes Lobo")
            for t in ["intra", "medio", "largo"]:
                if t in ana:
                    s = ana[t]
                    if s['prob'] >= 85: st.markdown(f'<div class="alerta-agresiva"><b>🚨 {t.upper()} ALTA ({s["prob"]}%)</b></div>', unsafe_allow_html=True)
                    with st.expander(f"{t.upper()} - {s['accion']}", expanded=(t=="intra")):
                        dist = abs(ana['p_act'] - s['sl'])
                        lotes = round(st.session_state.riesgo_op / (dist * 100), 2) if dist != 0 else 0.1
                        st.write(f"**Fundamento:** {s['why']}")
                        st.write(f"📍 Entrada: **{ana['p_act']}** | Lotes: **{lotes}**")
                        st.write(f"🛑 SL: {s['sl']} | ✅ TP: {s['tp']}")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.button(f"📱 Telegram", key=f"tel_{t}"):
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={
                                "chat_id": TELEGRAM_CHAT_ID, "text": f"🐺 {st.session_state.activo_sel} ({t.upper()})\nAcción: {s['accion']}\nPrecio: {ana['p_act']}\nSL: {s['sl']} | TP: {s['tp']}\nLotes: {lotes}",
                                "reply_markup": {"inline_keyboard": [[{"text": "🚀 XTB", "url": "https://xstation5.xtb.com/"}]]}
                            })
                            st.toast("Señal enviada")
                        if col_btn2.button(f"💼 Abrir Carpeta", key=f"open_{t}"):
                            st.session_state.cartera_abierta.append({
                                "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                                "tipo": s['accion'], "lotes": lotes, "entrada": ana['p_act'], "tp": s['tp'], "sl": s['sl']
                            })
                            guardar_datos(st.session_state.cartera_abierta, CSV_FILE); st.rerun()

# --- VENTANA: OPERACIONES ---
elif menu == "💼 Operaciones":
    st.header("🏢 Gestión de Cartera")
    tab_p, tab_h = st.tabs(["💼 Posiciones Abiertas", "📜 Historial de Cierre"])
    
    with tab_p:
        if st.session_state.cartera_abierta:
            pnl_total = 0
            for i, pos in enumerate(list(st.session_state.cartera_abierta)):
                with st.expander(f"📌 {pos['activo']} | {pos['tipo']} | {pos['lotes']} L"):
                    p_cierre = st.number_input("Precio Actual de Mercado", value=float(pos['entrada']), key=f"close_{pos['id']}")
                    es_compra = "COMPRA" in str(pos['tipo']).upper()
                    pnl = (p_cierre - float(pos['entrada'])) * float(pos['lotes']) * 100 if es_compra else (float(pos['entrada']) - p_cierre) * float(pos['lotes']) * 100
                    pnl_total += pnl
                    st.write(f"PnL Estimado: **{pnl:,.2f} €**")
                    if st.button("Cerrar Posición", key=f"btn_close_{pos['id']}"):
                        st.session_state.historial.append({"fecha": datetime.now().strftime("%d/%m %H:%M"), "activo": pos['activo'], "pnl": pnl})
                        st.session_state.wallet += pnl
                        st.session_state.cartera_abierta.pop(i)
                        guardar_datos(st.session_state.cartera_abierta, CSV_FILE); guardar_datos(st.session_state.historial, HIST_FILE); st.rerun()
            st.metric("PnL Total en Curso", f"{pnl_total:,.2f} €")
        else: st.info("No tienes operaciones abiertas.")

    with tab_h:
        if st.session_state.historial:
            df_hist = pd.DataFrame(st.session_state.historial)
            st.table(df_hist.iloc[::-1])
            if st.button("Limpiar Historial"): 
                st.session_state.historial = []; guardar_datos([], HIST_FILE); st.rerun()

# --- VENTANA: NOTICIAS ---
elif menu == "📰 Noticias":
    st.header("📡 Feed de Inteligencia Lobo")
    c_n1, c_n2 = st.columns(2)
    with c_n1:
        st.markdown("""
        ### 🌍 Macro y Geopolítica
        - **FED:** Rumores de mantenimiento de tipos. El Nasdaq respira.
        - **Petróleo:** Tensión en el Mar Rojo afecta al Brent.
        """)
    with c_n2:
        st.markdown("""
        ### 💡 Tips de Inversión
        - **Divergencia RSI:** Detectada en EUR/USD en gráfico de 1h.
        - **Nivel Psicológico:** El Bitcoin lucha por los 65k.
        """)

# --- VENTANA: AJUSTES ---
elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración del Terminal")
    st.session_state.wallet = st.number_input("Capital de Cuenta (€)", value=float(st.session_state.wallet))
    st.session_state.riesgo_op = st.number_input("Riesgo Máximo por Operación (€)", value=float(st.session_state.riesgo_op))
    st.divider()
    st.write("Configuración de API (Solo lectura)")
    st.text_input("OpenAI Key", value="********", disabled=True)
    st.text_input("Telegram Bot Token", value=TELEGRAM_TOKEN)
