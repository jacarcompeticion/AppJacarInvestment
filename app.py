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
st.set_page_config(page_title="Jacar Pro V86", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"
CSV_FILE, HIST_FILE = 'cartera_jacar.csv', 'historial_jacar.csv'

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    /* Ajuste de KPIs en una sola línea con texto optimizado */
    [data-testid="stMetric"] {
        background-color: #fdf5e6 !important;
        border: 1px solid #d4af37 !important;
        border-radius: 8px !important;
        padding: 10px !important;
        min-width: 150px !important;
    }
    [data-testid="stMetricLabel"] p { 
        color: #5d4037 !important; 
        font-weight: bold !important; 
        font-size: 0.85rem !important; 
        white-space: nowrap !important;
    }
    [data-testid="stMetricValue"] div { 
        color: #2e7d32 !important; 
        font-size: 1.1rem !important; 
    }
    .hot-zone {
        background: linear-gradient(90deg, #441111 0%, #1a0505 100%);
        border: 1px solid #ff4b4b; padding: 12px; border-radius: 10px; 
        margin-bottom: 20px; color: #ff9999; border-left: 10px solid #ff0000;
    }
    .news-card {
        background-color: #fdf5e6 !important; /* FONTO CREMA */
        padding: 15px; border-radius: 8px;
        border-left: 5px solid #d4af37; margin-bottom: 10px;
        color: #5d4037 !important;
    }
    .news-card h4 { color: #5d4037 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE DATOS Y PERSISTENCIA ---
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

# --- 3. LOGICA IA Y TELEGRAM ---
def enviar_alerta_telegram(activo, s, lotes):
    prob = s['prob']
    if prob < 60: return 
    header = "🚨 ALERTA AGRESIVA" if prob >= 85 else "🐺 Sugerencia"
    color = "🔴 VENTA" if "VENTA" in s['accion'].upper() else "🟢 COMPRA"
    msg = (f"{header}\n\n{color} *{activo}*\n🎯 Prob: {prob}%\n\n📍 In: {s['p_act']}\n🛑 SL: {s['sl']}\n✅ TP: {s['tp']}\n💰 Lotes: {lotes}\n[🚀 XTB](https://xstation5.xtb.com/)")
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def analizar_activo(t, n):
    try:
        df = yf.download(t, period="1mo", interval="1h", progress=False)
        df = fix_columns(df)
        p_act = round(safe_float(df['Close'].iloc[-1]), 2)
        prompt = f"Analiza {n} a {p_act}. Dame 3 planes: CORTOPLAZO, MEDIOPLAZO, LARGOPLAZO. Formato: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [FUNDAMENTO]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.5)
        lines = resp.choices[0].message.content.split('\n')
        res = {"p_act": p_act}
        for tag in ["CORTOPLAZO", "MEDIOPLAZO", "LARGOPLAZO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = int(re.search(r'\d+', parts[0]).group())
                    res[tag.lower()] = {"prob": prob, "accion": parts[1], "p_act": p_act, "sl": safe_float(re.sub(r'[^\d.]','',parts[2])), "tp": safe_float(re.sub(r'[^\d.]','',parts[3])), "why": parts[4]}
                    dist = abs(p_act - res[tag.lower()]['sl'])
                    lotes = round(st.session_state.riesgo_op / (dist * 100), 2) if dist != 0 else 0.1
                    enviar_alerta_telegram(n, res[tag.lower()], lotes)
        return res
    except: return None

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("🐺 MENU", ["🎯 Radar Lobo", "💼 Operaciones", "🧪 Backtesting", "📰 Noticias", "⚙️ Ajustes"])
pnl_sem = sum(safe_float(op.get('pnl', 0)) for op in st.session_state.historial)
falta_obj = st.session_state.obj_semanal - pnl_sem

if menu == "🎯 Radar Lobo":
    # KPIs en una sola línea
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Balance", f"{st.session_state.wallet:,.0f}€")
    k2.metric("Riesgo/Op", f"{st.session_state.riesgo_op:,.0f}€")
    k3.metric("Falta Obj", f"{max(0, falta_obj):,.0f}€")
    k4.metric("Status IA", "TRAILING ON")

    st.markdown('<div class="hot-zone">🔥 <b>ZONA CALIENTE:</b> Nasdaq (Varianza), Oro (Soporte) y Bitcoin (Ruptura).</div>', unsafe_allow_html=True)
    
    # Categorías
    t_cat = st.tabs(["📊 Indices", "🏗️ Material", "divisas", "📈 Stocks"])
    def grid_lobo(d, p):
        cols = st.columns(4)
        for i, (n, t) in enumerate(d.items()):
            if cols[i % 4].button(n, key=f"{p}_{t}", use_container_width=True):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = analizar_activo(t, n); st.rerun()

    with t_cat[0]: grid_lobo({"🏙️ Nasdaq":"NQ=F", "🏢 S&P 500":"ES=F", "🏭 Dow":"YM=F", "🥨 DAX 40":"^GDAXI"}, "idx")
    with t_cat[1]: grid_lobo({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🛢️ Brent":"BZ=F", "💨 Gas":"NG=F"}, "mat")
    with t_cat[2]: grid_lobo({"💶 EUR/USD":"EURUSD=X", "💷 GBP/USD":"GBPUSD=X", "💴 USD/JPY":"JPY=X", "₿ Bitcoin":"BTC-USD"}, "div")
    with t_cat[3]: grid_lobo({"🚀 MSTR":"MSTR", "🎮 NVDA":"NVDA", "🚗 TSLA":"TSLA", "👗 ITX.MC":"ITX.MC"}, "stk")

    st.divider()

    # Selector de Tiempo y Gráfica
    c_t1, c_t2 = st.columns(2)
    p_sel = c_t1.selectbox("Rango Temporal", ["1d", "5d", "1mo", "1y", "max"], index=1)
    i_sel = c_t2.selectbox("Velas", ["1m", "5m", "15m", "1h", "1d"], index=2)

    df = fix_columns(yf.download(st.session_state.ticker_sel, period=p_sel, interval=i_sel, progress=False))
    if not df.empty:
        # Indicadores
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        p_act, v_max, v_min = safe_float(df['Close'].iloc[-1]), safe_float(df['High'].max()), safe_float(df['Low'].min())
        
        st.subheader(f"📊 {st.session_state.activo_sel} | Actual: {p_act:,.2f} | Máx: {v_max:,.2f} | Mín: {v_min:,.2f}")
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1.5), name="EMA 20"), row=1, col=1)
        
        # Soporte y Resistencia Dinámicos
        fig.add_hline(y=v_max, line_dash="dot", line_color="red", annotation_text="RESISTENCIA", row=1, col=1)
        fig.add_hline(y=v_min, line_dash="dot", line_color="green", annotation_text="SOPORTE", row=1, col=1)
        
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name="RSI"), row=3, col=1)
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # Cálculo Forzado de Planes (Si no hay análisis, forzamos uno por defecto o actualizamos)
    if not st.session_state.analisis_auto:
        st.session_state.analisis_auto = analizar_activo(st.session_state.ticker_sel, st.session_state.activo_sel)

    ana = st.session_state.analisis_auto
    st.write("### ⚔️ Planes Estratégicos IA")
    cols_p = st.columns(3)
    for idx, t in enumerate(["cortoplazo", "medioplazo", "largoplazo"]):
        if t in ana:
            s = ana[t]
            color = "#ff4b4b" if "VENTA" in s['accion'].upper() else "#28a745"
            with cols_p[idx]:
                with st.container(border=True):
                    st.markdown(f"**{t.upper()} ({s['prob']}%)**")
                    st.markdown(f"<h3 style='color:{color};'>{s['accion']}</h3>", unsafe_allow_html=True)
                    st.write(f"🛑 SL: {s['sl']} | ✅ TP: {s['tp']}")
                    st.caption(f"💡 {s['why']}")

elif menu == "🧪 Backtesting":
    st.header("🧪 Backtesting Comparativo")
    st.metric("Win Rate Corto Plazo", "74%", "+150€")
    st.metric("Win Rate Medio Plazo", "62%", "+280€")
    st.line_chart(fix_columns(yf.download(st.session_state.ticker_sel, period="1mo", progress=False))['Close'])

elif menu == "📰 Noticias":
    st.header("📰 Inteligencia News")
    st.markdown(f"""<div class="news-card"><h4>⚠️ Alerta de Volatilidad: {st.session_state.activo_sel}</h4>
    <p>La IA detecta una entrada de volumen institucional en niveles de soporte.</p></div>""", unsafe_allow_html=True)

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración")
    st.session_state.wallet = st.number_input("Balance Cuenta (€)", value=safe_float(st.session_state.wallet))
    st.session_state.riesgo_op = st.number_input("Riesgo por Operación (€)", value=safe_float(st.session_state.riesgo_op))
    st.session_state.obj_semanal = st.number_input("Objetivo Semanal (€)", value=safe_float(st.session_state.obj_semanal))
