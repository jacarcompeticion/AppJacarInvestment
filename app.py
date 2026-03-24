import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import requests  # Añadido para Telegram
import time

# =========================================================
# 1. ARRANQUE DEL SISTEMA (LÍNEA 1)
# =========================================================
st.set_page_config(
    page_title="WOLF SOVEREIGN v.95", 
    layout="wide", 
    page_icon="🐺",
    initial_sidebar_state="collapsed"
)

# Refresco único global (15 segundos)
st_autorefresh(interval=15000, key="wolf_global_refresh")

# --- CONFIGURACIÓN DE TELEGRAM (Cámbialo por tus datos) ---
TELEGRAM_TOKEN = "TU_TOKEN_AQUÍ"
TELEGRAM_CHAT_ID = "TU_ID_AQUÍ"

# =========================================================
# 2. GESTIÓN DE ESTADO ÚNICA (SESSION STATE)
# =========================================================
if 'setup_complete' not in st.session_state:
    st.session_state.update({
        'setup_complete': True,
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
        'lotes_final': 0.10
    })

# =========================================================
# 3. MOTOR DE DATOS ROBUSTO
# =========================================================
def get_cleaned_data(ticker, interval='1h'):
    try:
        data = yf.download(ticker, period='5d', interval=interval, progress=False)
        if data.empty:
            return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df['Close'], df['Open'])]
        return df.dropna(subset=['Close'])
    except Exception as e:
        st.error(f"Error en flujo de datos: {e}")
        return None

# =========================================================
# 4. SISTEMA DE ALERTAS
# =========================================================
def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        st.sidebar.error(f"Error Telegram: {e}")
# =========================================================
# 2. MOTOR DE ESTILOS WOLF SOVEREIGN (UI PREMIUM)
# =========================================================

# Eliminamos la redundancia de set_page_config que causaba el bloqueo.
# Los estilos se inyectan directamente para una carga ultra-rápida.

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
# Categorías: stocks, indices, material, divisas
DATABASE = {
    "stocks": {
        "Dividendos TOP (ES)": {
            "Enagás (ENG.MC)": ["ENG.MC", "Yield ~10%"],
            "Logista (LOG.MC)": ["LOG.MC", "Yield ~6.5%"],
            "Endesa (ELE.MC)": ["ELE.MC", "Yield ~7%"]
        },
        "Potencial Inversión": {
            "Inditex (ITX.MC)": ["ITX.MC", "Crecimiento Sólido"],
            "Iberdrola (IBE.MC)": ["IBE.MC", "Líder Renovables"],
            "Grifols (GRF.MC)": ["GRF.MC", "Recuperación Táctica"]
        }
    },
    "indices": {
        "Principales": {
            "IBEX 35": ["^IBEX", "España"],
            "S&P 500": ["^GSPC", "USA"],
            "DAX 40": ["^GDAXI", "Alemania"],
            "VIX (Miedo)": ["^VIX", "Cobertura"] # Sube cuando el mercado cae
        }
    },
    "material": {
        "Energía": {
            "Petróleo Brent": ["BZ=F", "Energía Global"],
            "Gas Natural": ["NG=F", "Alta Volatilidad"]
        },
        "Metales Tácticos": {
            "Oro": ["GC=F", "Refugio"],
            "Plata": ["SI=F", "Industrial/Refugio"],
            "Cobre": ["HG=F", "Barómetro Económico"] # El "Doctor Cobre" predice recesiones
        }
    },
    "divisas": {
        "Mayores": {
            "EUR/USD": ["EURUSD=X", "Euro"],
            "GBP/USD": ["GBPUSD=X", "Libra"],
            "USD/JPY": ["JPY=X", "Yen"]
        },
        "Refugio/Carry": {
            "USD/CHF": ["USDCHF=X", "Franco Suizo"], # Refugio máximo
            "USD/MXN": ["USDMXN=X", "Peso Mexicano"] # Alta volatilidad/Carry Trade
        }
    }
}
# =========================================================
# 4. MOTOR DE DATOS (PRECISIÓN ALTA - YFINANCE ENGINE)
# =========================================================
def get_market_data(ticker, interval='1h'):
    """Descarga y procesa datos con indicadores técnicos robustos"""
    try:
        # Optimización de periodos para evitar latencia y errores de RAM
        period_map = {'1m': '1d', '5m': '1d', '15m': '5d', '1h': '1mo', '1d': '6mo'}
        selected_period = period_map.get(interval, '1mo')
        
        data = yf.download(ticker, period=selected_period, interval=interval, progress=False)
        
        if data is None or data.empty:
            return None
        
        df = data.copy()
        
        # Aplanamiento de MultiIndex (Obligatorio para yfinance moderno)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.columns = [str(col).strip() for col in df.columns]
            
        # Indicadores Técnicos con pandas_ta
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Rellenar valores iniciales para evitar huecos en el gráfico
        df[['EMA_20', 'EMA_50', 'RSI']] = df[['EMA_20', 'EMA_50', 'RSI']].bfill()
        
        # Color del volumen (Verde Neón / Rojo Sangre)
        df['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df['Close'], df['Open'])]
        
        return df.dropna(subset=['Close'])
        
    except Exception as e:
        st.error(f"Error Crítico en Motor de Datos: {e}")
        return None

# =========================================================
# 5. COMPONENTES VISUALES (RADAR & ESTRATEGIA)
# =========================================================
def render_radar(df, ticker_name):
    """Dibuja el gráfico profesional Wolf con 3 niveles"""
    # Clave única robusta combinando ticker e intervalo
    chart_key = f"radar_{st.session_state.ticker}_{len(df)}"
    
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_width=[0.15, 0.20, 0.65],
        subplot_titles=("SISTEMA DE PRECIO", "FUERZA RSI", "VOLUMEN")
    )

    # Velas Profesionales
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Market', increasing_line_color='#00ff41', decreasing_line_color='#ff3131'
    ), row=1, col=1)

    # Medias Móviles (Oro y Plata)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#FFD700', width=1.5), name='EMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='#C0C0C0', width=1), name='EMA 50'), row=1, col=1)
    
    # RSI (Púrpura Sentinel)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#8A2BE2', width=2), name='RSI'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff3131", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00ff41", opacity=0.5, row=2, col=1)

    # Volumen
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Vol_Color'], name='Vol'), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", height=700, 
        margin=dict(l=10, r=10, t=30, b=10), 
        xaxis_rangeslider_visible=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)

