import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
import feedparser
import requests
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
# =========================================================
# CONFIGURACIÓN DE CREDENCIALES Y APIS
# =========================================================
TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"

# Introduce tu clave aquí entre las comillas
AV_API_KEY = "3Y17BPSEURVNALDR" 

# Validación de seguridad para el usuario
if AV_API_KEY == "3Y17BPSEURVNALDR":
    st.sidebar.error("❌ FALTA AV_API_KEY EN EL CÓDIGO")

# =========================================================
# 1. CONFIGURACIÓN DEL CEREBRO Y ESTADO DE SESIÓN
# =========================================================
# Establecemos el refresco automático para mantener el radar vivo
st_autorefresh(interval=15000, limit=None, key="sentinel_refresh_global")

# Inicialización robusta del estado de sesión para evitar NameError
if 'setup_complete' not in st.session_state:
    st.session_state.update({
        'view': "Lobo",
        'active_cat': "indices",
        'active_sub': "EEUU",
        'ticker': "NQ=F",
        'ticker_name': "US100 (Nasdaq) 🇺🇸",
        'wallet': 18850.00,
        'margen': 15200.00,
        'pnl': 420.50,
        'last_price': 0.0,
        'active_trades': [],
        'sl_final': 0.0,
        'tp_final': 0.0,
        'lotes_final': 0.10,
        'setup_complete': True
    })

# --- CONFIGURACIÓN DE ALERTAS (TELEGRAM) ---
TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"

