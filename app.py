import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Jacar Pro V18 - High Confluence", layout="wide", page_icon="📈")

# Estilos CSS para legibilidad y diseño profesional
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; }
    .card-resumen { 
        background-color: #161a23; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #2d323e;
        margin-bottom: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }
    .val-buy { color: #00ff88; font-weight: bold; font-size: 1.2em; }
    .val-sell { color: #ff4b4b; font-weight: bold; font-size: 1.2em; }
    .metric-box { background-color: #1e222d; padding: 10px; border-radius: 8px; border: 1px solid #333; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: 
    st.session_state.activo_sel = "Nasdaq 100"
    st.session_state.ticker_sel = "^IXIC"
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Diccionario de activos
activos_dict = {
    "📈 Índices": {"Nasdaq 100": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"},
    "💻 Tecnología": {"NVDA": "NVDA", "Apple": "AAPL", "MSFT": "MSFT", "Tesla": "TSLA"},
    "⚱️ Materias Primas": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F", "Gas Nat": "NG=F"},
    "⚡ Energía": {"Iberdrola": "IBE.MC", "Repsol": "REP.MC", "Exxon": "XOM"},
    "💵 Divisas": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "Bitcoin": "BTC-USD"}
}

# --- 2. SELECTOR DE ACTIVOS ---
st.title("🏛️ Jacar Institutional Terminal V18")
tabs = st.tabs(list(activos_dict.keys()))
for i, (categoria, lista) in enumerate(activos_dict.items()):
    with tabs[i]:
        cols = st.columns(len(lista))
        for j, (nombre, ticker) in enumerate(lista.items()):
            if cols[j].button(f"{nombre}", key=f"btn_{ticker}", use_container_width=True):
                st.session_state.activo_sel = nombre
                st.session_state.ticker_sel = ticker
                st.rerun()

# --- 3. PROCESAMIENTO DE DATOS E INDICADORES ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h")
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    # Indicadores Técnicos
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1)
    
    precio_act = float(df['Close'].iloc[-1])
    max_sesion = float(df['High'].max())
    min_sesion = float(df['Low'].min())
    adx_val = float(df['ADX_14'].iloc[-1])
    
    # Soportes y Resistencias (Fractales de 20 periodos)
    resistencia = float(df['High'].rolling(window=20).max().iloc[-1])
    soporte = float(df['Low'].rolling(window=20).min().iloc[-1])
    
    moneda = "€" if any(x in st.session_state.ticker_sel for x in [".MC", "GDAXI", "IBEX"]) else "$"

    # --- 4. DASHBOARD VISUAL ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("PRECIO ACTUAL", f"{precio_act:,.2f} {moneda}")
    m2.metric("MÁX SESIÓN", f"{max_sesion:,.2f} {moneda}")
    m3.metric("MÍN SESIÓN", f"{min_sesion:,.2f} {moneda}")
    
    # Estado de Fuerza de Tendencia (ADX)
    fuerza_tenda = "Débil/Lateral" if adx_val < 25 else "Fuerte" if adx_val < 50 else "Muy Fuerte"
    m4.metric("FUERZA (ADX)", f"{adx_val:.1f}", help=f"Estado: {fuerza_tenda}")

    # Gráfica Unificada
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], 
                        vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    
    # Velas y EMA
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1.2), name="EMA 20"), row=1, col=1)
    
    # Niveles Clave
    fig.add_hline(y=resistencia, line_dash="dot", line_color="#ff4b4b", annotation_text="RES", row=1, col=1)
    fig.add_hline(y=soporte, line_dash="dot", line_color="#00ff88", annotation_text="SOP", row=1, col=1)
    
    # RSI en eje secundario
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1), name="RSI", opacity=0.3), row=1, col=1, secondary_y=True)
    
    # Volumen
    colors_vol = ['#00ff88' if r['Close'] >= r['Open'] else '#ff4b4b' for _, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name="Volumen"), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. LÓGICA DE ANÁLISIS ---
    if st.button(f"⚖️ ANALIZAR CONFLUENCIA: {st.session_state.activo_sel.upper()}"):
        with st.spinner('Analizando ADX, RSI y Noticias...'):
            ticker_obj = yf.Ticker(st.session_state.ticker_sel)
            news_text = "\n".join([n.get('title', '') for n in ticker_obj.news[:3]])
            
            prompt = f"""Analista Senior. Activo: {st.session_state.activo_sel}. Precio: {precio_act} {moneda}.
            Indicadores: ADX {adx_val:.1f} (fuerza), RSI {df['RSI'].iloc[-1]:.1f}, Soporte {soporte}, Resistencia {resistencia}.
            Capital: {st.session_state.wallet} EUR. Noticias: {news_text}.
            Genera 3 estrategias (INTRA, MEDIO, LARGO).
            Formato exacto: TAG: [Probabilidad %]|[Acción: COMPRA o VENTA]|[Lotes (1% riesgo EUR)]|[Entrada {moneda}]|[TP {moneda}]|[SL {moneda}]"""
            
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
            res_ia = resp.choices[0].message.content

            def parse_tag(tag):
                m = re.search(rf"{tag}:\s*(.*)", res_ia)
                return [p.strip() for p in m.group(1).split('|')] if m else ["---"]*6

            st.session_state.señal_actual = {"intra": parse_tag("INTRA"), "medio": parse_tag("MEDIO"), "largo": parse_tag("LARGO"), "moneda": moneda}
            st.rerun()

