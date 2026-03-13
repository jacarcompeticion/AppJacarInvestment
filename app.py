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
#INICIO
st.set_page_config(page_title="WOLF SOVEREIGN v.95", layout="wide", initial_sidebar_state="collapsed", page_icon="🐺")
# =========================================================
# CONFIGURACIÓN DE CREDENCIALES Y APIS
# =========================================================
TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"

# Clave Alpha Vantage (Verificada sin espacios extra)
AV_API_KEY = "3Y17BPSEURVNALDR"

# Validación de seguridad corregida
if not AV_API_KEY or AV_API_KEY == "TU_API_KEY_AQUI":
    st.sidebar.error("❌ FALTA AV_API_KEY EN EL CÓDIGO")
else:
    st.sidebar.success("✅ SISTEMA AV VINCULADO")

# =========================================================
# BLOQUE 0: SANEAMIENTO Y REINICIO DE EMERGENCIA
# =========================================================
def sanitize_session():
    """Limpia residuos de memoria que causan errores de renderizado"""
    # 1. Forzar claves de estado básicas si no existen
    defaults = {
        'view': 'Lobo',
        'active_cat': 'indices',
        'ticker': 'NQ=F',
        'ticker_name': 'NASDAQ 100',
        'wallet': 10000.0,
        'margen': 5000.0,
        'pnl': 0.0,
        'active_trades': []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # 2. Botón de Reset Total en el Sidebar (Solo visible si algo falla)
    if st.sidebar.button("🧹 REPARAR NÚCLEO (RESET)"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.cache_data.clear()
        st.rerun()

# Llamada inmediata al sanador
sanitize_session()

# =========================================================
# AJUSTE DE ESTABILIDAD EN EL RADAR (BLOQUE 7 MODIFICADO)
# =========================================================
# Busca tu función render_shielded_chart y asegúrate de que la 
# llamada final a plotly sea exactamente así:

def render_shielded_chart(df, ticker_actual):
    # ... (todo tu código anterior del bloque 7) ...
    
    # CLAVE DINÁMICA ÚNICA: Esto evita el error removeChild al cambiar de activo
    # Al añadir la longitud del dataframe a la key, forzamos un ID nuevo si los datos cambian
    unique_id = f"radar_{ticker_actual}_{len(df)}"
    st.plotly_chart(fig, use_container_width=True, key=unique_id)
# =========================================================
# 1. CONFIGURACIÓN DEL CEREBRO Y ESTADO DE SESIÓN
# =========================================================
# Refresco automático estable
st_autorefresh(interval=15000, key="wolf_global_monitor_refresh")

# Inicialización del estado de sesión
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

# --- SISTEMA DE ALERTAS ---
# Aseguramos que las variables existan para evitar NameError
def send_telegram_alert(message):
    """Envío de alertas blindado"""
    try:
        # Usamos las variables globales definidas en el Bloque 0
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        st.sidebar.error(f"Error de comunicación Telegram: {e}")
# =========================================================
# 2. MOTOR DE ESTILOS WOLF SOVEREIGN (UI PREMIUM)
# =========================================================

# NOTA: Esta línea DEBE ir al principio de tu archivo app.py, 
# justo debajo de los imports para evitar que la página se caiga.
try:
    st.set_page_config(page_title="Wolf Sovereign V95 - Precision Mode", layout="wide", page_icon="🐺")
except:
    pass # Si ya se ejecutó, evitamos el error crítico

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
# Categorías estrictamente separadas: stocks, indices, material, divisas
DATABASE = {
    "stocks": {
        "TECNOLOGÍA": {
            "APPLE (AAPL.US) 🍎": ["AAPL", "123"], 
            "TESLA (TSLA.US) ⚡": ["TSLA", "124"], 
            "NVIDIA (NVDA.US) 🟢": ["NVDA", "125"], 
            "AMAZON (AMZN.US) 📦": ["AMZN", "126"],
            "META (META.US) 📱": ["META", "127"], 
            "MICROSOFT (MSFT.US) 💻": ["MSFT", "128"]
        },
        "BANCA": {
            "SANTANDER (SAN.MC) 🏦": ["SAN.MC", "201"], 
            "BBVA (BBVA.MC) 💙": ["BBVA.MC", "202"]
        }
    },
    "indices": {
        "EEUU": {
            "US100 (Nasdaq) 🇺🇸": ["NQ=F", "100"], 
            "US500 (S&P500) 🇺🇸": ["ES=F", "500"],
            "US30 (Dow Jones) 🇺🇸": ["YM=F", "30"]
        },
        "EUROPA": {
            "DE40 (DAX) 🇩🇪": ["^GDAXI", "40"], 
            "SPA35 (IBEX) 🇪🇸": ["^IBEX", "35"]
        }
    },
    "material": {
        "ENERGÍA": { 
            "OIL.WTI 🛢️": ["CL=F", "001"], 
            "NATGAS 🔥": ["NG=F", "002"] 
        },
        "METALES": { 
            "GOLD (Oro) 🟡": ["GC=F", "003"], 
            "SILVER (Plata) ⚪": ["SI=F", "004"] 
        }
    },
    "divisas": {
        "MAJORS": {
            "EURUSD 🇪🇺🇺🇸": ["EURUSD=X", "501"], 
            "GBPUSD 🇬🇧🇺🇸": ["GBPUSD=X", "502"],
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
        # Optimizamos el periodo según el intervalo para no saturar la RAM
        period_map = {'1m': '1d', '5m': '1d', '15m': '2d', '1h': '5d', '1d': '1mo'}
        selected_period = period_map.get(interval, '5d')
        
        data = yf.download(ticker, period=selected_period, interval=interval, progress=False)
        
        if data is None or data.empty:
            return None
        
        df = data.copy()
        
        # Aplanamiento robusto de columnas (Compatible con yfinance v0.2.40+)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Limpieza de nombres de columnas (Quitar espacios accidentales)
        df.columns = [str(col).strip() for col in df.columns]
            
        # Cálculo de Indicadores con pandas_ta
        # Usamos fillna para evitar que nulos rompan el gráfico de Plotly
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Color del volumen para el gráfico (Bicolor)
        df['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df['Close'], df['Open'])]
        
        # Eliminamos filas con NaNs iniciales para que el gráfico empiece con datos limpios
        return df.dropna(subset=['Close'])
        
    except Exception as e:
        st.error(f"Error Crítico en Motor de Datos: {e}")
        return None

# =========================================================
# 5. COMPONENTES VISUALES (RADAR & ESTRATEGIA)
# =========================================================
def render_radar(df, ticker_name):
    """Dibuja el gráfico profesional con 3 niveles"""
    # Usamos una clave única para el gráfico basada en el ticker para evitar errores de Nodo
    chart_key = f"radar_chart_{st.session_state.ticker}"
    
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_width=[0.15, 0.20, 0.65],
        subplot_titles=("SISTEMA DE PRECIO", "FUERZA RSI", "VOLUMEN")
    )

    # Velas (Colores Wolf: Verde Neón / Rojo Sangre)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Market', increasing_line_color='#00ff41', decreasing_line_color='#ff3131'
    ), row=1, col=1)

    # Medias Móviles (Oro)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#FFD700', width=1.5), name='EMA 20'), row=1, col=1)
    
    # RSI (Púrpura)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#8A2BE2', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff3131", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00ff41", opacity=0.5, row=2, col=1)

    # Volumen Bicolor
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Vol_Color'], name='Vol'), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", height=700, 
        margin=dict(l=10, r=10, t=30, b=10), 
        xaxis_rangeslider_visible=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)

def render_strategy_cards(df):
    """Genera señales de trading robustas"""
    st.markdown("### 🎯 SEÑALES SENTINEL")
    
    # Aseguramos que existan datos antes de calcular
    if df is None or len(df) < 2:
        st.warning("Datos insuficientes para señales.")
        return

    last_p = float(df['Close'].iloc[-1])
    ema_v = float(df['EMA_20'].iloc[-1])
    ticker = st.session_state.ticker
    
    # Precisión adaptativa
    prec = 5 if "=X" in ticker or any(x in ticker for x in ["EUR", "USD", "GBP"]) else 2
    
    tendencia = "ALCISTA" if last_p > ema_v else "BAJISTA"
    color = "#00ff41" if tendencia == "ALCISTA" else "#ff3131"
    
    # Cálculo de ATR con fallback de seguridad
    diff = (df['High'] - df['Low']).tail(14)
    atr = diff.mean() if not diff.empty else last_p * 0.01
    
    sl = last_p - (atr * 1.5) if tendencia == "ALCISTA" else last_p + (atr * 1.5)
    tp = last_p + (atr * 3) if tendencia == "ALCISTA" else last_p - (atr * 3)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"""
        <div style="background:#0d1117; padding:20px; border-left:10px solid {color}; border-radius:10px; border:1px solid #333;">
            <h2 style="color:{color}; margin:0;">{tendencia}</h2>
            <p style="font-size:1.2em; margin-bottom:0;">Entrada: <b>{last_p:.{prec}f}</b></p>
            <hr style="opacity:0.1;">
            <p style="color:#00ff41; margin:0;">🎯 Objetivo TP: {tp:.{prec}f}</p>
            <p style="color:#ff3131; margin:0;">🛡️ Riesgo SL: {sl:.{prec}f}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 🚀 BRIDGE XTB")
        # Usamos un formulario para evitar refrescos accidentales al escribir
        with st.form(f"xtb_bridge_{ticker}"):
            lotes = st.number_input("Volumen", value=0.10, step=0.01, min_value=0.01)
            # Forzamos conversión a float para evitar errores de tipo en Streamlit
            sl_f = st.number_input("S/L Real", value=float(sl), format=f"%.{prec}f")
            tp_f = st.number_input("T/P Real", value=float(tp), format=f"%.{prec}f")
            
            if st.form_submit_button("VIGILAR OPERACIÓN"):
                msg = f"🐺 *SENTINEL ACTIVO*\nActivo: {st.session_state.ticker_name}\nLotes: {lotes}\nSL: {sl_f}\nTP: {tp_f}"
                send_telegram_alert(msg)
                st.success("Sincronizado con Central")

# =========================================================
# 6. ORQUESTADOR DE NAVEGACIÓN Y VISTAS (MODO SEGURO)
# =========================================================

# 1. Header de Capital Estabilizado
st.markdown(f"""
<div class="metric-container">
    <span>CAPITAL: {st.session_state.get('wallet', 0):,.2f}€</span>
    <span>DISPONIBLE: {st.session_state.get('margen', 0):,.2f}€</span>
    <span>PnL DÍA: {st.session_state.get('pnl', 0):,.2f}€</span>
</div>
""", unsafe_allow_html=True)

# 2. Ticker de noticias (Optimizado)
hot_list = [("NQ=F", "US100", "▲"), ("GC=F", "ORO", "▼"), ("EURUSD=X", "EURUSD", "▲")]
content = "".join([f'<div class="ticker-item">{n} {i} {t}</div>' for t, n, i in hot_list * 5])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# 3. Menú Principal (Blindado)
nav_cols = st.columns(6)
btns = ["🐺 LOBO", "💼 XTB", "📈 RATIOS", "🔮 PREDICCIONES", "📰 NOTICIAS", "⚙️ AJUSTES"]
v_list = ["Lobo", "XTB", "Ratios", "Predicciones", "Noticias", "Ajustes"]

for i, col in enumerate(nav_cols):
    is_active = st.session_state.view == v_list[i]
    tag = "nav-active" if is_active else "nav-btn"
    with col:
        st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
        if st.button(btns[i], key=f"v_main_{i}", use_container_width=True):
            st.session_state.view = v_list[i]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- LÓGICA DE VISTAS ---
if st.session_state.view == "Lobo":
    # Fila 1: Categorías
    cats = list(DATABASE.keys())
    c_cat = st.columns(len(cats))
    for i, cat in enumerate(cats):
        tag = "menu-active" if st.session_state.active_cat == cat else "menu-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(cat.upper(), key=f"btn_cat_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                # Reset de seguridad para subcategoría
                st.session_state.active_sub = list(DATABASE[cat].keys())[0]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # Fila 2: Subcategorías (Máximo 4 por fila para estabilidad)
    if st.session_state.active_cat in DATABASE:
        subs = list(DATABASE[st.session_state.active_cat].keys())
        c_sub = st.columns(min(len(subs), 4)) 
        for i, sub in enumerate(subs):
            col_idx = i % 4
            tag = "menu-active" if st.session_state.active_sub == sub else "menu-btn"
            with c_sub[col_idx]:
                st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                if st.button(sub, key=f"btn_sub_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # Fila 3: Activos Finales (Gestión de Grid segura)
        if st.session_state.active_sub in DATABASE[st.session_state.active_cat]:
            activos = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
            # Creamos filas de 4 activos para evitar que la UI se rompa
            cols_act = st.columns(4)
            for i, (name, val) in enumerate(activos.items()):
                col_idx = i % 4
                tag = "menu-active" if st.session_state.ticker_name == name else "menu-btn"
                with cols_act[col_idx]:
                    st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                    if st.button(name, key=f"btn_act_{name}", use_container_width=True):
                        st.session_state.ticker = val[0]
                        st.session_state.ticker_name = name
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

   # Lógica de descarga híbrida
df_lobo = get_market_data(st.session_state.ticker) # Fuente 1: Yahoo

if df_lobo is None:
    st.info("🔄 Fuente principal saturada. Activando respaldo Alpha Vantage...")
    df_lobo = get_alpha_vantage_data(st.session_state.ticker) # Fuente 2: AV
    else:
        st.error("📡 Error de enlace. El mercado seleccionado no responde.")

elif st.session_state.view == "Noticias":
    # Usamos el bloque de noticias que definimos anteriormente (Bloque 10 integrado)
    render_sentinel_news(st.session_state.ticker)

elif st.session_state.view == "Ajustes":
    st.title("⚙️ Panel de Control Wolf")
    with st.container():
        st.session_state.wallet = st.number_input("Capital (€)", value=float(st.session_state.wallet))
        if st.button("GUARDAR"): st.success("Ok")

else:
    st.info(f"Sección {st.session_state.view} en fase de calibración.")
# =========================================================
# BLOQUE 7: RADAR VISUAL (VOLUMEN BICOLOR & CONTROLES)
# =========================================================
def render_shielded_chart(df, ticker_actual):
    """Renderiza el radar táctico Wolf con protección de Nodos"""
    if df is None or len(df) == 0:
        st.warning("📡 Sincronizando radar...")
        return

    # --- 1. CONTROLES SUPERIORES ---
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        # Selector de intervalo (Asegúrate de que get_market_data use st.session_state.int_top)
        st.selectbox("⏳ Rango Temporal:", ["1m", "5m", "15m", "1h", "1d"], index=3, key="int_top")
    
    with c2:
        # Precio actual con detección de cambio
        current_price = float(df['Close'].iloc[-1])
        # Intentamos calcular el delta (cambio) para mayor robustez visual
        delta = current_price - float(df['Open'].iloc[-1])
        st.metric("Precio Actual", f"{current_price:,.2f}", delta=f"{delta:,.2f}")
    
    with c3:
        st.write(f"🛰️ **RADAR ACTIVO:** {ticker_actual}")

    # --- 2. CONFIGURACIÓN DEL GRÁFICO ---
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.04, 
        row_width=[0.15, 0.20, 0.65],
        subplot_titles=("SISTEMA DE PRECIO & ESTRATEGIA", "ÍNDICE DE FUERZA (RSI)", "FLUJO DE VOLUMEN")
    )

    # A. VELAS JAPONESAS
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Precio', increasing_line_color='#00ff41', decreasing_line_color='#ff3131'
    ), row=1, col=1)

    # B. EMA 20 (Oro)
    if 'EMA_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['EMA_20'], line=dict(color='#FFD700', width=1.5),
            name='EMA 20'
        ), row=1, col=1)

    # C. RSI
    if 'RSI' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['RSI'], line=dict(color='#8A2BE2', width=2), name='RSI'
        ), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ff3131", opacity=0.3, row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00ff41", opacity=0.3, row=2, col=1)

    # D. VOLUMEN BICOLOR
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'], name='Volumen',
        marker_color=df.get('Vol_Color', '#888'), opacity=0.8
    ), row=3, col=1)

    # --- 3. NIVELES REALES XTB (Seguridad contra valores nulos) ---
    active_trades = st.session_state.get('active_trades', [])
    for op in active_trades:
        if op.get('ticker') == ticker_actual:
            try:
                e, s, t = float(op['entrada']), float(op['sl']), float(op['tp'])
                fig.add_hline(y=e, line_color="#0066ff", line_dash="dash", annotation_text="ORDEN", row=1, col=1)
                fig.add_hline(y=s, line_color="#ff3131", line_dash="dot", annotation_text="STOP", row=1, col=1)
                fig.add_hline(y=t, line_color="#00ff41", line_dash="dot", annotation_text="TARGET", row=1, col=1)
            except (ValueError, KeyError, TypeError):
                continue # Si los datos de la orden están corruptos, saltamos para no romper el gráfico

    # --- 4. ESTÉTICA ---
    fig.update_layout(
        template="plotly_dark", height=800, xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # Key dinámica para forzar renderizado limpio al cambiar de ticker
    st.plotly_chart(fig, use_container_width=True, key=f"chart_v95_{ticker_actual}_{st.session_state.get('int_top', '1h')}")
chart_id = f"radar_node_{ticker_actual}_{len(df)}"
    
    st.plotly_chart(
        fig, 
        use_container_width=True, 
        key=chart_id,
        theme="streamlit" # Mantiene la estética integrada
    )
# =========================================================
# BLOQUE 8: ESTRATEGIAS CON PRECISIÓN DINÁMICA
# =========================================================
def render_strategy_cards(df):
    """
    Calcula y presenta estrategias automáticas.
    Blindado contra errores de cálculo (NaN) y precisión adaptativa.
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
    
    # --- PRECISIÓN DINÁMICA ---
    if "=X" in ticker or any(x in ticker for x in ["EUR", "USD", "GBP", "JPY", "divisas"]):
        precision = 5
    elif any(x in ticker for x in ["BTC", "ETH", "SOL"]):
        precision = 2
    else: 
        precision = 2

    es_compra = last_p > ema_v
    color_base = "#00ff41" if es_compra else "#ff3131"
    
    # Cálculo de ATR Robusto (Si falla el rolling, usa un 0.5% del precio)
    atr_series = (df['High'] - df['Low']).rolling(14).mean()
    atr = atr_series.iloc[-1] if not atr_series.isna().all() else last_p * 0.005
    if pd.isna(atr): atr = last_p * 0.005 # Doble seguridad

    col1, col2, col3 = st.columns(3)
    
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
                prob -= 12

            st.markdown(f"""
            <div style="background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #333; border-top: 5px solid {color_base};">
                <h4 style="margin:0; color:{color_base}; text-align:center; font-size:0.9rem;">{c['n']}</h4>
                <div style="text-align:center; margin:10px 0;">
                    <span style="font-size:1.5rem; font-weight:bold; color:white;">{prob}%</span>
                </div>
                <p style="margin:2px 0; font-size:0.8rem;">📍 <b>Entrada:</b> {c['ent']:.{precision}f}</p>
                <p style="margin:2px 0; font-size:0.8rem; color:{color_base};">🎯 <b>TP:</b> {tp:.{precision}f}</p>
                <p style="margin:2px 0; font-size:0.8rem; color:#ff3131;">🛡️ <b>SL:</b> {sl:.{precision}f}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Sincronizar {c['id']}", key=f"sync_v95_{c['id']}", use_container_width=True):
                st.session_state.update({
                    'sl_final': float(sl),
                    'tp_final': float(tp),
                    'lotes_final': float(c['lotes']),
                    'ent_final': float(c['ent'])
                })
                st.toast(f"Estrategia {c['id']} cargada")
                st.rerun() # Forzamos actualización para que el Bridge lea los nuevos datos

# =========================================================
# BLOQUE 9: MOTOR DE NOTICIAS & INTELIGENCIA DE SENTIMIENTO
# =========================================================

@st.cache_data(ttl=600) # Cache de 10 minutos para no quemar la API Key
def fetch_av_sentiment(ticker_limpio, api_key):
    """Consulta la API de Alpha Vantage de forma eficiente"""
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker_limpio}&apikey={api_key}"
    try:
        r = requests.get(url, timeout=5)
        return r.json()
    except:
        return None

def render_sentinel_news(ticker):
    """
    Motor híbrido de noticias con análisis de sentimiento.
    Blindado contra límites de API y errores de duplicidad.
    """
    st.markdown(f"## 📰 TERMINAL DE INTELIGENCIA: {ticker}")
    
    # --- 1. INTELIGENCIA DE SENTIMIENTO (ALPHA VANTAGE) ---
    clean_ticker = ticker.split('=')[0].split('.')[0]
    news_data = fetch_av_sentiment(clean_ticker, AV_API_KEY)
    
    if news_data and "feed" in news_data:
        st.subheader("🎯 SENTIMIENTO DE MERCADO REAL")
        with st.container():
            for i, item in enumerate(news_data["feed"][:4]):
                col_text, col_sent = st.columns([4, 1])
                with col_text:
                    st.markdown(f"**[{item['title']}]({item['url']})**")
                    st.caption(f"Fuente: {item['source']} | Relevancia: {item['relevance_score']}")
                with col_sent:
                    label = item.get('overall_sentiment_label', 'Neutral')
                    color = "#00ff41" if "Bullish" in label else "#ff3131" if "Bearish" in label else "#888"
                    st.markdown(f'<p style="color:{color}; font-weight:bold; margin:0;">{label}</p>', unsafe_allow_html=True)
                st.divider()
    elif news_data and "Note" in news_data:
        st.info("ℹ️ Límite de API alcanzado. Sentinel usando datos en cache...")
    else:
        st.caption("⏳ Esperando actualización de sentimiento Alpha Vantage...")

    # --- 2. MOTOR DE RESPALDO RSS (INVESTING) ---
    st.markdown("### 📡 ÚLTIMA HORA (GLOBAL RSS)")
    try:
        # Usamos cache también para el RSS para acelerar la carga
        f_news = feedparser.parse("https://es.investing.com/rss/news.rss")
        if f_news and f_news.entries:
            for i, entry in enumerate(f_news.entries[:6]):
                # Clave única absoluta para evitar removeChild
                u_key = f"rss_{clean_ticker}_{i}_{st.session_state.get('view', 'main')}"
                
                with st.expander(f"📌 {entry.title[:70]}...", expanded=False):
                    resumen = entry.summary.split('<')[0] if 'summary' in entry else "Ver noticia completa."
                    st.write(resumen)
                    # Botón con key estable
                    if st.button("Sincronizar con Telegram", key=u_key, use_container_width=True):
                        alert_msg = f"🐺 *NOTICIA TRADING*\nActivo: {ticker}\n{entry.title}\n{entry.link}"
                        send_telegram_alert(alert_msg)
                        st.toast("Enviado a Central")
    except Exception as e:
        st.error(f"Fallo en feed RSS: {e}")
# =========================================================
# BLOQUE 10: MOTOR DE DATOS ALPHA VANTAGE (SISTEMA DUAL)
# =========================================================
def get_alpha_vantage_data(symbol):
    """
    Obtiene velas japonesas desde Alpha Vantage como fuente secundaria.
    Blindado contra errores de formato y límites de API.
    """
    try:
        # 1. Construcción de URL según tipo de activo
        if any(x in symbol for x in ["EURUSD", "GBPUSD", "USDJPY", "=X"]):
            # Limpieza para Forex (Extrae el par base, ej: EURUSD)
            base = symbol[:3]
            target = symbol[3:6]
            url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={base}&to_symbol={target}&apikey={AV_API_KEY}&datatype=csv"
        elif "GC=F" in symbol or "GOLD" in symbol:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=GOLD&apikey={AV_API_KEY}&datatype=csv"
        else:
            clean_s = symbol.split('=')[0].split('.')[0]
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={clean_s}&apikey={AV_API_KEY}&datatype=csv"
            
        # 2. Descarga segura
        df_av = pd.read_csv(url)
        
        # Validación: Si Alpha Vantage devuelve error, el CSV tendrá una columna llamada "{ " o "Error Message"
        if df_av.empty or "timestamp" not in df_av.columns:
            return None
        
        # 3. Procesamiento y Estandarización
        df_av['timestamp'] = pd.to_datetime(df_av['timestamp'])
        df_av.set_index('timestamp', inplace=True)
        df_av.sort_index(ascending=True, inplace=True)
        
        # Renombrar columnas (AV las da en minúsculas)
        rename_map = {
            'open': 'Open', 'high': 'High', 'low': 'Low', 
            'close': 'Close', 'volume': 'Volume'
        }
        df_av.rename(columns=rename_map, inplace=True)
        
        # 4. Cálculo de Indicadores Sentinel (Indispensables para el Radar)
        df_av['EMA_20'] = ta.ema(df_av['Close'], length=20)
        df_av['EMA_50'] = ta.ema(df_av['Close'], length=50)
        df_av['RSI'] = ta.rsi(df_av['Close'], length=14)
        
        # Color de volumen para consistencia visual
        df_av['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df_av['Close'], df_av['Open'])]
        
        return df_av.dropna(subset=['Close'])

    except Exception as e:
        # Fallo silencioso en sidebar para no romper la estética principal
        st.sidebar.warning(f"Respaldo AV no disponible: {e}")
        return None
# =========================================================
# BLOQUE 11: ANÁLISIS FUNDAMENTAL (DATA MINING)
# =========================================================
def render_fundamental_analysis(ticker):
    """Extrae métricas de salud financiera con limpieza de datos"""
    
    # SEGURIDAD: Solo ejecutar si el activo es una acción (Stock)
    # Evitamos gastar API keys en Divisas o Índices que no tienen 'Overview'
    if any(x in ticker for x in ["=X", "=F", "^"]):
        return # Salida silenciosa para activos no aplicables

    clean_t = ticker.split('=')[0].split('.')[0]
    
    try:
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={clean_t}&apikey={AV_API_KEY}"
        # Usamos timeout corto para no congelar la UI
        response = requests.get(url, timeout=3)
        data = response.json()
        
        if data and "Symbol" in data:
            st.markdown(f"#### 📊 Análisis de Empresa: {data.get('Name')}")
            c1, c2, c3, c4 = st.columns(4)
            
            # Función interna para limpiar valores N/A
            def safe_f(val, is_pct=False):
                try:
                    num = float(val)
                    return f"{num*100:.2f}%" if is_pct else f"{num:.2f}"
                except (ValueError, TypeError):
                    return "N/A"

            c1.metric("PER Ratio", safe_f(data.get('PERatio')))
            c2.metric("PEG Ratio", safe_f(data.get('PEGRatio')))
            c3.metric("Dividend Yield", safe_f(data.get('DividendYield'), True))
            c4.metric("ROE", safe_f(data.get('ReturnOnEquityTTM')))
            
            with st.expander("🔍 Detalles del Negocio"):
                st.write(data.get('Description', 'Descripción no disponible.'))
                st.markdown(f"**Sector:** {data.get('Sector')} | **Industria:** {data.get('Industry')}")
        else:
            st.info("ℹ️ Datos fundamentales no disponibles para este ticker.")
            
    except Exception as e:
        st.caption("⚠️ Terminal Fundamental: Esperando disponibilidad de red...")
# =========================================================
# BLOQUE 12: ORQUESTADOR FINAL DE ALTA DISPONIBILIDAD
# =========================================================
def run_wolf_orchestrator():
    """Controla el flujo de la app y previene errores de colisión de nodos"""
    
    # 1. Recuperación Segura de Sesión
    t_active = st.session_state.get('ticker', 'NQ=F')
    view = st.session_state.get('view', 'Lobo')
    cat = st.session_state.get('active_cat', 'indices')
    
    # 2. Contenedor Maestro (Estabiliza el DOM de Streamlit)
    main_container = st.container()
    
    with main_container:
        if view == "Noticias":
            render_sentinel_news(t_active)
            
        elif view in ["Lobo", "XTB"]:
            # A. Obtención de datos técnicos (Fuente Primaria: Yahoo)
            # Usamos el intervalo persistente en sesión
            current_int = st.session_state.get('int_top', '1h')
            df = get_market_data(t_active, interval=current_int)
            
            if df is not None and not df.empty:
                # Actualización de precio en tiempo real
                st.session_state.last_price = float(df['Close'].iloc[-1])
                
                # Renderizado en Cascada Sentinel
                render_shielded_chart(df, t_active)
                
                # Mostrar fundamentales solo para stocks, debajo del gráfico
                if cat == "stocks":
                    render_fundamental_analysis(t_active)
                
                render_strategy_cards(df)
                
                # Verificación de existencia del Bridge antes de llamar
                if 'render_sentinel_bridge' in globals():
                    render_sentinel_bridge()
                else:
                    st.caption("🛡️ Bridge en espera de configuración de señales.")
            
            else:
                # B. Fallback Automático (Fuente Secundaria: Alpha Vantage)
                st.warning("🔄 Fuente Yahoo saturada. Activando protocolo de respaldo...")
                df_av = get_alpha_vantage_data(t_active)
                
                if df_av is not None:
                    render_shielded_chart(df_av, t_active)
                    render_strategy_cards(df_av)
                else:
                    st.error("🚨 Error de Red Global: Sin respuesta de servidores. Reintente en 15s.")

        elif view == "Ajustes":
            render_ajustes_view() # Asumiendo que tienes esta función del Bloque 6

# =========================================================
# LANZAMIENTO DEL SISTEMA
# =========================================================
if __name__ == "__main__":
    try:
        # Configuración inicial de la vista si no existe
        if 'view' not in st.session_state:
            st.session_state.view = 'Lobo'
            
        run_wolf_orchestrator()
        
    except Exception as e:
        # Captura de errores "Silent Kill" para depuración rápida
        st.error(f"⚠️ ALERTA DE SISTEMA: {e}")
        st.button("🔄 REINICIAR NÚCLEO", on_click=lambda: st.session_state.clear())

# =========================================================
# FINAL DEL ARCHIVO: WOLF SOVEREIGN PRECISION V95

# =========================================================
