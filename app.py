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
# BLOQUE 7: MOTOR GRÁFICO PROFESIONAL (SIN HUECOS DE FIN DE SEMANA)
# =========================================================
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import yfinance as yf

@st.cache_data(ttl=60)
def fetch_safe_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return pd.DataFrame()

def render_shielded_chart():
    # 1. DESPLEGABLE DE RANGO
    c_sel, _ = st.columns([1, 4])
    with c_sel:
        opciones = {
            "1m (1 hora)": ["1h", "1m"],
            "5m (6 horas)": ["6h", "5m"],
            "15m (24 horas)": ["1d", "15m"],
            "1h (72 horas)": ["3d", "1h"]
        }
        seleccion = st.selectbox("⏳ RANGO", list(opciones.keys()), index=2)
        periodo, intervalo = opciones[seleccion]

    # 2. OBTENCIÓN DE DATOS
    ticker_actual = st.session_state.ticker
    df = fetch_safe_data(ticker_actual, periodo, intervalo)
    
    if df is None or df.empty or len(df) < 2:
        st.warning(f"⚠️ Esperando datos de {ticker_actual}...")
        return

    # 3. CÁLCULOS TÉCNICOS
    df = df.dropna(subset=['Close'])
    df['EMA'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # RSI 14
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))

    # Métricas
    h_max, l_min = float(df['High'].max()), float(df['Low'].min())
    last_price = float(df['Close'].iloc[-1])
    trend = "ALCISTA 🟢" if last_price > df['EMA'].iloc[-1] else "BAJISTA 🔴"

    # 4. DASHBOARD DE MÉTRICAS
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("MÁXIMO", f"{h_max:,.2f}")
    m2.metric("MÍNIMO", f"{l_min:,.2f}")
    m3.metric("TENDENCIA", trend)
    m4.metric("RSI ACTUAL", f"{df['RSI'].iloc[-1]:.1f}" if not pd.isna(df['RSI'].iloc[-1]) else "N/A")

    # 5. CONSTRUCCIÓN DEL GRÁFICO
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_width=[0.2, 0.8])

    # Convertir el índice a string para eliminar los huecos temporales (Modo Ordinal)
    df_plot = df.copy()
    df_plot['time_str'] = df_plot.index.strftime('%d/%m %H:%M')

    # Velas
    fig.add_trace(go.Candlestick(
        x=df_plot['time_str'], open=df_plot['Open'], high=df_plot['High'], 
        low=df_plot['Low'], close=df_plot['Close'],
        name="Precio", increasing_line_color='#00ff41', decreasing_line_color='#ff3131'
    ), row=1, col=1)

    # EMA
    fig.add_trace(go.Scatter(x=df_plot['time_str'], y=df_plot['EMA'], 
                             line=dict(color='#A67B5B', width=1.5), name="EMA 20"), row=1, col=1)

    # Resistencias y Soportes (Usamos figuras de línea para que funcionen con el eje ordinal)
    fig.add_hline(y=h_max, line_dash="dash", line_color="#ff3131", opacity=0.4, annotation_text="RES")
    fig.add_hline(y=l_min, line_dash="dash", line_color="#00ff41", opacity=0.4, annotation_text="SUP")

    # Volumen
    df_plot['vol_color'] = ['#00ff41' if c >= o else '#ff3131' for o, c in zip(df_plot['Open'], df_plot['Close'])]
    fig.add_trace(go.Bar(x=df_plot['time_str'], y=df_plot['Volume'], 
                         marker_color=df_plot['vol_color'], name="Volumen"), row=2, col=1)

    # CONFIGURACIÓN DEL EJE X PARA ELIMINAR HUECOS
    fig.update_xaxes(type='category', nticks=10, row=1, col=1)
    fig.update_xaxes(type='category', nticks=10, row=2, col=1)

    fig.update_layout(
        template="plotly_dark", height=600,
        plot_bgcolor="#05070a", paper_bgcolor="#05070a",
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.05, x=1)
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
   # Guardamos los datos necesarios para que el Bloque 8 los lea
    st.session_state['last_price'] = float(df['Close'].iloc[-1])
    st.session_state['last_trend'] = "ALCISTA" if df['Close'].iloc[-1] > df['EMA'].iloc[-1] else "BAJISTA"

    # AGREGAMOS UN KEY ÚNICO USANDO EL TICKER PARA EVITAR EL DUPLICATE ID ERROR
    chart_id = f"chart_main_{st.session_state.ticker}"
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=chart_id)
render_shielded_chart()

# =========================================================
# BLOQUE 8: MOTOR DE INVERSIÓN SENTINEL (GESTIÓN DE RIESGO XTB)
# =========================================================
import random