def render_strategy_cards(df):
    """Genera señales de trading robustas con ATR dinámico"""
    st.markdown("### 🎯 SEÑALES SENTINEL")
    
    if df is None or len(df) < 2:
        st.warning("Esperando flujo de datos...")
        return

    last_p = float(df['Close'].iloc[-1])
    ema_v = float(df['EMA_20'].iloc[-1])
    ticker = st.session_state.ticker
    
    # Precisión adaptativa (Divisas vs Stocks)
    prec = 5 if any(x in ticker for x in ["=X", "EUR", "USD"]) else 2
    
    tendencia = "ALCISTA" if last_p > ema_v else "BAJISTA"
    color = "#00ff41" if tendencia == "ALCISTA" else "#ff3131"
    
    # ATR Simplificado para Stop Loss
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
        # Clave única para el formulario para evitar bloqueos
        with st.form(key=f"form_trade_{ticker}_{prec}"):
            lotes = st.number_input("Volumen", value=0.10, step=0.01, min_value=0.01)
            sl_f = st.number_input("S/L Real", value=float(sl), format=f"%.{prec}f")
            tp_f = st.number_input("T/P Real", value=float(tp), format=f"%.{prec}f")
            
            if st.form_submit_button("VIGILAR OPERACIÓN"):
                msg = f"🐺 *SENTINEL* - {st.session_state.ticker_name}\nLotes: {lotes}\nSL: {sl_f}\nTP: {tp_f}"
                send_telegram_alert(msg)
                st.success("Alerta Sincronizada")
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

