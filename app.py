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
st.set_page_config(page_title="Jacar Pro V21", layout="wide", page_icon="📈")

# CSS: FONDO CREMA, RECUADROS BLANCOS, TEXTO GRIS PROFUNDO
st.markdown("""
    <style>
    .stApp { background-color: #fdf6e3 !important; }
    
    /* Tarjetas de Estrategia: FONDO BLANCO PURO */
    .card-resumen { 
        background-color: #ffffff !important; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #dcd3b6 !important;
        margin-bottom: 20px;
        color: #586e75 !important;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }
    
    .card-resumen h3 { color: #268bd2 !important; margin-bottom: 15px; border-bottom: 1px solid #eee; }
    
    /* Panel de Oportunidades VIP */
    .panel-vip {
        background-color: #ffffff !important;
        border: 2px solid #268bd2 !important;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 25px;
    }

    .val-buy { color: #859900 !important; font-weight: bold; }
    .val-sell { color: #dc322f !important; font-weight: bold; }
    
    /* Forzar visibilidad de métricas */
    [data-testid="stMetricValue"] { color: #586e75 !important; }
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
    "⚱️ Materias Primas": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F"},
    "💵 Divisas": {"EUR/USD": "EURUSD=X", "Bitcoin": "BTC-USD"}
}

# --- 2. VENTANA DE OPORTUNIDADES VIP (PARALELO) ---
with st.container():
    st.markdown('<div class="panel-vip"><h3>🚀 Radar de Oportunidades VIP (Alta Probabilidad)</h3>', unsafe_allow_html=True)
    c_vip = st.columns(4)
    # Simulamos escaneo de activos calientes
    hot_assets = [("Bitcoin", "BTC-USD"), ("NVDA", "NVDA"), ("Oro", "GC=F"), ("Nasdaq", "^IXIC")]
    for idx, (n, t) in enumerate(hot_assets):
        with c_vip[idx]:
            if st.button(f"🔥 {n}", key=f"vip_{t}", use_container_width=True):
                st.session_state.activo_sel = n
                st.session_state.ticker_sel = t
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. SELECTOR DE ACTIVOS TRADICIONAL ---
tabs = st.tabs(list(activos_dict.keys()))
for i, (categoria, lista) in enumerate(activos_dict.items()):
    with tabs[i]:
        cols = st.columns(len(lista))
        for j, (nombre, ticker) in enumerate(lista.items()):
            if cols[j].button(f"{nombre}", key=f"btn_{ticker}", use_container_width=True):
                st.session_state.activo_sel = nombre
                st.session_state.ticker_sel = ticker
                st.rerun()

# --- 4. DATOS E INDICADORES ---
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
    
    res_line = float(df['High'].tail(20).max())
    sup_line = float(df['Low'].tail(20).min())
    moneda = "€" if any(x in st.session_state.ticker_sel for x in [".MC", "GDAXI", "IBEX"]) else "$"

    # MÉTRICAS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("PRECIO ACTUAL", f"{precio_act:,.2f} {moneda}")
    m2.metric("MÁX SESIÓN", f"{max_sesion:,.2f} {moneda}")
    m3.metric("MÍN SESIÓN", f"{min_sesion:,.2f} {moneda}")
    m4.metric("FUERZA ADX", f"{adx_val:.1f}")

    # GRÁFICA
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
                                 increasing_line_color='#859900', decreasing_line_color='#dc322f', name="Precio"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='#268bd2', width=1.5), name="EMA 20"), row=1, col=1)
    fig.add_hline(y=res_line, line_dash="dash", line_color="#dc322f", opacity=0.4, row=1, col=1)
    fig.add_hline(y=sup_line, line_dash="dash", line_color="#859900", opacity=0.4, row=1, col=1)
    
    fig.update_layout(plot_bgcolor='#fdf6e3', paper_bgcolor='#fdf6e3', font=dict(color='#586e75'), height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    if st.button(f"🔍 ANALIZAR CONFLUENCIA PARA {st.session_state.activo_sel.upper()}"):
        with st.spinner('IA Generando Estrategia...'):
            ticker_obj = yf.Ticker(st.session_state.ticker_sel)
            news_text = "\n".join([n.get('title', '') for n in ticker_obj.news[:3]])
            prompt = f"Analista Senior. Activo: {st.session_state.activo_sel}. Precio: {precio_act} {moneda}. ADX: {adx_val:.1f}. RSI: {df['RSI'].iloc[-1]:.1f}. Capital: {st.session_state.wallet} EUR. Genera 3 opciones (INTRA, MEDIO, LARGO). Formato: TAG: [Prob%]|[Accion: COMPRA/VENTA]|[Lotes]|[Entrada]|[TP]|[SL]"
            
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
            res_ia = resp.choices[0].message.content

            def parse_tag(tag):
                m = re.search(rf"{tag}:\s*(.*)", res_ia)
                if m:
                    parts = [p.strip() for p in m.group(1).split('|')]
                    if len(parts) >= 6: return parts
                return ["N/A", "Esperando", "0.0", "---", "---", "---"]

            st.session_state.señal_actual = {"intra": parse_tag("INTRA"), "medio": parse_tag("MEDIO"), "largo": parse_tag("LARGO"), "moneda": moneda}
            st.rerun()

# --- 5. TARJETAS DE RESULTADOS (FONDO BLANCO) ---
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
                <p>🏁 <b>TP:</b> <span style="color:#859900">{s[4]} {mon}</span></p>
                <p>🛡️ <b>SL:</b> <span style="color:#dc322f">{s[5]} {mon}</span></p>
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

# --- 6. CARTERA ---
st.sidebar.header("🏢 Balance (EUR)")
st.sidebar.metric("Equity", f"{st.session_state.wallet:,.2f} €")
st.divider()
if st.session_state.cartera_abierta:
    st.subheader("💼 Posiciones Abiertas")
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            st.write(f"**{pos['activo']}** ({pos['tipo']})")
            pnl = st.number_input("PnL (€)", key=f"pnl_{pos['id']}", value=0.0)
            if st.button("Cerrar", key=f"c_{pos['id']}"):
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                st.rerun()
