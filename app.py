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
# BLOQUE 8: ESTRATEGIAS CON VOLUMEN Y NIVELES INDEPENDIENTES
# =========================================================
def render_strategy_cards(df):
    st.markdown("---")
    st.subheader("🎯 ESTRATEGIAS SUGERIDAS SENTINEL")
    
    if df is None or 'EMA_20' not in df.columns:
        st.warning("Calculando indicadores de tendencia...")
        return

    last_p = float(df['Close'].iloc[-1])
    ema_v = float(df['EMA_20'].iloc[-1])
    
    # 1. SENTIDO DE LA OPERACIÓN (Basado en EMA 20)
    es_compra = last_p > ema_v
    color_base = "#00ff41" if es_compra else "#ff3131"
    label_sentido = "COMPRA (LONG)" if es_compra else "VENTA (SHORT)"
    
    # 2. VOLATILIDAD PARA CÁLCULO DE NIVELES
    atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    
    # CONFIGURACIÓN DIFERENCIADA POR TEMPORALIDAD
    # Cada una tiene su propio multiplicador de riesgo y volumen sugerido
    config = [
        {"id": "CP", "nombre": "CORTO PLAZO", "mult": 1.5, "lotes": 0.50, "col": col1},
        {"id": "MP", "nombre": "MEDIO PLAZO", "mult": 3.0, "lotes": 0.20, "col": col2},
        {"id": "LP", "nombre": "LARGO PLAZO", "mult": 6.0, "lotes": 0.05, "col": col3}
    ]

    for c in config:
        with c["col"]:
            # Cálculo de niveles independientes
            distancia = atr * c["mult"]
            if es_compra:
                sl = last_p - distancia
                tp = last_p + (distancia * 2.5) # Ratio 1:2.5
            else:
                sl = last_p + distancia
                tp = last_p - (distancia * 2.5)

            # --- INTERFAZ DE TARJETA ---
            st.markdown(f"""
            <div style="background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid {color_base}; border-top: 8px solid {color_base}; min-height: 280px;">
                <h4 style="margin:0; color: {color_base}; text-align: center;">{c["nombre"]}</h4>
                <p style="margin:10px 0; font-size: 1.2rem; text-align: center; font-weight: bold;">{label_sentido}</p>
                <hr style="margin:10px 0; border: 0.5px solid #333;">
                <p style="margin:5px 0;">💰 <b>Volumen:</b> <span style="color:{color_base}; font-size:1.1rem;">{c['lotes']} Lotes</span></p>
                <p style="margin:2px 0;">📍 <b>Entrada:</b> {last_p:,.2f}</p>
                <p style="margin:2px 0;">🎯 <b>Take Profit:</b> {tp:,.2f}</p>
                <p style="margin:2px 0;">🛡️ <b>Stop Loss:</b> {sl:,.2f}</p>
            </div>
            """, unsafe_allow_html=True)

            # 3. BOTÓN DE SELECCIÓN (Carga dinámica al Bloque 9)
            if st.button(f"Aplicar {c['id']}", key=f"btn_v2_{c['id']}", use_container_width=True):
                st.session_state['sl_final'] = sl
                st.session_state['tp_final'] = tp
                st.session_state['lotes_sug'] = c['lotes']
                st.session_state['entrada_sug'] = last_p
                st.session_state['modo_seleccionado'] = c['id']
                st.toast(f"✅ Datos de {c['id']} cargados en el Bridge")

            # 4. COPIADO RÁPIDO PARA XTB
            with st.expander("📋 Datos para X-Station"):
                st.write("Volumen (Lotes):")
                st.code(f"{c['lotes']}", language="text")
                st.write("Precio Entrada:")
                st.code(f"{last_p:,.4f}", language="text")
                st.write("Take Profit:")
                st.code(f"{tp:,.4f}", language="text")
                st.write("Stop Loss:")
                st.code(f"{sl:,.4f}", language="text")

# =========================================================
# BLOQUE 9: SENTINEL BRIDGE (RECIBE LOS LOTES Y PRECIOS)
# =========================================================
def render_sentinel_bridge():
    st.markdown("---")
    st.subheader("🚀 SENTINEL BRIDGE: REGISTRO REAL")
    
    # Recuperamos los valores de la estrategia seleccionada arriba
    sl_pre = st.session_state.get('sl_final', 0.0)
    tp_pre = st.session_state.get('tp_final', 0.0)
    lotes_pre = st.session_state.get('lotes_sug', 0.10)
    ent_pre = st.session_state.get('entrada_sug', st.session_state.get('last_price', 0.0))

    with st.form("form_sentinel_v2"):
        c1, c2, c3 = st.columns(3)
        with c1:
            p_entrada = st.number_input("Precio Entrada Real", value=float(ent_pre), format="%.4f")
            lotes_final = st.number_input("Lotes en XTB", value=float(lotes_pre), step=0.01)
        with c2:
            sl_real = st.number_input("Stop Loss Real", value=float(sl_pre), format="%.4f")
        with c3:
            tp_real = st.number_input("Take Profit Real", value=float(tp_pre), format="%.4f")
        
        if st.form_submit_button("🛰️ ACTIVAR VIGILANCIA EN RADAR", use_container_width=True):
            nueva_op = {
                "ticker": st.session_state.ticker,
                "entrada": p_entrada,
                "lotes": lotes_final,
                "sl": sl_real,
                "tp": tp_real,
                "modo": st.session_state.get('modo_seleccionado', 'MANUAL')
            }
            if 'active_trades' not in st.session_state: st.session_state.active_trades = []
            st.session_state.active_trades.append(nueva_op)
            st.success("🛰️ Operación registrada. Vigila el Radar (Bloque 7) para ver tus líneas.")
# --- LÓGICA DE RENDERIZADO FINAL ---
# 1. Bajamos los datos
df_final = get_market_data(st.session_state.get('ticker', 'NQ=F'), 
                           interval=st.session_state.get('int_top', '1h'))

# 2. Si hay datos, mostramos TODO en orden
if df_final is not None:
    # Bloque 7: Gráfica (Ya lo tienes)
    render_shielded_chart(df_final, st.session_state.ticker)
    
    # Bloque 8: Estrategias sugeridas
    render_strategy_cards(df_final)
    
    # Bloque 9: Botón XTB y Formulario de Registro
    render_sentinel_bridge()
    
    # Bloque 10: Monitor de posiciones (si lo tienes definido)
    # render_sentinel_monitor()
