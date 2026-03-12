import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
import feedparser
import requests
from streamlit_autorefresh import st_autorefresh
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.foreignexchange import ForeignExchange

# =========================================================
# 0. CONFIGURACIÓN Y MOTOR DE ALERTA
# =========================================================
AV_API_KEY = "3Y17BPSEURVNALDR"

if 'active_trades' not in st.session_state:
    st.session_state.active_trades = []

st_autorefresh(interval=15000, limit=None, key="sentinel_refresh")

TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except: pass

# =========================================================
# 1. ESTILOS WOLF SOVEREIGN (ROBUSTEZ VISUAL)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95 - Precision Mode", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    div.nav-btn button { background-color: #A67B5B !important; color: #000 !important; border-radius: 0px !important; height: 3.5em !important; }
    div.nav-active button { background-color: #FFF !important; color: #000 !important; border: 2px solid #000 !important; font-weight: 900 !important; height: 3.5em !important; }
    div.menu-btn button { background-color: #FFF !important; color: #000 !important; border: 1px solid #333 !important; border-radius: 0px !important; }
    div.menu-active button { background-color: #000 !important; color: #FFF !important; border: 1px solid #FFF !important; font-weight: bold !important; }
    .metric-card { background: #0d1117; padding: 15px; border: 1px solid #333; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 2. BASE DE DATOS Y ESTADO GLOBAL
# =========================================================
if 'setup' not in st.session_state:
    st.session_state.update({
        'view': "Lobo", 'active_cat': "indices", 'active_sub': "EEUU",
        'ticker': "QQQ", 'ticker_name': "US100 (Nasdaq) 🇺🇸",
        'wallet': 18850.00, 'margen': 15200.00, 'pnl': 420.50,
        'objetivo_semanal': 1000.0, 'ganancia_semanal': 0.0,
        'sl_final': 0.0, 'tp_final': 0.0, 'lotes_final': 0.10
    })

DATABASE = {
    "stocks": {
        "TECNOLOGÍA": {
            "APPLE (AAPL.US) 🍎": ["AAPL", ""], "TESLA (TSLA.US) ⚡": ["TSLA", ""], 
            "NVIDIA (NVDA.US) 🟢": ["NVDA", ""], "AMAZON (AMZN.US) 📦": ["AMZN", ""]
        },
        "BANCA": { "SANTANDER (SAN.MC) 🏦": ["SAN.MC", ""], "BBVA (BBVA.MC) 💙": ["BBVA.MC", ""] }
    },
    "indices": {
        "EEUU": { "US100 (Nasdaq) 🇺🇸": ["QQQ", ""], "US500 (S&P500) 🇺🇸": ["SPY", ""], "US30 (Dow Jones) 🇺🇸": ["DIA", ""] },
        "EUROPA": { "DE40 (DAX) 🇩🇪": ["EWG", ""], "SPA35 (IBEX) 🇪🇸": ["EWP", ""] }
    },
    "material": {
        "ENERGÍA": { "OIL.WTI 🛢️": ["USO", ""], "NATGAS 🔥": ["UNG", ""] },
        "METALES": { "GOLD (Oro) 🟡": ["GLD", ""], "SILVER (Plata) ⚪": ["SLV", ""] }
    },
    "divisas": {
        "MAJORS": { "EURUSD 🇪🇺🇺🇸": ["EURUSD", ""], "GBPUSD 🇬🇧🇺🇸": ["GBPUSD", ""], "USDJPY 🇺🇸🇯🇵": ["USDJPY", ""] }
    }
}

# =========================================================
# 3. MOTOR DE DATOS (ALTA PRECISIÓN)
# =========================================================
def get_precise_data(ticker):
    try:
        is_fx = any(x in ticker.upper() for x in ["EUR", "USD", "JPY", "GBP"]) and len(ticker) == 6
        if is_fx:
            fx = ForeignExchange(key=AV_API_KEY)
            res, _ = fx.get_currency_exchange_rate(ticker[:3], ticker[3:])
            price = float(res['5. Exchange Rate'])
            df = pd.DataFrame([price]*30, columns=['Close'], index=pd.date_range(end=pd.Timestamp.now(), periods=30, freq='H'))
            df['Open'] = df['High'] = df['Low'] = price
        else:
            ts = TimeSeries(key=AV_API_KEY, output_format='pandas')
            data, _ = ts.get_intraday(symbol=ticker, interval='5min', outputsize='compact')
            df = data.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'}).sort_index()
        
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df
    except: return None

# =========================================================
# 4. COMPONENTES VISUALES (RADAR & ESTRATEGIA)
# =========================================================
def render_radar(df, name):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.3, 0.7])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Market'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#FFD700'), name='Fast'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#8A2BE2'), name='RSI'), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

def render_logic(df):
    last_p = float(df['Close'].iloc[-1])
    ema_v = float(df['EMA_20'].iloc[-1])
    prec = 5 if "EUR" in st.session_state.ticker else 2
    
    col_s, col_b = st.columns([2, 1])
    with col_s:
        st.subheader("🎯 ESTRATEGIA")
        atr = (df['High'] - df['Low']).tail(10).mean() if 'High' in df.columns else last_p * 0.002
        dist = atr * 2
        sl = last_p - dist if last_p > ema_v else last_p + dist
        tp = last_p + (dist * 2.5) if last_p > ema_v else last_p - (dist * 2.5)
        
        # Lógica de Éxito: Gestión de Lotes
        riesgo_permitido = st.session_state.wallet * 0.01
        lotes = round(riesgo_permitido / (dist * 100 if dist != 0 else 1), 2)
        lotes = max(0.01, min(lotes, 2.0))

        st.info(f"SUGERENCIA: {'COMPRA' if last_p > ema_v else 'VENTA'} | LOTES: {lotes}")
        if st.button("SINCRONIZAR BRIDGE"):
            st.session_state.update({'sl_final': sl, 'tp_final': tp, 'lotes_final': lotes})

    with col_b:
        st.subheader("🚀 BRIDGE XTB")
        with st.form("xtb"):
            l = st.number_input("Volumen", value=st.session_state.lotes_final)
            s = st.number_input("Stop Loss", value=st.session_state.sl_final, format=f"%.{prec}f")
            t = st.number_input("Take Profit", value=st.session_state.tp_final, format=f"%.{prec}f")
            if st.form_submit_button("VIGILAR"):
                send_telegram_alert(f"🐺 SENTINEL ACTIVO\nActivo: {st.session_state.ticker_name}\nLotes: {l}\nSL: {s}\nTP: {t}")
                st.success("Enviado a Telegram")

# =========================================================
# 5. ORQUESTADOR DE NAVEGACIÓN (CORREGIDO)
# =========================================================
# Definimos los nombres de los botones y las vistas de destino
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]

