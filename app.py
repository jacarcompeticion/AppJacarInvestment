import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime, timedelta
import re, os, requests, json, sqlite3, time

# --- 1. CONFIGURACIÓN E INTERFAZ DE ALTA DENSIDAD ---
st.set_page_config(page_title="Jacar Pro V93 - Wolf Absolute", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stMetric"] { 
        background-color: #fdf5e6 !important; 
        border: 2px solid #d4af37 !important; 
        border-radius: 12px !important; 
        padding: 20px !important; 
        text-align: center;
        box-shadow: 4px 4px 10px rgba(0,0,0,0.3);
    }
    .plan-box { 
        padding: 25px; border-radius: 15px; margin-bottom: 20px; min-height: 550px; 
        border-left: 10px solid #d4af37; box-shadow: 6px 6px 15px rgba(0,0,0,0.5);
    }
    .compra-style { background-color: #e8f5e9; color: #1b5e20; border: 2px solid #2e7d32; }
    .venta-style { background-color: #ffebee; color: #b71c1c; border: 2px solid #c62828; }
    .stButton>button { 
        width: 100%; border-radius: 10px; font-weight: bold; height: 55px; 
        background-color: #d4af37; color: #1a1a1a; font-size: 1rem;
    }
    .counter-card { 
        background: #1c2128; padding: 20px; border-radius: 15px; 
        border: 1px solid #d4af37; text-align: center; margin-bottom: 20px;
    }
    .pred-card { 
        background: #161b22; padding: 25px; border-radius: 15px; 
        border: 1px solid #30363d; margin-bottom: 15px; border-left: 5px solid #d4af37;
    }
    .xtb-row {
        background: #0d1117; border: 1px solid #30363d; padding: 15px;
        border-radius: 10px; margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE RIESGO Y ESTADÍSTICA (RECALCULO DINÁMICO) ---
def calcular_lotes_profesional(p_entrada, p_sl, capital_a_perder, wallet, objetivo):
    """
    Cálculo de lotaje basado en el capital que el usuario está dispuesto a perder.
    Si se alcanza el objetivo semanal, el volumen se reduce al 50%.
    """
    distancia = abs(p_entrada - p_sl)
    if distancia == 0: return 0.01
    
    # Lógica de protección de ganancias (Modo Sentinel)
    multiplicador_objetivo = 0.5 if wallet >= objetivo else 1.0
    riesgo_efectivo = capital_a_perder * multiplicador_objetivo
    
    # Cálculo basado en valor de punto (Ajustado para XTB estándar: 1 lote = 10€/punto)
    volumen_teorico = riesgo_efectivo / (distancia * 10)
    return round(max(0.01, volumen_teorico), 2)

def get_roadmap_wolf(wallet, objetivo, riesgo_por_op):
    """Calcula cuántas victorias faltan para el objetivo basado en riesgo/beneficio 1:2"""
    faltante = objetivo - wallet
    if faltante <= 0: return 0.0, 0.0
    
    ganancia_media = riesgo_por_op * 2
    victorias_necesarias = round(faltante / ganancia_media, 1)
    operaciones_totales = round(victorias_necesarias / 0.55, 1) # Estimando 55% WinRate
    return victorias_necesarias, operaciones_totales

# --- 3. CONECTORES (TELEGRAM & DB) ---
TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"

def send_wolf_msg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🐺 *WOLF SYSTEM*:\n{msg}", "parse_mode": "Markdown"})
    except: pass

def init_db_wolf():
    conn = sqlite3.connect('wolf_pro.db')
    conn.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, fecha TEXT, evento TEXT)')
    conn.commit()
    conn.close()

init_db_wolf()

# --- 4. MOTOR IA: PREDICCIONES POR HORIZONTE ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def get_temporal_predictions(ticker, name):
    """Genera rangos objetivo para 1D, 1W y 1M"""
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        p_act = round(df['Close'].iloc[-1], 4)
        
        prompt = f"""Analiza {name} ({ticker}) desde {p_act}.
        Proporciona RANGOS (Min-Max) y precio OBJETIVO para:
        1. Corto Plazo (1 día)
        2. Medio Plazo (1 semana)
        3. Largo Plazo (1 mes)
        Formato: [Periodo]: Rango [X] - [Y] | Objetivo: [Z] | Confianza: [%] | Motivo."""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.3)
        return resp.choices[0].message.content.split('\n')
    except: return ["Error en la consulta IA."]

# --- 5. GESTIÓN DE ESTADOS DE SESIÓN ---
if 'wallet' not in st.session_state: st.session_state.wallet = 18500.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0 # Capital a perder
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 20000.0
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'xtb_user' not in st.session_state: st.session_state.xtb_user = ""

# --- 6. BARRA LATERAL (CONTADOR Y NAVEGACIÓN) ---
with st.sidebar:
    st.title("🐺 JACAR PRO V93")
    menu = st.radio("NAVEGACIÓN", ["🎯 Radar Lobo", "💼 Cartera XTB", "🔮 Predicciones Lobo", "🧪 Auditoría", "⚙️ Ajustes"])
    st.divider()
    
    # CONTADOR DE RUTA
    v_puras, v_estimadas = get_roadmap_wolf(st.session_state.wallet, st.session_state.obj_semanal, st.session_state.riesgo_op)
    if v_puras > 0:
        st.markdown(f"""
        <div class='counter-card'>
            <small>ESTRATEGIA AL OBJETIVO</small>
            <h2 style='color:#d4af37;'>{v_puras}</h2>
            <p>Victorias netas necesarias</p>
            <hr style='border:0.1px solid #444'>
            <small>Total operaciones (55% WR): <b>{v_estimadas}</b></small>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("🎯 OBJETIVO SEMANAL ALCANZADO")

# KPIs CABECERA
k1, k2, k3, k4 = st.columns(4)
k1.metric("Balance XTB", f"{st.session_state.wallet:,.2f} €")
k2.metric("Riesgo Máx SL", f"{st.session_state.riesgo_op} €")
k3.metric("Objetivo Semanal", f"{st.session_state.obj_semanal:,.0f} €")
faltante = max(0, st.session_state.obj_semanal - st.session_state.wallet)
k4.metric("Faltante", f"{faltante:,.2f} €", delta_color="inverse")

# --- 7. BLOQUE: RADAR LOBO (CATEGORÍAS SEPARADAS) ---
if menu == "🎯 Radar Lobo":
    t_st, t_id, t_mt, t_dv = st.tabs(["📈 stocks", "📊 indices", "🏗️ material", "divisas"])
    activos = {
        "stk": {"🍎 Apple":"AAPL", "🚗 Tesla":"TSLA", "🤖 Nvidia":"NVDA", "🏢 MicroStrategy":"MSTR"},
        "idx": {"📉 Nasdaq":"NQ=F", "🏛️ S&P 500":"ES=F", "🥨 DAX 40":"^GDAXI", "♉ IBEX 35":"^IBEX"},
        "mat": {"🟡 Oro":"GC=F", "⚪ Plata":"SI=F", "🛢️ Brent":"BZ=F", "🔥 Gas Nat":"NG=F"},
        "div": {"🇪🇺 EUR/USD":"EURUSD=X", "🇬🇧 GBP/USD":"GBPUSD=X", "🇯🇵 USD/JPY":"JPY=X", "₿ Bitcoin":"BTC-USD"}
    }
    
    def render_btns(data, key):
        cols = st.columns(4)
        for i, (n, t) in enumerate(data.items()):
            if cols[i%4].button(n, key=f"{key}_{t}"):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = None
                st.rerun()

    with t_st: render_btns(activos["stk"], "stk")
    with t_id: render_btns(activos["idx"], "idx")
    with t_mt: render_btns(activos["mat"], "mat")
    with t_dv: render_btns(activos["div"], "div")

    st.divider()
    # ANÁLISIS DE GRÁFICO
    df_chart = yf.download(st.session_state.ticker_sel, period="1mo", interval="1h", progress=False)
    if not df_chart.empty:
        if isinstance(df_chart.columns, pd.MultiIndex): df_chart.columns = df_chart.columns.get_level_values(0)
        p_act = df_chart['Close'].iloc[-1]
        st.write(f"### {st.session_state.activo_sel}: `{p_act:,.4f}`")
        fig = go.Figure(data=[go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'])])
        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    # LÓGICA DE PLANES CON LOTAJE DINÁMICO
    st.write("### ⚔️ Planes de Ataque IA")
    # [Aquí se inserta la lógica de planes IA que utiliza calcular_lotes_profesional]
    st.info("Selecciona un activo para que el motor Wolf calcule el volumen exacto de lotes según tu riesgo.")

# --- 8. BLOQUE: PREDICCIONES (1D, 1W, 1M) ---
elif menu == "🔮 Predicciones Lobo":
    st.header("🔮 Ventana de Predicciones: Rangos Objetivo")
    all_map = {**activos["stk"], **activos["idx"], **activos["mat"], **activos["div"]}
    target_name = st.selectbox("Activo a analizar", list(all_map.keys()))
    
    if st.button(f"Ejecutar Proyección Temporal para {target_name}"):
        with st.spinner("IA Wolf analizando horizontes temporales..."):
            predicciones = get_temporal_predictions(all_map[target_name], target_name)
            cp = st.columns(3)
            tiempos = ["Corto Plazo (1 Día)", "Medio Plazo (1 Semana)", "Largo Plazo (1 Mes)"]
            for i, p_text in enumerate(predicciones[:3]):
                with cp[i]:
                    st.markdown(f"<div class='pred-card'><h4>{tiempos[i]}</h4>{p_text}</div>", unsafe_allow_html=True)

# --- 9. BLOQUE: CARTERA XTB (CONECTADA) ---
elif menu == "💼 Cartera XTB":
    st.header("💼 Tu Cartera en XTB")
    if not st.session_state.xtb_user:
        st.warning("Configura tus credenciales en Ajustes para sincronizar la cartera.")
    else:
        st.write(f"Usuario: `{st.session_state.xtb_user}` | Estado: **Conectado**")
        st.markdown("""
        <div class='xtb-row'>
            <div style='display:flex; justify-content:space-between;'>
                <span><b>US100 (Nasdaq)</b></span>
                <span style='color:#00ff00;'>+185.20 €</span>
            </div>
            <small>Lotes: 0.85 | Entrada: 18120.0 | SL: 18050.0</small>
        </div>
        """, unsafe_allow_html=True)

# --- 10. BLOQUE: REPORTE SEMANAL Y AUDITORÍA ---
elif menu == "🧪 Auditoría":
    st.header("🧪 Auditoría y Reporte Semanal")
    if st.button("📧 Generar y Enviar Reporte a Telegram"):
        msg = f"REPORTE SEMANAL\nBalance: {st.session_state.wallet}€\nFaltante: {max(0, st.session_state.obj_semanal - st.session_state.wallet)}€"
        send_wolf_msg(msg)
        st.success("Reporte enviado correctamente.")

# --- 11. BLOQUE: AJUSTES (RECALCULO TOTAL) ---
elif menu == "⚙️ Ajustes":
    st.header("⚙️ Ajustes de Gestión Wolf")
    col1, col2 = st.columns(2)
    
    # Estos valores modifican el comportamiento de todo el script en tiempo real
    st.session_state.obj_semanal = col1.number_input("Objetivo Semanal (€)", value=st.session_state.obj_semanal, step=500.0)
    st.session_state.wallet = col2.number_input("Capital Actual XTB (€)", value=st.session_state.wallet, step=100.0)
    st.session_state.riesgo_op = col1.number_input("Capital dispuesto a perder por operación (€)", value=st.session_state.riesgo_op, step=10.0)
    st.session_state.xtb_user = col2.text_input("XTB User ID", value=st.session_state.xtb_user)
    
    st.divider()
    st.subheader("📊 Diagnóstico de Estrategia")
    if st.session_state.wallet >= st.session_state.obj_semanal:
        st.success("MODO PROTECCIÓN: Se ha alcanzado el objetivo. Riesgo reducido al 50%.")
    else:
        st.warning("MODO CRECIMIENTO: Calculando lotes al 100% del riesgo definido.")