# --- 6. TARJETAS DE OPERATIVA ---
if st.session_state.señal_actual:
    st.divider()
    cols_res = st.columns(3)
    mon = st.session_state.señal_actual["moneda"]
    for i, (name, tag) in enumerate([("INTRADÍA", "intra"), ("MEDIO PLAZO", "medio"), ("LARGO PLAZO", "largo")]):
        s = st.session_state.señal_actual[tag]
        tipo = s[1].upper()
        clase_txt = "val-buy" if "COMPRA" in tipo else "val-sell"
        
        with cols_res[i]:
            st.markdown(f"""
            <div class="card-resumen">
                <h3 style="text-align:center; color:#bbb;">{name}</h3>
                <hr style="border-color:#333;">
                <p>🎯 Probabilidad: <b>{s[0]}</b></p>
                <p>⚡ Acción: <span class="{clase_txt}">{tipo}</span></p>
                <p>📦 Lotes: <b>{s[2]}</b></p>
                <p>📥 Entrada: <b>{s[3]} {mon}</b></p>
                <p>🏁 Take Profit: <b style="color:#00ff88">{s[4]} {mon}</b></p>
                <p>🛡️ Stop Loss: <b style="color:#ff4b4b">{s[5]} {mon}</b></p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Ejecutar {name}", key=f"exe_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "ticker": st.session_state.ticker_sel, "tipo": tipo, "lotes": s[2],
                    "entrada": s[3], "tp": s[4], "sl": s[5], "moneda": mon
                })
                st.session_state.señal_actual = None
                st.rerun()

# --- 7. GESTIÓN DE CARTERA (SIDEBAR) ---
with st.sidebar:
    st.header("💼 Cartera XTB")
    st.metric("Balance Total (EUR)", f"{st.session_state.wallet:,.2f} €")
    st.divider()
    
    if st.session_state.cartera_abierta:
        for i, pos in enumerate(st.session_state.cartera_abierta):
            with st.expander(f"{pos['activo']} ({pos['tipo']})", expanded=True):
                st.write(f"In: {pos['entrada']} {pos['moneda']}")
                pos['sl'] = st.text_input("Ajustar SL", value=pos['sl'], key=f"sl_sd_{pos['id']}")
                pos['tp'] = st.text_input("Ajustar TP", value=pos['tp'], key=f"tp_sd_{pos['id']}")
                pnl = st.number_input("PnL (€)", key=f"pnl_sd_{pos['id']}")
                if st.button("Cerrar Operación", key=f"cl_sd_{pos['id']}", type="primary"):
                    st.session_state.wallet += pnl
                    st.session_state.cartera_abierta.pop(i)
                    st.rerun()
    else:
        st.info("Sin posiciones abiertas.")
