import streamlit as st
import yfinance as yf
import random

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
# BLOQUE 7: MOTOR GRÁFICO (V101 - CON PRECIO EN TIEMPO REAL)
# =========================================================
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import yfinance as yf

def render_shielded_chart():
    # Placeholder para evitar duplicados
    main_chart_placeholder = st.empty()
    
    with st.container():
        c_sel, _ = st.columns([1, 4])
        with c_sel:
            opciones = {
                "1m (1 hora)": ["1h", "1m"],
                "5m (6 horas)": ["6h", "5m"],
                "15m (24 horas)": ["1d", "15m"],
                "1h (72 horas)": ["3d", "1h"]
            }
            seleccion = st.selectbox("⏳ RANGO", list(opciones.keys()), index=2, key="range_selector_v101")
            periodo, intervalo = opciones[seleccion]

    # Obtención de datos
    ticker_actual = st.session_state.ticker
    df = fetch_safe_data(ticker_actual, periodo, intervalo)
    
    if df is None or df.empty or len(df) < 5:
        st.warning(f"⚠️ Sincronizando flujo de datos para {ticker_actual}...")
        return

    # Cálculos de Precio y Tendencia
    df = df.dropna(subset=['Close'])
    precio_actual = float(df['Close'].iloc[-1])
    ema_20 = df['Close'].ewm(span=20, adjust=False).mean()
    tendencia_raw = "ALCISTA" if precio_actual > ema_20.iloc[-1] else "BAJISTA"
    
    # Guardar en sesión para el Bloque 8
    st.session_state['last_price'] = precio_actual
    st.session_state['last_trend'] = tendencia_raw

    # --- NUEVA FILA DE MÉTRICAS (4 COLUMNAS) ---
    h_max, l_min = float(df['High'].max()), float(df['Low'].min())
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric("PRECIO ACTUAL", f"{precio_actual:,.4f}", delta_color="normal")
    m2.metric("MÁXIMO", f"{h_max:,.4f}")
    m3.metric("MÍNIMO", f"{l_min:,.4f}")
    
    # Color dinámico para la tendencia
    t_icon = "🟢" if tendencia_raw == "ALCISTA" else "🔴"
    m4.metric("TENDENCIA", f"{tendencia_raw} {t_icon}")

    # Construcción del Gráfico Profesional
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_width=[0.2, 0.8])

    time_labels = df.index.strftime('%H:%M')

    # Velas
    fig.add_trace(go.Candlestick(
        x=time_labels, open=df['Open'], high=df['High'], 
        low=df['Low'], close=df['Close'],
        name="Precio", increasing_line_color='#00ff41', decreasing_line_color='#ff3131'
    ), row=1, col=1)

    # Línea de Precio Actual (HILO HORIZONTAL)
    fig.add_hline(y=precio_actual, line_dash="dot", line_color="white", 
                  annotation_text=f"ACTUAL: {precio_actual:,.4f}", 
                  annotation_position="bottom right", row=1, col=1)

    # EMA 20
    fig.add_trace(go.Scatter(x=time_labels, y=ema_20, 
                             line=dict(color='#A67B5B', width=1.5), name="EMA 20"), row=1, col=1)

    # Volumen
    vol_colors = ['#00ff41' if c >= o else '#ff3131' for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(x=time_labels, y=df['Volume'], 
                         marker_color=vol_colors, name="Volumen"), row=2, col=1)

    fig.update_xaxes(type='category', nticks=10)
    fig.update_layout(
        template="plotly_dark", height=500,
        plot_bgcolor="#05070a", paper_bgcolor="#05070a",
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.05, x=1)
    )

    main_chart_placeholder.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key="chart_v101")

render_shielded_chart()
# =========================================================
# BLOQUE 8: MOTOR DE INVERSIÓN SENTINEL (CESTA DE ÓRDENES)
# =========================================================
import random

