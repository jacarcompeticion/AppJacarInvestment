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
    .main { background-color: #0d1117; color: #c9d1d9; font-family: 'Consolas', 'Courier New', monospace; }
    [data-testid="stMetric"] { 
        background-color: #161b22 !important; border: 1px solid #d4af37 !important; 
        border-radius: 15px !important; padding: 20px !important;
    }
    .strategy-card {
        background: #1c2128; border: 1px solid #30363d; padding: 25px; border-radius: 20px;
        margin-bottom: 20px; border-left: 8px solid #d4af37; transition: 0.4s;
    }
    .strategy-card:hover { border-left-color: #00ff41; transform: translateX(10px); background: #21262d; }
    .buy-signal { color: #00ff41; font-weight: bold; font-size: 1.2rem; }
    .sell-signal { color: #ff4b4b; font-weight: bold; font-size: 1.2rem; }
    .hot-action { 
        background: linear-gradient(90deg, #4a0000 0%, #1c2128 100%); 
        padding: 15px; border-radius: 10px; margin: 10px 0; border: 1px solid #ff4b4b; 
    }
    .news-box { background: #161b22; padding: 15px; border-radius: 10px; border-bottom: 2px solid #333; margin-bottom: 10px; }
    .audit-terminal { 
        background: #000; color: #00ff00; font-family: 'Fira Code', monospace; 
        padding: 25px; border-radius: 12px; height: 500px; border: 1px solid #333; overflow-y: auto; font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CREDENCIALES Y CONECTORES (SISTEMA DE CONTROL IA) ---
# Sustituir por credenciales reales en producción
XTB_API_URL = "wss://ws.xtb.com/demo"
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "TU_TOKEN")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "TU_ID")

def send_telegram_alert(message):
    """Envía notificaciones de la IA sobre operaciones y predicciones."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=data)
    except Exception as e:
        st.error(f"Error Telegram: {e}")

def xtb_order_execution(symbol, side, volume, sl, tp):
    """Interfaz para que la IA tome control de la cuenta XTB."""
    # Lógica de envío de paquetes JSON a XTB (Simulado para entorno seguro)
    timestamp = datetime.now().strftime("%H:%M:%S")
    msg = f"🐺 *IA EXECUTION REPORT*\n📌 Activo: {symbol}\n🔑 Acción: {side}\n📊 Vol: {volume}\n🛑 SL: {sl}\n🎯 TP: {tp}\n⏰ Hora: {timestamp}"
    send_telegram_alert(msg)
    log_ia_audit(symbol, side, f"Ejecución Automatizada Vol:{volume}", 0, 0)
    return True

# --- 3. MOTOR DE PERSISTENCIA (SISTEMA DE AUDITORÍA) ---
def init_db():
    conn = sqlite3.connect('wolf_v93_absolute_full.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS audit 
                 (id INTEGER PRIMARY KEY, fecha TEXT, activo TEXT, accion TEXT, motivo TEXT, margen REAL, pnl REAL)''')
    conn.commit()
    conn.close()

def log_ia_audit(activo, accion, motivo, margen=0.0, pnl=0.0):
    conn = sqlite3.connect('wolf_v93_absolute_full.db')
    conn.execute("INSERT INTO audit (fecha, activo, accion, motivo, margen, pnl) VALUES (?,?,?,?,?,?)",
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), activo, accion, motivo, float(margen), float(pnl)))
    conn.commit()
    conn.close()

init_db()

# --- 4. MOTOR DE MARGEN Y CÁLCULO DE LOTES (ANTI-COLAPSO) ---
def get_wolf_leverage_plan(p_ent, p_sl, p_tp, cap_riesgo, wallet, leverage=20):
    """Calcula volumen evitando el colapso de margen de la cuenta."""
    try:
        ent, sl, tp = float(p_ent), float(p_sl), float(p_tp)
        wal = float(wallet)
        dist_sl = abs(ent - sl)
        if dist_sl < 0.00001: return 0.01, 0.0, 0.0, 0.0
        
        # 1. Lotes por Riesgo (SL)
        lotes_riesgo = cap_riesgo / (dist_sl * 10)
        
        # 2. Protección de Margen (Máximo 12% del capital en garantía)
        max_margen = wal * 0.12
        lotes_margen = (max_margen * leverage) / (ent * 100)
        
        lotes_final = round(min(lotes_riesgo, lotes_margen), 2)
        lotes_final = max(0.01, lotes_final)
        
        margen_real = (ent * lotes_final * 100) / leverage
        beneficio_est = (abs(tp - ent) * 10) * lotes_final
        ratio_rr = round(abs(tp - ent) / dist_sl, 2)
        
        return lotes_final, margen_real, beneficio_est, ratio_rr
    except: return 0.01, 0.0, 0.0, 0.0

# --- 5. CATEGORÍAS Y SUBCATEGORÍAS EXTENDIDAS ---
activos_master = {
    "stocks": {
        "Tecnología": {"AAPL": "Apple", "NVDA": "Nvidia", "TSLA": "Tesla", "MSFT": "Microsoft", "MSTR": "MicroStrategy"},
        "Energía": {"XOM": "Exxon", "CVX": "Chevron", "SHEL": "Shell"},
        "Banca": {"JPM": "JP Morgan", "GS": "Goldman Sachs", "SAN.MC": "Santander"}
    },
    "indices": {
        "Americanos": {"NQ=F": "Nasdaq 100", "ES=F": "S&P 500", "YM=F": "Dow Jones 30", "RTY=F": "Russell 2000"},
        "Europeos": {"^GDAXI": "DAX 40", "^IBEX": "IBEX 35", "^FCHI": "CAC 40", "^FTSE": "FTSE 100"},
        "Asiáticos": {"^N225": "Nikkei 225", "HSI": "Hang Seng"}
    },
    "material": {
        "Metales": {"GC=F": "Oro", "SI=F": "Plata", "HG=F": "Cobre", "PA=F": "Paladio"},
        "Energía": {"BZ=F": "Petróleo Brent", "CL=F": "WTI Oil", "NG=F": "Gas Natural"},
        "Agro": {"ZC=F": "Maíz", "ZS=F": "Soja"}
    },
    "divisas": {
        "Majors": {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD"},
        "Exóticas": {"USDMXN=X": "USD/MXN", "USDTRY=X": "USD/TRY"},
        "Crypto": {"BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana"}
    }
}

# --- 6. ESTADOS Y SIDEBAR ---
if 'wallet' not in st.session_state: st.session_state.wallet = 18850.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel = "NQ=F"
if 'activo_nombre' not in st.session_state: st.session_state.activo_nombre = "Nasdaq 100"

with st.sidebar:
    st.title("🐺 JACAR PRO V93")
    menu = st.radio("MENÚ PRINCIPAL", ["🎯 Radar Lobo", "🔮 Predicciones IA", "📰 Noticias", "🧪 Auditoría", "⚙️ Ajustes"])
    
    st.divider()
    st.subheader("🔥 Acciones Calientes")
    # Simulación de escáner en tiempo real
    hot_picks = [("NVDA", "+4.2%", "COMPRA"), ("TSLA", "-2.1%", "VENTA"), ("MSTR", "+6.8%", "COMPRA")]
    for tic, chg, signal in hot_picks:
        st.markdown(f"<div class='hot-action'><b>{tic}</b>: {chg} | <span style='color:#00ff41;'>{signal}</span></div>", unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📅 Calendario Económico")
    st.markdown("<div style='font-size:0.8rem;'>🔴 14:30 - USD NFP<br>🟠 16:00 - EUR Lagarde<br>🔴 20:00 - FOMC</div>", unsafe_allow_html=True)

# --- 7. VENTANA: RADAR LOBO (CONTROL TOTAL) ---
if menu == "🎯 Radar Lobo":
    st.header(f"🎯 Centro de Operaciones: {st.session_state.activo_nombre}")
    
    # Selectores dinámicos
    c1, c2, c3 = st.columns(3)
    with c1: cat = st.selectbox("Categoría", list(activos_master.keys()))
    with c2: sub = st.selectbox("Subcategoría", list(activos_master[cat].keys()))
    with c3: 
        final_asset = st.selectbox("Activo", list(activos_master[cat][sub].keys()))
        st.session_state.ticker_sel = final_asset
        st.session_state.activo_nombre = activos_master[cat][sub][final_asset]

    # Gráfico Profesional
    df = yf.download(st.session_state.ticker_sel, period="5d", interval="15m", progress=False)
    if not df.empty:
        
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        p_act = float(df['Close'].iloc[-1])
        st.subheader("🛠️ Estrategias de Ejecución IA")
        
        c_long, c_mid, c_short = st.columns(3)
        estrategias = [
            {"plazo": "Corto (Scalp)", "tipo": "COMPRA", "tp": 1.008, "sl": 0.998, "prob": 82},
            {"plazo": "Medio (Swing)", "tipo": "VENTA", "tp": 0.980, "sl": 1.015, "prob": 65},
            {"plazo": "Largo (Posición)", "tipo": "COMPRA", "tp": 1.150, "sl": 0.940, "prob": 51}
        ]
        
        cols = [c_short, c_mid, c_long]
        for i, est in enumerate(estrategias):
            with cols[i]:
                tp_val = p_act * est['tp']
                sl_val = p_act * est['sl']
                lotes, marg, gan, rr = get_wolf_leverage_plan(p_act, sl_val, tp_val, st.session_state.riesgo_op, st.session_state.wallet)
                
                st.markdown(f"""
                <div class='strategy-card'>
                    <h4>{est['plazo']}</h4>
                    <p class='{"buy-signal" if est["tipo"]=="COMPRA" else "sell-signal"}'>{est['tipo']} @ {p_act:,.2f}</p>
                    <hr>
                    <p><b>Volumen:</b> {lotes} Lotes</p>
                    <p><b>SL:</b> {sl_val:,.2f}</p>
                    <p><b>TP:</b> {tp_val:,.2f}</p>
                    <p>Profit: +{gan:,.2f}€ | Prob: {est['prob']}%</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"EJECUTAR {est['plazo'].split()[0]}", key=f"btn_{i}"):
                    xtb_order_execution(st.session_state.ticker_sel, est['tipo'], lotes, sl_val, tp_val)
                    st.success(f"IA tomando control de {st.session_state.activo_nombre}")

# --- 8. VENTANA: PREDICCIONES IA (CON ENVÍO A TELEGRAM) ---
elif menu == "🔮 Predicciones IA":
    st.header("🔮 Escáner Predictivo Multi-Plazo")
    
    
    # Simulador de predicción de alto beneficio
    preds = [
        {"n": "Oro", "t": "GC=F", "plazo": "Medio", "tipo": "COMPRA", "prob": "94%", "ent": 2350.0, "sl": 2310.0, "tp": 2450.0, "vol": 0.45},
        {"n": "Bitcoin", "t": "BTC-USD", "plazo": "Largo", "tipo": "COMPRA", "prob": "88%", "ent": 65000.0, "sl": 61000.0, "tp": 85000.0, "vol": 0.10},
        {"n": "EUR/USD", "t": "EURUSD=X", "plazo": "Corto", "tipo": "VENTA", "prob": "79%", "ent": 1.0850, "sl": 1.0920, "tp": 1.0710, "vol": 1.2}
    ]
    
    for p in preds:
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            col1.metric(p['n'], p['prob'], p['plazo'])
            col2.markdown(f"""
            **Plan IA:** {p['tipo']} | Entrada: {p['ent']} | SL: {p['sl']} | TP: {p['tp']}
            **Volumen Sugerido:** {p['vol']} Lotes para proteger margen.
            """)
            if col3.button(f"Enviar Señal {p['n']} a Telegram", key=f"tel_{p['t']}"):
                msg = f"🔮 *SEÑAL IA LOBO*\n📌 {p['n']} ({p['plazo']})\n🔑 {p['tipo']}\n📊 Vol: {p['vol']}\n🛑 SL: {p['sl']}\n🎯 TP: {p['tp']}\n🔥 Éxito: {p['prob']}"
                send_telegram_alert(msg)
                st.info("Señal enviada a tu dispositivo móvil.")
        st.divider()

# --- 9. VENTANA: NOTICIAS ---
elif menu == "📰 Noticias":
    st.header("📰 Economic News Sentinel")
    
    noticias = [
        "EE.UU: El NFP supera expectativas, el Dólar se fortalece.",
        "BCE: Lagarde sugiere que los tipos podrían bajar en Junio.",
        "China: Nuevos estímulos económicos impulsan los índices asiáticos.",
        "OPEP+: Mantendrá los recortes de producción hasta final de año."
    ]
    for n in noticias:
        st.markdown(f"<div class='news-box'>⚡ {n}</div>", unsafe_allow_html=True)

# --- 10. VENTANA: AUDITORÍA (CAJA NEGRA) ---
elif menu == "🧪 Auditoría":
    st.header("🧪 Registro Forense de Decisiones IA")
    
    conn = sqlite3.connect('wolf_v93_absolute_full.db')
    df_audit = pd.read_sql_query("SELECT * FROM audit ORDER BY id DESC LIMIT 100", conn)
    conn.close()
    
    st.markdown("### 📟 Terminal Sentinel V93")
    terminal_output = ""
    for _, row in df_audit.iterrows():
        terminal_output += f"[{row['fecha']}] - {row['activo']}: {row['accion']} -> {row['motivo']}<br>"
    st.markdown(f"<div class='audit-terminal'>{terminal_output if terminal_output else 'Iniciando sistemas...'}</div>", unsafe_allow_html=True)

# --- 11. AJUSTES ---
elif menu == "⚙️ Ajustes":
    st.header("⚙️ Configuración del Sistema")
    st.session_state.wallet = st.number_input("Capital Real XTB (€)", value=st.session_state.wallet)
    st.session_state.riesgo_op = st.number_input("Riesgo Máximo por Operación (€)", value=st.session_state.riesgo_op)
    st.divider()
    st.subheader("🔌 Conexiones")
    st.text_input("XTB User ID", "123456")
    st.text_input("Telegram Token", value=TELEGRAM_TOKEN, type="password")
    st.text_input("Telegram Chat ID", value=TELEGRAM_CHAT_ID)
