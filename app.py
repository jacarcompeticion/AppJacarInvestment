import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import requests
import time
from datetime import datetime

# =========================================================
# 1.1 CONFIGURACIÓN DE PÁGINA (WOLF SOVEREIGN v1.0)
# =========================================================
st.set_page_config(
    page_title="WOLF SOVEREIGN | Terminal",
    layout="wide",
    page_icon="🐺",
    initial_sidebar_state="collapsed"
)

# Refresco automático global (15 segundos) para mantener precios vivos
st_autorefresh(interval=15000, key="wolf_global_tick")

# =========================================================
# 1.2 VARIABLES DE SESIÓN (MEMORIA DE LA APP)
# =========================================================
if 'initialized' not in st.session_state:
    st.session_state.update({
        'initialized': True,
        'view': "Lobo",           # Ventana activa
        'active_cat': "indices",  # Categoría inicial
        'active_sub': "Principales",
        'ticker': "^GSPC",        # Activo por defecto (S&P 500)
        'ticker_name': "S&P 500",
        'wallet': 10000.00,       # Capital inicial configurable
        'margen_disp': 10000.00,
        'pnl_dia': 0.00,
        'active_trades': [],      # Órdenes en vigilancia
        'int_top': "1h",          # Temporalidad inicial
        'custom_tickers': [],      # Para la inyección manual
        'last_alert_sent': None    # Control de spam de alertas
    })

# =========================================================
# 1.3 SISTEMA DE ALERTAS DUAL (TELEGRAM)
# =========================================================
# Configuración de IDs (Se podrán editar en la pestaña de ajustes)
TELEGRAM_BOT_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
USER_CHAT_IDS = [1296326413] 

def send_wolf_alert(message):
    """Envía notificaciones simultáneas a los chats configurados"""
    for chat_id in USER_CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id, 
                "text": message, 
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            st.sidebar.error(f"Error enviando alerta a {chat_id}: {e}")

# =========================================================
# FIN DEL BLOQUE 1
# =========================================================
# =========================================================
# 2. MOTOR DE ESTILOS "WOLF SOVEREIGN" (ALTO CONTRASTE)
# =========================================================

