import streamlit as st
import yfinance as yf

# =========================================================
# BLOQUE 1: MOTOR DE ESTILOS (COLORES FIJOS Y SENTINEL ROJO)
# =========================================================
st.set_page_config(page_title="Wolf Sovereign V95", layout="wide", page_icon="🐺")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; }
    [data-testid="stVerticalBlock"] { gap: 0rem !important; }
    div[data-testid="stColumn"] { padding: 0px !important; margin: 0px !important; }

    /* NAV SUPERIOR: MARRÓN -> BLANCO */
    div.nav-btn button {
        background-color: #A67B5B !important; color: #000000 !important;
        border: 1px solid #000 !important; border-radius: 0px !important; height: 3.5em !important;
    }
    div.nav-active button {
        background-color: #FFFFFF !important; color: #000000 !important;
        border: 2px solid #000000 !important; border-radius: 0px !important; height: 3.5em !important; font-weight: 900 !important;
    }

    /* MENÚ LOBO: BLANCO -> NEGRO */
    div.menu-btn button {
        background-color: #FFFFFF !important; color: #000000 !important;
        border: 1px solid #333333 !important; border-radius: 0px !important; height: 3.2em !important;
    }
    div.menu-active button {
        background-color: #000000 !important; color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important; border-radius: 0px !important; height: 3.2em !important; font-weight: bold !important;
    }

    /* SENTINEL: ROJO / LETRAS NEGRAS */
    div.sentinel-btn button {
        background-color: #FF0000 !important; color: #000000 !important;
        border: 2px solid #000000 !important; font-weight: 900 !important; height: 4em !important;
    }

    .sentinel-space { margin-top: 60px !important; margin-bottom: 20px !important; }

    /* Ticker */
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #000; border-bottom: 2px solid #A67B5B; padding: 10px 0;
    }
    .ticker-move { display: flex; width: fit-content; animation: ticker 60s linear infinite; }
    .ticker-item { padding: 0 50px; white-space: nowrap; font-family: monospace; font-size: 1.1rem; color: #fff; }
    @keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# BLOQUE 2: BASE DE DATOS (NOMBRES XTB + LOGOS)
# =========================================================
if 'setup' not in st.session_state:
    st.session_state.update({
        'view': "Lobo", 'active_cat': None, 'active_sub': None,
        'ticker': "NQ=F", 'ticker_name': "US100",
        'wallet': 18850.00, 'margen': 15200.00, 'pnl': 420.50, 'setup': True
    })

DATABASE = {
    "stocks": {
        "TECNOLOGÍA": {
            "APPLE (AAPL.US) 🍎": ["AAPL", ""], "TESLA (TSLA.US) ⚡": ["TSLA", ""], 
            "NVIDIA (NVDA.US) 🟢": ["NVDA", ""], "AMAZON (AMZN.US) 📦": ["AMZN", ""],
            "META (META.US) 📱": ["META", ""], "MICROSOFT (MSFT.US) 💻": ["MSFT", ""],
            "ALPHABET (GOOGL.US) 🔍": ["GOOGL", ""], "NETFLIX (NFLX.US) 🎬": ["NFLX", ""],
            "INTEL (INTC.US) 🔵": ["INTC", ""], "AMD (AMD.US) 🔴": ["AMD", ""]
        },
        "BANCA": {
            "SANTANDER (SAN.MC) 🏦": ["SAN.MC", ""], "BBVA (BBVA.MC) 💙": ["BBVA.MC", ""],
            "JPMORGAN (JPM.US) 🏛️": ["JPM", ""], "HSBC (HSBA.UK) 🦁": ["HSBA.L", ""]
        },
        "SALUD": {
            "PFIZER (PFE.US) 💊": ["PFE", ""], "MODERNA (MRNA.US) 🧬": ["MRNA", ""]
        }
    },
    "indices": {
        "EEUU": {
            "US100 (Nasdaq) 🇺🇸": ["NQ=F", ""], "US500 (S&P500) 🇺🇸": ["ES=F", ""], 
            "US30 (Dow Jones) 🇺🇸": ["YM=F", ""], "RUSSELL2000 🇺🇸": ["RTY=F", ""]
        },
        "EUROPA": {
            "DE40 (DAX) 🇩🇪": ["^GDAXI", ""], "SPA35 (IBEX) 🇪🇸": ["^IBEX", ""], 
            "EU50 (Eurostoxx) 🇪🇺": ["^STOXX50E", ""], "FRA40 (CAC) 🇫🇷": ["^FCHI", ""]
        },
        "ASIA": {
            "HK50 (Hang Seng) 🇭🇰": ["^HSI", ""], "JPN225 (Nikkei) 🇯🇵": ["^N225", ""]
        }
    },
    "material": {
        "ENERGÍA": {
            "OIL.WTI (Petróleo) 🛢️": ["CL=F", ""], "OIL (Brent) 🌍": ["BZ=F", ""], 
            "NATGAS (Gas) 🔥": ["NG=F", ""], "GASOIL 🚛": ["HO=F", ""],
            "GASOLINE ⛽": ["RB=F", ""]
        },
        "METALES": {
            "GOLD (Oro) 🟡": ["GC=F", ""], "SILVER (Plata) ⚪": ["SI=F", ""], 
            "COPPER (Cobre) 🥉": ["HG=F", ""], "PLATINUM 💍": ["PL=F", ""],
            "PALLADIUM 💎": ["PA=F", ""]
        },
        "GRANOS": {
            "WHEAT (Trigo) 🌾": ["ZW=F", ""], "CORN (Maíz) 🌽": ["ZC=F", ""], 
            "SOYBEAN (Soja) 🌱": ["ZS=F", ""]
        }
    },
    "divisas": {
        "MAJORS": {
            "EURUSD 🇪🇺🇺🇸": ["EURUSD=X", ""], "GBPUSD 🇬🇧🇺🇸": ["GBPUSD=X", ""], 
            "USDJPY 🇺🇸🇯🇵": ["USDJPY=X", ""], "AUDUSD 🇦🇺🇺🇸": ["AUDUSD=X", ""]
        },
        "CRYPTO": {
            "BITCOIN (BTC) ₿": ["BTC-USD", ""], "ETHEREUM (ETH) ⟠": ["ETH-USD", ""], 
            "RIPPLE (XRP) 💠": ["XRP-USD", ""], "SOLANA (SOL) ☀️": ["SOL-USD", ""]
        }
    }
}

# =========================================================
# BLOQUE 3: HEADER Y TICKER
# =========================================================
st.markdown(f'<div style="background-color:#0d1117; padding:8px; display:flex; justify-content:space-around; border-bottom:1px solid #333; color:#A67B5B; font-weight:bold;">'
            f'<span>CAPITAL: {st.session_state.wallet:,.2f}€</span>'
            f'<span>MARGEN: {st.session_state.margen:,.2f}€</span>'
            f'<span>PnL: {st.session_state.pnl:,.2f}€</span></div>', unsafe_allow_html=True)

hot_list = [("NQ=F", "US100", "🇺🇸", "COMPRAR"), ("GC=F", "GOLD", "🟡", "COMPRAR")]
content = "".join([f'<div class="ticker-item">{i} {n} <span style="color:{"#00ff41" if s=="COMPRAR" else "#ff3131"};">[{s}]</span></div>' for t, n, i, s in hot_list * 10])
st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

# ACCIÓN SENTINEL (ROJO)
st.markdown('<div class="sentinel-space"></div>', unsafe_allow_html=True)
with st.expander("🚨 ALERTAS CRÍTICAS SENTINEL"):
    c_sen = st.columns(2)
    for idx, (t, n, i, s) in enumerate(hot_list):
        with c_sen[idx]:
            st.markdown('<div class="sentinel-btn">', unsafe_allow_html=True)
            if st.button(f"EJECUTAR {s}: {n} {i}", key=f"sen_{n}"):
                st.warning(f"ORDEN SENTINEL LANZADA: {n}")
            st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 4: NAVEGACIÓN (VENTANAS)
# =========================================================
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
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 5: VENTANA LOBO (CASCADA FIJADA)
# =========================================================
if st.session_state.view == "Lobo":
    # 5.1 - CATEGORÍAS (Stocks, Indices, Materiales, Divisas)
    cats = list(DATABASE.keys())
    c_cat = st.columns(len(cats))
    for i, cat in enumerate(cats):
        is_active = st.session_state.active_cat == cat
        tag = "menu-active" if is_active else "menu-btn"
        with c_cat[i]:
            st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
            if st.button(cat.upper(), key=f"c_{cat}", use_container_width=True):
                st.session_state.active_cat = cat
                st.session_state.active_sub = None 
            st.markdown('</div>', unsafe_allow_html=True)

    # 5.2 - SUBCATEGORÍAS
    if st.session_state.active_cat:
        sub_dict = DATABASE[st.session_state.active_cat]
        sub_list = list(sub_dict.keys())
        c_sub = st.columns(len(sub_list))
        for i, sub in enumerate(sub_list):
            is_active = st.session_state.active_sub == sub
            tag = "menu-active" if is_active else "menu-btn"
            with c_sub[i]:
                st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                if st.button(sub, key=f"s_{sub}", use_container_width=True):
                    st.session_state.active_sub = sub
                st.markdown('</div>', unsafe_allow_html=True)

        # 5.3 - ACTIVOS (Nombres XTB + Logos)
        if st.session_state.active_sub:
            items = sub_dict[st.session_state.active_sub]
            # Grid dinámico: si hay más de 5, crea filas de 5
            num_items = len(items)
            cols_act = st.columns(5)
            for idx, (name, data) in enumerate(items.items()):
                is_active = st.session_state.ticker_name == name
                tag = "menu-active" if is_active else "menu-btn"
                with cols_act[idx % 5]:
                    st.markdown(f'<div class="{tag}">', unsafe_allow_html=True)
                    if st.button(name, key=f"f_{name}", use_container_width=True):
                        st.session_state.ticker = data[0]
                        st.session_state.ticker_name = name
                    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BLOQUE 7: MOTOR GRÁFICO ULTRA-RÁPIDO (V95 OPTIMIZADO)
# =========================================================
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import yfinance as yf

# Función con caché para acelerar la descarga de datos
@st.cache_data(ttl=60)  # Los datos se refrescan cada 60 segundos
def fetch_fast_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    return df

def render_optimized_chart():
    # 1. DESPLEGABLE DE RANGO (Sustituye a los botones)
    c_sel, _ = st.columns([1, 4])
    with c_sel:
        opciones = {
            "1m (Última hora)": ["1h", "1m"],
            "5m (Últimas 6h)": ["6h", "5m"],
            "15m (Últimas 24h)": ["24h", "15m"],
            "1h (Últimas 72h)": ["72h", "1h"]
        }
        seleccion = st.selectbox("⏳ RANGO TEMPORAL", list(opciones.keys()), index=2)
        periodo, intervalo = opciones[seleccion]

    # 2. CARGA DE DATOS
    df = fetch_fast_data(st.session_state.ticker, periodo, intervalo)
    
    if df.empty:
        st.info("Esperando flujo de datos del mercado...")
        return

    # 3. CÁLCULOS TÉCNICOS EXPRESS
    df['EMA'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # RSI (Cálculo rápido)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))

    # Niveles Dinámicos
    h_max, l_min = df['High'].max(), df['Low'].min()
    current_price = df['Close'].iloc[-1]
    trend = "ALCISTA 🟢" if current_price > df['EMA'].iloc[-1] else "BAJISTA 🔴"

    # 4. DASHBOARD DE MÉTRICAS (Fuera del gráfico)
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("MÁXIMO", f"{h_max:,.2f}")
    m2.metric("MÍNIMO", f"{l_min:,.2f}")
    m3.metric("TENDENCIA", trend)
    m4.metric("ÚLTIMO RSI", f"{df['RSI'].iloc[-1]:.1f}")

    # 5. GRÁFICO DE VELAS + VOLUMEN (Renderizado en un solo paso)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.02, row_width=[0.2, 0.8])

    # Velas e Indicadores
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Precio", increasing_line_color='#00ff41', decreasing_line_color='#ff3131'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['EMA'], line=dict(color='#A67B5B', width=1), name="EMA 20"), row=1, col=1)

    # Soportes y Resistencias (Lineas horizontales fijas al rango)
    fig.add_hline(y=h_max, line_dash="dash", line_color="#ff3131", opacity=0.3)
    fig.add_hline(y=l_min, line_dash="dash", line_color="#00ff41", opacity=0.3)

    # Volumen
    colors = ['#00ff41' if row['Open'] < row['Close'] else '#ff3131' for i, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name="Volumen"), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", height=600,
        plot_bgcolor="#05070a", paper_bgcolor="#05070a",
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.05, x=1)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

render_optimized_chart()
