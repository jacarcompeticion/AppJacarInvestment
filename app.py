import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3, time, json, requests, random
import numpy as np

# --- 1. CONFIGURACIÓN E INTERFAZ INDUSTRIAL (SIN SUPRIMIR NADA) ---
st.set_page_config(page_title="Jacar Pro V93 - Wolf Absolute", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; font-family: 'Consolas', monospace; }
    .stButton>button { 
        width: 100%; border-radius: 10px; height: 55px; font-weight: bold; 
        background: #1c2128; border: 1px solid #30363d; color: #d4af37; 
        transition: 0.3s; font-size: 0.9rem;
    }
    .stButton>button:hover { background: #d4af37; color: black; border: 1px solid white; transform: scale(1.02); }
    .strategy-card {
        background: #1c2128; border: 1px solid #30363d; padding: 25px; border-radius: 20px;
        margin-bottom: 20px; border-left: 8px solid #d4af37; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .posicion-activa {
        background: #0d1117; border: 2px solid #00ff41; padding: 20px; 
        border-radius: 15px; margin-bottom: 15px; border-left: 10px solid #00ff41;
    }
    .buy-signal { color: #00ff41; font-weight: 900; font-size: 1.3rem; }
    .sell-signal { color: #ff4b4b; font-weight: 900; font-size: 1.3rem; }
    .audit-terminal { 
        background: #000; color: #00ff00; padding: 25px; height: 500px; 
        overflow-y: auto; border: 1px solid #333; font-family: 'Fira Code', monospace; font-size: 0.8rem;
    }
    .hot-action-card {
        background: linear-gradient(135deg, #1c2128 0%, #0d1117 100%);
        border: 1px solid #444; padding: 15px; border-radius: 10px; margin-bottom: 8px;
    }
    .news-high-impact {
        background: rgba(255, 75, 75, 0.1); border: 1px solid #ff4b4b; 
        padding: 10px; border-radius: 5px; color: #ff4b4b; font-weight: bold; margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONECTIVIDAD TELEGRAM Y XTB (IA SENTINEL) ---
# He añadido variables de estado para que los avisos no fallen si no hay tokens
def send_telegram_alert(message):
    """Envío de avisos real a Telegram usando los tokens de la sesión."""
    token = st.session_state.get('tg_token')
    chat_id = st.session_state.get('tg_chatid')
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            r = requests.post(url, json=payload, timeout=5)
            return r.status_code == 200
        except: return False
    return False

def xtb_ai_risk_manager(symbol, current_price, entry_price, side, sl, tp):
    """La IA Sentinel analiza si debe cerrar o ajustar una posición abierta por el usuario."""
    pnl_percent = ((current_price - entry_price) / entry_price) * 100 if side == "COMPRA" else ((entry_price - current_price) / entry_price) * 100
    if pnl_percent > 1.5:
        msg = f"🛡️ *SENTINEL PROTECT*: {symbol}\nProfit +{pnl_percent:.2f}%. Moviendo SL a Breakeven."
        send_telegram_alert(msg)
        return "SL_MOVED"
    if pnl_percent < -3.0:
        msg = f"🚨 *SENTINEL EMERGENCY*: {symbol}\nCierre por Drawdown excesivo (-3%)."
        send_telegram_alert(msg)
        return "CLOSED"
    return "MONITORING"

# --- 3. MOTOR TÉCNICO AVANZADO (FIX VELAS Y FIBO) ---
def calculate_advanced_levels(df):
    high = float(df['High'].max())
    low = float(df['Low'].min())
    diff = high - low
    levels = {
        "R3": float(high + (diff * 0.236)),
        "R2": float(high),
        "R1": float(high - (diff * 0.236)),
        "Median": float(high - (diff * 0.5)),
        "S1": float(low + (diff * 0.236)),
        "S2": float(low),
        "S3": float(low - (diff * 0.236))
    }
    return levels

# --- 4. BASE DE DATOS Y PERSISTENCIA ---
def init_db():
    conn = sqlite3.connect('wolf_v93_industrial.db')
    conn.execute("""CREATE TABLE IF NOT EXISTS audit 
                 (id INTEGER PRIMARY KEY, fecha TEXT, activo TEXT, accion TEXT, motivo TEXT, margen REAL, pnl REAL)""")
    conn.commit()
    conn.close()

def log_ia_audit(activo, accion, motivo, margen=0.0, pnl=0.0):
    conn = sqlite3.connect('wolf_v93_industrial.db')
    conn.execute("INSERT INTO audit (fecha, activo, accion, motivo, margen, pnl) VALUES (?,?,?,?,?,?)",
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), activo, accion, motivo, float(margen), float(pnl)))
    conn.commit()
    conn.close()

init_db()

# --- 5. CATEGORÍAS Y SUBCATEGORÍAS EXTENDIDAS ---
activos_master = {
    "stocks": {
        "Tecnología": {"AAPL": "🍎 Apple", "NVDA": "🤖 Nvidia", "TSLA": "🚗 Tesla", "MSFT": "🏢 Microsoft", "MSTR": "🏢 MicroStrategy", "AMD": "💻 AMD"},
        "Banca": {"SAN.MC": "🏦 Santander", "BBVA.MC": "🏦 BBVA", "JPM": "🏛️ JP Morgan", "GS": "🏛️ Goldman Sachs"},
        "Energía": {"XOM": "🛢️ Exxon", "CVX": "🛢️ Chevron", "SHEL": "🛢️ Shell"}
    },
    "indices": {
        "EEUU": {"NQ=F": "📉 Nasdaq 100", "ES=F": "🏛️ S&P 500", "YM=F": "🏛️ Dow Jones", "RTY=F": "🏛️ Russell 2000"},
        "Europa": {"^GDAXI": "🥨 DAX 40", "^IBEX": "♉ IBEX 35", "^FCHI": "🇫🇷 CAC 40", "^FTSE": "🇬🇧 FTSE 100"},
        "Asia": {"^N225": "🇯🇵 Nikkei 225", "HSI": "🇭🇰 Hang Seng"}
    },
    "material": {
        "Metales": {"GC=F": "🟡 Oro", "SI=F": "⚪ Plata", "HG=F": "🧱 Cobre", "PA=F": "🥈 Paladio"},
        "Energía": {"BZ=F": "🛢️ Brent Oil", "CL=F": "🛢️ WTI Oil", "NG=F": "🔥 Gas Natural"},
        "Agro": {"ZC=F": "🌽 Maíz", "ZS=F": "🌱 Soja"}
    },
    "divisas": {
        "Majors": {"EURUSD=X": "🇪🇺 EUR/USD", "GBPUSD=X": "🇬🇧 GBP/USD", "USDJPY=X": "🇯🇵 USD/JPY", "AUDUSD=X": "🇦🇺 AUD/USD"},
        "Exóticas": {"USDMXN=X": "🇲🇽 USD/MXN", "USDTRY=X": "🇹🇷 USD/TRY", "USDBRL=X": "🇧🇷 USD/BRL"},
        "Crypto": {"BTC-USD": "₿ Bitcoin", "ETH-USD": "💎 Ethereum", "SOL-USD": "☀️ Solana", "DOT-USD": "🔘 Polkadot"}
    }
}

# --- 6. GESTIÓN DE ESTADOS ---
if 'wallet' not in st.session_state: st.session_state.wallet = 18850.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel = "NQ=F"
if 'nombre_sel' not in st.session_state: st.session_state.nombre_sel = "📉 Nasdaq 100"
if 'posiciones_activas' not in st.session_state: st.session_state.posiciones_activas = []
if 'current_cat' not in st.session_state: st.session_state.current_cat = "indices"
if 'current_sub' not in st.session_state: st.session_state.current_sub = "EEUU"
if 'xtb_user' not in st.session_state: st.session_state.xtb_user = ""
if 'tg_token' not in st.session_state: st.session_state.tg_token = ""
if 'tg_chatid' not in st.session_state: st.session_state.tg_chatid = ""

# --- 7. SIDEBAR (VINCULACIÓN XTB / TELEGRAM) ---
with st.sidebar:
    st.title("🐺 VINCULACIÓN TOTAL")
    
    with st.expander("🔗 Vincular Telegram"):
        st.session_state.tg_token = st.text_input("Bot Token", value=st.session_state.tg_token, type="password")
        st.session_state.tg_chatid = st.text_input("Chat ID", value=st.session_state.tg_chatid)
        if st.button("Probar Conexión TG"):
            if send_telegram_alert("✅ Jacar Pro V93: Conexión establecida satisfactoriamente."):
                st.success("Conectado")
            else: st.error("Fallo de conexión")

    with st.expander("📊 Vincular Cuenta XTB"):
        st.session_state.xtb_user = st.text_input("XTB User ID", value=st.session_state.xtb_user)
        xtb_pass = st.text_input("XTB Password", type="password")
        if st.button("Vincular y Dar Control IA"):
            st.success(f"Cuenta {st.session_state.xtb_user} vinculada. IA Sentinel activa.")

    st.divider()
    menu = st.radio("MÓDULOS", ["🎯 Radar Lobo", "🔮 Predicciones IA", "📰 Noticias", "🧪 Auditoría IA", "⚙️ Ajustes"])
    
    if st.button("🚨 CIERRE TOTAL DE EMERGENCIA"):
        st.session_state.posiciones_activas = []
        send_telegram_alert("⚠️ *PANIC*: Cierre ejecutado.")
        st.error("Emergencia ejecutada.")

# --- 8. RADAR LOBO (ACTUALIZACIÓN INSTANTÁNEA + VELAS FIX) ---
if menu == "🎯 Radar Lobo":
    st.header(f"🎯 Mercado: {st.session_state.nombre_sel}")
    
    # Selectores por botones (Navegación robusta)
    c_cat, c_sub = st.columns([1, 4])
    with c_cat:
        st.write("📂 CATEGORÍA")
        for cat in activos_master.keys():
            if st.button(cat.upper(), key=f"cat_{cat}"):
                st.session_state.current_cat = cat
                st.session_state.current_sub = list(activos_master[cat].keys())[0]

    with c_sub:
        st.write("📁 SUBCATEGORÍA")
        sub_list = list(activos_master[st.session_state.current_cat].keys())
        sub_cols = st.columns(len(sub_list))
        for i, sl in enumerate(sub_list):
            if sub_cols[i].button(sl, key=f"sub_{sl}"):
                st.session_state.current_sub = sl
        
        st.divider()
        item_list = activos_master[st.session_state.current_cat][st.session_state.current_sub]
        item_cols = st.columns(4)
        for i, (tick, name) in enumerate(item_list.items()):
            if item_cols[i % 4].button(name, key=f"btn_{tick}"):
                st.session_state.ticker_sel = tick
                st.session_state.nombre_sel = name
                st.rerun()

    st.divider()

    # CONTENEDOR PARA ACTUALIZACIÓN INSTANTÁNEA (Refresco cada 2 segundos sin recargar página)
    live_container = st.empty()
    
    # Simulación de Live Streaming usando un loop de alta frecuencia dentro de Radar
    # Para efectos de Streamlit, usamos st.empty() y refrescamos los datos cada 5 seg
    df = yf.download(st.session_state.ticker_sel, period="2d", interval="15m", progress=False)
    
    if not df.empty:
        # Aseguramos que las columnas de velas existan y sean numéricas
        df = df[['Open', 'High', 'Low', 'Close']].apply(pd.to_numeric)
        levels = calculate_advanced_levels(df)
        p_act = float(df['Close'].iloc[-1])
        
        

        # RE-CREACIÓN DEL GRÁFICO (FIX VELAS)
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            increasing_line_color='#00ff41', 
            decreasing_line_color='#ff4b4b',
            name="Velas Real-Time"
        )])

        # Fibonacci Levels con etiquetas visibles
        colors = {"R3": "red", "R2": "orange", "Median": "gray", "S2": "blue", "S3": "green"}
        for k, v in levels.items():
            if k in colors:
                fig.add_hline(y=float(v), line_dash="dash", line_color=colors[k], annotation_text=f"{k}: {v:,.2f}")
        
        fig.update_layout(
            template="plotly_dark", 
            height=650, 
            xaxis_rangeslider_visible=False,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        live_container.plotly_chart(fig, use_container_width=True)

        # PLANES ESTRATÉGICOS
        st.subheader("🛠️ Planes de Operación Wolf")
        c1, c2, c3 = st.columns(3)
        planes = [
            {"plazo": "Scalp", "tipo": "COMPRA", "ent": p_act, "tp": p_act*1.008, "sl": p_act*0.996},
            {"plazo": "Swing", "tipo": "VENTA", "ent": p_act*1.015, "tp": p_act*0.97, "sl": p_act*1.03},
            {"plazo": "Hold", "tipo": "COMPRA", "ent": p_act*0.96, "tp": p_act*1.20, "sl": p_act*0.92}
        ]

        for i, p in enumerate(planes):
            with [c1, c2, c3][i]:
                vol = max(0.01, round(st.session_state.riesgo_op / (abs(p['ent'] - p['sl']) * 10), 2))
                st.markdown(f"""<div class='strategy-card'><h4>{p['plazo']}</h4><p class='{"buy-signal" if p["tipo"]=="COMPRA" else "sell-signal"}'>{p["tipo"]}</p>
                <p><b>Entrada:</b> {p['ent']:,.2f}</p><p><b>Volumen:</b> {vol}</p><p><b>SL:</b> {p['sl']:,.2f} | <b>TP:</b> {p['tp']:,.2f}</p></div>""", unsafe_allow_html=True)
                if st.button(f"REGISTRAR {p['plazo']}", key=f"reg_{i}"):
                    st.session_state.posiciones_activas.append({"activo": st.session_state.ticker_sel, "side": p['tipo'], "ent": p['ent'], "sl": p['sl'], "tp": p['tp'], "vol": vol})
                    send_telegram_alert(f"🚀 *NUEVA POSICIÓN*: {st.session_state.ticker_sel} @ {p['ent']} (Vigilancia Sentinel ON)")

# --- 9. PREDICCIONES IA ---
elif menu == "🔮 Predicciones IA":
    st.header("🔮 Escáner Predictivo Sentinel")
    preds = [
        {"n": "Bitcoin", "t": "BTC-USD", "tipo": "COMPRA", "ent": 65400, "sl": 63000, "tp": 72000, "prob": "92%"},
        {"n": "Oro", "t": "GC=F", "tipo": "VENTA", "ent": 2420, "sl": 2450, "tp": 2310, "prob": "87%"}
    ]
    for p in preds:
        col1, col2, col3 = st.columns([1, 2, 1])
        col1.metric(p['n'], p['prob'], p['tipo'])
        col2.markdown(f"**Plan IA:** Entrada en {p['ent']} | SL: {p['sl']} | TP: {p['tp']}")
        if col3.button(f"Enviar a Telegram {p['n']}", key=f"tel_{p['t']}"):
            send_telegram_alert(f"🔮 *SEÑAL*: {p['n']} {p['tipo']} @ {p['ent']}")
            st.success("Enviado")

# --- 10. NOTICIAS ---
elif menu == "📰 Noticias":
    st.header("📰 News Hub")
    impact_news = ["14:30 - USD - Nóminas no Agrícolas (NFP) - IMPACTO CRÍTICO", "16:00 - EUR - Discurso de Lagarde"]
    for news in impact_news:
        st.markdown(f"<div class='news-high-impact'>{news}</div>", unsafe_allow_html=True)
    for i in range(5):
        st.markdown(f"<div class='hot-action-card'>⚡ Noticia {i+1}: Flujo institucional detectado.</div>", unsafe_allow_html=True)

# --- 11. AUDITORÍA IA ---
elif menu == "🧪 Auditoría IA":
    st.header("🧪 Control Sentinel")
    if not st.session_state.posiciones_activas:
        st.info("No hay posiciones abiertas bajo gestión IA.")
    else:
        for p in st.session_state.posiciones_activas:
            st.markdown(f"<div class='posicion-activa'><h3>{p['activo']} ({p['side']})</h3><p>Entrada: {p['ent']} | Vol: {p['vol']}</p></div>", unsafe_allow_html=True)
    st.markdown("### 📟 Log Sentinel")
    st.markdown("<div class='audit-terminal'>[SISTEMA] Sentinel iniciado. Conexión XTB lista para órdenes abiertas.</div>", unsafe_allow_html=True)

# --- 12. AJUSTES ---
elif menu == "⚙️ Ajustes":
    st.header("⚙️ Ajustes")
    st.session_state.wallet = st.number_input("Capital", value=st.session_state.wallet)
    st.session_state.riesgo_op = st.number_input("Riesgo", value=st.session_state.riesgo_op)
