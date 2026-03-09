import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# --- AQUÍ VA EL NUEVO IMPORT ---
from streamlit_autorefresh import st_autorefresh

# =========================================================
# 2. CONFIGURACIÓN Y CEREBRO (Bloque 0)
# =========================================================
if 'active_trades' not in st.session_state:
    st.session_state.active_trades = []

# PEGADO DEL PASO 2 AQUÍ:
# Esto hará que toda la app se recargue cada 15 segundos.
count = st_autorefresh(interval=15000, limit=None, key="sentinel_refresh")

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
# BLOQUE 6: MOTOR DE DATOS E INDICADORES (EMA & RSI)
# =========================================================
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def get_market_data(ticker, interval='1h'):
    # Ajuste dinámico de periodo para el Zoom automático
    period_map = {'1m': '1d', '5m': '1d', '15m': '3d', '1h': '7d', '1d': '60d'}
    period = period_map.get(interval, '7d')
    
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty: return None
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        
        df = data.dropna().copy()
        
        # --- CÁLCULO DE INDICADORES ---
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # --- LÓGICA DE COLOR PARA VOLUMEN ---
        # Si Close > Open = Verde (#00ff41), else Rojo (#ff3131)
        df['Vol_Color'] = ['#00ff41' if row['Close'] >= row['Open'] else '#ff3131' for _, row in df.iterrows()]
        
        if not df.empty:
            st.session_state.last_price = float(df['Close'].iloc[-1])
            st.session_state.df_analisis = df
            st.session_state.ticker = ticker
        return df
    except Exception as e:
        st.error(f"Error B6: {e}")
        return None

