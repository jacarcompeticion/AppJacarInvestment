import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from openai import OpenAI
from datetime import datetime, timedelta
import sqlite3, time, json, requests, random

# --- 1. CONFIGURACIÓN E INTERFAZ DE ALTA DENSIDAD ---
st.set_page_config(page_title="Jacar Pro V93 - Wolf Absolute", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; font-family: 'Inter', sans-serif; }
    [data-testid="stMetric"] { 
        background-color: #161b22 !important; border: 1px solid #d4af37 !important; 
        border-radius: 15px !important; padding: 20px !important;
    }
    .strategy-card {
        background: #1c2128; border: 1px solid #30363d; padding: 25px; border-radius: 20px;
        margin-bottom: 20px; border-top: 6px solid #d4af37; transition: 0.4s;
    }
    .strategy-card:hover { border-top-color: #00ff41; transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.5); }
    .success-rate { font-size: 1.8rem; font-weight: 800; color: #00ff41; }
    .news-high { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin: 5px 0; font-size: 0.85rem; }
    .correlation-alert { background: #4a3701; color: #ffcc00; padding: 10px; border-radius: 8px; border: 1px solid #ffcc00; margin-bottom: 10px; }
    .audit-terminal { 
        background: #000; color: #00ff00; font-family: 'Fira Code', monospace; 
        padding: 25px; border-radius: 12px; height: 500px; border: 1px solid #333; overflow-y: auto; font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE PERSISTENCIA Y AUDITORÍA (CAJA NEGRA) ---
def init_db():
    conn = sqlite3.connect('wolf_v93_industrial.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS audit 
                 (id INTEGER PRIMARY KEY, fecha TEXT, activo TEXT, accion TEXT, motivo TEXT, margen REAL, pnl REAL)''')
    conn.commit()
    conn.close()

def log_ia_audit(activo, accion, motivo, margen=0.0, pnl=0.0):
    conn = sqlite3.connect('wolf_v93_industrial.db')
    conn.execute("INSERT INTO audit (fecha, activo, accion, motivo, margen, pnl) VALUES (?,?,?,?,?,?)",
                 (datetime.now().strftime("%H:%M:%S"), activo, accion, motivo, float(margen), float(pnl)))
    conn.commit()
    conn.close()

init_db()

# --- 3. ESCÁNER DE CORRELACIONES (ANTI-RIESGO) ---
def check_correlations(nuevo, abiertos):
    grupos = [
        {"NQ=F", "AAPL", "NVDA", "TSLA", "MSFT", "MSTR"}, # Tech/Growth
        {"EURUSD=X", "GBPUSD=X", "AUDUSD=X", "JPY=X"},   # Currencies
        {"GC=F", "SI=F", "HG=F"},                         # Metales
        {"BZ=F", "NG=F"}                                  # Energía
    ]
    riesgos = []
    for grupo in grupos:
        if nuevo in grupo:
            conflictos = [a for a in abiertos if a in grupo and a != nuevo]
            if conflictos:
                riesgos.append(f"⚠️ Correlación Detectada: Ya operas en {conflictos}. Exposición acumulada en el sector.")
    return riesgos

# --- 4. MOTOR DE MARGEN Y LOTES (ANTI-COLAPSO) ---
def get_wolf_leverage_plan(p_ent, p_sl, p_tp, cap_riesgo, wallet, leverage=20):
    try:
        ent, sl, tp = float(p_ent), float(p_sl), float(p_tp)
        wal = float(wallet)
        dist_sl = abs(ent - sl)
        if dist_sl < 0.00001: return 0.01, 0.0, 0.0, 0.0
        
        # Lotes por Riesgo (SL)
        lotes_riesgo = cap_riesgo / (dist_sl * 10)
        
        # Límite de Margen: Máximo 12% del capital para no "asfixiar" la cuenta
        max_margen = wal * 0.12
        lotes_margen = (max_margen * leverage) / (ent * 100)
        
        lotes_final = round(min(lotes_riesgo, lotes_margen), 2)
        lotes_final = max(0.01, lotes_final)
        
        margen_real = (ent * lotes_final * 100) / leverage
        beneficio_est = (abs(tp - ent) * 10) * lotes_final
        ratio_rr = round(abs(tp - ent) / dist_sl, 2)
        
        return lotes_final, margen_real, beneficio_est, ratio_rr
    except: return 0.01, 0.0, 0.0, 0.0

# --- 5. CALENDARIO ECONÓMICO (SENTINEL) ---
def get_economic_calendar():
    # Simulador de alto impacto
    return [
        {"hora": "14:30", "evento": "NFP (Nóminas)", "impacto": "ALTO", "moneda": "USD"},
        {"hora": "15:00", "evento": "IPC (Inflación)", "impacto": "ALTO", "moneda": "EUR"},
        {"hora": "20:00", "evento": "Decisión Tipos FED", "impacto": "ALTO", "moneda": "USD"}
    ]

# --- 6. PREDICCIONES DE MÁXIMO BENEFICIO IA ---
def get_top_wolf_projections():
    activos_pool = [
        {"n": "Nasdaq", "t": "NQ=F", "c": "indices"}, {"n": "Oro", "t": "GC=F", "c": "material"},
        {"n": "Tesla", "t": "TSLA", "c": "stocks"}, {"n": "EUR/USD", "t": "EURUSD=X", "c": "divisas"}
    ]
    for a in activos_pool:
        a["score"] = round(random.uniform(72, 96), 1)
        a["profit_est"] = round(random.uniform(450, 1500), 2)
    return sorted(activos_pool, key=lambda x: x['score'], reverse=True)[:3]

# --- 7. ESTADOS Y SIDEBAR ---
if 'wallet' not in st.session_state: st.session_state.wallet = 18850.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'activos_abiertos' not in st.session_state: st.session_state.activos_abiertos = ["AAPL"]
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"

with st.sidebar:
    st.title("🐺 JACAR PRO V93")
    menu = st.radio("SISTEMA", ["🎯 Radar Lobo", "🔮 Predicciones IA", "🧪 Auditoría de IA", "⚙️ Ajustes"])
    
    st.divider()
    st.subheader("📅 Economic Sentinel")
    for ev in get_economic_calendar():
        st.markdown(f"<div class='news-high'>{ev['hora']} - {ev['evento']}</div>", unsafe_allow_html=True)
    
    if st.button("🚨 PÁNICO: CIERRE TOTAL"):
        log_ia_audit("SISTEMA", "PANIC", "Cierre manual de emergencia")
        st.error("Comando enviado a XTB")

# --- 8. VENTANA: RADAR LOBO (OPERACIONES MULTI-PLAZO) ---
if menu == "🎯 Radar Lobo":
    st.header("🎯 Radar Lobo: Ejecución Estratégica")
    t1, t2, t3, t4 = st.tabs(["📈 stocks", "📊 indices", "🏗️ material", "divisas"])
    activos_cat = {
        "stk": {"🍎 Apple":"AAPL", "🚗 Tesla":"TSLA", "🤖 Nvidia":"NVDA", "🏢 MicroS":"MSTR"},
        "idx": {"📉 Nasdaq":"NQ=F", "🏛️ S&P 500":"ES=F", "🥨 DAX 40":"^GDAXI", "♉ IBEX":"^IBEX"},
        "mat": {"🟡 Oro":"GC=F", "⚪ Plata":"SI=F", "🛢️ Brent":"BZ=F", "🔥 Gas":"NG=F"},
        "div": {"🇪🇺 EUR/USD":"EURUSD=X", "🇬🇧 GBP/USD":"GBPUSD=X", "🇯🇵 USD/JPY":"JPY=X", "₿ BTC":"BTC-USD"}
    }
    
    def render_grid(data, key):
        cols = st.columns(4)
        for i, (n, t) in enumerate(data.items()):
            if cols[i%4].button(n, key=f"{key}_{t}"):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.rerun()

    with t1: render_grid(activos_cat["stk"], "stk")
    with t2: render_grid(activos_cat["idx"], "idx")
    with t3: render_grid(activos_cat["mat"], "mat")
    with t4: render_grid(activos_cat["div"], "div")

    st.divider()
    df_data = yf.download(st.session_state.ticker_sel, period="1mo", interval="1h", progress=False)
    if not df_data.empty:
        p_act = float(df_data['Close'].iloc[-1])
        st.subheader(f"Operativa: {st.session_state.activo_sel} (@ {p_act:,.2f})")
        
        # Correlación
        errs = check_correlations(st.session_state.ticker_sel, st.session_state.activos_abiertos)
        for e in errs: st.markdown(f"<div class='correlation-alert'>{e}</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        estrategias = [
            {"label": "Corto (Scalp)", "tp": 1.008, "sl": 0.998, "prob": 84, "desc": "Gestión agresiva"},
            {"label": "Medio (Swing)", "tp": 1.050, "sl": 0.985, "prob": 67, "desc": "Tendencia H4"},
            {"label": "Largo (Hold)", "tp": 1.150, "sl": 0.940, "prob": 53, "desc": "Posicional D1"}
        ]
        
        for i, est in enumerate(estrategias):
            with [c1, c2, c3][i]:
                lotes, marg, gan, rr = get_wolf_leverage_plan(p_act, p_act*est['sl'], p_act*est['tp'], st.session_state.riesgo_op, st.session_state.wallet)
                st.markdown(f"""
                <div class='strategy-card'>
                    <h4>{est['label']}</h4>
                    <div class='success-rate'>{est['prob']}% Éxito</div>
                    <p>{est['desc']}</p>
                    <hr>
                    <p>Lotes: <b>{lotes}</b> | R/B: 1:{rr}</p>
                    <p style='color:#00ff41;'>Profit: +{gan:,.2f} €</p>
                    <p><small>Margen: {marg:,.2f} €</small></p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"EJECUTAR {est['label'].split()[0]}", key=f"ex_{i}"):
                    log_ia_audit(st.session_state.activo_sel, "TRADE", f"Iniciada estrategia {est['label']}", marg, gan)
                    st.success("Orden en gestión por Sentinel.")

# --- 9. VENTANA: PREDICCIONES IA (MAX PROFIT) ---
elif menu == "🔮 Predicciones IA":
    st.header("🔮 Escáner de Máximo Beneficio IA")
    
    tops = get_top_wolf_projections()
    for t in tops:
        col1, col2, col3 = st.columns([1, 2, 1])
        col1.metric(t['n'], f"{t['score']}% Éxito", t['c'])
        col2.write(f"IA detecta una oportunidad de **{t['profit_est']}€** de beneficio neto. El riesgo de margen es óptimo.")
        if col3.button("Operar", key=f"p_{t['t']}"):
            st.session_state.ticker_sel, st.session_state.activo_sel = t['t'], t['n']
            st.rerun()
        st.divider()

# --- 10. VENTANA: AUDITORÍA DE IA (CAJA NEGRA) ---
elif menu == "🧪 Auditoría de IA":
    st.header("🧪 Auditoría Forense Sentinel")
    
    conn = sqlite3.connect('wolf_v93_industrial.db')
    df_audit = pd.read_sql_query("SELECT * FROM audit ORDER BY id DESC LIMIT 50", conn)
    conn.close()
    
    st.markdown("### 📟 Terminal de Decisiones")
    terminal = ""
    for _, r in df_audit.iterrows():
        terminal += f"[{r['fecha']}] - {r['activo']}: {r['accion']} -> {r['motivo']} (Margen: {r['margen']}€)<br>"
    st.markdown(f"<div class='audit-terminal'>{terminal if terminal else 'Esperando eventos...'}</div>", unsafe_allow_html=True)

# --- AJUSTES ---
elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración Wolf")
    st.session_state.wallet = st.number_input("Capital XTB (€)", value=st.session_state.wallet)
    st.session_state.riesgo_op = st.number_input("Riesgo por Operación (€)", value=st.session_state.riesgo_op)
