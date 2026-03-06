import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re, os, requests, json, time

# Intentar importar websocket de forma segura para evitar el crash
try:
    import websocket
except ImportError:
    os.system('pip install websocket-client')
    import websocket

# --- 1. CONFIGURACIÓN DE ÉLITE Y ESTILOS ---
st.set_page_config(page_title="Jacar Pro V93 - Wolf Absolute", layout="wide", page_icon="🐺")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"

# Persistencia de Estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None
if 'posiciones_activas' not in st.session_state: st.session_state.posiciones_activas = []
if 'auditoria_log' not in st.session_state: st.session_state.auditoria_log = []
if 'sentimiento_global' not in st.session_state: st.session_state.sentimiento_global = "Analizando..."

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background-color: #fdf5e6 !important; border: 2px solid #d4af37 !important; border-radius: 12px !important; padding: 15px !important; }
    .plan-box { border: 2px solid #d4af37; padding: 25px; border-radius: 15px; background-color: #fdf5e6; color: #5d4037; margin-bottom: 20px; min-height: 480px; box-shadow: 5px 5px 20px rgba(0,0,0,0.6); border-left: 10px solid #d4af37; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 55px; background-color: #d4af37; color: #1a1a1a; font-size: 1.1rem; }
    .news-card { background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; border-left: 6px solid #d4af37; margin-bottom: 15px; }
    .sentiment-bar { padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; border: 1px solid #d4af37; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONECTORES Y AUDITORÍA ---

def notify_wolf(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🐺 *WOLF V93*:\n{msg}", "parse_mode": "Markdown"})
    except: pass

def registrar_auditoria(evento, detalle):
    log_entry = {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "evento": evento, "detalle": detalle}
    st.session_state.auditoria_log.append(log_entry)

# --- 3. MÓDULO DE SENTIMIENTO GLOBAL (NUEVO) ---

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def escanear_sentimiento_mercado():
    """Analiza titulares macro para determinar el sesgo del día"""
    try:
        # En una versión Pro, aquí se inyectarían noticias reales vía API
        contexto_noticias = "FED mantiene tipos, tensiones en Oriente Medio, Nvidia reporta beneficios récord."
        prompt = f"Basado en: {contexto_noticias}. Define sentimiento: ALCISTA, BAJISTA o NEUTRAL. 1 frase de por qué."
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        st.session_state.sentimiento_global = resp.choices[0].message.content
    except:
        st.session_state.sentimiento_global = "Neutral: Sin datos macro claros."

# --- 4. CEREBRO DE GESTIÓN DINÁMICA ---

def wolf_ai_manager():
    if not st.session_state.posiciones_activas: return
    
    for pos in st.session_state.posiciones_activas:
        df = yf.download(pos['ticker'], period="1d", interval="1m", progress=False)
        if df.empty: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        precio_act = df['Close'].iloc[-1]
        distancia_total = abs(pos['tp'] - pos['entrada'])
        recorrido = abs(precio_act - pos['entrada'])

        # Lógica Break Even (BE)
        if pos['estado'] == "OPEN" and recorrido >= (distancia_total * 0.45):
            pos['sl'] = pos['entrada']
            pos['estado'] = "BREAK_EVEN"
            registrar_auditoria("BREAK EVEN", f"{pos['activo']} protegido en entrada.")
            notify_wolf(f"🛡️ *BE ACTIVADO*: {pos['activo']} ya no tiene riesgo.")

        # Lógica Trailing IA
        if pos['estado'] in ["BREAK_EVEN", "TRAILING"]:
            trail_dist = distancia_total * 0.25
            if pos['tipo'] == "COMPRA" and (precio_act - trail_dist) > pos['sl']:
                pos['sl'] = round(precio_act - trail_dist, 4)
                pos['estado'] = "TRAILING"
                registrar_auditoria("TRAILING", f"Subiendo SL de {pos['activo']} a {pos['sl']}")
            elif pos['tipo'] == "VENTA" and (precio_act + trail_dist) < pos['sl']:
                pos['sl'] = round(precio_act + trail_dist, 4)
                pos['estado'] = "TRAILING"

# --- 5. INTERFAZ MAESTRA ---

with st.sidebar:
    st.title("WOLF V93 PRO")
    if st.button("🔄 Refrescar Sentimiento Macro"):
        escanear_sentimiento_mercado()
    st.markdown(f"<div class='sentiment-bar'>{st.session_state.sentimiento_global}</div>", unsafe_allow_html=True)
    menu = st.sidebar.radio("MENÚ", ["🎯 Radar Lobo", "💼 Gestión XTB", "🔮 Predicción", "🧪 Backtesting", "📜 Auditoría", "⚙️ Ajustes"])

if menu == "🎯 Radar Lobo":
    # KPIs
    st.columns(3)[0].metric("Capital", f"{st.session_state.wallet:,.2f} €")
    st.columns(3)[1].metric("Riesgo Fijo", f"{st.session_state.riesgo_op} €")
    st.columns(3)[2].metric("Activo", st.session_state.activo_sel)

    # CATEGORÍAS INDEPENDIENTES
    t_st, t_id, t_mt, t_dv = st.tabs(["📈 stocks", "📊 indices", "🏗️ material", "divisas"])
    
    def grid_render(data, key):
        cols = st.columns(4)
        for i, (n, t) in enumerate(data.items()):
            if cols[i % 4].button(n, key=f"{key}_{t}"):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = None # Forzar nuevo análisis
                st.rerun()

    with t_st: grid_render({"Nvidia":"NVDA", "Tesla":"TSLA", "Apple":"AAPL", "MSTR":"MSTR", "Inditex":"ITX.MC", "Santander":"SAN.MC"}, "stk")
    with t_id: grid_render({"Nasdaq":"NQ=F", "S&P 500":"ES=F", "DAX 40":"^GDAXI", "IBEX 35":"^IBEX"}, "idx")
    with t_mt: grid_render({"Oro":"GC=F", "Plata":"SI=F", "Brent":"BZ=F", "Gas Nat":"NG=F"}, "mat")
    with t_dv: grid_render({"EUR/USD":"EURUSD=X", "GBP/USD":"GBPUSD=X", "Bitcoin":"BTC-USD", "Ethereum":"ETH-USD"}, "div")

    # GRÁFICO TÉCNICO
    st.divider()
    df = yf.download(st.session_state.ticker_sel, period="1mo", interval="1h", progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen"), row=2, col=1)
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # PLANES ESTRATÉGICOS
    st.write("### ⚔️ Inteligencia de Combate Wolf")
    if st.session_state.analisis_auto is None:
        with st.spinner("Analizando activo y contexto global..."):
            # Aquí iría la función generar_estrategia_ia (mantenida del paso anterior)
            p_act = round(df['Close'].iloc[-1], 4)
            prompt = f"Analiza {st.session_state.activo_sel} a {p_act}. Dame 3 planes: CORTO, MEDIO, LARGO. Formato: TAG: [Prob]% | [COMPRA/VENTA] | [SL] | [TP] | [MOTIVO]."
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.2)
            raw = resp.choices[0].message.content.split('\n')
            
            res = {"p_act": p_act}
            for tag in ["CORTO", "MEDIO", "LARGO"]:
                for l in raw:
                    if tag in l.upper() and '|' in l:
                        p = [i.strip() for i in l.split('|')]
                        sl = float(re.sub(r'[^\d.]','',p[2]))
                        tp = float(re.sub(r'[^\d.]','',p[3]))
                        dist = abs(p_act - sl)
                        vol = round(st.session_state.riesgo_op / (dist * 10) if dist > 0 else 0.1, 2)
                        res[tag.lower()] = {"prob": p[0], "accion": p[1], "sl": sl, "tp": tp, "vol": vol, "why": p[4]}
            st.session_state.analisis_auto = res

    ana = st.session_state.analisis_auto
    if ana:
        cols = st.columns(3)
        for i, tag in enumerate(["corto", "medio", "largo"]):
            if tag in ana:
                s = ana[tag]
                with cols[i]:
                    st.markdown(f"""<div class="plan-box">
                        <h3>{tag.upper()}</h3>
                        <p style='color:#2e7d32; font-size:1.2rem;'><b>{s['accion']} ({s['prob']})</b></p>
                        <hr>
                        <b>Entrada: {ana['p_act']}</b><br>
                        <b>Lotes: {s['vol']}</b><br><br>
                        🛑 SL: {s['sl']} | ✅ TP: {s['tp']}
                        <p style='margin-top:20px; font-size:0.85rem;'>{s['why']}</p>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 EJECUTAR {tag.upper()}", key=f"ex_{tag}"):
                        new_pos = {"activo": st.session_state.activo_sel, "ticker": st.session_state.ticker_sel, "entrada": ana['p_act'], "tipo": "COMPRA" if "COMPRA" in s['accion'] else "VENTA", "sl": s['sl'], "tp": s['tp'], "estado": "OPEN"}
                        st.session_state.posiciones_activas.append(new_pos)
                        notify_wolf(f"🚀 *ORDEN ABIERTA*\nActivo: {new_pos['activo']}\nTipo: {new_pos['tipo']}\nPrecio: {new_pos['entrada']}")
                        registrar_auditoria("ORDEN ABIERTA", f"Ejecutado plan de {tag} en {new_pos['activo']}")
                        st.success("Orden en XTB (Sim) y Telegram.")

elif menu == "💼 Gestión XTB":
    st.header("💼 Gestión de Riesgo en Vivo")
    wolf_ai_manager()
    if not st.session_state.posiciones_activas:
        st.info("No hay posiciones para gestionar.")
    else:
        for p in st.session_state.posiciones_activas:
            st.write(f"**{p['activo']}** | Estado: {p['estado']} | SL: {p['sl']} | TP: {p['tp']}")

elif menu == "📜 Auditoría":
    st.header("📜 Bitácora de Operaciones")
    if st.session_state.auditoria_log:
        st.table(pd.DataFrame(st.session_state.auditoria_log))
    else: st.info("Bitácora vacía.")

elif menu == "⚙️ Ajustes":
    st.header("⚙️ Ajustes del Sistema")
    st.session_state.wallet = st.number_input("Balance", value=st.session_state.wallet)
    st.session_state.riesgo_op = st.number_input("Riesgo", value=st.session_state.riesgo_op)