def render_sentinel_investment_cards():
    st.markdown("---")
    st.subheader(f"🛡️ ESTRATEGIA TÁCTICA: {st.session_state.ticker_name}")
    
    # 1. Datos dinámicos de la sesión
    balance = st.session_state.get('wallet', 18850.00)
    margen_libre = st.session_state.get('margen', 15200.00)
    precio_actual = st.session_state.get('last_price', 0.0)
    tendencia = st.session_state.get('last_trend', "NEUTRAL")
    ticker = st.session_state.get('ticker', "").upper()
    
    if precio_actual == 0.0:
        st.info("💡 Sincronizando niveles de entrada...")
        return

    color = "#00ff41" if tendencia == "ALCISTA" else "#ff3131"
    accion = "COMPRA" if tendencia == "ALCISTA" else "VENTA"
    
    # 2. FACTOR DE ACTIVO (Ajuste de Nominal XTB)
    if any(x in ticker for x in ["USD", "EUR", "GBP", "JPY"]): factor_nominal = 1.0   # Forex
    elif any(x in ticker for x in ["GOLD", "SILVER", "OIL"]): factor_nominal = 0.05   # Materiales
    else: factor_nominal = 0.02                                                       # Índices (US100, etc)

    # 3. CONFIGURACIÓN DE CESTA (Entradas Escalonadas)
    # Definimos 'offset' para que los precios de entrada NO sean iguales
    estrategias = [
        {"id": "CP", "label": "CORTO PLAZO", "t": "1-4H", "risk": 0.005, "dist": 0.004, "offset": 0.0000}, # Mercado
        {"id": "MP", "label": "MEDIO PLAZO", "t": "1-3D", "risk": 0.008, "dist": 0.015, "offset": 0.0015}, # Limit
        {"id": "LP", "label": "LARGO PLAZO", "t": "+1 SEM", "risk": 0.012, "dist": 0.040, "offset": 0.0035} # Deep Limit
    ]

    cols = st.columns(3)

    for i, est in enumerate(estrategias):
        # A. Cálculo del Precio de Entrada Escalonado
        # En compra, queremos entrar más abajo (offset negativo). En venta, más arriba.
        if accion == "COMPRA":
            precio_entrada = precio_actual * (1 - est['offset'])
            tp = precio_entrada * (1 + est['dist'])
            sl = precio_entrada * (1 - est['dist'] * 0.6)
        else:
            precio_entrada = precio_actual * (1 + est['offset'])
            tp = precio_entrada * (1 - est['dist'])
            sl = precio_entrada * (1 + est['dist'] * 0.6)

        # B. Cálculo de Volumen Fraccionado (Para permitir 4 operaciones)
        # Dividimos el riesgo para que cada operación ocupe una fracción del margen
        riesgo_operacion = (balance * est['risk']) / 4 
        vol_calc = (riesgo_operacion / (precio_entrada * est['dist'])) * factor_nominal
        
        # Límite de seguridad: máximo 0.5% del margen libre por posición
        lotes_finales = min(vol_calc, (margen_libre * 0.005) / 100)
        lotes_finales = max(0.01, round(lotes_finales, 2))

        prob = random.randint(75, 94)

        with cols[i]:
            # HTML con Precios de Entrada Diferenciados
            html_card = (
                f'<div style="border: 2px solid {color}; border-radius: 10px; padding: 18px; background-color: #0d1117; min-height: 420px;">'
                f'<h3 style="color: {color}; text-align: center; margin-top: 0;">{est["label"]}</h3>'
                f'<p style="text-align: center; color: #888; font-size: 0.8rem; margin: 0;">({est["t"]})</p>'
                f'<hr style="border-color: #333; margin: 12px 0;">'
                
                f'<div style="margin-bottom: 12px; background-color: #161b22; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #333;">'
                f'<span style="color: #888; font-size: 0.75rem; display: block;">PRECIO DE ENTRADA</span>'
                f'<b style="font-size: 1.25rem; color: white;">{precio_entrada:,.4f}</b>'
                f'</div>'

                f'<div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.85rem;">'
                f'<span style="color: #bbb;">ORDEN:</span><span style="color: {color}; font-weight: bold;">{accion}</span>'
                f'</div>'
                f'<div style="display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 0.85rem;">'
                f'<span style="color: #bbb;">PROBABILIDAD:</span><span style="font-weight: bold; color: white;">{prob}%</span>'
                f'</div>'
                
                f'<div style="background-color: #161b22; padding: 10px; border-radius: 5px; border-left: 4px solid {color}; margin-bottom: 15px;">'
                f'<small style="color: #888;">VOLUMEN SUGERIDO</small><br>'
                f'<b style="font-size: 1.2rem; color: white;">{lotes_finales:.2f} LOTES</b>'
                f'</div>'

                f'<div style="font-size: 0.9rem; border-top: 1px solid #333; padding-top: 12px;">'
                f'<p style="margin: 3px 0; color: #00ff41; display: flex; justify-content: space-between;">'
                f'<b>TAKE PROFIT:</b> <span>{tp:,.4f}</span></p>'
                f'<p style="margin: 3px 0; color: #ff3131; display: flex; justify-content: space-between;">'
                f'<b>STOP LOSS:</b> <span>{sl:,.4f}</span></p>'
                f'</div>'
                f'</div>'
            )
            
            st.markdown(html_card, unsafe_allow_html=True)
            st.write("")
            if st.button(f"EJECUTAR {est['label'][:1]}", key=f"btn_basket_{i}", use_container_width=True):
                st.success(f"Cesta cargada: {lotes_finales} lotes.")

render_sentinel_investment_cards()