# =========================================================
# BLOQUE 7: RADAR VISUAL (VOLUMEN BICOLOR & CONTROLES)
# =========================================================
def render_shielded_chart(df, ticker_actual):
    if df is None or len(df) == 0:
        st.warning("📡 Sincronizando radar...")
        return

    # --- 1. CONTROLES SUPERIORES (Temporalidad integrada) ---
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        # Nota: Usamos session_state para que el cambio de intervalo sea inmediato
        st.selectbox("⏳ Rango Temporal:", ["1m", "5m", "15m", "1h", "1d"], index=3, key="int_top")
    with c2:
        st.metric("Precio Actual", f"{st.session_state.last_price:,.2f}")
    with c3:
        st.write(f"🛰️ **RADAR ACTIVO:** {ticker_actual}")

    # --- 2. CONFIGURACIÓN DEL GRÁFICO (3 Niveles: Precio, RSI, Volumen) ---
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.04, 
        row_width=[0.15, 0.20, 0.65], # Proporciones de los paneles
        subplot_titles=("PRECIO & ESTRATEGIA", "ÍNDICE DE FUERZA (RSI)", "FLUJO DE VOLUMEN")
    )

    # A. VELAS JAPONESAS
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Precio', increasing_line_color='#00ff41', decreasing_line_color='#ff3131'
    ), row=1, col=1)

    # B. EMA 20 (Media móvil rápida en Oro)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['EMA_20'], line=dict(color='#FFD700', width=1.5),
        name='EMA 20', opacity=0.7
    ), row=1, col=1)

    # C. RSI (Panel intermedio)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['RSI'], line=dict(color='#8A2BE2', width=2), name='RSI'
    ), row=2, col=1)
    # Zonas de Sobrecompra (70) y Sobreventa (30)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff3131", opacity=0.3, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00ff41", opacity=0.3, row=2, col=1)

    # D. VOLUMEN BICOLOR (Verde Compra / Rojo Venta)
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'], name='Volumen',
        marker_color=df['Vol_Color'], opacity=0.8
    ), row=3, col=1)

    # --- 3. NIVELES REALES XTB (DESDE B9) ---
    if 'active_trades' in st.session_state:
        for op in st.session_state.active_trades:
            if op['ticker'] == ticker_actual:
                # Entrada (Azul)
                fig.add_hline(y=float(op['entrada']), line_color="#0066ff", line_dash="dash", 
                              annotation_text="ENTRADA", row=1, col=1)
                # Stop Loss (Rojo)
                fig.add_hline(y=float(op['sl']), line_color="#ff3131", line_dash="dot", 
                              annotation_text="SL", row=1, col=1)
                # Take Profit (Verde)
                fig.add_hline(y=float(op['tp']), line_color="#00ff41", line_dash="dot", 
                              annotation_text="TP", row=1, col=1)

    # --- 4. ESTÉTICA & ZOOM ---
    fig.update_layout(
        template="plotly_dark", height=800, xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    fig.update_yaxes(gridcolor='#1e1e1e', zeroline=False)
    fig.update_xaxes(gridcolor='#1e1e1e')
    
    st.plotly_chart(fig, use_container_width=True, key=f"radar_elite_{ticker_actual}")

# --- EJECUCIÓN ---
# Asegúrate de llamar a get_market_data con st.session_state.int_top
# =========================================================
# FIN DE INTEGRACIÓN B6 + B7
# =========================================================

# =========================================================
# BLOQUE 8: ESTRATEGIAS CON PRECISIÓN DINÁMICA
# =========================================================
def render_strategy_cards(df):
    st.markdown("---")
    st.subheader("🎯 ESTRATEGIAS SUGERIDAS SENTINEL")
    
    if df is None or 'EMA_20' not in df.columns:
        st.warning("Calculando métricas de precisión...")
        return

    ticker = st.session_state.get('ticker', 'NQ=F')
    last_p = float(df['Close'].iloc[-1])
    ema_v = float(df['EMA_20'].iloc[-1])
    rsi_v = float(df['RSI'].iloc[-1])
    
    # --- LÓGICA DE PRECISIÓN (DECIMALES) ---
    # Divisas suelen terminar en =X (EURUSD=X) o ser pares de 6 letras
    if "=X" in ticker or any(x in ticker for x in ["EUR", "USD", "GBP", "JPY"]):
        precision = 5
        step_val = 0.0001
    elif "BTC" in ticker or "ETH" in ticker:
        precision = 2
        step_val = 0.01
    else: # Índices y Materias Primas
        precision = 2
        step_val = 0.25

    es_compra = last_p > ema_v
    color_base = "#00ff41" if es_compra else "#ff3131"
    atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
    
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
            
            prob = c["p"]
            if (rsi_v > 70 and es_compra) or (rsi_v < 30 and not es_compra): prob -= 15

            # Aplicamos la precisión en el f-string: :.{precision}f
            st.markdown(f"""
            <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid {color_base}; border-top: 10px solid {color_base};">
                <h3 style="margin:0; color:{color_base}; text-align:center;">{c['n']}</h3>
                <div style="text-align:center; margin:15px 0;">
                    <span style="font-size:2rem; font-weight:bold; color:white;">{prob}%</span><br>
                    <span style="color:#888; font-size:0.8rem;">PROBABILIDAD</span>
                </div>
                <p style="margin:5px 0;">💰 <b>Lotes:</b> {c['lotes']}</p>
                <p style="margin:5px 0;">📍 <b>Entrada:</b> {c['ent']:.{precision}f}</p>
                <p style="margin:5px 0; color:{color_base}; font-weight:bold;">🎯 TP: {tp:.{precision}f}</p>
                <p style="margin:5px 0; color:#ff3131;">🛡️ SL: {sl:.{precision}f}</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Sincronizar {c['id']}", key=f"sync_prec_{c['id']}", use_container_width=True):
                st.session_state['precision'] = precision
                st.session_state['step_val'] = step_val
                st.session_state['sl_final'] = sl
                st.session_state['tp_final'] = tp
                st.session_state['lotes_sug'] = c['lotes']
                st.session_state['entrada_sug'] = c['ent']
                st.rerun()
# =========================================================
# BLOQUE 9: SENTINEL BRIDGE - REGISTRO Y VINCULACIÓN XTB
# =========================================================
def render_sentinel_bridge():
    st.markdown("---")
    st.subheader("🚀 SENTINEL BRIDGE: REGISTRO Y EJECUCIÓN")

    # 1. Recuperamos la configuración de precisión del activo actual
    # Si no existe (por ser el primer arranque), detectamos el ticker
    ticker_actual = st.session_state.get('ticker', 'NQ=F')
    
    # Lógica de decimales dinámica
    if "=X" in ticker_actual or any(x in ticker_actual for x in ["EUR", "USD", "GBP", "JPY", "AUD"]):
        prec = 5
        step_val = 0.0001
    elif "BTC" in ticker_actual or "ETH" in ticker_actual:
        prec = 2
        step_val = 0.01
    else:
        prec = 2
        step_val = 0.25

    # 2. Recuperamos valores predefinidos (desde los botones 'Sincronizar' del Bloque 8)
    # Usamos .get() con valores por defecto para evitar errores de NameError
    sl_sug = st.session_state.get('sl_final', 0.0)
    tp_sug = st.session_state.get('tp_final', 0.0)
    ent_sug = st.session_state.get('entrada_sug', st.session_state.get('last_price', 0.0))
    lotes_sug = st.session_state.get('lotes_sug', 0.10)
    modo_sug = st.session_state.get('modo_op', 'MANUAL')

    # 3. INTERFAZ DE FORMULARIO
    with st.form("registro_operacion_sentinel"):
        col_info, col_precios = st.columns([1, 2])
        
        with col_info:
            st.markdown(f"**Activo:** `{ticker_actual}`")
            st.markdown(f"**Modo Sugerido:** `{modo_sug}`")
            lotes_real = st.number_input("Volumen (Lotes)", value=float(lotes_sug), step=0.01, help="Ajusta el tamaño de tu posición en XTB")
            
            # Enlace directo a XTB
            xtb_ticker = ticker_actual.replace("-USD", "").replace("=F", "")
            url_xtb = f"https://xstation5.xtb.com/?symbol={xtb_ticker}"
            st.markdown(f"[⚡ Abrir {xtb_ticker} en X-Station]({url_xtb})")

        with col_precios:
            c1, c2 = st.columns(2)
            # Entrada y Stop Loss
            ent_real = c1.number_input("Precio Entrada Real", value=float(ent_sug), format=f"%.{prec}f", step=step_val)
            sl_real = c1.number_input("Stop Loss Real", value=float(sl_sug), format=f"%.{prec}f", step=step_val)
            
            # Take Profit y Comentario
            tp_real = c2.number_input("Take Profit Real", value=float(tp_sug), format=f"%.{prec}f", step=step_val)
            comentario = c2.text_input("Nota de estrategia", placeholder="Ej: Rebote en EMA 20")

        # BOTÓN DE ACTIVACIÓN
        if st.form_submit_button("🛰️ ACTIVAR VIGILANCIA SENTINEL", use_container_width=True):
            # Creamos el diccionario de la operación
            nueva_op = {
                "ticker": ticker_actual,
                "entrada": ent_real,
                "lotes": lotes_real,
                "sl": sl_real,
                "tp": tp_real,
                "modo": modo_sug,
                "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
            }
            
            # Guardamos en el historial de trades activos para que el Bloque 7 dibuje las líneas
            if 'active_trades' not in st.session_state:
                st.session_state.active_trades = []
            
            st.session_state.active_trades.append(nueva_op)
            
            st.success(f"✅ Radar Sincronizado: Vigilando {ticker_actual} a {ent_real:.{prec}f}")
            # Forzamos un refresco para que las líneas aparezcan en el gráfico inmediatamente
            st.rerun()

# 4. MONITOR DE POSICIONES ACTIVAS (Opcional, debajo del formulario)
    if 'active_trades' in st.session_state and len(st.session_state.active_trades) > 0:
        with st.expander("📋 Ver Posiciones bajo Vigilancia", expanded=True):
            for i, op in enumerate(st.session_state.active_trades):
                st.info(f"**{op['ticker']}** | Entrada: {op['entrada']} | SL: {op['sl']} | TP: {op['tp']} | [{op['timestamp']}]")
                if st.button(f"Eliminar Vigilancia {i}", key=f"del_{i}"):
                    st.session_state.active_trades.pop(i)
                    st.rerun()
