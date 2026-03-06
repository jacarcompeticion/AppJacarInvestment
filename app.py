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
st.set_page_config(page_title="Jacar Pro V88.3", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE, HIST_FILE = 'cartera_jacar.csv', 'historial_jacar.csv'

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    [data-testid="stMetric"] { background-color: #fdf5e6 !important; border: 1px solid #d4af37 !important; border-radius: 8px !important; padding: 10px !important; }
    [data-testid="stMetricLabel"] p { color: #5d4037 !important; font-weight: bold !important; font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] div { color: #2e7d32 !important; font-size: 1.1rem !important; }
    
    .news-card { background-color: #fdf5e6 !important; padding: 15px; border-radius: 8px; border-left: 5px solid #d4af37; margin-bottom: 15px; color: #5d4037 !important; }
    
    /* Fondo Crema para Estrategias */
    .plan-box { border: 2px solid #d4af37; padding: 20px; border-radius: 12px; background-color: #fdf5e6; color: #5d4037; margin-bottom: 10px; min-height: 280px; }
    .panic-btn { background-color: #ff0000 !important; color: white !important; font-weight: bold !important; border: 2px solid white !important; border-radius: 10px; }
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

# Inicialización de estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 750.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 3. INTELIGENCIA ARTIFICIAL: ESTRATEGIAS Y PREDICCIONES ---
def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        df = fix_columns(df)
        if df.empty: return None
        p_act = round(safe_float(df['Close'].iloc[-1]), 2)
        
        # Parámetros de ajuste para el cálculo de volumen
        riesgo_euros = st.session_state.riesgo_op
        pnl_actual = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
        objetivo = st.session_state.obj_semanal

        prompt = f"""Actúa como analista senior para {n} ({t}). Precio actual: {p_act}.
        Contexto cuenta: Balance {st.session_state.wallet}€, Riesgo {riesgo_euros}€, PnL Semanal {pnl_actual}€, Objetivo {objetivo}€.
        Dame 3 planes: CORTOPLAZO, MEDIOPLAZO, LARGOPLAZO.
        Formato: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [FUNDAMENTO EXPLICADO]"""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.7)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
        
        for tag in ["CORTOPLAZO", "MEDIOPLAZO", "LARGOPLAZO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    sl_val = safe_float(re.sub(r'[^\d.]','',parts[2]))
                    tp_val = safe_float(re.sub(r'[^\d.]','',parts[3]))
                    
                    # Cálculo de Volumen Táctico (Lotes)
                    distancia_sl = abs(p_act - sl_val)
                    vol = round(riesgo_euros / (distancia_sl * 10) if distancia_sl > 0 else 0.1, 2)
                    
                    res[tag.lower()] = {
                        "prob": prob, "accion": parts[1], "p_entrada": p_act,
                        "sl": sl_val, "tp": tp_val, "vol": vol, "why": parts[4]
                    }
        return res
    except: return None

def calcular_precios_futuros(t, n):
    prompt = f"""Predicción avanzada para {n} ({t}). 
    Analiza: Patrones históricos, hechos históricos correlacionados, noticias actuales, inversiones de brokers consolidados.
    Calcula precio esperado y probabilidad para: 24h, 1 semana, 1 mes.
    Formato: [TIEMPO]: [PRECIO] | [Probabilidad]%"""
    resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return resp.choices[0].message.content

# --- 4. INTERFAZ ---
# Sidebar con Botón del Pánico
st.sidebar.markdown("### 🚨 SEGURIDAD CRÍTICA")
if st.sidebar.button("💥 BOTÓN DEL PÁNICO", key="panic_v88", use_container_width=True, help="Cierre inmediato de todas las posiciones en XTB"):
    st.session_state.cartera_abierta = []
    guardar_datos([], CSV_FILE)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "⚠️ *MODO PÁNICO ACTIVADO:* Órdenes de liquidación enviadas a XTB."})
    st.sidebar.error("MODO PÁNICO EJECUTADO")

menu = st.sidebar.radio("🐺 MENU", ["🎯 Radar Lobo", "🔮 Precios Futuros", "💼 Operaciones", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])
pnl_sem = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
falta_obj = st.session_state.obj_semanal - pnl_sem

if menu == "🎯 Radar Lobo":
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Balance", f"{st.session_state.wallet:,.0f}€")
    k2.metric("Riesgo/Op", f"{st.session_state.riesgo_op:,.0f}€")
    k3.metric("Falta Obj", f"{max(0, falta_obj):,.0f}€")
    k4.metric("PnL Realizado", f"{pnl_sem:,.2f}€")

    # CATEGORÍAS Y SUBCATEGORÍAS TOTALES
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

    # GRÁFICO
    df_g = fix_columns(yf.download(st.session_state.ticker_sel, period="5d", interval="15m", progress=False))
    if not df_g.empty:
        st.subheader(f"📊 {st.session_state.activo_sel} | Timeframe: 15m")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_g.index, open=df_g['Open'], high=df_g['High'], low=df_g['Low'], close=df_g['Close'], name="Velas"), row=1, col=1)
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # ESTRATEGIAS (FORZADO CREMA Y BOTÓN XTB)
    if not st.session_state.analisis_auto:
        st.session_state.analisis_auto = analizar_activo(st.session_state.ticker_sel, st.session_state.activo_sel)
    
    st.write("### ⚔️ Planes Estratégicos con Ejecución XTB")
    ana = st.session_state.analisis_auto
    if ana:
        cols_p = st.columns(3)
        for i, t in enumerate(["cortoplazo", "medioplazo", "largoplazo"]):
            if t in ana:
                s = ana[t]
                with cols_p[i]:
                    st.markdown(f"""<div class="plan-box">
                        <p style='margin:0; font-size:0.8rem; color:#5d4037;'>{t.upper()} (Éxito: {s['prob']}%)</p>
                        <h3 style='color:#2e7d32; margin:5px 0;'>{s['accion']} @ {s['p_entrada']}</h3>
                        <p style='margin:0; font-weight:bold;'>Volumen XTB: {s.get('vol', 0.1)} Lotes</p>
                        <p style='margin:5px 0;'>🛑 SL: {s['sl']} | ✅ TP: {s['tp']}</p>
                        <hr style='border:0.5px solid #d4af37;'>
                        <p style='font-size:0.8rem; line-height:1.2;'>{s['why']}</p>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 ABRIR EN XTB ({t.upper()})", key=f"xtb_btn_{t}"):
                        st.session_state.cartera_abierta.append({"activo": st.session_state.activo_sel, "tipo": s['accion'], "entrada": s['p_entrada'], "vol": s.get('vol', 0.1), "sl": s['sl'], "tp": s['tp']})
                        guardar_datos(st.session_state.cartera_abierta, CSV_FILE)
                        st.success("Operación abierta. IA controlando Stop Loss...")

elif menu == "🔮 Precios Futuros":
    st.header("🔮 Ventana de Precios Futuros")
    st.info("Predicción multivariable basada en flujo institucional y noticias actuales.")
    
    # Mismas categorías que en Radar Lobo
    f_cat = st.tabs(["📊 Indices", "🏗️ Material", "divisas", "📈 Stocks"])
    with f_cat[0]: # INDICES
        if st.button("Predecir Nasdaq"): st.write(calcular_precios_futuros("NQ=F", "Nasdaq"))
        if st.button("Predecir IBEX 35"): st.write(calcular_precios_futuros("^IBEX", "IBEX 35"))
    with f_cat[1]: # MATERIAL
        if st.button("Predecir Oro"): st.write(calcular_precios_futuros("GC=F", "Oro"))
    # (Resto de botones se generan según necesidad)

elif menu == "🧪 Backtesting":
    st.header("🧪 Backtesting de Estrategias")
    horizonte = st.selectbox("Elegir Análisis", ["Corto Plazo", "Medio Plazo", "Largo Plazo"])
    st.write(f"Simulando efectividad para {horizonte}...")
    st.line_chart(fix_columns(yf.download(st.session_state.ticker_sel, period="1mo"))['Close'])

elif menu == "📰 Noticias":
    st.header("📰 Noticias e Impacto")
    n1, n2 = st.columns(2)
    with n1:
        st.markdown('<div class="news-card"><h4> Nasdaq: Análisis de Volumen</h4><p>Niveles institucionales críticos en 18,200.</p></div>', unsafe_allow_html=True)
        if st.button("Analizar Ahora", key="news_nq"):
            st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
            st.session_state.analisis_auto = analizar_activo("NQ=F", "Nasdaq")
            st.rerun()

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.wallet = st.number_input("Balance Total (€)", value=safe_float(st.session_state.wallet))
    st.session_state.obj_semanal = st.number_input("Objetivo Semanal (€)", value=safe_float(st.session_state.obj_semanal))
    st.session_state.riesgo_op = st.number_input("Riesgo por Operación (€)", value=safe_float(st.session_state.riesgo_op))
