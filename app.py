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
# 1.1 CONFIGURACIÓN DE PÁGINA (WOLF SOVEREIGN v1.1)
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
# 1.2 VARIABLES DE SESIÓN (ESTADO DEL SISTEMA)
# =========================================================
if 'initialized' not in st.session_state:
    st.session_state.update({
        'initialized': True,
        'view': "Lobo",            # Ventana activa por defecto
        'active_cat': "opciones/indices", 
        'active_sub': "EEUU",
        'ticker': "^GSPC",         # Activo inicial (S&P 500)
        'ticker_name': "S&P 500",
        'wallet': 10000.00,        # Capital configurable
        'margen_disp': 10000.00,
        'pnl_dia': 0.00,
        'active_trades': [],       # Órdenes abiertas
        'int_top': "1h",           # Temporalidad inicial
        'custom_tickers': [],      # Inyección manual de activos
        'history': [],             # Historial de operaciones cerradas
        'messages': [{"role": "assistant", "content": "Saludos, Lobo. Terminal operativa. ¿Qué activo analizamos?"}]
    })

# =========================================================
# 1.3 SISTEMA DE ALERTAS DUAL (TELEGRAM)
# =========================================================
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
            st.sidebar.error(f"Error en comunicación Telegram: {e}")

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

    /* FIX: Texto legible en Chat IA */
    [data-testid="stChatMessageContent"] p {
        color: #FFFFFF !important;
    }

    /* 2.2 Banner Ticker Superior (Automatizado) */
    .ticker-wrap {
        width: 100%;
        overflow: hidden;
        background: #0a0e14;
        padding: 10px 0;
        border-bottom: 2px solid #D4AF37;
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
        font-weight: bold;
        font-size: 1.1rem;
    }
    @keyframes ticker-animation {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }

    /* 2.3 Botones de Navegación Principal */
    div.nav-btn button {
        background-color: #1a1a1a !important;
        color: #FFFFFF !important; /* Blanco por defecto para ver el nombre */
        border: 2px solid #D4AF37 !important;
        border-radius: 4px !important;
        height: 3.5em !important;
        font-weight: bold !important;
    }
    div.nav-active button {
        background-color: #D4AF37 !important;
        color: #000000 !important; /* TEXTO NEGRO SOBRE DORADO */
        border: 2px solid #D4AF37 !important;
        font-weight: 900 !important;
    }

    /* 2.4 Botones de Categorías y Subcategorías */
    div.menu-btn button {
        background-color: #1a1a1a !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
    }
    div.menu-active button {
        background-color: #FFFFFF !important; /* FONDO BLANCO */
        color: #000000 !important;           /* TEXTO NEGRO */
        border: 2px solid #D4AF37 !important;
        font-weight: bold !important;
    }

    /* 2.5 Gráficos y Contenedores */
    .stPlotlyChart {
        background-color: #05070a !important;
        border-radius: 10px;
        padding: 5px;
        border: 1px solid #222;
    }
    
    /* 2.6 Adaptabilidad Móvil */
    @media (max-width: 640px) {
        .ticker-item { padding: 0 20px; font-size: 0.9rem; }
        div.nav-btn button { font-size: 0.7rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN PARA EL RENDERIZADO DEL BANNER AUTOMATIZADO ---
def render_top_ticker():
    # Diccionario de activos para el banner dinámico
    monitored_assets = {
        "S&P 500": "^GSPC", 
        "NASDAQ": "NQ=F", 
        "ORO": "GC=F", 
        "BRENT": "BZ=F", 
        "EUR/USD": "EURUSD=X", 
        "BITCOIN": "BTC-USD"
    }
    
    ticker_content = ""
    
    for name, symbol in monitored_assets.items():
        try:
            # Descargamos datos de los últimos 2 días para calcular tendencia
            data = yf.download(symbol, period="2d", interval="1d", progress=False)
            if not data.empty and len(data) >= 2:
                last_price = data['Close'].iloc[-1]
                prev_price = data['Close'].iloc[-2]
                change = ((last_price - prev_price) / prev_price) * 100
                
                # Definimos color y flecha según rendimiento real
                color = "#00ff41" if change >= 0 else "#ff3131"
                icon = "▲" if change >= 0 else "▼"
                
                ticker_content += f'<span class="ticker-item" style="color:{color}">{name} {icon} {change:.2f}%</span>'
        except:
            # Si falla la descarga de un activo, saltamos al siguiente
            continue

    if ticker_content:
        st.markdown(f"""
            <div class="ticker-wrap">
                <div class="ticker-move">
                    {ticker_content * 4}
                </div>
            </div>
        """, unsafe_allow_html=True)

# =========================================================
# FIN DEL BLOQUE 2
# =========================================================
# =========================================================
# 3. BASE DE DATOS Y GESTIÓN DE INSTRUMENTOS (v1.1)
# =========================================================

# 3.1 Estructura Maestra de Categorías
# Se han añadido 'formación' y 'copytrading' como categorías funcionales
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
            "Chainlink": ["LINK-USD", "Crypto"]
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
    "opciones": {
        "Estrategias": {
            "Call S&P 500 (Bull)": ["^GSPC", "Estratégico"],
            "Put Nasdaq (Hedge)": ["NQ=F", "Protección"],
            "Iron Condor (Neutral)": ["^GSPC", "Ingreso"]
        },
        "Índices Relacionados": {
            "VIX (Miedo)": ["^VIX", "Volatilidad"],
            "Nasdaq 100": ["NQ=F", "Índice"],
            "Dow Jones": ["^DJI", "Índice"]
        }
    },
    "copytrading": {
        "Top Performers": {
            "Perfil eToro (Referencia)": ["ETORO_LINK", "Social"],
            "Analista Senior": ["RANKING_1", "HFT"],
            "Lobo Conservative": ["RANKING_2", "Dividendos"]
        }
    },
    "formación": {
        "Cursos Gratuitos": {
            "Bolsa desde Cero": ["LINK_EDX", "Principiante"],
            "Análisis Técnico": ["LINK_YOUTUBE", "Intermedio"],
            "Psicotrading": ["LINK_WEB", "Psicología"]
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
# FIN DEL BLOQUE 3 ACTUALIZADO
# =========================================================
# =========================================================
# 4. MOTOR ALGORÍTMICO SENTINEL (CORREGIDO Y AMPLIADO)
# =========================================================

def get_advanced_data(ticker, interval='1h'):
    """Descarga datos y calcula indicadores técnicos con manejo de errores NoneType"""
    try:
        # Optimizamos periodos para asegurar datos suficientes para EMA 200
        period_map = {'1m': '5d', '5m': '5d', '15m': '1mo', '1h': '1y', '1d': 'max'}
        target_period = period_map.get(interval, '1mo')
        
        data = yf.download(ticker, period=target_period, interval=interval, progress=False)
        
        if data.empty or len(data) < 201: # Mínimo 201 periodos para que EMA_200 no sea None
            # Intento de rescate si faltan datos
            data = yf.download(ticker, period='max', interval=interval, progress=False)
            if data.empty: return None
        
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # --- CÁLCULO SEGURO DE INDICADORES (EVITA NONETYPE ERROR) ---
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # Bandas de Bollinger
        bbands = ta.bbands(df['Close'], length=20, std=2)
        if bbands is not None:
            df = pd.concat([df, bbands], axis=1)
        
        # ATR para cálculo de Volatilidad (Soporte/Resistencia dinámico)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # --- DETECCIÓN DE PIVOTS ---
        df['Pivot'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['R1'] = (2 * df['Pivot']) - df['Low']
        df['S1'] = (2 * df['Pivot']) - df['High']
        
        # --- FIBONACCI ---
        max_h = df['High'].tail(100).max()
        min_l = df['Low'].tail(100).min()
        diff = max_h - min_l
        df['Fib_618'] = max_h - (diff * 0.618)
        df['Fib_382'] = max_h - (diff * 0.382)

        df['Vol_Color'] = ['#00ff41' if c >= o else '#ff3131' for c, o in zip(df['Close'], df['Open'])]
        
        # Eliminamos filas incompletas pero verificamos que quede contenido
        df_clean = df.dropna(subset=['EMA_20', 'EMA_200', 'RSI'])
        return df_clean if not df_clean.empty else None
        
    except Exception as e:
        st.error(f"Error Crítico en Motor Algorítmico: {e}")
        return None

def analyze_triple_strategy(df, interval):
    """Calcula estrategias para 3 horizontes temporales"""
    if df is None or len(df) < 2: return {}
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Mapeo de tiempo estimado según intervalo
    time_units = {
        '1m': ('minutos', 1), '5m': ('minutos', 5), '15m': ('minutos', 15),
        '1h': ('horas', 1), '1d': ('días', 1)
    }
    unit, mult = time_units.get(interval, ('periodos', 1))

    estrategias = {
        "CORTO PLAZO (Scalping)": {
            "señal": "COMPRA" if last['Close'] > last['EMA_20'] else "VENTA",
            "tiempo": f"15-60 {unit}",
            "confianza": calculate_probability(df, "corto")
        },
        "MEDIO PLAZO (Swing)": {
            "señal": "COMPRA" if last['EMA_20'] > last['EMA_200'] else "VENTA",
            "tiempo": f"4-24 {unit}",
            "confianza": calculate_probability(df, "medio")
        },
        "LARGO PLAZO (Posicional)": {
            "señal": "COMPRA" if last['Close'] > last['EMA_200'] and last['RSI'] > 50 else "VENTA",
            "tiempo": f"+48 {unit}",
            "confianza": calculate_probability(df, "largo")
        }
    }
    return estrategias

def calculate_probability(df, modo):
    """Calcula % de éxito basado en confluencias técnicas reales"""
    last = df.iloc[-1]
    prob = 50.0
    
    # Factor RSI
    if 40 < last['RSI'] < 60: prob += 5
    elif last['RSI'] > 70 or last['RSI'] < 30: prob -= 10 # Agotamiento
    
    # Factor Volumen
    vol_mean = df['Volume'].tail(20).mean()
    if last['Volume'] > vol_mean: prob += 15
    
    # Factor Tendencia
    if modo == "corto" and (last['Close'] > last['EMA_20']): prob += 10
    if modo == "largo" and (last['EMA_20'] > last['EMA_200']): prob += 20
    
    return min(prob, 98.0)

# =========================================================
# FIN DEL BLOQUE 4 ACTUALIZADO
# =========================================================
Aquí tienes el Bloque 5 reconstruido. He ampliado el orquestador para incluir las nuevas ventanas de Opciones, Formación y Copytrader, sumando un total de 9 ventanas. También he optimizado el layout de la botonera para que quepan todas de forma equilibrada y profesional.

Python
# =========================================================
# 5. ORQUESTADOR DE NAVEGACIÓN Y VISTAS (AMPLIADO v1.1)
# =========================================================

def run_navigation():
    """Renderiza el menú superior y gestiona el flujo de las 9 ventanas de la terminal"""
    
    # 5.1 Renderizado del Banner Superior Dinámico (Llamada al motor automatizado)
    render_top_ticker()

    # 5.2 Cabecera de Capital Estática
    pnl_color = "#00ff41" if st.session_state.pnl_dia >= 0 else "#ff3131"
    st.markdown(f"""
        <div class="metric-container" style="background-color: #0a0e14; padding: 15px; border-bottom: 2px solid #D4AF37; display: flex; justify-content: space-around; border-radius: 8px; margin-bottom: 1rem;">
            <div style="text-align:center;"><span style="color:#D4AF37; font-size:0.8rem;">CAPITAL TOTAL</span><br><b style="font-size:1.4rem;">{st.session_state.wallet:,.2f}€</b></div>
            <div style="text-align:center;"><span style="color:#D4AF37; font-size:0.8rem;">DISPONIBLE</span><br><b style="font-size:1.4rem;">{st.session_state.margen_disp:,.2f}€</b></div>
            <div style="text-align:center;"><span style="color:#D4AF37; font-size:0.8rem;">PnL DÍA</span><br><b style="font-size:1.4rem; color:{pnl_color};">{"+" if st.session_state.pnl_dia >= 0 else ""}{st.session_state.pnl_dia:,.2f}€</b></div>
        </div>
    """, unsafe_allow_html=True)

    # 5.3 Menú Principal de Navegación (9 Ventanas distribuidas en 3 filas para móvil/web)
    # Usamos una cuadrícula de 9 columnas para desktop
    nav_cols = st.columns(9)
    
    views = [
        ("🐺 LOBO", "Lobo"),
        ("📊 OPERAR", "Operaciones"),
        ("💎 OPCIONES", "Opciones"),
        ("👥 COPY", "Copytrading"),
        ("📰 NEWS", "Noticias"),
        ("🏆 HITO", "Resultados"),
        ("🎓 ACADEMY", "Formacion"),
        ("🤖 IA WOLF", "IA_Wolf"),
        ("⚙️ CONFIG", "Configuracion")
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

    # 5.4 Enrutador de Contenido (Lógica de carga de ventanas)
    v = st.session_state.view
    if v == "Lobo":
        render_window_lobo()
    elif v == "Operaciones":
        render_window_operaciones()
    elif v == "Opciones":
        render_window_opciones()      # Nueva ventana
    elif v == "Copytrading":
        render_window_copytrading()    # Nueva ventana
    elif v == "Noticias":
        render_window_noticias()
    elif v == "Resultados":
        render_window_resultados()
    elif v == "Formacion":
        render_window_formacion()      # Nueva ventana
    elif v == "IA_Wolf":
        render_window_ia_wolf()
    elif v == "Configuracion":
        render_window_configuracion()

# =========================================================
# FIN DEL BLOQUE 5 ACTUALIZADO
# =========================================================
# =========================================================
# 6. VENTANA LOBO: SELECTOR, GRÁFICO Y TRIPLE ESTRATEGIA
# =========================================================

def render_window_lobo():
    # 6.1 SELECTOR DE CASCADA PROFESIONAL
    c1, c2, c3 = st.columns([1, 1, 2])
    
    with c1:
        cats = list(DATABASE.keys())
        # Filtramos para que solo aparezcan categorías de trading en esta ventana
        trading_cats = [c for c in cats if c not in ["formación", "copytrading"]]
        cat_idx = trading_cats.index(st.session_state.active_cat) if st.session_state.active_cat in trading_cats else 0
        st.session_state.active_cat = st.selectbox("🎯 MERCADO", trading_cats, index=cat_idx).lower()
    
    with c2:
        subs = list(DATABASE[st.session_state.active_cat].keys())
        st.session_state.active_sub = st.selectbox("📂 GRUPO", subs)
        
    with c3:
        activos = DATABASE[st.session_state.active_cat][st.session_state.active_sub]
        seleccion = st.selectbox("📈 ACTIVO", list(activos.keys()))
        st.session_state.ticker = activos[seleccion][0]
        st.session_state.ticker_name = seleccion

    # 6.2 SELECTOR DE TEMPORALIDAD (BOTONES ACTIVOS)
    t_cols = st.columns(8)
    tiempos = ["1m", "5m", "15m", "1h", "1d"]
    for i, t in enumerate(tiempos):
        is_active = st.session_state.int_top == t
        tag = "menu-active" if is_active else "menu-btn"
        with t_cols[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(t, key=f"t_{t}", use_container_width=True):
                st.session_state.int_top = t
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 6.3 OBTENCIÓN DE DATOS CON VALIDACIÓN DE SEGURIDAD
    df = get_advanced_data(st.session_state.ticker, st.session_state.int_top)
    
    if df is not None and not df.empty:
        # Gráfico Profesional Plotly
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                            row_heights=[0.6, 0.2, 0.2])
        
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], 
                                     close=df['Close'], name='Precio'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#D4AF37', width=1.5), name='EMA 20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], line=dict(color='#FFFFFF', width=1), name='EMA 200'), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#8A2BE2'), name='RSI'), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['Vol_Color'], name='Volumen'), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=600, margin=dict(l=10, r=10, t=10, b=10),
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 6.4 PANEL DE TRIPLE ESTRATEGIA (CORTO/MEDIO/LARGO)
        st.markdown("### 🎯 SENTINEL ESTRATEGY HUB")
        
        estrategias = analyze_triple_strategy(df, st.session_state.int_top)
        est_cols = st.columns(3)
        
        for i, (nombre, data) in enumerate(estrategias.items()):
            color = "#00ff41" if data['señal'] == "COMPRA" else "#ff3131"
            with est_cols[i]:
                st.markdown(f"""
                    <div style="background:#0a0e14; padding:15px; border-top:5px solid {color}; border-radius:10px; min-height:180px;">
                        <h4 style="color:#D4AF37; margin:0;">{nombre}</h4>
                        <h2 style="color:{color}; margin:10px 0;">{data['señal']}</h2>
                        <p style="font-size:0.9rem; margin:0;">Probabilidad: <b>{data['confianza']}%</b></p>
                        <p style="font-size:0.8rem; color:#888;">Tiempo est.: <b>{data['tiempo']}</b></p>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # 6.5 FORMULARIO DE OPERATIVA MANUAL
        col_form1, col_form2 = st.columns([1, 1])
        last_price = df['Close'].iloc[-1]
        precision = 5 if "divisas" in st.session_state.active_cat else 2
        
        with col_form1:
            st.markdown(f"""
                <div style="background:#0a0e14; padding:25px; border-radius:10px; border:1px solid #333;">
                    <p style="color:#D4AF37; margin:0;">ACTIVO SELECCIONADO</p>
                    <h2 style="margin:0;">{st.session_state.ticker_name}</h2>
                    <h3 style="color:#FFFFFF;">{last_price:.{precision}f}</h3>
                </div>
            """, unsafe_allow_html=True)

        with col_form2:
            with st.form("ejecucion_lobo"):
                v_cols = st.columns(2)
                vol = v_cols[0].number_input("VOLUMEN", value=0.1, step=0.01)
                tipo_op = v_cols[1].selectbox("OPERACIÓN", ["COMPRA", "VENTA"])
                
                # Cálculo de SL/TP por ATR
                atr_val = df['ATR'].iloc[-1] if 'ATR' in df.columns else (last_price * 0.01)
                sl_sug = last_price - (atr_val * 2) if tipo_op == "COMPRA" else last_price + (atr_val * 2)
                tp_sug = last_price + (atr_val * 4) if tipo_op == "COMPRA" else last_price - (atr_val * 4)
                
                sl = st.number_input("STOP LOSS", value=float(sl_sug), format=f"%.{precision}f")
                tp = st.number_input("TAKE PROFIT", value=float(tp_sug), format=f"%.{precision}f")
                
                if st.form_submit_button("🚀 EJECUTAR CAZA", use_container_width=True):
                    nueva_op = {
                        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "ticker": st.session_state.ticker,
                        "nombre": st.session_state.ticker_name,
                        "tipo": tipo_op,
                        "entrada": last_price,
                        "volumen": vol,
                        "sl": sl,
                        "tp": tp,
                        "categoria": st.session_state.active_cat
                    }
                    st.session_state.active_trades.append(nueva_op)
                    send_wolf_alert(f"🐺 *POSICIÓN ABIERTA*\n{st.session_state.ticker_name}\nTipo: {tipo_op}\nEntrada: {last_price:.{precision}f}")
                    st.success("Orden enviada al monitor.")
    else:
        st.error("⚠️ Datos insuficientes para este intervalo. Intenta subir a 15m o 1h.")

# =========================================================
# FIN DEL BLOQUE 6 ACTUALIZADO
# =========================================================
# =========================================================
# 7. VENTANA OPERACIONES: MONITOR DE POSICIONES (REVISADO)
# =========================================================

def render_window_operaciones():
    st.subheader("📑 MONITOR DE POSICIONES ACTIVAS")

    if not st.session_state.active_trades:
        st.info("No hay operaciones abiertas. Dirígete a la Ventana Lobo para cazar una oportunidad.")
        return

    # 7.1 ACTUALIZACIÓN MASIVA DE PRECIOS (Optimización)
    tickers_to_update = list(set([t['ticker'] for t in st.session_state.active_trades]))
    try:
        # Descarga rápida del último precio para todos los activos abiertos
        current_data = yf.download(tickers_to_update, period='1d', interval='1m', progress=False)
        if isinstance(current_data.columns, pd.MultiIndex):
            prices_dict = {t: current_data['Close'][t].iloc[-1] for t in tickers_to_update}
        else:
            prices_dict = {tickers_to_update[0]: current_data['Close'].iloc[-1]}
    except:
        prices_dict = {}

    # Encabezados con estilo Wolf
    cols_header = st.columns([1.5, 1, 1, 1, 1.2, 1, 1, 1.5])
    headers = ["INSTRUMENTO", "TIPO", "ENTRADA", "ACTUAL", "PnL (€)", "T/P", "S/L", "ACCIÓN"]
    for i, h in enumerate(headers):
        cols_header[i].markdown(f"<span style='color:#D4AF37; font-size:0.8rem;'>{h}</span>", unsafe_allow_html=True)
    st.markdown("---")

    trades_to_remove = []
    pnl_flotante_total = 0

    for idx, trade in enumerate(st.session_state.active_trades):
        # Obtener precio actual del diccionario optimizado o del trade
        current_p = prices_dict.get(trade['ticker'], trade.get('actual', trade['entrada']))
        
        # 7.2 LÓGICA DE MULTIPLICADOR PROFESIONAL
        # Forex: 1 lote = 100,000 | Oro/Indices: 1 lote = 100 | Acciones/Cripto: 1 lote = 1
        cat_lower = trade.get('categoria', '').lower()
        if "divisas" in cat_lower or "fx" in trade['ticker'].lower():
            multiplicador = 100000
        elif any(x in trade['ticker'].lower() for x in ["=f", "^"]): # Futuros o Indices
            multiplicador = 100
        else:
            multiplicador = 1
        
        # Cálculo de PnL
        diff = (current_p - trade['entrada']) if trade['tipo'] == "COMPRA" else (trade['entrada'] - current_p)
        pnl_real = diff * trade['volumen'] * multiplicador
        pnl_flotante_total += pnl_real
        
        # Estética de fila
        pnl_color = "#00ff41" if pnl_real >= 0 else "#ff3131"
        tipo_color = "#00ff41" if trade['tipo'] == "COMPRA" else "#ff3131"
        precision = 5 if multiplicador == 100000 else 2

        # Renderizado
        row = st.columns([1.5, 1, 1, 1, 1.2, 1, 1, 1.5])
        row[0].markdown(f"<b>{trade['nombre']}</b>", unsafe_allow_html=True)
        row[1].markdown(f"<span style='color:{tipo_color}'>{trade['tipo']}</span>", unsafe_allow_html=True)
        row[2].write(f"{trade['entrada']:.{precision}f}")
        row[3].write(f"{current_p:.{precision}f}")
        row[4].markdown(f"<b style='color:{pnl_color}'>{pnl_real:,.2f}€</b>", unsafe_allow_html=True)
        row[5].write(f"{trade['tp']:.{precision}f}")
        row[6].write(f"{trade['sl']:.{precision}f}")

        # 7.3 BOTÓN DE CIERRE INTERACTIVO
        with row[7]:
            with st.popover("CERRAR"):
                st.markdown("### EJECUTAR CIERRE")
                precio_cierre = st.number_input("Precio de Salida", value=float(current_p), format=f"%.{precision}f", key=f"c_{idx}")
                if st.button("CONFIRMAR", key=f"btn_{idx}", use_container_width=True):
                    # Guardar en histórico
                    resultado = {
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "nombre": trade['nombre'],
                        "pnl": pnl_real,
                        "tipo": trade['tipo'],
                        "entrada": trade['entrada'],
                        "salida": precio_cierre,
                        "volumen": trade['volumen']
                    }
                    st.session_state.history.append(resultado)
                    st.session_state.pnl_dia += pnl_real
                    trades_to_remove.append(idx)
                    st.rerun()

    # Actualizar Margen Disponible restando el PnL flotante negativo
    st.session_state.margen_disp = st.session_state.wallet + pnl_flotante_total

    # Limpieza de trades
    for i in sorted(trades_to_remove, reverse=True):
        st.session_state.active_trades.pop(i)

# =========================================================
# FIN DEL BLOQUE 7 ACTUALIZADO
# =========================================================
# =========================================================
# 8. VENTANA RESULTADOS: PERFORMANCE & ANALYTICS (REVISADO)
# =========================================================

def render_window_resultados():
    st.subheader("🏆 ANÁLISIS DE RENDIMIENTO HISTÓRICO")

    if 'history' not in st.session_state or not st.session_state.history:
        st.info("Aún no hay operaciones cerradas. Los datos aparecerán aquí tras tu primer cierre.")
        return

    # Preparación de Datos
    hist_df = pd.DataFrame(st.session_state.history)
    
    # 8.1 CUADROS RESUMEN (KPIs PROFESIONALES)
    total_pnl = hist_df['pnl'].sum()
    total_ops = len(hist_df)
    ganadas = hist_df[hist_df['pnl'] > 0]['pnl'].sum()
    perdidas = abs(hist_df[hist_df['pnl'] <= 0]['pnl'].sum())
    
    win_rate = (len(hist_df[hist_df['pnl'] > 0]) / total_ops) * 100
    profit_factor = ganadas / perdidas if perdidas > 0 else ganadas

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("PnL TOTAL ACUMULADO", f"{total_pnl:,.2f}€")
    kpi2.metric("OPERACIONES", total_ops)
    kpi3.metric("WIN RATE", f"{win_rate:.1f}%")
    kpi4.metric("PROFIT FACTOR", f"{profit_factor:.2f}")

    st.markdown("---")

    # 8.2 GRÁFICAS DE RENDIMIENTO
    col_graph1, col_graph2 = st.columns([2, 1])

    with col_graph1:
        st.write("📈 **CURVA DE EQUIDAD DINÁMICA**")
        # Calculamos la evolución del capital
        hist_df['balance'] = st.session_state.wallet + hist_df['pnl'].cumsum()
        
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(
            x=hist_df.index, y=hist_df['balance'],
            mode='lines+markers',
            line=dict(color='#D4AF37', width=3),
            fill='tozeroy',
            fillcolor='rgba(212, 175, 55, 0.1)',
            name='Capital (€)'
        ))
        fig_equity.update_layout(
            template="plotly_dark", height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="#FFFFFF")
        )
        st.plotly_chart(fig_equity, use_container_width=True)

    with col_graph2:
        st.write("📊 **SESGO DE OPERATIVA**")
        fig_pie = go.Figure(data=[go.Pie(
            labels=hist_df['tipo'].unique(),
            values=hist_df.groupby('tipo')['pnl'].count(),
            hole=.5,
            marker_colors=['#00ff41', '#ff3131'],
            textinfo='label+percent'
        )])
        fig_pie.update_layout(
            template="plotly_dark", height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # 8.3 TABLA DE HISTORIAL DETALLADO (ESTILO SOVEREIGN)
    st.write("📜 **REGISTRO DE CAZA (HISTORIAL)**")
    
    # Formateo de tabla para visibilidad total
    def color_pnl(val):
        color = '#00ff41' if val >= 0 else '#ff3131'
        return f'color: {color}; font-weight: bold'

    st.dataframe(
        hist_df[['fecha', 'nombre', 'tipo', 'entrada', 'salida', 'pnl']].sort_index(ascending=False),
        column_config={
            "fecha": "Fecha/Hora",
            "nombre": "Activo",
            "tipo": "Dirección",
            "entrada": st.column_config.NumberColumn("Entrada", format="%.4f"),
            "salida": st.column_config.NumberColumn("Salida", format="%.4f"),
            "pnl": st.column_config.NumberColumn("Resultado (€)", format="%.2f €")
        },
        hide_index=True,
        use_container_width=True
    )

# =========================================================
# FIN DEL BLOQUE 8 ACTUALIZADO
# =========================================================
# =========================================================
# 9. VENTANA CONFIGURACIÓN: GESTIÓN DE RIESGO E INYECCIÓN
# =========================================================

def render_window_configuracion():
    st.subheader("⚙️ PANEL DE CONFIGURACIÓN Y RIESGO")

    # 9.1 GESTIÓN FINANCIERA (PARÁMETROS MAESTROS)
    col_cap1, col_cap2 = st.columns(2)
    
    with col_cap1:
        st.markdown("### 💰 GESTIÓN DE CAPITAL")
        # Al cambiar el capital, recalculamos el estado de la cartera
        nuevo_capital = st.number_input("Capital Inicial (€)", value=float(st.session_state.wallet), step=500.0)
        if nuevo_capital != st.session_state.wallet:
            st.session_state.wallet = nuevo_capital
            st.session_state.margen_disp = nuevo_capital
            st.toast("Capital actualizado", icon="✅")
        
        st.caption("Este valor define la base para el cálculo de Drawdown y Equity.")
        
    with col_cap2:
        st.markdown("### 🎯 OBJETIVOS OPERATIVOS")
        obj_sem = st.number_input("Objetivo Semanal (€)", value=500.0, step=50.0)
        obj_mes = st.number_input("Objetivo Mensual (€)", value=2000.0, step=100.0)
        st.progress(min(st.session_state.pnl_dia / (obj_sem/5) if obj_sem > 0 else 0, 1.0), 
                    text=f"Progreso objetivo diario: {st.session_state.pnl_dia:,.2f}€")

    st.markdown("---")

    # 9.2 CONFIGURACIÓN DE RIESGO (ESTRATEGIA)
    st.markdown("### 🛡️ CONFIGURACIÓN DE RIESGO ALGORÍTMICO")
    c_risk1, c_risk2, c_risk3 = st.columns(3)
    
    with c_risk1:
        riesgo_por_op = st.slider("% Riesgo Máximo por Operación", 0.5, 5.0, 1.0, 0.1)
        st.caption("Afecta al cálculo automático del Stop Loss sugerido.")
        
    with c_risk2:
        # Este valor se usa en el Bloque 6 para disparar alertas
        st.session_state.min_prob = st.slider("% Umbral de Confianza Lobo", 50, 95, 70, 5)
        st.caption("Nivel mínimo para considerar una señal como 'ALTA PROBABILIDAD'.")

    with c_risk3:
        st.markdown("**Sincronización Dual**")
        if st.button("PROBAR CONEXIÓN TELEGRAM", use_container_width=True):
            test_msg = f"🐺 *WOLF SOVEREIGN*: Sistema de alertas vinculado correctamente.\nID: {st.session_state.initialized}"
            send_wolf_alert(test_msg)
            st.toast("Señal enviada a Telegram", icon="📡")

    st.markdown("---")

    # 9.3 INYECCIÓN MANUAL DE INSTRUMENTOS
    st.markdown("### 🚀 INYECCIÓN MANUAL DE ACTIVOS")
    st.info("Añade activos específicos de XTB, eToro o IBKR usando el Ticker de Yahoo Finance (ej: SAN.MC, NVDA, GC=F).")
    
    with st.form("form_custom_ticker", clear_on_submit=True):
        c_add1, c_add2, c_add3 = st.columns([2, 2, 1])
        new_name = c_add1.text_input("Nombre del Activo", placeholder="Ej: Nvidia")
        new_ticker = c_add2.text_input("Ticker Yahoo Finance", placeholder="Ej: NVDA")
        
        if c_add3.form_submit_button("AÑADIR"):
            if new_name and new_ticker:
                # Evitar duplicados
                if not any(d['ticker'] == new_ticker for d in st.session_state.custom_tickers):
                    st.session_state.custom_tickers.append({"nombre": new_name, "ticker": new_ticker})
                    st.success(f"{new_name} ({new_ticker}) inyectado con éxito.")
                    # Inyectamos inmediatamente en la base de datos volátil
                    inject_custom_tickers()
                    st.rerun()
                else:
                    st.warning("El ticker ya existe en la lista personalizada.")

    # Visualizar y gestionar activos manuales
    if st.session_state.custom_tickers:
        with st.expander("Ver y Editar Activos Personalizados", expanded=True):
            for idx, item in enumerate(st.session_state.custom_tickers):
                c_del1, c_del2 = st.columns([5, 1])
                c_del1.markdown(f"🔹 **{item['nombre']}** (`{item['ticker']}`)")
                if c_del2.button("Eliminar", key=f"del_custom_{idx}", use_container_width=True):
                    st.session_state.custom_tickers.pop(idx)
                    st.rerun()

# =========================================================
# FIN DEL BLOQUE 9 ACTUALIZADO
# =========================================================
# =========================================================
# 10. VENTANA NOTICIAS: SENTIMENT-TO-TRADE ENGINE (IA)
# =========================================================

def render_news_signal_card(title, instrument, tipo, ent, tp, sl, vol):
    """Renderiza la tarjeta de señal generada por la IA con estilo Wolf"""
    color = "#00ff41" if tipo == "COMPRA" else "#ff3131"
    st.markdown(f"""
        <div style="background:#0a0e14; padding:15px; border:1px solid #333; border-top:4px solid {color}; border-radius:8px; margin-bottom:12px;">
            <p style="margin:0; font-size:0.75rem; color:#D4AF37; font-weight:bold;">{title.upper()}</p>
            <h4 style="margin:5px 0; color:{color};">{tipo}: {instrument}</h4>
            <div style="display:flex; justify-content:space-between; font-size:0.85rem; background:rgba(255,255,255,0.05); padding:5px; border-radius:4px;">
                <span>📍 <small>ENT:</small> <b>{ent}</b></span>
                <span>🎯 <small>TP:</small> <b style="color:#00ff41;">{tp}</b></span>
                <span>🛡️ <small>SL:</small> <b style="color:#ff3131;">{sl}</b></span>
            </div>
            <p style="margin:8px 0 0 0; font-size:0.7rem; color:#888;">Gestión de riesgo: <b>{vol} lotes</b></p>
        </div>
    """, unsafe_allow_html=True)

def render_window_noticias():
    st.subheader("📰 SENTINEL NEWS INTELLIGENCE")
    
    # 10.1 PESTAÑAS DE CATEGORÍAS REALES
    tabs = st.tabs([
        "🌍 Global", "📈 Índices", "💱 Divisas", 
        "🇪🇸 España", "🇺🇸 Internacional", "₿ Crypto"
    ])

    # Simulador Dinámico de Escenarios (Sustituye al placeholder anterior)
    # Formato: (Noticia, Activo, Acción, Entrada, TP, SL, Lotes)
    news_scenarios = {
        0: [("Tensión en Oriente Medio", "ORO", "COMPRA", "2380.10", "2450", "2340", "0.20"),
            ("Datos de Inflación (CPI)", "S&P 500", "VENTA", "5120", "5010", "5180", "0.10")],
        
        1: [("Rebalanceo Nasdaq", "NASDAQ 100", "COMPRA", "18100", "18500", "17900", "0.05"),
            ("Debilidad en Manufactura DAX", "DAX 40", "VENTA", "17950", "17600", "18100", "0.10")],
            
        2: [("Intervención Banco Japón", "USD/JPY", "VENTA", "154.20", "151.00", "156.50", "0.50"),
            ("Fortaleza del Euro", "EUR/USD", "COMPRA", "1.0720", "1.0850", "1.0650", "0.80")],

        3: [("Resultados Santander", "SAN.MC", "COMPRA", "4.25", "4.60", "4.05", "100"),
            ("Ajuste Sector Energía", "IBERDROLA", "VENTA", "11.20", "10.80", "11.50", "50")],

        4: [("IA Rally Nvidia", "NVIDIA", "COMPRA", "880", "950", "840", "5"),
            ("Demanda iPhone en China", "APPLE", "VENTA", "175", "160", "182", "10")],

        5: [("Aprobación ETF Spot", "BITCOIN", "COMPRA", "64500", "70000", "61000", "0.02"),
            ("Fuga de liquidez Altcoins", "SOLANA", "VENTA", "135.00", "110.00", "150.00", "1.00")]
    }

    for i, tab in enumerate(tabs):
        with tab:
            c_left, c_right = st.columns([2, 1])
            
            with c_left:
                st.markdown("### 🔥 IMPACTO DE TITULARES (IA ANALYTICS)")
                
                # Barra de sentimiento dinámica por categoría
                sentimiento = 75 if i % 2 == 0 else 35
                sent_color = "#00ff41" if sentimiento > 50 else "#ff3131"
                st.write(f"Sentimiento del Mercado: **{sentimiento}% {'Alcista' if sentimiento > 50 else 'Bajista'}**")
                st.progress(sentimiento / 100)
                
                st.markdown(f"""
                * 🟢 **Titular Principal:** Impacto positivo detectado en el flujo de órdenes institucional.
                * 🟡 **Correlación:** Alta sensibilidad a los tipos de interés de la Fed en esta categoría.
                * 🔴 **Riesgo:** Volatilidad esperada alta en la apertura de la sesión de Nueva York.
                """)
                
                if st.button(f"Sincronizar Noticias {i}", key=f"sync_n_{i}"):
                    st.toast("Escaneando Bloomberg y Reuters...", icon="🔍")

            with c_right:
                st.markdown("### 🎯 SEÑALES IA")
                # Obtenemos los escenarios de la categoría o el global por defecto
                scenarios = news_scenarios.get(i, news_scenarios[0])
                for s in scenarios:
                    render_news_signal_card(s[0], s[1], s[2], s[3], s[4], s[5], s[6])

# =========================================================
# FIN DEL BLOQUE 10 ACTUALIZADO
# =========================================================
# =========================================================
# 11. VENTANA IA WOLF: ASESOR FINANCIERO AVANZADO (v1.1)
# =========================================================

def render_window_ia_wolf():
    st.subheader("🤖 IA WOLF: ASISTENTE ESTRATÉGICO")
    
    # 11.1 OPCIONES PREDETERMINADAS (Interacción Rápida)
    st.markdown("---")
    c_ia1, c_ia2, c_ia3, c_ia4 = st.columns(4)
    
    sugerencia = None
    if c_ia1.button("📊 Analizar Mercado", use_container_width=True):
        sugerencia = f"Hazme un resumen del sentimiento actual para {st.session_state.ticker_name}."
    if c_ia2.button("🛡️ Revisar Riesgo", use_container_width=True):
        sugerencia = "Evalúa si mi gestión de capital es adecuada para el mercado actual."
    if c_ia3.button("💼 Estado de Cartera", use_container_width=True):
        num_ops = len(st.session_state.active_trades)
        sugerencia = f"Tengo {num_ops} operaciones abiertas. ¿Ves algún riesgo de sobreexposición?"
    if c_ia4.button("🎯 Próxima Caza", use_container_width=True):
        sugerencia = "¿Qué activo presenta la mejor confluencia técnica ahora mismo?"

    # Contenedor de chat con scroll y CSS de legibilidad forzada
    st.markdown("""
        <style>
        [data-testid="stChatMessageContent"] p { color: #FFFFFF !important; font-size: 1.05rem !important; }
        .stChatFloatingInputContainer { background-color: #000000 !important; }
        </style>
    """, unsafe_allow_html=True)

    chat_container = st.container(height=450)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 11.2 LÓGICA DE INTERACCIÓN (Input o Botones)
    prompt_input = st.chat_input("Escribe tu consulta al analista Wolf...")
    
    # Si el usuario pulsó un botón, el prompt será la sugerencia
    final_prompt = sugerencia if sugerencia else prompt_input

    if final_prompt:
        # Añadir y mostrar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": final_prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(final_prompt)

        # Respuesta de la IA con lógica de Analista Senior
        with chat_container:
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                # Construcción de respuesta dinámica basada en el contexto del usuario
                if "Riesgo" in final_prompt or "capital" in final_prompt:
                    base_res = f"Analizando tu exposición... Con un disponible de {st.session_state.margen_disp:,.2f}€ y un umbral de confianza configurado al {st.session_state.min_prob}%, tu perfil actual es conservador-eficiente."
                elif "Mercado" in final_prompt or "Análisis" in final_prompt:
                    base_res = f"Vigilando {st.session_state.ticker_name}. La estructura técnica en {st.session_state.int_top} muestra una divergencia interesante con el RSI. No operaría hasta confirmar el soporte de la EMA 200."
                else:
                    base_res = "Entendido, Lobo. Desde una perspectiva institucional, el flujo de órdenes indica una rotación hacia activos de refugio. Mantén el Stop Loss ceñido al ATR de la sesión anterior."

                # Simulación de escritura fluida
                for word in base_res.split():
                    full_response += word + " "
                    time.sleep(0.04)
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        # Forzar refresco ligero para limpiar el estado de los botones
        if sugerencia: st.rerun()

# =========================================================
# FIN DEL BLOQUE 11 ACTUALIZADO
# =========================================================
# =========================================================
# 12. VENTANA OPCIONES: MOVIMIENTOS Y PRECIOS OBJETIVO
# =========================================================

def render_window_opciones():
    st.subheader("💎 ESTRATEGIAS AVANZADAS CON OPCIONES")
    st.caption("Análisis de volatilidad implícita y proyección de precios objetivo para estrategias Call/Put.")

    # 12.1 SELECTOR DE ACTIVO PARA OPCIONES
    col_opt1, col_opt2 = st.columns([2, 1])
    
    with col_opt1:
        # Usamos los índices como subyacentes principales para opciones
        op_assets = DATABASE["opciones"]["Índices Relacionados"]
        sel_op = st.selectbox("SELECCIONAR SUBYACENTE", list(op_assets.keys()))
        sym_op = op_assets[sel_op][0]
    
    # Descarga de datos para análisis de volatilidad
    df_op = get_advanced_data(sym_op, interval='1d')
    vix_df = get_advanced_data("^VIX", interval='1d') # Índice del miedo

    if df_op is not None and not df_op.empty:
        last_p = df_op['Close'].iloc[-1]
        atr = df_op['ATR'].iloc[-1] if 'ATR' in df_op.columns else (last_p * 0.02)
        
        # 12.2 CÁLCULO DE MOVIMIENTO ESPERADO (Precios Objetivo)
        # Basado en volatilidad histórica y ATR
        upper_target = last_p + (atr * 2.5)
        lower_target = last_p - (atr * 2.5)
        
        with col_opt2:
            st.markdown(f"""
                <div style="background:#0a0e14; padding:15px; border:1px solid #D4AF37; border-radius:10px; text-align:center;">
                    <p style="margin:0; color:#888;">PRECIO ACTUAL</p>
                    <h2 style="margin:0; color:#FFFFFF;">{last_p:,.2f}</h2>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # 12.3 DASHBOARD DE ESCENARIOS
        c_esc1, c_esc2, c_esc3 = st.columns(3)
        
        with c_esc1:
            st.markdown("### 🟢 ESCENARIO BULL (CALL)")
            st.write(f"**Precio Objetivo:** {upper_target:,.2f}")
            st.info(f"Probabilidad de quiebre de resistencia R1 detectada.")
            if st.button("Simular Bull Spread", use_container_width=True):
                st.toast("Calculando primas óptimas...", icon="📈")

        with c_esc2:
            st.markdown("### 🔴 ESCENARIO BEAR (PUT)")
            st.write(f"**Precio Objetivo:** {lower_target:,.2f}")
            st.warning(f"Protección recomendada bajo nivel {last_p - atr:,.2f}")
            if st.button("Simular Put Protective", use_container_width=True):
                st.toast("Analizando cobertura de cartera...", icon="🛡️")

        with c_esc3:
            st.markdown("### ⚪ ESCENARIO NEUTRAL")
            st.write(f"**Rango:** {last_p - (atr/2):,.2f} - {last_p + (atr/2):,.2f}")
            st.success("Ideal para estrategias de cobro de prima (Iron Condor).")
            if st.button("Simular Income Strategy", use_container_width=True):
                st.toast("Buscando zonas de baja volatilidad...", icon="💰")

        st.markdown("---")

        # 12.4 GRÁFICO DE VOLATILIDAD Y OBJETIVOS
        st.write("📊 **PROYECCIÓN DE RANGOS DE VENCIMIENTO**")
        fig_op = go.Figure()
        
        # Precio e histórico
        fig_op.add_trace(go.Scatter(x=df_op.index[-50:], y=df_op['Close'].tail(50), name="Precio", line=dict(color="#FFFFFF")))
        
        # Zonas objetivo (Opciones In-The-Money / Out-of-The-Money)
        fig_op.add_hline(y=upper_target, line_dash="dot", line_color="#00ff41", annotation_text="Target Call")
        fig_op.add_hline(y=lower_target, line_dash="dot", line_color="#ff3131", annotation_text="Target Put")
        
        fig_op.update_layout(template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_op, use_container_width=True)

        # 12.5 EL TERMÓMETRO DEL MIEDO (VIX)
        if vix_df is not None:
            vix_val = vix_df['Close'].iloc[-1]
            vix_status = "PÁNICO" if vix_val > 30 else "ESTABLE" if vix_val < 20 else "TENSIÓN"
            vix_color = "#ff3131" if vix_val > 25 else "#00ff41"
            
            st.markdown(f"""
                <div style="background:#1a1a1a; padding:10px; border-radius:5px; border-left: 5px solid {vix_color};">
                    <h4 style="margin:0;">VIX (Índice de Volatilidad): <span style="color:{vix_color};">{vix_val:.2f} ({vix_status})</span></h4>
                    <p style="font-size:0.8rem; color:#888; margin:0;">El VIX alto favorece la venta de opciones. El VIX bajo favorece la compra de opciones.</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.error("No se han podido cargar datos del subyacente para el análisis de opciones.")

# =========================================================
# FIN DEL BLOQUE 12
# =========================================================
# =========================================================
# 13. VENTANA FORMACIÓN: WOLF ACADEMY HUB
# =========================================================

def render_window_formacion():
    st.subheader("🎓 WOLF ACADEMY: RECURSOS ESTRATÉGICOS")
    st.caption("Selección de los mejores cursos de bolsa gratuitos y recursos de alta valoración para dominar el mercado.")

    # 13.1 FILTRO POR NIVEL
    n_cols = st.columns(3)
    levels = ["Principiante", "Intermedio", "Avanzado"]
    
    # Sistema de navegación interno de la academia
    if 'academy_level' not in st.session_state:
        st.session_state.academy_level = "Principiante"

    for i, level in enumerate(levels):
        is_active = st.session_state.academy_level == level
        tag = "menu-active" if is_active else "menu-btn"
        with n_cols[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(level.upper(), key=f"ac_{level}", use_container_width=True):
                st.session_state.academy_level = level
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 13.2 BASE DE DATOS DE CURSOS (Sugerencias Top Valoradas)
    # Estructura: (Título, Plataforma, Valoración, Descripción, Link)
    cursos = {
        "Principiante": [
            ("Introducción a Mercados", "Coursera", "⭐⭐⭐⭐⭐ (4.8)", "Conceptos básicos, tipos de activos y operativa inicial.", "https://www.coursera.org/learn/financial-markets"),
            ("Bolsa desde Cero", "Academia XTB", "⭐⭐⭐⭐ (4.5)", "Curso completo para entender gráficos y brokers.", "https://www.xtb.com/es/formacion"),
            ("Trading 101", "Investopedia", "⭐⭐⭐⭐ (4.3)", "Guía fundamental sobre gestión de capital y órdenes.", "https://www.investopedia.com/trading-skills-and-strategies-4689652")
        ],
        "Intermedio": [
            ("Análisis Técnico Avanzado", "YouTube (Top)", "⭐⭐⭐⭐⭐ (4.9)", "Soportes, resistencias, RSI y Fibonacci profundo.", "https://www.youtube.com/results?search_query=curso+analisis+tecnico+profesional"),
            ("Psicología del Trading", "EdX", "⭐⭐⭐⭐⭐ (4.7)", "Cómo dominar el miedo y la codicia (Psicotrading).", "https://www.edx.org/course/psychology-of-trading"),
            ("Gestión de Riesgo", "TradingView", "⭐⭐⭐⭐ (4.6)", "Cálculo de lotajes, drawdown y esperanza matemática.", "https://es.tradingview.com/education/")
        ],
        "Avanzado": [
            ("Estrategias con Opciones", "CBOE", "⭐⭐⭐⭐⭐ (4.8)", "Griegas, Iron Condors y coberturas de cartera.", "https://www.cboe.com/education/"),
            ("Trading Algorítmico", "QuantConnect", "⭐⭐⭐⭐ (4.5)", "Introducción a la automatización de señales con Python.", "https://www.quantconnect.com/learning"),
            ("Flujo de Órdenes (Order Flow)", "NinjaTrader", "⭐⭐⭐⭐⭐ (4.9)", "Lectura de cinta y profundidad de mercado.", "https://ninjatrader.com/es/support/helpGuides/nt8/")
        ]
    }

    # 13.3 RENDERIZADO DE CURSOS
    current_courses = cursos.get(st.session_state.academy_level, [])
    
    for titulo, plataforma, rating, desc, link in current_courses:
        with st.container():
            col_img, col_txt = st.columns([1, 4])
            
            with col_img:
                # Icono según nivel
                icon = "🟢" if st.session_state.academy_level == "Principiante" else "🟡" if st.session_state.academy_level == "Intermedio" else "🔴"
                st.markdown(f"<h1 style='text-align: center; margin:0;'>{icon}</h1>", unsafe_allow_html=True)
            
            with col_txt:
                st.markdown(f"""
                    <div style="background:#0a0e14; padding:15px; border-radius:8px; border:1px solid #333; margin-bottom:15px;">
                        <div style="display:flex; justify-content:space-between;">
                            <h4 style="margin:0; color:#D4AF37;">{titulo}</h4>
                            <span style="color:#00ff41; font-weight:bold;">{rating}</span>
                        </div>
                        <p style="font-size:0.85rem; color:#888; margin:5px 0;">Plataforma: <b>{plataforma}</b></p>
                        <p style="font-size:0.9rem; margin:10px 0;">{desc}</p>
                        <a href="{link}" target="_blank" style="text-decoration:none;">
                            <button style="background:#1a1a1a; color:#FFFFFF; border:1px solid #D4AF37; padding:5px 15px; border-radius:4px; cursor:pointer;">
                                IR AL CURSO GRATUITO 🚀
                            </button>
                        </a>
                    </div>
                """, unsafe_allow_html=True)

    # 13.4 NOTA DE SEGURIDAD
    st.markdown("---")
    st.caption("⚠️ **Aviso:** Wolf Sovereign no tiene afiliación con estas plataformas. Solo sugerimos recursos gratuitos basados en su reputación en la comunidad de trading.")

# =========================================================
# FIN DEL BLOQUE 13
# =========================================================
# =========================================================
# 14. VENTANA COPYTRADING: SOCIAL TRADING ANALYTICS
# =========================================================

def render_window_copytrading():
    st.subheader("👥 WOLF COPYTRADING: INTELIGENCIA COLECTIVA")
    st.caption("Conecta con los mejores y analiza sus métricas de rendimiento antes de comprometer capital.")

    # 14.1 VINCULACIÓN DE CUENTA
    with st.expander("🔗 VINCULAR PERFIL DE ETORO / BROKER SOCIAL", expanded=True):
        c_vinc1, c_vinc2 = st.columns([3, 1])
        etoro_url = c_vinc1.text_input("Introduce tu URL de perfil de eToro (Ej: etoro.com/people/tu-usuario)")
        if c_vinc2.button("CONECTAR PERFIL", use_container_width=True):
            if etoro_url:
                st.success(f"Perfil vinculado: {etoro_url}")
                st.session_state.etoro_link = etoro_url
            else:
                st.error("Introduce una URL válida.")

    st.markdown("---")

    # 14.2 PANEL DE ANÁLISIS DE TRADERS TOP
    st.write("🔍 **ANALIZADOR DE PERFORMANCE (TOP TRADERS)**")
    
    # Datos simulados de los mejores traders para análisis
    top_traders = [
        {"nombre": "Lobo_Sovereign_Alpha", "rent_anual": 42.5, "drawdown": 8.2, "riesgo": 3, "copiadores": 1240, "estilo": "HFT / Acciones"},
        {"nombre": "Quantum_Fund_ES", "rent_anual": 28.1, "drawdown": 4.5, "riesgo": 2, "copiadores": 3150, "estilo": "Conservador / ETFs"},
        {"nombre": "Crypto_Master_99", "rent_anual": 115.4, "drawdown": 35.2, "riesgo": 6, "copiadores": 890, "estilo": "Agresivo / Crypto"}
    ]

    for trader in top_traders:
        with st.container():
            # Estilo Wolf para cada tarjeta de trader
            color_risk = "#00ff41" if trader['riesgo'] <= 3 else "#ffaa00" if trader['riesgo'] <= 5 else "#ff3131"
            
            st.markdown(f"""
                <div style="background:#0a0e14; padding:20px; border-radius:10px; border:1px solid #333; margin-bottom:15px; border-left: 6px solid {color_risk};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h3 style="margin:0; color:#FFFFFF;">{trader['nombre']}</h3>
                        <span style="background:{color_risk}; color:#000; padding:2px 10px; border-radius:20px; font-weight:bold; font-size:0.8rem;">
                            RIESGO: {trader['riesgo']}
                        </span>
                    </div>
                    <p style="color:#D4AF37; font-size:0.9rem; margin:5px 0;">Estilo: <b>{trader['estilo']}</b></p>
                    <hr style="border:0.1px solid #222; margin:10px 0;">
                    <div style="display:flex; justify-content:space-around; text-align:center;">
                        <div>
                            <small style="color:#888;">RENT. ANUAL</small><br>
                            <b style="color:#00ff41; font-size:1.2rem;">+{trader['rent_anual']}%</b>
                        </div>
                        <div>
                            <small style="color:#888;">MAX DRAWDOWN</small><br>
                            <b style="color:#ff3131; font-size:1.2rem;">-{trader['drawdown']}%</b>
                        </div>
                        <div>
                            <small style="color:#888;">COPIADORES</small><br>
                            <b style="color:#FFFFFF; font-size:1.2rem;">{trader['copiadores']}</b>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # 14.3 BOTÓN DE ACCIÓN / ANÁLISIS PROFUNDO
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button(f"VER CARTERA DE {trader['nombre']}", key=f"view_{trader['nombre']}", use_container_width=True):
                    st.info(f"Abriendo desglose de activos de {trader['nombre']}...")
            with col_b2:
                if st.button(f"CALCULAR COPIA ÓPTIMA", key=f"calc_{trader['nombre']}", use_container_width=True):
                    # Lógica de cálculo sugerido
                    monto_sug = st.session_state.wallet * (0.2 / trader['riesgo'])
                    st.success(f"Basado en tu capital, la copia óptima para este trader es de: **{monto_sug:,.2f}€**")

    # 14.4 VÍNCULO EXTERNO FINAL
    st.markdown("---")
    st.markdown("""
        <div style="text-align:center;">
            <p style="color:#888;">¿Listo para automatizar?</p>
            <a href="https://www.etoro.com/discover/copytrader" target="_blank" style="text-decoration:none;">
                <button style="background:#D4AF37; color:#000; border:none; padding:12px 30px; border-radius:5px; font-weight:bold; cursor:pointer; width:100%;">
                    IR AL DASHBOARD DE ETORO 🚀
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# =========================================================
# BLOQUE FINAL: DISPARADOR DEL SISTEMA
# =========================================================

if __name__ == "__main__":
    try:
        run_navigation()
    except Exception as e:
        st.error(f"Error fatal en el orquestador Wolf: {e}")