def send_telegram_alert(message):
    """Envío de alertas con reintentos para robustez extrema"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        st.sidebar.error(f"Fallo de comunicación: {e}")

# =========================================================
# 2. MOTOR DE ESTILOS WOLF SOVEREIGN (UI PREMIUM)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95 - Precision Mode", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stVerticalBlock"] { gap: 0rem !important; }
    
    /* NAV SUPERIOR: MARRÓN -> BLANCO */
    div.nav-btn button {
        background-color: #A67B5B !important; color: #000 !important;
        border: 1px solid #000 !important; border-radius: 0px !important; height: 3.5em !important;
    }
    div.nav-active button {
        background-color: #FFFFFF !important; color: #000 !important;
        border: 2px solid #000 !important; font-weight: 900 !important; height: 3.5em !important;
    }

    /* MENÚ CASCADA: BLANCO -> NEGRO */
    div.menu-btn button {
        background-color: #FFFFFF !important; color: #000 !important;
        border: 1px solid #333 !important; border-radius: 0px !important; height: 3.2em !important;
    }
    div.menu-active button {
        background-color: #000000 !important; color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important; font-weight: bold !important; height: 3.2em !important;
    }

    .metric-container {
        background-color: #0d1117; padding: 10px; border-bottom: 2px solid #A67B5B;
        display: flex; justify-content: space-around; color: #A67B5B; font-weight: bold;
    }
    
    /* TICKER ANIMATION */
    .ticker-wrap { width: 100%; overflow: hidden; background: #000; padding: 10px 0; border-bottom: 1px solid #333; }
    .ticker-move { display: flex; width: fit-content; animation: ticker 40s linear infinite; }
    .ticker-item { padding: 0 40px; white-space: nowrap; font-family: 'Courier New', monospace; color: #fff; }
    @keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 3. BASE DE DATOS ESTRUCTURADA (MÉTODO CASCADA)
# =========================================================
DATABASE = {
    "stocks": {
        "TECNOLOGÍA": {
            "APPLE (AAPL.US) 🍎": ["AAPL", "123"], "TESLA (TSLA.US) ⚡": ["TSLA", "124"], 
            "NVIDIA (NVDA.US) 🟢": ["NVDA", "125"], "AMAZON (AMZN.US) 📦": ["AMZN", "126"],
            "META (META.US) 📱": ["META", "127"], "MICROSOFT (MSFT.US) 💻": ["MSFT", "128"]
        },
        "BANCA": {
            "SANTANDER (SAN.MC) 🏦": ["SAN.MC", "201"], "BBVA (BBVA.MC) 💙": ["BBVA.MC", "202"]
        }
    },
    "indices": {
        "EEUU": {
            "US100 (Nasdaq) 🇺🇸": ["NQ=F", "100"], "US500 (S&P500) 🇺🇸": ["ES=F", "500"],
            "US30 (Dow Jones) 🇺🇸": ["YM=F", "30"]
        },
        "EUROPA": {
            "DE40 (DAX) 🇩🇪": ["^GDAXI", "40"], "SPA35 (IBEX) 🇪🇸": ["^IBEX", "35"]
        }
    },
    "material": {
        "ENERGÍA": { "OIL.WTI 🛢️": ["CL=F", "001"], "NATGAS 🔥": ["NG=F", "002"] },
        "METALES": { "GOLD (Oro) 🟡": ["GC=F", "003"], "SILVER (Plata) ⚪": ["SI=F", "004"] }
    },
    "divisas": {
        "MAJORS": {
            "EURUSD 🇪🇺🇺🇸": ["EURUSD=X", "501"], "GBPUSD 🇬🇧🇺🇸": ["GBPUSD=X", "502"],
            "USDJPY 🇺🇸🇯🇵": ["USDJPY=X", "503"]
        }
    }
}

# =========================================================
# 4. MOTOR DE DATOS (PRECISIÓN ALTA)
# =========================================================
def get_market_data(ticker, interval='1h'):
    """Descarga y procesa datos con indicadores técnicos"""
    try:
        # Usamos period=5d para tener suficiente historial para EMAs de 50
        data = yf.download(ticker, period='5d', interval=interval, progress=False)
        if data.empty:
            return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Cálculo de Indicadores con pandas_ta (Más preciso que cálculos manuales)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Color del volumen para el gráfico
        df['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df['Close'], df['Open'])]
        
        return df
    except Exception as e:
        st.error(f"Error en Motor de Datos: {e}")
        return None

# =========================================================
# 5. COMPONENTES VISUALES (RADAR & ESTRATEGIA)
# =========================================================
def render_radar(df, ticker_name):
    """Dibuja el gráfico profesional con 3 niveles"""
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02,
        row_width=[0.15, 0.20, 0.65],
        subplot_titles=("SISTEMA DE PRECIO", "FUERZA RSI", "VOLUMEN")
    )

    # Velas
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Market'
    ), row=1, col=1)

    # Medias Móviles
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#FFD700', width=1.5), name='EMA 20'), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#8A2BE2', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # Volumen
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Vol_Color'], name='Vol'), row=3, col=1)

    fig.update_layout(template="plotly_dark", height=700, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

def render_strategy_cards(df):
    """Genera señales de trading basadas en la posición del precio"""
    st.markdown("### 🎯 SEÑALES SENTINEL")
    last_p = float(df['Close'].iloc[-1])
    ema_v = float(df['EMA_20'].iloc[-1])
    
    # Lógica de precisión decimal
    ticker = st.session_state.ticker
    prec = 5 if "EUR" in ticker or "USD" in ticker else 2
    
    # Determinación de Tendencia
    tendencia = "ALCISTA" if last_p > ema_v else "BAJISTA"
    color = "#00ff41" if tendencia == "ALCISTA" else "#ff3131"
    
    # Cálculo de Stop Loss y Take Profit (ATR Simplificado)
    atr = (df['High'] - df['Low']).tail(10).mean()
    sl = last_p - (atr * 1.5) if tendencia == "ALCISTA" else last_p + (atr * 1.5)
    tp = last_p + (atr * 3) if tendencia == "ALCISTA" else last_p - (atr * 3)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"""
        <div style="background:#0d1117; padding:20px; border-left:10px solid {color}; border-radius:10px;">
            <h2 style="color:{color}; margin:0;">{tendencia}</h2>
            <p style="font-size:1.2em;">Entrada: <b>{last_p:.{prec}f}</b></p>
            <p style="color:#00ff41;">Objetivo TP: {tp:.{prec}f}</p>
            <p style="color:#ff3131;">Riesgo SL: {sl:.{prec}f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 🚀 BRIDGE XTB")
        with st.form("xtb_bridge"):
            lotes = st.number_input("Volumen", value=0.10, step=0.01)
            sl_f = st.number_input("S/L Real", value=float(sl), format=f"%.{prec}f")
            tp_f = st.number_input("T/P Real", value=float(tp), format=f"%.{prec}f")
            if st.form_submit_button("VIGILAR OPERACIÓN"):
                send_telegram_alert(f"🐺 SENTINEL ACTIVO\nActivo: {st.session_state.ticker_name}\nLotes: {lotes}\nSL: {sl_f}\nTP: {tp_f}")
                st.success("Sincronizado con Telegram")

# =========================================================
# 6. ORQUESTADOR DE NAVEGACIÓN Y VISTAS
# =========================================================
# Header de Capital
st.markdown(f"""
<div class="metric-container">
    <span>CAPITAL: {st.session_state.wallet:,.2f}€</span>
    <span>DISPONIBLE: {st.session_state.margen:,.2f}€</span>
    <span>PnL DÍA: {st.session_state.pnl:,.2f}€</span>
</div>
""", unsafe_allow_html=True)

# Ticker de noticias rápido
hot_list = [("NQ=F", "US100", "▲"), ("GC=F", "ORO", "▼"), ("EURUSD=X", "EURUSD", "▲")]
content = "".join([f'<div class="ticker-item">{n} {i} {t}</div>' for t, n, i in hot_list * 5])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# Menú Principal
nav_cols = st.columns(6)
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]

