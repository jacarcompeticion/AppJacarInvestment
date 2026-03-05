import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from openai import OpenAI
from datetime import datetime
import re
import os

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
st.set_page_config(page_title="Jacar Pro V25", layout="wide", page_icon="🏦")

CSV_FILE = 'cartera_jacar.csv'

def guardar_en_csv():
    if st.session_state.cartera_abierta:
        pd.DataFrame(st.session_state.cartera_abierta).to_csv(CSV_FILE, index=False)
    elif os.path.exists(CSV_FILE): 
        os.remove(CSV_FILE)

def cargar_desde_csv():
    if os.path.exists(CSV_FILE):
        try: return pd.read_csv(CSV_FILE).to_dict('records')
        except: return []
    return []

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_desde_csv()
if 'activo_sel' not in st.session_state: st.session_state.activo_sel, st.session_state.ticker_sel = "Nasdaq 100", "^IXIC"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #fdf6e3 !important; }
    .card-ia { 
        background-color: #ffffff !important; 
        padding: 20px; border-radius: 12px; border: 1px solid #dcd3b6;
        margin-bottom: 15px; color: #586e75 !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .alerta-roja { 
        background-color: #ffcccc; color: #cc0000; padding: 10px; 
        border-radius: 8px; border: 2px solid #ff0000; font-weight: bold; text-align: center;
    }
    .val-buy { color: #859900 !important; font-weight: bold; }
    .val-sell { color: #dc322f !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE ANÁLISIS ---
def auto_analizar(t, n):
    try:
        df_t = yf.download(t, period="5d", interval="1h", progress=False)
        if df_t.empty: return None
        if isinstance(df_t.columns, pd.MultiIndex): df_t.columns = df_t.columns.get_level_values(0)
        
        rsi = ta.rsi(df_t['Close']).iloc[-1] if ta.rsi(df_t['Close']) is not None else 50.0
        p = df_t['Close'].iloc[-1]
        moneda = "€" if any(x in t for x in [".MC", "GDAXI", "IBEX"]) else "$"

        prompt = f"Activo: {n}. Precio: {p}. RSI: {rsi:.1f}. Genera 3 señales para INTRA, MEDIO, LARGO. Formato EXACTO: TAG: [Prob%]|[Accion]|[Lotes]|[Entrada]|[TP]|[SL]|[Nominal EUR]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        res_ia = resp.choices[0].message.content
        
        def p_tag(tag):
            m = re.search(rf"{tag}:\s*(.*)", res_ia)
            if m:
                parts = [p.strip() for p in m.group(1).split('|')]
                if len(parts) >= 7: return parts
            return ["0%","N/A","0","0","0","0","0"]
        
        return {"intra": p_tag("INTRA"), "medio": p_tag("MEDIO"), "largo": p_tag("LARGO"), "moneda": moneda}
    except: return None

# --- 4. CATEGORÍAS ACTUALIZADAS ---
activos_dict = {
    "Acciones": {"NVDA": "NVDA", "Tesla": "TSLA", "Apple": "AAPL", "Iberdrola": "IBE.MC", "Repsol": "REP.MC"},
    "Indices": {"Nasdaq": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"},
    "Material": {"Oro": "GC=F", "Plata": "SI=F", "Brent": "BZ=F", "Gas": "NG=F"},
    "Divisas": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "Bitcoin": "BTC-USD"}
}

tabs = st.tabs(list(activos_dict.keys()))
for i, (cat, lista) in enumerate(activos_dict.items()):
    with tabs[i]:
        cols = st.columns(len(lista))
        for j, (n, t) in enumerate(lista.items()):
            if cols[j].button(n, key=f"btn_{t}", use_container_width=True):
                st.session_state.activo_sel, st.session_state.ticker_sel = n, t
                st.session_state.analisis_auto = auto_analizar(t, n)
                st.rerun()

# --- 5. GRÁFICA ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h", progress=False)
if not df.empty:
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(plot_bgcolor='#1e212b', paper_bgcolor='#fdf6e3', height=400, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- 6. ESTRATEGIAS ---
if st.session_state.analisis_auto:
    st.subheader(f"📊 Estrategias: {st.session_state.activo_sel}")
    cols_ia = st.columns(3)
    res = st.session_state.analisis_auto
    for i, tag in enumerate(["intra", "medio", "largo"]):
        s = res[tag]
        with cols_ia[i]:
            st.markdown(f"""<div class="card-ia">
                <h4 style="text-align:center;">{tag.upper()}</h4>
                <p>🎯 Prob: <b>{s[0]}</b> | Acción: <b class="{'val-buy' if 'COMPRA' in s[1] else 'val-sell'}">{s[1]}</b></p>
                <p>📦 Lotes: {s[2]} | In: {s[3]} {res['moneda']}</p>
                <p>🏁 TP: <span class="val-buy">{s[4]}</span> | 🛡️ SL: <span class="val-sell">{s[5]}</span></p>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Ejecutar {tag.capitalize()}", key=f"op_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "tipo": s[1], "lotes": s[2], "entrada": s[3], "tp": s[4], "sl": s[5], 
                    "valor_nominal": s[6], "ticker": st.session_state.ticker_sel, "moneda": res['moneda']
                })
                guardar_en_csv()
                st.rerun()

# --- 7. SIDEBAR CON ALERTA DE RIESGO ---
with st.sidebar:
    st.header("🏢 Balance Jacar")
    v_total = sum([float(str(p['valor_nominal']).replace('EUR','').strip()) for p in st.session_state.cartera_abierta]) if st.session_state.cartera_abierta else 0
    margen = v_total / 20
    porcentaje_margen = (margen / st.session_state.wallet) * 100
    
    st.metric("Equity (EUR)", f"{st.session_state.wallet:,.2f} €")
    st.write(f"**Margen Utilizado:** {margen:,.2f} € ({porcentaje_margen:.1f}%)")
    
    if porcentaje_margen > 50:
        st.markdown('<div class="alerta-roja">⚠️ RIESGO ALTO: MARGEN > 50%</div>', unsafe_allow_html=True)
    
    st.divider()
    st.subheader("💼 Posiciones")
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            st.write(f"**{pos['activo']}** ({pos['tipo']})")
            pnl = st.number_input("PnL (€)", key=f"pnl_{pos['id']}", value=0.0)
            if st.button("Cerrar", key=f"c_{pos['id']}", type="primary"):
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                guardar_en_csv()
                st.rerun()
