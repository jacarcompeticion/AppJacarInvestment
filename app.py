import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import re
import os

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Jacar Pro V23 - Storage", layout="wide", page_icon="🏦")

# RUTAS DE ALMACENAMIENTO
CSV_FILE = 'cartera_jacar.csv'

def guardar_en_csv():
    if st.session_state.cartera_abierta:
        df_save = pd.DataFrame(st.session_state.cartera_abierta)
        df_save.to_csv(CSV_FILE, index=False)
    else:
        if os.path.exists(CSV_FILE): os.remove(CSV_FILE)

def cargar_desde_csv():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE).to_dict('records')
    return []

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_desde_csv()
if 'activo_sel' not in st.session_state: st.session_state.activo_sel = "Nasdaq 100"
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel = "^IXIC"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. CSS AVANZADO ---
st.markdown("""
    <style>
    .stApp { background-color: #fdf6e3 !important; }
    .card-resumen { 
        background-color: #ffffff !important; 
        padding: 20px; border-radius: 12px; border: 1px solid #dcd3b6;
        margin-bottom: 15px; color: #586e75 !important;
    }
    .panel-vip { background-color: #ffffff; border: 2px solid #268bd2; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
    .val-buy { color: #859900 !important; font-weight: bold; }
    .val-sell { color: #dc322f !important; font-weight: bold; }
    .sidebar-metrics { background-color: #eee8d5; padding: 15px; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. GESTIÓN FINANCIERA (APALANCAMIENTO 1:20) ---
def calcular_balance():
    # Convertimos valores a float para evitar errores de tipo al cargar del CSV
    valor_total = sum([float(pos['valor_nominal']) for pos in st.session_state.cartera_abierta])
    margen = valor_total / 20
    disponible = st.session_state.wallet - margen
    # Recomendable: Máximo 30% del capital disponible en una sola operación
    recomendable = disponible * 0.3
    return valor_total, margen, disponible, recomendable

# --- 4. FUNCIÓN IA AUTOMÁTICA ---
def auto_analizar(t, n):
    df_t = yf.download(t, period="2d", interval="1h")
    if not df_t.empty:
        if isinstance(df_t.columns, pd.MultiIndex): df_t.columns = df_t.columns.get_level_values(0)
        p = df_t['Close'].iloc[-1]
        rsi = ta.rsi(df_t['Close']).iloc[-1]
        adx = ta.adx(df_t['High'], df_t['Low'], df_t['Close'])['ADX_14'].iloc[-1]
        
        prompt = f"Activo: {n}. Precio: {p}. ADX: {adx:.1f}. RSI: {rsi:.1f}. Genera 3 niveles (INTRA, MEDIO, LARGO). Formato: TAG: [Prob%]|[Accion]|[Lotes]|[Entrada]|[TP]|[SL]|[Valor Nominal EUR]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        res_ia = resp.choices[0].message.content
        
        def p_tag(tag):
            m = re.search(rf"{tag}:\s*(.*)", res_ia)
            return [p.strip() for p in m.group(1).split('|')] if m else ["0%","N/A","0","0","0","0","0"]
        
        return {"intra": p_tag("INTRA"), "medio": p_tag("MEDIO"), "largo": p_tag("LARGO")}
    return None

# --- 5. RADAR VIP & SELECCIÓN ---
st.markdown('<div class="panel-vip"><h3>🚀 Radar VIP & Operativa Automática</h3>', unsafe_allow_html=True)
activos = {"Nasdaq": "^IXIC", "Gold": "GC=F", "NVDA": "NVDA", "BTC": "BTC-USD", "EURUSD": "EURUSD=X", "S&P500": "^SPX", "DAX": "^GDAXI", "IBEX": "^IBEX"}
c_vip = st.columns(len(activos))
for i, (n, t) in enumerate(activos.items()):
    if c_vip[i].button(n, key=f"v_{t}", use_container_width=True):
        st.session_state.activo_sel = n
        st.session_state.ticker_sel = t
        st.session_state.analisis_auto = auto_analizar(t, n)
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 6. GRÁFICA PROFESIONAL ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h")
if not df.empty:
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(plot_bgcolor='#1e212b', paper_bgcolor='#fdf6e3', height=400, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- 7. RESULTADOS DEL ANÁLISIS ---
if st.session_state.analisis_auto:
    st.subheader(f"📊 Estrategias para {st.session_state.activo_sel}")
    cols = st.columns(3)
    for i, tag in enumerate(["intra", "medio", "largo"]):
        s = st.session_state.analisis_auto[tag]
        with cols[i]:
            st.markdown(f"""<div class="card-resumen">
                <h4>{tag.upper()}</h4>
                <p>Prob: <b>{s[0]}</b> | Acción: <b class="{'val-buy' if 'COMPRA' in s[1] else 'val-sell'}">{s[1]}</b></p>
                <p>In: {s[3]} | Lotes: {s[2]}</p>
                <p><b>TP: {s[4]}</b> | <b>SL: {s[5]}</b></p>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Ejecutar {tag}", key=f"e_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "tipo": s[1], "lotes": s[2], "entrada": s[3], "tp": s[4], "sl": s[5], 
                    "valor_nominal": s[6], "ticker": st.session_state.ticker_sel
                })
                guardar_en_csv()
                st.rerun()

# --- 8. BARRA LATERAL: FINANZAS Y POSICIONES ---
with st.sidebar:
    v_total, margen, disponible, recomend = calcular_balance()
    st.header("🏢 Balance de Cuenta")
    st.markdown(f"""<div class="sidebar-metrics">
        <p><b>Equity:</b> {st.session_state.wallet:,.2f} €</p>
        <p><b>Valor Nominal:</b> {v_total:,.2f} €</p>
        <p><b>Margen Utilizado:</b> {margen:,.2f} €</p>
        <p><b>Disponible:</b> {disponible:,.2f} €</p>
        <hr>
        <p style="color:#268bd2"><b>Sugerencia:</b> {recomend:,.2f} €</p>
    </div>""", unsafe_allow_html=True)

    st.subheader("💼 Posiciones Activas")
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            st.write(f"**{pos['activo']}** ({pos['tipo']})")
            pnl = st.number_input(f"PnL (€)", key=f"pnl_{pos['id']}", value=0.0)
            if st.button("Cerrar", key=f"c_{pos['id']}"):
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                guardar_en_csv()
                st.rerun()