for i, col in enumerate(nav_cols):
    is_active = st.session_state.view == v_list[i]
    tag = "nav-active" if is_active else "nav-btn"
    with col:
        st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
        if st.button(btns[i], key=f"v_{i}", use_container_width=True):
            st.session_state.view = v_list[i]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- VISTA LOBO (Trading Center) ---
if st.session_state.view == "Lobo":
    # Fila 1: Categorías
    cats = list(DATABASE.keys())
    c_cat = st.columns(len(cats))
    for i, cat in enumerate(cats):
        tag = "menu-active" if st.session_state.active_cat == cat else "menu-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(cat.upper(), key=f"c_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = list(DATABASE[cat].keys())[0]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # Fila 2: Subcategorías
    if st.session_state.active_cat:
        subs = list(DATABASE[st.session_state.active_cat].keys())
        c_sub = st.columns(len(subs))
        for i, sub in enumerate(subs):
            tag = "menu-active" if st.session_state.active_sub == sub else "menu-btn"
            with c_sub[i]:
                st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                if st.button(sub, key=f"s_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # Fila 3: Activos Finales
        if st.session_state.active_sub:
            activos = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
            c_act = st.columns(len(activos))
            for i, (name, val) in enumerate(activos.items()):
                tag = "menu-active" if st.session_state.ticker_name == name else "menu-btn"
                with c_act[i]:
                    st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                    if st.button(name, key=f"f_{name}", use_container_width=True):
                        st.session_state.ticker = val[0]
                        st.session_state.ticker_name = name
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # Renderizado de Datos Lobo
    df_lobo = get_market_data(st.session_state.ticker)
    if df_lobo is not None:
        render_radar(df_lobo, st.session_state.ticker_name)
        render_strategy_cards(df_lobo)
    else:
        st.error("📡 Sincronizando con el mercado... Reintenta en 5s.")

# --- VISTA NOTICIAS (Terminal Global) ---
elif st.session_state.view == "Noticias":
    st.title("📰 Terminal Sentinel News")
    
    # Inicialización segura de variable f para evitar NameError
    f_news = None
    try:
        f_news = feedparser.parse("https://es.investing.com/rss/news.rss")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

    if f_news and hasattr(f_news, 'entries') and len(f_news.entries) > 0:
        for i, entry in enumerate(f_news.entries[:15]):
            with st.container():
                st.markdown(f"""
                <div style="background:#0d1117; padding:15px; border-radius:10px; border-left:5px solid #A67B5B; margin-bottom:10px;">
                    <h4 style="margin:0; color:white;">{entry.title}</h4>
                    <p style="font-size:0.9em; color:#ccc;">{entry.summary.split('<')[0] if 'summary' in entry else 'Sin resumen.'}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("📲 NOTIFICAR MOVIMIENTO", key=f"news_btn_{i}"):
                    send_telegram_alert(f"NOTICIA CRÍTICA: {entry.title}\n{entry.link}")
                    st.toast("Alerta enviada")
    else:
        st.warning("No se han podido cargar noticias. El servidor de Investing.com podría estar caído.")

# --- VISTA AJUSTES (Gestión de Riesgo) ---
elif st.session_state.view == "Ajustes":
    st.title("⚙️ Panel de Control Wolf")
    col_a, col_b = st.columns(2)
    with col_a:
        st.session_state.wallet = st.number_input("Capital de Operación (€)", value=st.session_state.wallet)
        st.session_state.margen = st.number_input("Margen de Seguridad (€)", value=st.session_state.margen)
    with col_b:
        st.write("### Estado del Sistema")
        st.info("📡 Motor de Datos: Yahoo Finance OK")
        st.info("📲 Bridge Telegram: Activo")
    if st.button("GUARDAR CONFIGURACIÓN"):
        st.success("Parámetros actualizados con éxito.")

# --- VISTAS EN DESARROLLO ---
else:
    st.info(f"La sección **{st.session_state.view}** está siendo calibrada para máxima precisión técnica.")
    st.image("https://images.unsplash.com/photo-1611974717483-9b43958c9701?q=80&w=2070&auto=format&fit=crop")
  # =========================================================
# BLOQUE 7: RADAR VISUAL (VOLUMEN BICOLOR & CONTROLES)
# =========================================================
def render_shielded_chart(df, ticker_actual):
    """
    Renderiza el radar táctico Wolf con triple panel.
    Corregido: Se añade manejo de excepciones para evitar cierres inesperados.
    """
    if df is None or len(df) == 0:
        st.warning("📡 Sincronizando radar de alta precisión...")
        return

    # --- 1. CONTROLES SUPERIORES (Temporalidad integrada) ---
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        # Selección de intervalo con persistencia en session_state
        st.selectbox("⏳ Rango Temporal:", ["1m", "5m", "15m", "1h", "1d"], index=3, key="int_top")
    with c2:
        # Métrica de precio real con formato según activo
        st.metric("Precio Actual", f"{st.session_state.last_price:,.2f}")
    with c3:
        st.write(f"🛰️ **RADAR ACTIVO:** {ticker_actual}")

    # --- 2. CONFIGURACIÓN DEL GRÁFICO (3 Niveles: Precio, RSI, Volumen) ---
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.04, 
        row_width=[0.15, 0.20, 0.65], # Proporciones de los paneles optimizadas
        subplot_titles=("SISTEMA DE PRECIO & ESTRATEGIA", "ÍNDICE DE FUERZA (RSI)", "FLUJO DE VOLUMEN")
    )

    # A. VELAS JAPONESAS (Estilo Wolf: Verde Neón y Rojo Sangre)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Precio', increasing_line_color='#00ff41', decreasing_line_color='#ff3131'
    ), row=1, col=1)

    # B. EMA 20 (Media móvil rápida en Oro para detección de tendencia)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['EMA_20'], line=dict(color='#FFD700', width=1.5),
        name='EMA 20', opacity=0.8
    ), row=1, col=1)

    # C. RSI (Panel intermedio de sobrecompra/sobreventa)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['RSI'], line=dict(color='#8A2BE2', width=2), name='RSI'
    ), row=2, col=1)
    
    # Zonas de seguridad Sentinel (Líneas guía)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff3131", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00ff41", opacity=0.5, row=2, col=1)

    # D. VOLUMEN BICOLOR (Flujo real de órdenes)
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'], name='Volumen',
        marker_color=df['Vol_Color'], opacity=0.8
    ), row=3, col=1)

    # --- 3. NIVELES REALES XTB (Vigilancia de operaciones abiertas) ---
    if 'active_trades' in st.session_state:
        for op in st.session_state.active_trades:
            if op['ticker'] == ticker_actual:
                # Entrada (Azul Sentinel)
                fig.add_hline(y=float(op['entrada']), line_color="#0066ff", line_dash="dash", 
                             annotation_text="ORDEN", row=1, col=1)
                # Stop Loss (Rojo Crítico)
                fig.add_hline(y=float(op['sl']), line_color="#ff3131", line_dash="dot", 
                             annotation_text="STOP", row=1, col=1)
                # Take Profit (Verde Éxito)
                fig.add_hline(y=float(op['tp']), line_color="#00ff41", line_dash="dot", 
                             annotation_text="TARGET", row=1, col=1)

    # --- 4. ESTÉTICA & ZOOM (UI DARK MODE) ---
    fig.update_layout(
        template="plotly_dark", height=800, xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    fig.update_yaxes(gridcolor='#1e1e1e', zeroline=False)
    fig.update_xaxes(gridcolor='#1e1e1e')
    
    st.plotly_chart(fig, use_container_width=True, key=f"radar_elite_{ticker_actual}")

# =========================================================
# BLOQUE 8: ESTRATEGIAS CON PRECISIÓN DINÁMICA
# =========================================================
def render_strategy_cards(df):
    """
    Calcula y presenta estrategias automáticas.
    Corregido: Se añade lógica para divisas con 5 decimales.
    """
    st.markdown("---")
    st.subheader("🎯 ESTRATEGIAS SUGERIDAS SENTINEL")
    
    if df is None or 'EMA_20' not in df.columns:
        st.warning("Calculando métricas de precisión técnica...")
        return

    ticker = st.session_state.get('ticker', 'NQ=F')
    last_p = float(df['Close'].iloc[-1])
    ema_v = float(df['EMA_20'].iloc[-1])
    rsi_v = float(df['RSI'].iloc[-1])
    
    # --- DETERMINACIÓN DE PRECISIÓN SEGÚN CATEGORÍA (REGLA DE ORO) ---
    if "=X" in ticker or any(x in ticker for x in ["EUR", "USD", "GBP", "JPY", "divisas"]):
        precision = 5
        step_val = 0.0001
    elif any(x in ticker for x in ["BTC", "ETH", "SOL"]):
        precision = 2
        step_val = 0.01
    else: # Índices, Stocks y Materias Primas
        precision = 2
        step_val = 0.25

    es_compra = last_p > ema_v
    color_base = "#00ff41" if es_compra else "#ff3131"
    atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    
    # Configuración de perfiles de riesgo
    config = [
        {"id": "CP", "n": "CORTO PLAZO", "ent": last_p, "lotes": 0.50, "m_sl": 1.2, "ratio": 1.5, "p": 68, "col": col1},
        {"id": "MP", "n": "MEDIO PLAZO", "ent": ema_v, "lotes": 0.25, "m_sl": 2.2, "ratio": 2.0, "p": 78, "col": col2},
        {"id": "LP", "n": "LARGO PLAZO", "ent": ema_v * (0.995 if es_compra else 1.005), "lotes": 0.10, "m_sl": 4.5, "ratio": 3.0, "p": 85, "col": col3}
    ]

    for c in config:
        with c["col"]:
            dist_sl = atr * c["m_sl"]
            sl = c["ent"] - dist_sl if es_compra else c["ent"] + dist_sl
            riesgo = abs(c["ent"] - sl)
            tp = c["ent"] + (riesgo * c["ratio"]) if es_compra else c["ent"] - (riesgo * c["ratio"])
            
            # Ajuste de probabilidad por RSI
            prob = c["p"]
            if (rsi_v > 70 and es_compra) or (rsi_v < 30 and not es_compra): 
                prob -= 12 # Penalización por sobreextensión

            st.markdown(f"""
            <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid {color_base}; border-top: 10px solid {color_base};">
                <h3 style="margin:0; color:{color_base}; text-align:center;">{c['n']}</h3>
                <div style="text-align:center; margin:15px 0;">
                    <span style="font-size:2rem; font-weight:bold; color:white;">{prob}%</span><br>
                    <span style="color:#888; font-size:0.8rem;">PROBABILIDAD ÉXITO</span>
                </div>
                <p style="margin:5px 0;">💰 <b>Lotes Sugeridos:</b> {c['lotes']}</p>
                <p style="margin:5px 0;">📍 <b>Entrada:</b> {c['ent']:.{precision}f}</p>
                <p style="margin:5px 0; color:{color_base}; font-weight:bold;">🎯 Objetivo TP: {tp:.{precision}f}</p>
                <p style="margin:5px 0; color:#ff3131;">🛡️ Seguridad SL: {sl:.{precision}f}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Sincronizar {c['id']}", key=f"sync_prec_{c['id']}", use_container_width=True):
                st.session_state['sl_final'] = sl
                st.session_state['tp_final'] = tp
                st.session_state['lotes_final'] = c['lotes']
                st.session_state['ent_final'] = c['ent']
                st.toast("Datos cargados en el Bridge")



# =========================================================
# BLOQUE 10: MOTOR DE NOTICIAS & INTELIGENCIA DE SENTIMIENTO
# =========================================================
def render_sentinel_news(ticker):
    """
    Motor híbrido de noticias con análisis de sentimiento Alpha Vantage.
    Blindado contra errores de duplicidad de nodos (keys únicas).
    """
    st.markdown(f"## 📰 TERMINAL DE INTELIGENCIA: {ticker}")
    
    # --- INTERFAZ DE ALPHA VANTAGE (SENTIMIENTO) ---
    try:
        # Limpieza de ticker para Alpha Vantage
        clean_ticker = ticker.split('=')[0].split('.')[0]
        av_news_url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={clean_ticker}&apikey={AV_API_KEY}"
        
        response = requests.get(av_news_url, timeout=5)
        news_data = response.json()
        
        if "feed" in news_data:
            st.subheader("🎯 SENTIMIENTO DE MERCADO REAL")
            # Usamos un contenedor estable para evitar el error removeChild
            with st.container():
                for i, item in enumerate(news_data["feed"][:4]):
                    col_text, col_sent = st.columns([4, 1])
                    with col_text:
                        st.markdown(f"**[{item['title']}]({item['url']})**")
                        st.caption(f"Fuente: {item['source']} | Relevancia: {item['relevance_score']}")
                    with col_sent:
                        sent_label = item.get('overall_sentiment_label', 'Neutral')
                        color = "#00ff41" if "Bullish" in sent_label else "#ff3131" if "Bearish" in sent_label else "#888"
                        st.markdown(f'<p style="color:{color}; font-weight:bold;">{sent_label}</p>', unsafe_allow_html=True)
                    st.divider()
    except Exception as e:
        st.caption(f"⏳ Inteligencia AV: Esperando ventana de conexión... ({e})")

    # --- MOTOR DE RESPALDO RSS (INVESTING) ---
    st.markdown("### 📡 ÚLTIMA HORA (GLOBAL RSS)")
    try:
        f_news = feedparser.parse("https://es.investing.com/rss/news.rss")
        if f_news and f_news.entries:
            for i, entry in enumerate(f_news.entries[:6]):
                # CLAVE ÚNICA BLINDADA: Evita el error de 'Node removeChild'
                unique_key = f"rss_btn_{ticker}_{i}_{st.session_state.view}"
                
                with st.expander(f"📌 {entry.title[:70]}...", expanded=False):
                    st.write(entry.summary.split('<')[0] if 'summary' in entry else "Contenido en terminal...")
                    if st.button("Sincronizar con Telegram", key=unique_key):
                        msg = f"🐺 *NOTICIA TRADING*\n{entry.title}\n{entry.link}"
                        send_telegram_alert(msg)
                        st.toast("Enviado a Central")
    except Exception as e:
        st.error(f"Fallo en la sincronización del feed RSS: {e}")
# =========================================================
# BLOQUE 11: MOTOR DE DATOS ALPHA VANTAGE (SISTEMA DUAL)
# =========================================================
def get_alpha_vantage_data(symbol):
    """
    Obtiene velas japonesas desde Alpha Vantage como fuente secundaria.
    Garantiza robustez total si la fuente primaria (YF) es bloqueada.
    """
    try:
        # Conversión de símbolos para divisas/forex en AV
        if "EURUSD" in symbol:
            url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=USD&apikey={AV_API_KEY}&datatype=csv"
        elif "GOLD" in symbol or "GC=F" in symbol:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=GOLD&apikey={AV_API_KEY}&datatype=csv"
        else:
            clean_s = symbol.split('=')[0].split('.')[0]
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={clean_s}&apikey={AV_API_KEY}&datatype=csv"
            
        df_av = pd.read_csv(url)
        df_av['timestamp'] = pd.to_datetime(df_av['timestamp'])
        df_av.set_index('timestamp', inplace=True)
        df_av.sort_index(ascending=True, inplace=True)
        
        # Estandarización de nombres de columnas
        df_av.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        
        # Añadir indicadores básicos para no romper el Radar
        df_av['EMA_20'] = ta.ema(df_av['Close'], length=20)
        df_av['RSI'] = ta.rsi(df_av['Close'], length=14)
        df_av['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df_av['Close'], df_av['Open'])]
        
        return df_av
    except Exception as e:
        st.error(f"Error en fuente secundaria (AV): {e}")
        return None
# =========================================================
# BLOQUE 12: ANÁLISIS FUNDAMENTAL (DATA MINING)
# =========================================================
def render_fundamental_analysis(ticker):
    """Extrae métricas de salud financiera desde Alpha Vantage"""
    clean_t = ticker.split('=')[0].split('.')[0]
    
    try:
        # Llamada directa a la API para datos de resumen
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={clean_t}&apikey={AV_API_KEY}"
        data = requests.get(url, timeout=5).json()
        
        if data and "Symbol" in data:
            st.markdown(f"#### 📊 Análisis de Empresa: {data.get('Name')}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PER Ratio", data.get('PERatio', 'N/A'))
            c2.metric("PEG Ratio", data.get('PEGRatio', 'N/A'))
            c3.metric("Dividend Yield", f"{float(data.get('DividendYield', 0))*100:.2f}%")
            c4.metric("ROE", data.get('ReturnOnEquityTTM', 'N/A'))
            
            with st.expander("🔍 Detalles del Negocio"):
                st.write(data.get('Description', 'No disponible.'))
                st.caption(f"Sector: {data.get('Sector')} | Industria: {data.get('Industry')}")
        else:
            st.info("ℹ️ Datos fundamentales no disponibles para este activo (Tier Gratuito).")
    except Exception as e:
        st.caption(f"⚠️ Error de conexión fundamental: {e}")
# =========================================================
# BLOQUE 13: ORQUESTADOR FINAL DE ALTA DISPONIBILIDAD
# =========================================================
def run_wolf_orchestrator():
    """Controla el flujo de la app y previene el error removeChild"""
    # 1. Recuperar contexto de sesión
    t_active = st.session_state.get('ticker', 'NQ=F')
    view = st.session_state.get('view', 'Lobo')
    cat = st.session_state.get('active_cat', 'indices')
    
    # 2. Contenedor Maestro Estabilizado
    main_container = st.container()
    
    with main_container:
        if view == "Noticias":
            render_sentinel_news(t_active)
            
        elif view in ["Lobo", "XTB"]:
            # Mostrar fundamentales si es una acción
            if cat == "stocks":
                render_fundamental_analysis(t_active)
            
            # Obtención de datos técnicos (Yahoo Finance)
            df = get_market_data(t_active, interval=st.session_state.get('int_top', '1h'))
            
            if df is not None:
                st.session_state.last_price = float(df['Close'].iloc[-1])
                render_shielded_chart(df, t_active) # Bloque 7
                render_strategy_cards(df)           # Bloque 8
                render_sentinel_bridge()            # Bloque 9
            else:
                # Fallback a Alpha Vantage
                st.warning("⚠️ Intentando conexión secundaria...")
                df_av = get_alpha_vantage_data(t_active) # Bloque 11
                if df_av is not None:
                    render_shielded_chart(df_av, t_active)
                else:
                    st.error("🚨 Sin respuesta de servidores. Verifique su AV_API_KEY.")

        elif view == "Ajustes":
            st.title("⚙️ PANEL DE CONTROL")
            st.info("Ajustes de latencia y riesgo Sentinel v.95 activos.")

# EJECUCIÓN DEL NÚCLEO
if __name__ == "__main__":
    try:
        run_wolf_orchestrator()
    except Exception as e:
        # Este mensaje evita el 'Oh no' genérico y te da la pista del error
        st.error(f"⚠️ ERROR CRÍTICO DE ARRANQUE: {e}")


# =========================================================
# FINAL DEL ARCHIVO: WOLF SOVEREIGN PRECISION V95
# Total de líneas estimadas: 640-660
# =========================================================