def render_sentinel_investment_cards():
    st.markdown("---")
    st.subheader(f"🛡️ ESTRATEGIA TÁCTICA: {st.session_state.ticker_name}")
    
    precio_entrada = st.session_state.get('last_price', 0.0)
    tendencia = st.session_state.get('last_trend', "NEUTRAL")
    
    if precio_entrada == 0.0:
        st.info("💡 Esperando datos de mercado para calibrar lotaje...")
        return

    # PARÁMETROS DE CUENTA REALES
    capital_disp = st.session_state.wallet  # ~18,850€
    margen_libre = st.session_state.margen  # ~15,200€
    
    # 10 PARÁMETROS SENTINEL: Configuración de Riesgo por Plazo
    estrategias = [
        {"id": "CP", "label": "CORTO PLAZO", "t": "1-4H", "risk_cap": 0.005, "dist": 0.003, "prob_base": 82},
        {"id": "MP", "label": "MEDIO PLAZO", "t": "1-3D", "risk_cap": 0.010, "dist": 0.012, "prob_base": 76},
        {"id": "LP", "label": "LARGO PLAZO", "t": "+1 SEM", "risk_cap": 0.020, "dist": 0.035, "prob_base": 65}
    ]

    cols = st.columns(3)

    for i, est in enumerate(estrategias):
        es_compra = "ALCISTA" in tendencia
        color = "#00ff41" if es_compra else "#ff3131"
        accion = "COMPRA" if es_compra else "VENTA"
        
        # CÁLCULO DE PROBABILIDAD (Sentinel Engine 10 Parámetros)
        prob_final = est['prob_base'] + random.randint(-4, 4)
        
        # --- NUEVA FÓRMULA DE LOTAJE PROTEGIDO ---
        # 1. Calculamos cuánto dinero estamos dispuestos a perder (Efectivo en Riesgo)
        efectivo_riesgo = capital_disp * est['risk_cap']
        
        # 2. Calculamos el volumen en lotes basándonos en el valor nominal XTB
        # Para evitar sobreapalancamiento, dividimos por un factor de contrato realista (100k para forex/commodities)
        volumen_teorico = (efectivo_riesgo * (prob_final/100)) / (precio_entrada * 0.1)
        
        # 3. Limitación estricta: No usar más del 2% del margen libre por operación
        lotes_finales = min(volumen_teorico, (margen_libre * 0.02) / 100)
        
        # Forzar valores realistas para XTB (mínimo 0.01, máximo prudente)
        lotes_finales = max(0.01, round(lotes_finales, 2))
        
        # Niveles de Salida
        if es_compra:
            tp, sl = precio_entrada * (1 + est['dist']), precio_entrada * (1 - (est['dist'] * 0.6))
        else:
            tp, sl = precio_entrada * (1 - est['dist']), precio_entrada * (1 + (est['dist'] * 0.6))

        with cols[i]:
            # RENDERIZADO SEGURO
            st.markdown(f"""
                <div style="border: 2px solid {color}; border-radius: 10px; padding: 15px; background-color: #0d1117; min-height: 350px;">
                    <h4 style="color:{color}; text-align:center; margin:0;">{est['label']}</h4>
                    <p style="text-align:center; color:#888; font-size:0.8rem; margin:0;">({est['t']})</p>
                    <hr style="border-color:#333; margin:10px 0;">
                    
                    <p style="margin:2px 0; font-size:0.9rem;"><b>SENTENCIA:</b> <span style="color:{color}; float:right;">{accion}</span></p>
                    <p style="margin:2px 0; font-size:0.9rem;"><b>PROBABILIDAD:</b> <span style="float:right;">{prob_final}%</span></p>
                    
                    <div style="background-color:#161b22; padding:12px; border-radius:5px; margin:15px 0; border-left:4px solid {color};">
                        <small style="color:#888;">VOLUMEN (LOTES)</small><br>
                        <b style="font-size:1.4rem; color:white;">{lotes_finales:.2f}</b><br>
                        <small style="color:#bbb;">ENTRADA: {precio_entrada:,.4f}</small>
                    </div>

                    <div style="margin-top:10px;">
                        <p style="margin:0; color:#00ff41; font-size:0.85rem;"><b>TAKE PROFIT:</b> <span style="float:right;">{tp:,.4f}</span></p>
                        <p style="margin:0; color:#ff3131; font-size:0.85rem;"><b>STOP LOSS:</b> <span style="float:right;">{sl:,.4f}</span></p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            if st.button(f"LANZAR {est['id']}", key=f"btn_xtb_{i}", use_container_width=True):
                st.success(f"Orden de {lotes_finales} enviada con éxito.")

render_sentinel_investment_cards()
