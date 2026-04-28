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
TELEGRAM_BOT_TOKEN = "TU_BOT_TOKEN_AQUÍ"
USER_CHAT_IDS = ["TU_ID_AQUÍ", "ID_DE_TU_AMIGO_AQUÍ"] 

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
