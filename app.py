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
st.set_page_config(page_title="Jacar Pro V17", layout="wide", page_icon="📈")

# CSS para corregir visibilidad y tarjetas
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .card-resumen { 
        background-color: #1e2129; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #3b3f4b;
        margin-bottom: 15px;
        color: white;
    }
    .val-destacado { color: #00ff00; font-weight: bold; font-size: 1.1em; }
    .val-short { color: #ff4b4b; font-weight: bold; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = []
if 'activo_sel' not in st.session_state: 
    st.session_state.activo_sel = "Oro"
    st.session_state.ticker_sel = "GC=F"
if 'señal_actual' not in st.session_state: st.session_state.señal_actual = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

activos_dict = {
    "💻 Tecnología": {"NVDA": "NVDA", "Apple": "AAPL", "MSFT": "MSFT", "Tesla": "TSLA"},
    "⚡ Energía": {"Iberdrola": "IBE.MC", "Repsol": "REP.MC", "Exxon": "XOM", "Chevron": "CVX"},
    "⚱️ Materias Primas": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F", "Gas Nat": "NG=F"},
    "💵 Divisas": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X", "Bitcoin": "BTC-USD"},
    "📈 Índices": {"Nasdaq 100": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"}
}

# --- 2. MENU SUPERIOR ---
st.title("🏛️ Jacar Institutional Terminal")
tabs = st.tabs(list(activos_dict.keys()))
for i, (categoria, lista) in enumerate(activos_dict.items()):
    with tabs[i]:
        cols = st.columns(len(lista))
        for j, (nombre, ticker) in enumerate(lista.items()):
            if cols[j].button(f"{nombre}", key=f"btn_{ticker}"):
                st.session_state.activo_sel = nombre
                st.session_state.ticker_sel = ticker
                st.rerun()

# --- 3. DATOS Y CÁLCULOS ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h")
if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
df = df.dropna()

if not df.empty:
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # Valores de Sesión
    precio_act = float(df['Close'].iloc[-1])
    max_sesion = float(df['High'].max())
    min_sesion = float(df['Low'].min())
    
    # Soportes y Resistencias simples (Pivotes)
    soporte = float(df['Low'].tail(20).min())
    resistencia = float(df['High'].tail(20).max())
    
    moneda = "€" if any(x in st.session_state.ticker_sel for x in [".MC", "GDAXI", "IBEX"]) else "$"

    # --- 4. GRÁFICA PROFESIONAL ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03, specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
    
    # Velas y EMA (SOLO UNA VEZ)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='yellow', width=1.5), name="EMA 20"), row=1, col=1, secondary_y=False)
    
    # Soportes y Resistencias (Líneas horizontales)
    fig.add_hline(y=resistencia, line_dash="dash", line_color="red", annotation_text="Resistencia", row=1, col=1)
    fig.add_hline(y=soporte, line_dash="dash", line_color="green", annotation_text="Soporte", row=1, col=1)
    
    # RSI (SOLO UNA VEZ en eje secundario)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='magenta', width=1, dash='dot'), name="RSI", opacity=0.4), row=1, col=1, secondary_y=True)
    
    # Volumen
    colors_vol = ['#26a69a' if row['Close'] >= row['Open'] else '#ef5350' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors_vol, name="Volumen"), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=550, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Métricas de Sesión
    c1, c2, c3 = st.columns(3)
    c1.metric("Precio Actual", f"{precio_act:,.2f} {moneda}")
    c2.metric("Máximo Sesión", f"{max_sesion:,.2f} {moneda}", delta_color="normal")
    c3.metric("Mínimo Sesión", f"{min_sesion:,.2f} {moneda}", delta_color="inverse")

    # --- 5. ANÁLISIS ---
    if st.button(f"⚖️ GENERAR ESTRATEGIA: {st.session_state.activo_sel.upper()}"):
        with st.spinner('Analizando confluencia...'):
            ticker_obj = yf.Ticker(st.session_state.ticker_sel)
            news_text = "\n".join([n.get('title', '') for n in ticker_obj.news[:3]])
            prompt = f"Analista XTB. Activo: {st.session_state.activo_sel}. Precio: {precio_act} {moneda}. RSI: {df['RSI'].iloc[-1]:.1f}. Capital: {st.session_state.wallet} EUR. Genera 3 opciones (INTRA, MEDIO, LARGO). Formato: TAG: [Probabilidad %]|[Acción: COMPRA o VENTA]|[Lotes]|[Entrada]|[TP]|[SL]"
            resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
            res_ia = resp.choices[0].message.content

            def parse_tag(tag):
                m = re.search(rf"{tag}:\s*(.*)", res_ia)
                return [p.strip() for p in m.group(1).split('|')] if m else ["---"]*6

            st.session_state.señal_actual = {"intra": parse_tag("INTRA"), "medio": parse_tag("MEDIO"), "largo": parse_tag("LARGO"), "moneda": moneda}
            st.rerun()

# --- 6. TARJETAS DE RESULTADOS (CORREGIDO FONDO Y DATOS) ---
if st.session_state.señal_actual:
    st.divider()
    cols_res = st.columns(3)
    mon = st.session_state.señal_actual["moneda"]
    for i, (name, tag) in enumerate([("INTRADÍA", "intra"), ("MEDIO PLAZO", "medio"), ("LARGO PLAZO", "largo")]):
        s = st.session_state.señal_actual[tag]
        tipo = s[1].upper()
        estilo_texto = "val-destacado" if "COMPRA" in tipo else "val-short"
        
        with cols_res[i]:
            st.markdown(f"""
            <div class="card-resumen">
                <h3>{name}</h3>
                <p>Probabilidad: <b>{s[0]}</b></p>
                <p>Acción: <span class="{estilo_texto}">{tipo}</span></p>
                <p>Lotes: <b>{s[2]}</b></p>
                <p>Entrada: <b>{s[3]} {mon}</b></p>
                <p>TP: <span style="color:#00ff00">{s[4]} {mon}</span></p>
                <p>SL: <span style="color:#ff4b4b">{s[5]} {mon}</span></p>
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

# --- 7. CARTERA Y BALANCE ---
st.sidebar.header("🏢 Balance General")
st.sidebar.metric("Cuenta (EUR)", f"{st.session_state.wallet:,.2f} €")
st.divider()
st.subheader("💼 Operaciones Activas")
if st.session_state.cartera_abierta:
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.markdown(f"**{pos['activo']}** | {pos['tipo']} ({pos['lotes']} lotes)")
            c1.write(f"In: {pos['entrada']} {pos['moneda']}")
            pos['sl'] = c2.text_input(f"Ajustar SL", value=pos['sl'], key=f"sl_{pos['id']}")
            pos['tp'] = c2.text_input(f"Ajustar TP", value=pos['tp'], key=f"tp_{pos['id']}")
            pnl = c3.number_input("PnL (€)", key=f"pnl_{pos['id']}")
            if c3.button("Cerrar", key=f"c_{pos['id']}"):
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                st.rerun()