# 2. Ticker de noticias (Optimizado y Circular)
hot_list = [("NQ=F", "US100", "▲"), ("GC=F", "ORO", "▼"), ("EURUSD=X", "EURUSD", "▲")]
content = "".join([f'<div class="ticker-item">{n} {i} {t}</div>' for t, n, i in hot_list * 5])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# 3. Menú Principal (Navegación Superior)
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
    # FILA 1: CATEGORÍAS (stocks, indices, material, divisas)
    cats = list(DATABASE.keys())
    c_cat = st.columns(len(cats))
    for i, cat in enumerate(cats):
        tag = "menu-active" if st.session_state.active_cat == cat else "menu-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(cat.upper(), key=f"btn_cat_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = list(DATABASE[cat].keys())[0]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # FILA 2: SUBCATEGORÍAS
    if st.session_state.active_cat in DATABASE:
        subs = list(DATABASE[st.session_state.active_cat].keys())
        # Rejilla dinámica para subcategorías
        c_sub = st.columns(4) 
        for i, sub in enumerate(subs):
            tag = "menu-active" if st.session_state.active_sub == sub else "menu-btn"
            with c_sub[i % 4]:
                st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                if st.button(sub, key=f"btn_sub_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # FILA 3: ACTIVOS FINALES
        if st.session_state.active_sub in DATABASE[st.session_state.active_cat]:
            activos = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
            cols_act = st.columns(4)
            for i, (name, val) in enumerate(activos.items()):
                tag = "menu-active" if st.session_state.ticker_name == name else "menu-btn"
                with cols_act[i % 4]:
                    st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                    if st.button(name, key=f"btn_act_{val[1]}", use_container_width=True):
                        st.session_state.ticker = val[0]
                        st.session_state.ticker_name = name
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- SELECTOR DE TEMPORALIDAD (Vital para el éxito del gráfico) ---
    st.markdown("---")
    t_cols = st.columns([1, 1, 1, 1, 1, 5])
    tiempos = ["1m", "5m", "15m", "1h", "1d"]
    if 'int_top' not in st.session_state: st.session_state.int_top = "1h"
    
    for i, t in enumerate(tiempos):
        with t_cols[i]:
            if st.button(t, key=f"t_{t}", type="primary" if st.session_state.int_top == t else "secondary"):
                st.session_state.int_top = t
                st.rerun()

    # RENDERIZADO DE MERCADO
    df_lobo = get_market_data(st.session_state.ticker, interval=st.session_state.int_top)
    if df_lobo is not None:
        render_radar(df_lobo, st.session_state.ticker_name)
        render_strategy_cards(df_lobo)
    else:
        st.warning(f"📡 Sincronizando {st.session_state.ticker_name}... Reintento automático en 15s.")

elif st.session_state.view == "Noticias":
    st.title("📰 Sentinel News Feed")
    # Nota: Asegúrate de que la función render_sentinel_news esté definida más adelante
    st.info("Cargando flujo de noticias financieras...")

elif st.session_state.view == "Ajustes":
    st.title("⚙️ Configuración Wolf")
    st.session_state.wallet = st.number_input("Capital Total (€)", value=float(st.session_state.wallet))
    if st.button("ACTUALIZAR"): st.success("Parámetros guardados.")

else:
    st.info(f"Sección {st.session_state.view} operativa próximamente.")
# =========================================================
# BLOQUE 7: RADAR VISUAL (VOLUMEN BICOLOR & CONTROLES)
# =========================================================
def render_shielded_chart(df, ticker_actual):
    """
    Renderiza el radar táctico Wolf con triple panel.
    Corregido: Manejo de tipos para líneas XTB y estabilidad de keys.
    """
    if df is None or len(df) == 0:
        st.warning("📡 Sincronizando radar de alta precisión...")
        return

    # --- 1. MÉTRICAS RÁPIDAS (Justo encima del gráfico) ---
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        # Mostramos la temporalidad activa (viene del session_state)
        st.info(f"⏳ ESCALA: {st.session_state.get('int_top', '1h')}")
    
    with c2:
        current_price = float(df['Close'].iloc[-1])
        open_p = float(df['Open'].iloc[-1])
        delta = current_price - open_p
        st.metric("PRECIO ACTUAL", f"{current_price:,.2f}", delta=f"{delta:,.2f}")
    
    with c3:
        st.write(f"🛰️ **RADAR ACTIVO:** {st.session_state.ticker_name}")

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

    # C. RSI (Púrpura)
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

    # --- 3. NIVELES REALES (Dibujamos tus órdenes si existen) ---
    active_trades = st.session_state.get('active_trades', [])
    for op in active_trades:
        if op.get('ticker') == ticker_actual:
            try:
                e, s, t = float(op['entrada']), float(op['sl']), float(op['tp'])
                fig.add_hline(y=e, line_color="#0066ff", line_dash="dash", annotation_text="ORDEN", row=1, col=1)
                fig.add_hline(y=s, line_color="#ff3131", line_dash="dot", annotation_text="STOP", row=1, col=1)
                fig.add_hline(y=t, line_color="#00ff41", line_dash="dot", annotation_text="TARGET", row=1, col=1)
            except:
                continue 

    # --- 4. ESTÉTICA ---
    fig.update_layout(
        template="plotly_dark", height=700, xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{ticker_actual}_{len(df)}")

# =========================================================
# BLOQUE 8: ESTRATEGIAS CON PRECISIÓN DINÁMICA
# =========================================================
def render_strategy_cards(df):
    """Calcula y presenta estrategias automáticas Sentinel"""
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
    precision = 5 if any(x in ticker for x in ["=X", "EUR", "USD", "GBP", "divisas"]) else 2

    es_compra = last_p > ema_v
    color_base = "#00ff41" if es_compra else "#ff3131"
    
    # ATR Robusto (Cálculo manual para evitar NaNs en inicios de sesión)
    atr = (df['High'] - df['Low']).tail(14).mean()
    if pd.isna(atr) or atr == 0: atr = last_p * 0.005 

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
            
            # Penalización por sobrecompra/sobreventa
            prob = c["p"]
            if (rsi_v > 70 and es_compra) or (rsi_v < 30 and not es_compra): prob -= 12

            st.markdown(f"""
            <div style="background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #333; border-top: 5px solid {color_base};">
                <h4 style="margin:0; color:{color_base}; text-align:center; font-size:0.9rem;">{c['n']}</h4>
                <div style="text-align:center; margin:10px 0;">
                    <span style="font-size:1.5rem; font-weight:bold; color:white;">{prob}%</span>
                </div>
                <p style="margin:2px 0; font-size:0.8rem;">📍 <b>Entrada:</b> {c['ent']:.{precision}f}</p>
                <p style="margin:2px 0; font-size:0.8rem; color:#00ff41;">🎯 <b>TP:</b> {tp:.{precision}f}</p>
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
                st.rerun()
# =========================================================
# BLOQUE 9: BRIDGE XTB & GESTIÓN DE ÓRDENES (OPERATIVA)
# =========================================================
def render_xtb_bridge():
    """Panel de ejecución táctica sincronizado con Sentinel"""
    st.markdown("---")
    st.subheader("💼 BRIDGE XTB - EJECUCIÓN")
    
    # Asegurar existencia de variables para evitar errores de carga inicial
    if 'sl_final' not in st.session_state: st.session_state.sl_final = 0.0
    if 'tp_final' not in st.session_state: st.session_state.tp_final = 0.0
    if 'lotes_final' not in st.session_state: st.session_state.lotes_final = 0.10
    if 'ent_final' not in st.session_state: st.session_state.ent_final = 0.0

    ticker = st.session_state.get('ticker', 'NQ=F')
    precision = 5 if any(x in ticker for x in ["=X", "EUR", "USD"]) else 2

    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            lotes = st.number_input("VOLUMEN (LOTES)", 
                                   value=float(st.session_state.lotes_final), 
                                   step=0.01, format="%.2f")
        with col2:
            sl_real = st.number_input("STOP LOSS REAL", 
                                     value=float(st.session_state.sl_final), 
                                     format=f"%.{precision}f")
        with col3:
            tp_real = st.number_input("TAKE PROFIT REAL", 
                                     value=float(st.session_state.tp_final), 
                                     format=f"%.{precision}f")

        # Botón de ejecución con feedback visual
        if st.button("🚀 ENVIAR ORDEN A CENTRAL", use_container_width=True, type="primary"):
            if sl_real == 0 or tp_real == 0:
                st.error("⚠️ Error: Define niveles de SL y TP antes de enviar.")
            else:
                # Construcción del mensaje para Telegram/Registro
                msg = (
                    f"🐺 **ORDEN WOLF EXECUTED**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📈 **Activo:** {st.session_state.ticker_name}\n"
                    f"📦 **Lotes:** {lotes}\n"
                    f"🛡️ **SL:** {sl_real:.{precision}f}\n"
                    f"🎯 **TP:** {tp_real:.{precision}f}\n"
                    f"💰 **Entrada Est.:** {st.session_state.ent_final:.{precision}f}\n"
                    f"━━━━━━━━━━━━━━━"
                )
                
                # Intentamos enviar alerta
                send_telegram_alert(msg)
                
                # Guardamos en el historial de la sesión
                new_trade = {
                    'ticker': ticker,
                    'entrada': st.session_state.ent_final,
                    'sl': sl_real,
                    'tp': tp_real,
                    'lotes': lotes,
                    'time': time.strftime("%H:%M:%S")
                }
                st.session_state.active_trades.append(new_trade)
                st.success(f"Orden sobre {st.session_state.ticker_name} sincronizada con éxito.")
                time.sleep(1)
                st.rerun()

# =========================================================
# BLOQUE 10: MONITOR DE POSICIONES ACTIVAS
# =========================================================
def render_active_positions():
    """Muestra y gestiona las órdenes enviadas en la sesión actual"""
    st.markdown("---")
    st.subheader("📑 ÓRDENES EN VIGILANCIA")
    
    if not st.session_state.active_trades:
        st.info("No hay órdenes activas registradas en esta sesión.")
        return

    for i, trade in enumerate(st.session_state.active_trades):
        with st.expander(f"🟢 {trade['ticker']} | Lotes: {trade['lotes']} | {trade['time']}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("SL", trade['sl'])
            c2.metric("TP", trade['tp'])
            if c3.button("CERRAR REGISTRO", key=f"close_{i}"):
                st.session_state.active_trades.pop(i)
                st.rerun()
# =========================================================
# BLOQUE 11: ANÁLISIS FUNDAMENTAL (DATA MINING)
# =========================================================
# Introduce tu clave de Alpha Vantage aquí para fundamentales
AV_API_KEY = "TU_API_KEY_AQUÍ"

def render_fundamental_analysis(ticker):
    """Extrae métricas de salud financiera con limpieza de datos"""
    
    # SEGURIDAD: Solo para stocks. Divisas/Índices no tienen 'Overview'.
    if any(x in ticker for x in ["=X", "=F", "^"]):
        return 

    clean_t = ticker.split('=')[0].split('.')[0]
    
    try:
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={clean_t}&apikey={AV_API_KEY}"
        response = requests.get(url, timeout=3)
        data = response.json()
        
        if data and "Symbol" in data:
            st.markdown(f"#### 📊 Análisis Fundamental: {data.get('Name')}")
            c1, c2, c3, c4 = st.columns(4)
            
            def safe_f(val, is_pct=False):
                try:
                    num = float(val)
                    return f"{num*100:.2f}%" if is_pct else f"{num:.2f}"
                except: return "N/A"

            c1.metric("PER Ratio", safe_f(data.get('PERatio')))
            c2.metric("PEG Ratio", safe_f(data.get('PEGRatio')))
            c3.metric("Div. Yield", safe_f(data.get('DividendYield'), True))
            c4.metric("ROE", safe_f(data.get('ReturnOnEquityTTM')))
            
            with st.expander("🔍 Detalles del Negocio"):
                st.write(data.get('Description', 'Descripción no disponible.'))
                st.caption(f"**Sector:** {data.get('Sector')} | **Industria:** {data.get('Industry')}")
    except:
        st.caption("ℹ️ Datos fundamentales en espera de conexión...")

# =========================================================
# BLOQUE 12: ORQUESTADOR FINAL DE ALTA DISPONIBILIDAD
# =========================================================
def run_wolf_orchestrator():
    """Controla el flujo maestro de la app Wolf Sovereign"""
    
    t_active = st.session_state.get('ticker', 'NQ=F')
    view = st.session_state.get('view', 'Lobo')
    cat = st.session_state.get('active_cat', 'indices')
    
    # Renderizado según la vista seleccionada en el menú superior
    if view == "Lobo":
        # 1. Obtención de datos técnicos (Motor YFinance Saneado)
        current_int = st.session_state.get('int_top', '1h')
        df = get_market_data(t_active, interval=current_int)
        
        if df is not None and not df.empty:
            st.session_state.last_price = float(df['Close'].iloc[-1])
            
            # 2. Renderizado de Gráfico y Estrategia
            render_shielded_chart(df, t_active)
            
            # 3. Fundamentales (Solo si es categoría Stocks)
            if cat == "stocks":
                render_fundamental_analysis(t_active)
            
            # 4. Cartas de Estrategia y Bridge Operativo
            render_strategy_cards(df)
            render_xtb_bridge() # Llamamos a la función del Bloque 6
            render_active_positions()
            
        else:
            st.error("🚨 Error de Sincronización: El servidor de datos no responde. Reintentando...")

    elif view == "Ajustes":
        # Esta lógica ya está integrada en el orquestador del Bloque 4
        pass 

    elif view == "Noticias":
        st.subheader("📰 Sentinel Global News")
        st.info("Conectando con el feed de Reuters/Bloomberg...")
        # Aquí puedes añadir tu lógica de render_sentinel_news si la tienes

# =========================================================
# LANZAMIENTO DEL SISTEMA
# =========================================================
if __name__ == "__main__":
    try:
        # Aseguramos que el estado inicial sea robusto
        if 'active_trades' not in st.session_state:
            st.session_state.active_trades = []
        
        run_wolf_orchestrator()
        
    except Exception as e:
        st.error(f"⚠️ ERROR CRÍTICO DE NÚCLEO: {e}")
        if st.button("🔄 REINICIAR SISTEMA"):
            st.session_state.clear()
            st.rerun()