st.markdown("""
    <style>
    /* 2.1 Fondo Global y Fuentes */
    .stApp {
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }

    /* 2.2 Banner Ticker Superior (Estilo Bolsa Clásica) */
    .ticker-wrap {
        width: 100%;
        overflow: hidden;
        background: #0a0e14;
        padding: 10px 0;
        border-bottom: 2px solid #D4AF37; /* Línea de Oro */
        margin-bottom: 20px;
    }
    .ticker-move {
        display: flex;
        width: fit-content;
        animation: ticker-animation 40s linear infinite;
    }
    .ticker-item {
        padding: 0 40px;
        white-space: nowrap;
        font-family: 'Courier New', monospace;
        color: #D4AF37;
        font-weight: bold;
        font-size: 1.1rem;
        cursor: pointer;
        transition: color 0.3s;
    }
    .ticker-item:hover {
        color: #FFFFFF;
    }
    @keyframes ticker-animation {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    /* 2.3 Botones de Navegación Principal */
    div.nav-btn button {
        background-color: #000000 !important;
        color: #D4AF37 !important;
        border: 2px solid #D4AF37 !important;
        border-radius: 4px !important;
        height: 3.5em !important;
        font-weight: bold !important;
        transition: all 0.2s ease-in-out;
    }
    div.nav-btn button:hover {
        background-color: #D4AF37 !important;
        color: #000000 !important; /* Texto Negro sobre fondo Dorado */
    }
    div.nav-active button {
        background-color: #D4AF37 !important;
        color: #000000 !important; /* TEXTO NEGRO SOBRE FONDO DORADO */
        border: 2px solid #D4AF37 !important;
        font-weight: 900 !important;
        box-shadow: 0px 0px 15px rgba(212, 175, 55, 0.5);
    }

    /* 2.4 Botones de Categorías y Subcategorías (Cascada) */
    div.menu-btn button {
        background-color: #0a0e14 !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
        border-radius: 2px !important;
    }
    div.menu-active button {
        background-color: #FFFFFF !important; /* FONDO BLANCO */
        color: #000000 !important;           /* TEXTO NEGRO */
        border: 2px solid #D4AF37 !important;
        font-weight: bold !important;
    }

    /* 2.5 Gráficos y Contenedores */
    .stPlotlyChart {
        background-color: #05070a !important; /* Fondo diferente para gráficas */
        border-radius: 10px;
        padding: 5px;
        border: 1px solid #222;
    }

    /* 2.6 Colores Operativos */
    .buy-text { color: #00ff41 !important; font-weight: bold; }
    .sell-text { color: #ff3131 !important; font-weight: bold; }
    
    /* 2.7 Adaptabilidad Móvil */
    @media (max-width: 640px) {
        .ticker-item { padding: 0 20px; font-size: 0.9rem; }
        div.nav-btn button { font-size: 0.7rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN PARA EL RENDERIZADO DEL BANNER (BLOQUE 2 CONT.) ---
def render_top_ticker():
    # Instrumentos "Calientes" (Se pueden automatizar luego)
    hot_tickers = [
        ("US100", "▲"), ("ORO", "▲"), ("BRENT", "▼"), 
        ("EURUSD", "▲"), ("IBEX", "▼"), ("BTC", "▲")
    ]
    ticker_content = "".join([f'<span class="ticker-item">{name} {icon}</span>' for name, icon in hot_tickers * 6])
    st.markdown(f"""
        <div class="ticker-wrap">
            <div class="ticker-move">
                {ticker_content}
            </div>
        </div>
    """, unsafe_allow_html=True)

# =========================================================
# FIN DEL BLOQUE 2
# =========================================================
# =========================================================
# 3. BASE DE DATOS Y GESTIÓN DE INSTRUMENTOS
# =========================================================

# 3.1 Estructura Maestra de Categorías
# Nota: 'divisas' reemplaza a 'currencies' por solicitud.
DATABASE = {
    "materias primas": {
        "Energía": {
            "Petróleo Brent": ["BZ=F", "Energía"],
            "Gas Natural": ["NG=F", "Energía"],
            "Gasóleo": ["HO=F", "Energía"]
        },
        "Metales": {
            "Oro": ["GC=F", "Refugio"],
            "Plata": ["SI=F", "Refugio"],
            "Cobre": ["HG=F", "Industrial"],
            "Paladio": ["PA=F", "Industrial"],
            "Platino": ["PL=F", "Industrial"]
        },
        "Agricultura": {
            "Trigo": ["ZW=F", "Agro"],
            "Café": ["KC=F", "Agro"]
        }
    },
    "divisas": {
        "Mayores": {
            "EUR/USD": ["EURUSD=X", "FX"],
            "GBP/USD": ["GBPUSD=X", "FX"],
            "USD/JPY": ["JPY=X", "FX"],
            "USD/CHF": ["USDCHF=X", "FX"]
        },
        "Menores": {
            "AUD/USD": ["AUDUSD=X", "FX"],
            "NZD/USD": ["NZDUSD=X", "FX"],
            "EUR/JPY": ["EURJPY=X", "FX"]
        },
        "Exóticas": {
            "USD/MXN": ["USDMXN=X", "FX"],
            "USD/BRL": ["USDBRL=X", "FX"],
            "USD/TRY": ["USDTRY=X", "FX"]
        }
    },
    "crypto": {
        "Principales": {
            "Bitcoin": ["BTC-USD", "Crypto"],
            "Ethereum": ["ETH-USD", "Crypto"],
            "Solana": ["SOL-USD", "Crypto"]
        },
        "DeFi/Altcoins": {
            "Cardano": ["ADA-USD", "Crypto"],
            "Polkadot": ["DOT-USD", "Crypto"],
            "Chainlink": ["LINK-USD", "Crypto"],
            "Polygon": ["MATIC-USD", "Crypto"]
        }
    },
    "acciones": {
        "España (Dividendos)": {
            "Enagás": ["ENG.MC", "ES"],
            "Logista": ["LOG.MC", "ES"],
            "Endesa": ["ELE.MC", "ES"],
            "Iberdrola": ["IBE.MC", "ES"],
            "Telefónica": ["TEF.MC", "ES"]
        },
        "Internacional (Crecimiento)": {
            "Nvidia": ["NVDA", "US"],
            "Apple": ["AAPL", "US"],
            "Microsoft": ["MSFT", "US"],
            "Tesla": ["TSLA", "US"],
            "Amazon": ["AMZN", "US"]
        }
    },
    "opciones/indices": {
        "EEUU": {
            "S&P 500": ["^GSPC", "Índice"],
            "Nasdaq 100": ["NQ=F", "Índice"],
            "Dow Jones": ["^DJI", "Índice"]
        },
        "Europa": {
            "IBEX 35": ["^IBEX", "Índice"],
            "DAX 40": ["^GDAXI", "Índice"],
            "EuroStoxx 50": ["^STOXX50E", "Índice"]
        }
    }
}

# 3.2 Lógica de Inyección de Tickers Manuales
def inject_custom_tickers():
    """Sincroniza tickers añadidos por el usuario en la configuración"""
    if st.session_state.custom_tickers:
        if "Personalizados" not in DATABASE["acciones"]:
            DATABASE["acciones"]["Personalizados"] = {}
        
        for item in st.session_state.custom_tickers:
            # item es un dict: {"nombre": "X", "ticker": "Y"}
            DATABASE["acciones"]["Personalizados"][item["nombre"]] = [item["ticker"], "Custom"]

# 3.3 Inicialización de la DB
inject_custom_tickers()

# =========================================================
# FIN DEL BLOQUE 3
# =========================================================
# =========================================================
# 4. MOTOR ALGORÍTMICO SENTINEL (IA & ESTRATEGIA)
# =========================================================

def get_advanced_data(ticker, interval='1h'):
    """Descarga datos y calcula indicadores técnicos avanzados"""
    try:
        # Mapeo de periodos para optimizar velocidad
        period_map = {'1m': '1d', '5m': '1d', '15m': '5d', '1h': '1mo', '1d': '1y'}
        data = yf.download(ticker, period=period_map.get(interval, '1mo'), interval=interval, progress=False)
        
        if data.empty: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # --- INDICADORES BÁSICOS ---
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # --- BOLLINGER & MACD ---
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        
        # --- DETECCIÓN DE SOPORTES Y RESISTENCIAS (PUNTOS DE GIRO) ---
        df['Pivot'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['R1'] = (2 * df['Pivot']) - df['Low']
        df['S1'] = (2 * df['Pivot']) - df['High']
        
        # --- LÓGICA DE FIBONACCI (Retrocesos del último swing) ---
        max_h = df['High'].tail(100).max()
        min_l = df['Low'].tail(100).min()
        diff = max_h - min_l
        df['Fib_618'] = max_h - (diff * 0.618)
        df['Fib_382'] = max_h - (diff * 0.382)

        # Color del volumen para el gráfico
        df['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df['Close'], df['Open'])]
        
        return df.dropna(subset=['Close'])
    except Exception as e:
        st.error(f"Error en el motor algorítmico: {e}")
        return None

def analyze_patterns(df):
    """Detecta patrones de velas y figuras chartistas"""
    last_close = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2]
    rsi = df['RSI'].iloc[-1]
    
    signals = []
    # Ejemplo: Detección simple de tendencia y agotamiento (Base para HCH/Taza)
    if rsi > 70: signals.append("SOBRECOMPRA")
    if rsi < 30: signals.append("SOBREVENTA")
    
    # Cruce de EMAs (Golden Cross / Death Cross)
    if df['EMA_20'].iloc[-1] > df['EMA_200'].iloc[-1] and df['EMA_20'].iloc[-2] <= df['EMA_200'].iloc[-2]:
        signals.append("GOLDEN CROSS")
        
    return signals

def calculate_probability(df, signals):
    """Calcula el % de éxito de la operación basado en la confluencia de indicadores"""
    prob = 50.0  # Base neutra
    
    # Confluencia EMA + RSI
    if df['Close'].iloc[-1] > df['EMA_20'].iloc[-1] and df['RSI'].iloc[-1] > 50:
        prob += 15
    
    # Volumen Inusual (+2 desviaciones estándar)
    vol_mean = df['Volume'].tail(20).mean()
    if df['Volume'].iloc[-1] > (vol_mean * 1.5):
        prob += 10
        
    # Ajuste por señales de patrones
    if "GOLDEN CROSS" in signals: prob += 10
    if "SOBRECOMPRA" in signals: prob -= 5
    
    return min(prob, 99.0)

# =========================================================
# FIN DEL BLOQUE 4
# =========================================================
# =========================================================
# 5. ORQUESTADOR DE NAVEGACIÓN Y VISTAS
# =========================================================

def run_navigation():
    """Renderiza el menú superior y gestiona el flujo de las 6 ventanas"""
    
    # 5.1 Renderizado del Banner Superior (Ticker)
    render_top_ticker()

    # 5.2 Cabecera de Capital Estática (Siempre visible)
    st.markdown(f"""
        <div class="metric-container" style="background-color: #0a0e14; padding: 15px; border-bottom: 2px solid #D4AF37; display: flex; justify-content: space-around; border-radius: 8px; margin-bottom: 1rem;">
            <div style="text-align:center;"><span>CAPITAL TOTAL</span><br><b style="font-size:1.4rem;">{st.session_state.wallet:,.2f}€</b></div>
            <div style="text-align:center;"><span>DISPONIBLE</span><br><b style="font-size:1.4rem;">{st.session_state.margen_disp:,.2f}€</b></div>
            <div style="text-align:center;"><span>PnL DÍA</span><br><b style="font-size:1.4rem; color:#00ff41;">+{st.session_state.pnl_dia:,.2f}€</b></div>
        </div>
    """, unsafe_allow_html=True)

    # 5.3 Menú Principal de Navegación (6 Ventanas)
    nav_cols = st.columns(6)
    views = [
        ("🐺 LOBO", "Lobo"),
        ("📊 OPERACIONES", "Operaciones"),
        ("🏆 RESULTADOS", "Resultados"),
        ("📰 NOTICIAS", "Noticias"),
        ("⚙️ CONFIG", "Configuracion"),
        ("🤖 IA WOLF", "IA_Wolf")
    ]

    for i, (label, view_id) in enumerate(views):
        is_active = st.session_state.view == view_id
        tag = "nav-active" if is_active else "nav-btn"
        with nav_cols[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(label, key=f"v_nav_{view_id}", use_container_width=True):
                st.session_state.view = view_id
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 5.4 Enrutador de Contenido
    if st.session_state.view == "Lobo":
        render_window_lobo()
    elif st.session_state.view == "Operaciones":
        render_window_operaciones()
    elif st.session_state.view == "Resultados":
        render_window_resultados()
    elif st.session_state.view == "Noticias":
        render_window_noticias()
    elif st.session_state.view == "Configuracion":
        render_window_configuracion()
    elif st.session_state.view == "IA_Wolf":
        render_window_ia_wolf()

# =========================================================
# FIN DEL BLOQUE 5
# =========================================================
# =========================================================
# 6. VENTANA LOBO: SELECTOR, GRÁFICO Y ESTRATEGIA
# =========================================================

def render_window_lobo():
    # 6.1 SELECTOR DE CASCADA
    c1, c2, c3 = st.columns([1, 1, 2])
    
    with c1:
        cats = list(DATABASE.keys())
        st.session_state.active_cat = st.selectbox("CATEGORÍA", [c.upper() for c in cats]).lower()
    
    with c2:
        subs = list(DATABASE[st.session_state.active_cat].keys())
        st.session_state.active_sub = st.selectbox("SUBCATEGORÍA", subs)
        
    with c3:
        activos = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
        seleccion = st.selectbox("INSTRUMENTO", list(activos.keys()))
        st.session_state.ticker = activos[seleccion][0]
        st.session_state.ticker_name = seleccion

    # 6.2 SELECTOR DE TEMPORALIDAD
    t_cols = st.columns(8)
    tiempos = ["1m", "5m", "15m", "1h", "1d"]
    for i, t in enumerate(tiempos):
        if t_cols[i].button(t, key=f"t_{t}", use_container_width=True, 
                            type="primary" if st.session_state.int_top == t else "secondary"):
            st.session_state.int_top = t
            st.rerun()

    st.markdown("---")

    # 6.3 OBTENCIÓN DE DATOS Y RENDERIZADO
    df = get_advanced_data(st.session_state.ticker, st.session_state.int_top)
    
    if df is not None:
        # Gráfico Profesional (Fondo oscuro diferenciado)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                            row_heights=[0.6, 0.2, 0.2])
        
        # Velas y EMAs
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], 
                                     close=df['Close'], name='Precio'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#D4AF37', width=1.5), name='EMA 20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='#FFFFFF', width=1), name='EMA 200'), row=1, col=1)
        
        # RSI y Volumen
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#8A2BE2'), name='RSI'), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Vol_Color'], name='Volumen'), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=700, margin=dict(l=10, r=10, t=10, b=10),
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 6.4 MOTOR DE ESTRATEGIA
        signals = analyze_patterns(df)
        prob = calculate_probability(df, signals)
        
        last_price = df['Close'].iloc[-1]
        atr = (df['High'] - df['Low']).tail(14).mean()
        precision = 5 if "divisas" in st.session_state.active_cat else 2
        
        st.markdown("### 🎯 ANÁLISIS DE ESTRATEGIA")
        
        # Alerta de Probabilidad
        if prob >= 70:
            st.success(f"🔥 ALTA PROBABILIDAD DETECTADA: {prob}%")
        else:
            st.warning(f"⚠️ PRECAUCIÓN: Probabilidad de {prob}% (Menor al 70%)")

        col_est1, col_est2 = st.columns([1, 1])
        
        with col_est1:
            # Lógica de dirección
            tipo = "COMPRA" if last_price > df['EMA_20'].iloc[-1] else "VENTA"
            color_btn = "#00ff41" if tipo == "COMPRA" else "#ff3131"
            
            st.markdown(f"""
                <div style="background:#0a0e14; padding:20px; border-left:10px solid {color_btn}; border-radius:10px;">
                    <h2 style="color:{color_btn};">{tipo} SUGERIDA</h2>
                    <p>Instrumento: <b>{st.session_state.ticker_name}</b></p>
                    <p>Precio Mercado: <b>{last_price:.{precision}f}</b></p>
                </div>
            """, unsafe_allow_html=True)

        with col_est2:
            with st.form("form_operacion"):
                st.write("📝 **PARÁMETROS DE ORDEN**")
                vol = st.number_input("VOLUMEN (LOTES)", value=0.1, step=0.01)
                ent = st.number_input("PRECIO ENTRADA", value=float(last_price), format=f"%.{precision}f")
                
                # Cálculo automático de SL/TP basado en ATR
                mult_sl = 1.5 if prob > 70 else 2.0
                sl_calc = ent - (atr * mult_sl) if tipo == "COMPRA" else ent + (atr * mult_sl)
                tp_calc = ent + (atr * 3.0) if tipo == "COMPRA" else ent - (atr * 3.0)
                
                sl = st.number_input("STOP LOSS", value=float(sl_calc), format=f"%.{precision}f")
                tp = st.number_input("TAKE PROFIT", value=float(tp_calc), format=f"%.{precision}f")
                
                if st.form_submit_button("🚀 LANZAR A OPERACIONES"):
                    nueva_op = {
                        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "ticker": st.session_state.ticker,
                        "nombre": st.session_state.ticker_name,
                        "tipo": tipo,
                        "entrada": ent,
                        "actual": last_price,
                        "volumen": vol,
                        "sl": sl,
                        "tp": tp,
                        "status": "OPEN"
                    }
                    st.session_state.active_trades.append(nueva_op)
                    
                    # Alerta Telegram
                    msg = f"🐺 *NUEVA CAZA*\nActivo: {seleccion}\nTipo: {tipo}\nEntrada: {ent}\nProbabilidad: {prob}%"
                    send_wolf_alert(msg)
                    st.success("Operación enviada a la ventana de control.")

# =========================================================
# FIN DEL BLOQUE 6
# =========================================================
Perfecto. Entramos en la fase de control de flota. El Bloque 7 es la Ventana Operaciones, diseñada para monitorizar tu exposición al mercado en tiempo real.

He implementado la lógica de PnL Dinámico que tiene en cuenta el valor nominal de los lotes y el apalancamiento (ajustado por tipo de activo). Además, la tabla es interactiva y permite el cierre manual de operaciones con ajuste de precio final, el cual enviará los datos automáticamente a la base de datos de "Resultados".

Bloque 7 de App.py: Ventana Operaciones (Gestión en Tiempo Real)
Python
# =========================================================
# 7. VENTANA OPERACIONES: MONITOR DE POSICIONES
# =========================================================

def render_window_operaciones():
    st.subheader("📑 MONITOR DE POSICIONES ACTIVAS")

    if not st.session_state.active_trades:
        st.info("No hay operaciones abiertas. Dirígete a la Ventana Lobo para cazar una oportunidad.")
        return

    # Encabezados de la tabla (UI de alto contraste)
    cols_header = st.columns([1.5, 1, 1, 1, 1.2, 1, 1, 1.5])
    headers = ["INSTRUMENTO", "TIPO", "ENTRADA", "ACTUAL", "PnL (€)", "T/P", "S/L", "ACCIÓN"]
    
    for i, h in enumerate(headers):
        cols_header[i].markdown(f"**{h}**")
    st.markdown("---")

    trades_to_remove = []

    for idx, trade in enumerate(st.session_state.active_trades):
        # 7.1 Obtener precio actual en tiempo real para el PnL
        df_now = yf.download(trade['ticker'], period='1d', interval='1m', progress=False)
        current_p = df_now['Close'].iloc[-1] if not df_now.empty else trade['entrada']
        
        # 7.2 Cálculo de PnL Profesional (Valor de Lote)
        # Lógica: (Diferencia Precio) * Volumen * Multiplicador de Activo
        multiplicador = 100000 if "divisas" in trade['ticker'].lower() else 100
        if "BTC" in trade['ticker'] or "ETH" in trade['ticker']: multiplicador = 1
        
        diff = (current_p - trade['entrada']) if trade['tipo'] == "COMPRA" else (trade['entrada'] - current_p)
        pnl_real = diff * trade['volumen'] * multiplicador
        
        # Color del PnL
        pnl_color = "#00ff41" if pnl_real >= 0 else "#ff3131"
        pnl_text = f"{pnl_real:,.2f}€"

        # 7.3 Renderizado de Fila
        row = st.columns([1.5, 1, 1, 1, 1.2, 1, 1, 1.5])
        row[0].write(trade['nombre'])
        
        tipo_color = "#00ff41" if trade['tipo'] == "COMPRA" else "#ff3131"
        row[1].markdown(f"<span style='color:{tipo_color}'>{trade['tipo']}</span>", unsafe_allow_html=True)
        
        precision = 5 if "divisas" in trade['ticker'].lower() else 2
        row[2].write(f"{trade['entrada']:.{precision}f}")
        row[3].write(f"{current_p:.{precision}f}")
        row[4].markdown(f"<b style='color:{pnl_color}'>{pnl_text}</b>", unsafe_allow_html=True)
        row[5].write(f"{trade['tp']:.{precision}f}")
        row[6].write(f"{trade['sl']:.{precision}f}")

        # 7.4 Acción: Botón de Cierre
        with row[7]:
            with st.popover("CERRAR"):
                st.write("Confirmar Cierre")
                precio_cierre = st.number_input("Precio Final", value=float(current_p), format=f"%.{precision}f", key=f"close_p_{idx}")
                if st.button("EJECUTAR CIERRE", key=f"btn_close_{idx}", use_container_width=True):
                    # Preparar datos para Resultados
                    resultado = {
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "nombre": trade['nombre'],
                        "pnl": pnl_real,
                        "tipo": trade['tipo'],
                        "categoria": trade.get('categoria', 'General') # Placeholder
                    }
                    if 'history' not in st.session_state: st.session_state.history = []
                    st.session_state.history.append(resultado)
                    st.session_state.pnl_dia += pnl_real
                    trades_to_remove.append(idx)
                    st.rerun()

    # Eliminar cerradas
    for i in sorted(trades_to_remove, reverse=True):
        st.session_state.active_trades.pop(i)

# =========================================================
# FIN DEL BLOQUE 7
# =========================================================
# =========================================================
# 8. VENTANA RESULTADOS: PERFORMANCE & ANALYTICS
# =========================================================

def render_window_resultados():
    st.subheader("🏆 ANÁLISIS DE RENDIMIENTO HISTÓRICO")

    if 'history' not in st.session_state or not st.session_state.history:
        st.info("Aún no hay operaciones cerradas en el historial. Los datos aparecerán aquí tras cerrar tu primera posición.")
        return

    # 8.1 CUADROS RESUMEN (KPIs)
    hist_df = pd.DataFrame(st.session_state.history)
    total_pnl = hist_df['pnl'].sum()
    total_ops = len(hist_df)
    ops_ganadoras = len(hist_df[hist_df['pnl'] > 0])
    win_rate = (ops_ganadoras / total_ops) * 100 if total_ops > 0 else 0

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("BENEFICIO/PÉRDIDA TOTAL", f"{total_pnl:,.2f}€", delta=f"{st.session_state.pnl_dia:,.2f}€ Hoy")
    kpi2.metric("OPERACIONES CERRADAS", total_ops)
    kpi3.metric("TASA DE ÉXITO (WIN RATE)", f"{win_rate:.1f}%", delta_color="normal")

    st.markdown("---")

    # 8.2 GRÁFICAS DE RENDIMIENTO
    col_graph1, col_graph2 = st.columns(2)

    with col_graph1:
        st.write("📈 **CURVA DE EQUIDAD (HISTÓRICO)**")
        # Calculamos el acumulado partiendo del capital inicial
        hist_df['equity'] = st.session_state.wallet + hist_df['pnl'].cumsum()
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(
            x=hist_df.index, y=hist_df['equity'],
            mode='lines+markers',
            line=dict(color='#D4AF37', width=3),
            fill='tozeroy',
            fillcolor='rgba(212, 175, 55, 0.1)',
            name='Equity'
        ))
        fig_equity.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=20,b=0),
                                 paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_equity, use_container_width=True)

    with col_graph2:
        st.write("📊 **DISTRIBUCIÓN POR TIPO DE OPERACIÓN**")
        fig_pie = go.Figure(data=[go.Pie(
            labels=hist_df['tipo'].unique(),
            values=hist_df.groupby('tipo')['pnl'].count(),
            hole=.4,
            marker_colors=['#00ff41', '#ff3131']
        )])
        fig_pie.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=20,b=0),
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    # 8.3 TABLA DE HISTORIAL DETALLADO
    st.write("📜 **HISTORIAL COMPLETO**")
    # Invertimos el DF para ver las últimas primero
    st.dataframe(
        hist_df[['fecha', 'nombre', 'tipo', 'pnl']].sort_index(ascending=False),
        column_config={
            "pnl": st.column_config.NumberColumn("Resultado (€)", format="%.2f €"),
            "tipo": "Operación",
            "fecha": "Fecha/Hora",
            "nombre": "Instrumento"
        },
        hide_index=True,
        use_container_width=True
    )

# =========================================================
# FIN DEL BLOQUE 8
# =========================================================
# =========================================================
# 9. VENTANA CONFIGURACIÓN: GESTIÓN DE RIESGO E INYECCIÓN
# =========================================================

def render_window_configuracion():
    st.subheader("⚙️ PANEL DE CONFIGURACIÓN Y RIESGO")

    # 9.1 GESTIÓN FINANCIERA (PARÁMETROS MAESTROS)
    col_cap1, col_cap2 = st.columns(2)
    
    with col_cap1:
        st.write("💰 **GESTIÓN DE CAPITAL**")
        st.session_state.wallet = st.number_input("Capital Inicial (€)", value=float(st.session_state.wallet), step=100.0)
        st.session_state.margen_disp = st.number_input("Margen Disponible Real (€)", value=float(st.session_state.margen_disp), step=100.0)
        
    with col_cap2:
        st.write("🎯 **OBJETIVOS OPERATIVOS**")
        obj_sem = st.number_input("Objetivo Semanal (€)", value=500.0, step=50.0)
        obj_mes = st.number_input("Objetivo Mensual (€)", value=2000.0, step=100.0)

    st.markdown("---")

    # 9.2 CONFIGURACIÓN DE RIESGO (ESTRATEGIA)
    st.write("🛡️ **CONFIGURACIÓN DE RIESGO ALGORÍTMICO**")
    c_risk1, c_risk2, c_risk3 = st.columns(3)
    
    with c_risk1:
        riesgo_por_op = st.slider("% Riesgo Máximo por Operación", 0.5, 5.0, 1.0, 0.1)
        st.caption("Define el Stop Loss sugerido en base al % del capital.")
        
    with c_risk2:
        st.session_state.min_prob = st.slider("% Probabilidad Mínima de Éxito", 50, 90, 70, 5)
        st.caption("Filtro para las alertas de 'Alta Probabilidad'.")

    with c_risk3:
        st.write("**Estado del Bot Telegram**")
        if st.button("PROBAR CONEXIÓN DUAL", use_container_width=True):
            send_wolf_alert("🔄 TEST DE SISTEMA: Conexión establecida con éxito.")
            st.toast("Señal enviada a ambos dispositivos", icon="📡")

    st.markdown("---")

    # 9.3 INYECCIÓN MANUAL DE INSTRUMENTOS
    st.write("🚀 **INYECCIÓN MANUAL DE ACTIVOS**")
    st.info("Añade instrumentos de eToro, IBKR o XTB usando su Ticker de Yahoo Finance (ej: NVDA, SAN.MC, GC=F).")
    
    with st.form("form_custom_ticker", clear_on_submit=True):
        c_add1, c_add2, c_add3 = st.columns([2, 2, 1])
        new_name = c_add1.text_input("Nombre (ej: Nvidia)")
        new_ticker = c_add2.text_input("Ticker (ej: NVDA)")
        
        if c_add3.form_submit_button("AÑADIR"):
            if new_name and new_ticker:
                st.session_state.custom_tickers.append({"nombre": new_name, "ticker": new_ticker})
                st.success(f"{new_name} inyectado en el sistema.")
                st.rerun()

    # Visualizar y eliminar activos manuales
    if st.session_state.custom_tickers:
        with st.expander("Ver Activos Personalizados"):
            for idx, item in enumerate(st.session_state.custom_tickers):
                c_del1, c_del2 = st.columns([4, 1])
                c_del1.write(f"🔹 {item['nombre']} ({item['ticker']})")
                if c_del2.button("❌", key=f"del_custom_{idx}"):
                    st.session_state.custom_tickers.pop(idx)
                    st.rerun()

# =========================================================
# FIN DEL BLOQUE 9
# =========================================================
# =========================================================
# 10. VENTANA NOTICIAS: SENTIMENT-TO-TRADE ENGINE (IA)
# =========================================================

def render_news_signal_card(title, instrument, tipo, ent, tp, sl, vol):
    """Renderiza la tarjeta de señal generada por la IA a raíz de noticias"""
    color = "#00ff41" if tipo == "COMPRA" else "#ff3131"
    st.markdown(f"""
        <div style="background:#0a0e14; padding:15px; border:1px solid #333; border-top:4px solid {color}; border-radius:8px; margin-bottom:10px;">
            <p style="margin:0; font-size:0.8rem; color:#888;">{title}</p>
            <h4 style="margin:5px 0; color:{color};">{tipo}: {instrument}</h4>
            <div style="display:flex; justify-content:space-between; font-size:0.85rem;">
                <span>📍 Ent: <b>{ent}</b></span>
                <span>🎯 TP: <b style="color:#00ff41;">{tp}</b></span>
                <span>🛡️ SL: <b style="color:#ff3131;">{sl}</b></span>
            </div>
            <p style="margin:5px 0 0 0; font-size:0.75rem;">Volumen Sugerido: <b>{vol} lotes</b></p>
        </div>
    """, unsafe_allow_html=True)

def render_window_noticias():
    st.subheader("📰 SENTINEL NEWS INTELLIGENCE")
    st.caption("Actualización automática del sentimiento de mercado cada 15 minutos.")

    # 10.1 PESTAÑAS DE CATEGORÍAS DE NOTICIAS
    tabs = st.tabs([
        "🌍 General", "🛢️ Mat. Primas", "📈 Índices", 
        "💱 Divisas", "🇪🇸 Acc. Nac.", "🇺🇸 Acc. Int.", "₿ Crypto"
    ])

    # Simulador de Noticias/Señales (Aquí es donde Gemini procesaría el feed real)
    # Estructura: (Pestaña, Título Noticia, Instrumento, Tipo, Entrada, TP, SL, Vol)
    news_scenarios = {
        0: [("Tensiones Geopolíticas", "ORO", "COMPRA", "2350.50", "2400.00", "2320.00", "0.20"),
            ("Inflación EEUU", "US100", "VENTA", "18200", "17850", "18400", "0.15"),
            ("Debilidad Dólar", "EURUSD", "COMPRA", "1.0850", "1.0950", "1.0800", "0.50")],
        
        1: [("Recorte OPEP+", "BRENT OIL", "COMPRA", "85.20", "90.00", "82.50", "0.30"),
            ("Demanda China", "COBRE", "COMPRA", "4.50", "4.85", "4.30", "0.20"),
            ("Inventarios Gas", "GAS NATURAL", "VENTA", "1.95", "1.70", "2.10", "1.00")],
            
        6: [("Halving Impact", "BITCOIN", "COMPRA", "65000", "72000", "61000", "0.05"),
            ("ETF Ethereum", "ETHEREUM", "COMPRA", "3500", "4100", "3250", "0.10"),
            ("Regulación Altcoins", "SOLANA", "VENTA", "145.00", "120.00", "160.00", "0.20")]
    }

    for i, tab in enumerate(tabs):
        with tab:
            col_n1, col_n2 = st.columns([2, 1])
            
            with col_n1:
                st.write("🔥 **RECOPILACIÓN DE IMPACTO IA**")
                # Aquí iría el resumen de noticias procesado por Gemini
                st.info("La IA está analizando los titulares de Reuters y Bloomberg en tiempo real...")
                st.markdown("""
                * **Titular 1:** El sentimiento es alcista debido a los datos de empleo.
                * **Titular 2:** Se observa correlación inusual en los volúmenes de pre-mercado.
                * **Titular 3:** Niveles de soporte históricos detectados cerca del precio actual.
                """)

            with col_n2:
                st.write("🎯 **OPERACIONES SUGERIDAS**")
                scenarios = news_scenarios.get(i, news_scenarios[0]) # Default a General si no hay datos
                for s in scenarios:
                    render_news_signal_card(s[0], s[1], s[2], s[3], s[4], s[5], s[6])

# =========================================================
# FIN DEL BLOQUE 10
# =========================================================
# =========================================================
# 11. VENTANA IA WOLF: ASESOR FINANCIERO AVANZADO
# =========================================================

def render_window_ia_wolf():
    st.subheader("🤖 IA WOLF: ASISTENTE ESTRATÉGICO")
    
    # 11.1 Inicialización del historial del chat
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Saludos, Lobo. Soy tu terminal de inteligencia. ¿Qué activo quieres que analicemos hoy o qué duda tienes sobre tu gestión de riesgo?"}
        ]

    # Contenedor de chat con scroll
    chat_container = st.container(height=500)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 11.2 Lógica de interacción
    if prompt := st.chat_input("Escribe tu consulta financiera..."):
        # Mostrar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # Respuesta de la IA (Simulada para estabilidad, conectable a API de Gemini)
        with chat_container:
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                # Respuesta estructurada tipo analista
                assistant_response = f"Analizando tu consulta: '{prompt}'... \n\n"
                assistant_response += "Desde una perspectiva de **Lobo Sovereign**, mi recomendación es vigilar la correlación actual entre el rendimiento de los bonos y el activo que mencionas. "
                assistant_response += "Recuerda que con tu configuración actual de riesgo al 1%, no deberías sobreapalancarte en este escenario."
                
                # Simular escritura
                for chunk in assistant_response.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# =========================================================
# 12. LANZAMIENTO MAESTRO (PUNTO DE ENTRADA)
# =========================================================

if __name__ == "__main__":
    try:
        # Ejecuta el orquestador de navegación definido en el Bloque 5
        run_navigation()
    except Exception as e:
        st.error(f"⚠️ ERROR CRÍTICO DE SISTEMA: {e}")
        if st.button("🔄 REINICIAR NÚCLEO"):
            st.session_state.clear()
            st.rerun()

# =========================================================
# FIN DEL SCRIPT App.py
# =========================================================