# Header Metrics (Resumen visual superior)
st.markdown(f'<div class="metric-card">CAPITAL: {st.session_state.wallet:,.2f}€ | PnL: {st.session_state.pnl:,.2f}€</div>', unsafe_allow_html=True)

# Renderizado de la barra de navegación principal
nav_cols = st.columns(len(btns))
for i, v in enumerate(v_list):
    with nav_cols[i]:
        # Verificamos si la vista actual coincide con el botón para resaltar el estilo
        is_active = (st.session_state.view == v)
        tag = "nav-active" if is_active else "nav-btn"
        
        st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
        if st.button(btns[i], key=f"nav_btn_{v}", use_container_width=True):
            st.session_state.view = v
            st.rerun() # Forzamos el refresco para cambiar de vista al instante
        st.markdown('</div>', unsafe_allow_html=True)
    for e in f.entries[:8]:
        with st.expander(e.title):
            st.write(e.summary)
            if st.button("Notificar", key=e.link): send_telegram_alert(f"Noticia: {e.title}")
# =========================================================
# 6. ORQUESTADOR DE VISTAS Y SECCIÓN DE NOTICIAS (ROBUSTO)
# =========================================================

if st.session_state.view == "Lobo":
    # (Aquí va tu lógica del modo Lobo que ya tenemos)
    st.subheader(f"🦊 Radar Activo: {st.session_state.ticker_name}")
    data = get_precise_data(st.session_state.ticker)
    if data is not None:
        render_radar(data, st.session_state.ticker_name)
        render_logic(data)
    else:
        st.error("📡 Error de conexión con Alpha Vantage.")

elif st.session_state.view == "Noticias":
    st.markdown("<h1 style='text-align: center; color: #A67B5B;'>📰 TERMINAL DE NOTICIAS</h1>", unsafe_allow_html=True)
    
    # --- BLOQUE DE SEGURIDAD ANTIFALLO ---
    # Inicializamos f como None para evitar el NameError si el parseo falla
    f_data = None 
    
    try:
        # Intentamos la descarga
        f_data = feedparser.parse("https://es.investing.com/rss/news.rss")
    except Exception as e:
        st.error(f"No se pudo conectar con el servidor de noticias: {e}")

    # Solo intentamos leer si f_data existe y tiene entradas
    if f_data and hasattr(f_data, 'entries') and len(f_data.entries) > 0:
        for i, e in enumerate(f_data.entries[:12]):
            with st.container():
                # Diseño limpio y profesional
                st.markdown(f"""
                <div style="background:#0d1117; padding:15px; border-radius:10px; border-left:5px solid #A67B5B; margin-bottom:10px;">
                    <h4 style="margin:0; color:white;">{e.title}</h4>
                    <p style="font-size:0.9em; color:#ccc; margin-top:8px;">
                        {e.summary.split('<')[0] if 'summary' in e else 'Noticia de última hora.'}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón de acción con ID único para evitar conflictos
                if st.button("📲 NOTIFICAR A TELEGRAM", key=f"news_{i}"):
                    send_telegram_alert(f"🐺 NOTICIA CRÍTICA:\n{e.title}\n{e.link}")
                    st.success("Alerta enviada correctamente.")
    else:
        st.warning("🔄 El servidor de noticias no responde. Por favor, intenta refrescar la página.")

elif st.session_state.view == "Ajustes":
    st.title("⚙️ Configuración Wolf Sovereign")
    st.session_state.wallet = st.number_input("Capital Total (€)", value=st.session_state.wallet)
    st.info("Configuración de precisión activa.")

else:
    st.info(f"La sección {st.session_state.view} está en fase de despliegue.")
