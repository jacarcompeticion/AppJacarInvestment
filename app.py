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
st.set_page_config(page_title="Jacar Pro V19 - Contrast Fix", layout="wide", page_icon="📈")

# FORZAR ESTILO VISUAL (Solución al fondo negro)
st.markdown("""
    <style>
    /* Fondo general de la app */
    .stApp { background-color: #0b0e14; }
    
    /* Tarjetas de Estrategia: Forzamos fondo gris oscuro y texto blanco */
    .card-resumen { 
        background-color: #1c212d !important; 
        padding: 25px; 
        border-radius: 12px; 
        border: 2px solid #3d4455 !important;
        margin-bottom: 20px;
        color: #ffffff !important;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.6);
    }
    
    /* Forzar color de etiquetas dentro de tarjetas */
    .card-resumen h3 { color: #4dabf7 !important; text-align: center; border-bottom: 1px solid #3d4455; padding-bottom: 10px; }
    .card-resumen p { color: #e9ecef !important; font-size: 1.05em; margin: 8px 0; }
    
    /* Colores de acción */
    .val-buy { color: #22c55e !important; font-weight: bold; font-size: 1.2em; }
    .val-sell { color: #ef4444 !important; font-weight: bold; font-size: 1.2em; }
    
    /* Botones de ejecución */
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: 
    st.session_state.activo_sel = "Nasdaq 100"
    st.session_state.ticker_sel = "^IXIC"
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

activos_dict = {
    "📈 Índices": {"Nasdaq 100": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"},
    "💻 Tecnología": {"NVDA": "NVDA", "Apple": "AAPL", "MSFT": "MSFT", "Tesla": "TSLA"},
    "⚱️ Materias Primas": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F", "Gas Nat": "NG=F"},
    "⚡ Energía": {"Iberdrola": "IBE.MC", "Repsol": "REP.MC", "Exxon": "XOM"},
    "💵 Divisas": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "Bitcoin": "BTC-USD"}
}

# --- 2. SELECTOR DE ACTIVOS ---
st.title("🏛️ Jacar Terminal - Edición Contraste")
tabs = st.tabs(list(activos_dict.keys()))
for i, (categoria, lista) in enumerate(activos_dict.items()):
    with tabs[i]:
        cols = st.columns(len(lista))
        for j, (nombre, ticker) in enumerate(lista.items()):
            if cols[j].button(f"{nombre}", key=f"btn_{ticker}", use_container_width=True):
                st.session_state.activo_sel = nombre
                st.session_state.ticker_sel = ticker
                st.rerun()

# --- 3. DATOS E INDICADORES (ADX INCLUIDO) ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h")
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx], axis=1)
    
    precio_act = float(df['Close'].iloc[-1])
    max_sesion = float(df['High'].max())
    min_sesion = float(df['Low'].min())
    adx_val = float(df['ADX_14'].iloc[-1])
    
    # Soporte y Resistencia Dinámica
    res_line = float(df['High'].tail(20).max())
    sup_line = float(df['Low'].tail(20).min())
    
    moneda = "€" if any(x in st.session_state.ticker_sel for x in [".MC", "GDAXI", "IBEX"]) else "$"

    # --- 4. MÉTRICAS SUPERIORES ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("PRECIO ACTUAL", f"{precio_act:,.2f} {moneda}")
    m2.metric("MÁX SESIÓN", f"{max_sesion:,.2f} {moneda}")
    m3.metric("MÍN SESIÓN", f"{min_sesion:,.2f} {moneda}")
    m4.metric("FUERZA ADX", f"{adx_val:.1f}")

    # Gráfica
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1), name="EMA 20"), row=1, col=1)
    fig.add_hline(y=res_line, line_dash="dash", line_color="#ff4b4b", opacity=0.5, row=1, col=1)
    fig.add_hline(y=sup_line, line_dash="dash", line_color="#00ff88", opacity=0.5, row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1, dash='dot'), name="RSI", opacity=0.3), row=1, col=1, secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    if st.button(f"⚖️ ANALIZAR ESTRATEGIA COMPLETA"):
        with st.spinner('IA analizando tendencias...'):
            ticker_obj = yf.Ticker(st.session_state.ticker_sel)
            news_text = "\n".join([n.get('title', '') for n in ticker_obj.news[:3]])
            prompt = f"Analista XTB. Activo: {st.session_state.activo_sel}. Precio: {precio_act} {moneda}. ADX: {adx_val:.1f}. RSI: {df['RSI'].iloc[-1]:.1f}. Capital: {st.session_state.wallet} EUR. Noticias: {news_text}. Genera 3 opciones (INTRA, MEDIO, LARGO). Formato: TAG: [Prob%]|[Accion: COMPRA/VENTA]|[Lotes]|[Entrada]|[TP]|[SL]"
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
            res_ia = resp.choices[0].message.content

            def parse_tag(tag):
                m = re.search(rf"{tag}:\s*(.*)", res_ia)
                return [p.strip() for p in m.group(1).split('|')] if m else ["---"]*6

            st.session_state.señal_actual = {"intra": parse_tag("INTRA"), "medio": parse_tag("MEDIO"), "largo": parse_tag("LARGO"), "moneda": moneda}
            st.rerun()

# --- 5. TARJETAS DE ESTRATEGIA (CON FONDO FORZADO) ---
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
                <h3>{name}</h3>
                <p>🎯 <b>Probabilidad:</b> {s[0]}</p>
                <p>⚡ <b>Acción:</b> <span class="{clase_txt}">{tipo}</span></p>
                <p>📦 <b>Lotes:</b> {s[2]}</p>
                <p>📥 <b>Entrada:</b> {s[3]} {mon}</p>
                <p>🏁 <b>Take Profit:</b> <span style="color:#22c55e">{s[4]} {mon}</span></p>
                <p>🛡️ <b>Stop Loss:</b> <span style="color:#ef4444">{s[5]} {mon}</span></p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Aceptar {name}", key=f"exe_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "ticker": st.session_state.ticker_sel, "tipo": tipo, "lotes": s[2],
                    "entrada": s[3], "tp": s[4], "sl": s[5], "moneda": mon
                })
                st.session_state.señal_actual = None
                st.rerun()

# --- 6. CARTERA ---
st.sidebar.header("🏢 Cuenta Real (EUR)")
st.sidebar.metric("Balance", f"{st.session_state.wallet:,.2f} €")
st.divider()
if st.session_state.cartera_abierta:
    st.subheader("💼 Operaciones en Curso")
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"**{pos['activo']}** ({pos['tipo']})")
            c1.write(f"Lotes: {pos['lotes']} | In: {pos['entrada']}")
            pos['sl'] = c2.text_input("Ajustar SL", value=pos['sl'], key=f"sl_{pos['id']}")
            pos['tp'] = c2.text_input("Ajustar TP", value=pos['tp'], key=f"tp_{pos['id']}")
            pnl = c3.number_input("PnL (€)", key=f"pnl_{pos['id']}")
            if c3.button("Cerrar", key=f"c_{pos['id']}"):
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                st.rerun()
