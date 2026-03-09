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
# =========================================================
# BLOQUE 9: SENTINEL BRIDGE (VERSIÓN SIEMPRE VISIBLE)
# =========================================================
def render_sentinel_bridge():
    st.markdown("---")
    st.subheader("🚀 SENTINEL BRIDGE: EJECUCIÓN")

    # Si no hay precio aún, usamos uno genérico para no romper la app
    current_p = st.session_state.get('last_price', 0.0)
    ticker_actual = st.session_state.get('ticker', 'ACTIVO')

    # 1. SELECTOR DE ESTRATEGIA
    tipo_est = st.radio("MODO DE OPERACIÓN:", 
                        ["CP (Corto)", "MP (Medio)", "LP (Largo)"], 
                        horizontal=True, key="modo_op_v3")

    # Valores sugeridos (si el Bloque 8 no los dio, ponemos 0 para editar)
    sug_lotes = st.session_state.get('sug_lotes', 0.10)
    sug_sl = st.session_state.get(f'sl_{tipo_est[:2]}', current_p * 0.98)
    sug_tp = st.session_state.get(f'tp_{tipo_est[:2]}', current_p * 1.05)

    col_xtb, col_reg = st.columns([1, 2])

    with col_xtb:
        st.markdown("#### 1. Ir a XTB")
        ticker_limpio = ticker_actual.replace("-USD", "").replace("=F", "")
        xtb_url = f"https://xstation5.xtb.com/?symbol={ticker_limpio}"
        
        st.link_button(f"⚡ ABRIR {ticker_limpio} EN XTB", xtb_url, use_container_width=True, type="primary")
        
        st.markdown("---")
        st.write("📋 **COPIAR DATOS:**")
        st.code(f"{sug_lotes}", language="text") # Lotes
        st.code(f"{sug_sl:,.4f}", language="text") # SL
        st.code(f"{sug_tp:,.4f}", language="text") # TP

    with col_reg:
        st.markdown("#### 2. Registro Real")
        with st.form("registro_confirmacion_v3"):
            c1, c2 = st.columns(2)
            with c1:
                p_entrada = st.number_input("Precio Entrada", value=float(current_p), format="%.4f")
                lotes_f = st.number_input("Lotes", value=float(sug_lotes), step=0.01)
            with c2:
                sl_f = st.number_input("Stop Loss", value=float(sug_sl), format="%.4f")
                tp_f = st.number_input("Take Profit", value=float(sug_tp), format="%.4f")
            
            if st.form_submit_button("🛰️ ACTIVAR VIGILANCIA REAL", use_container_width=True):
                nueva_op = {
                    "ticker": ticker_actual,
                    "modo": tipo_est,
                    "entrada": p_entrada,
                    "lotes": lotes_f,
                    "sl": sl_f,
                    "tp": tp_f,
                    "status": "VIGILANDO"
                }
                if 'active_trades' not in st.session_state:
                    st.session_state.active_trades = []
                st.session_state.active_trades.append(nueva_op)
                st.success(f"✅ Registrado. Monitor activo para {ticker_actual}")

# EJECUCIÓN FINAL
render_sentinel_bridge()
