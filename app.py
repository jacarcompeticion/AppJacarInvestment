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
st.set_page_config(page_title="Jacar Pro V24", layout="wide", page_icon="🏦")

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

# --- 2. CSS PARA EL LOOK CREMA & WHITE ---
st.markdown("""
    <style>
    .stApp { background-color: #fdf6e3 !important; }
    .card-ia { 
        background-color: #ffffff !important; 
        padding: 20px; border-radius: 12px; border: 1px solid #dcd3b6;
        margin-bottom: 15px; color: #586e75 !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .panel-vip { background-color: #ffffff; border: 2px solid #268bd2; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
    .val-buy { color: #859900 !important; font-weight: bold; }
    .val-sell { color: #dc322f !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE ANÁLISIS (CON FIX PARA EL ERROR DE RSI) ---
def auto_analizar(t, n):
    try:
        df_t = yf.download(t, period="5d", interval="1h", progress=False)
        if df_t.empty: return None
        if isinstance(df_t.columns, pd.MultiIndex): df_t.columns = df_t.columns.get_level_values(0)
        
        # FIX: Verificamos que haya datos para el RSI
        rsi_series = ta.rsi(df_t['Close'], length=14)
        rsi_val = rsi_series.iloc[-1] if rsi_series is not None and not rsi_series.empty else 50.0
        
        adx_df = ta.adx(df_t['High'], df_t['Low'], df_t['Close'])
        adx_val = adx_df['ADX_14'].iloc[-1] if adx_df is not None and not adx_df.empty else 20.0
        
        p = df_t['Close'].iloc[-1]
        moneda = "€" if any(x in t for x in [".MC", "GDAXI", "IBEX"]) else "$"

        prompt = f"Analista. Activo: {n}. Precio: {p} {moneda}. RSI: {rsi_val:.1f}. ADX: {adx_val:.1f}. Genera 3 señales: [INTRA], [MEDIO], [LARGO]. Formato: TAG: [Prob%]|[Accion]|[Lotes]|[Entrada]|[TP]|[SL]|[Nominal EUR]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        res_ia = resp.choices[0].message.content
        
        def p_tag(tag):
            m = re.search(rf"{tag}:\s*(.*)", res_ia)
            return [p.strip() for p in m.group(1).split('|')] if m else ["0%","N/A","0","0","0","0","0"]
        
        return {"intra": p_tag("INTRA"), "medio": p_tag("MEDIO"), "largo": p_tag("LARGO"), "moneda": moneda}
    except Exception as e:
        st.error(f"Error en análisis de {n}: {e}")
        return None

# --- 4. RADAR VIP Y CATEGORÍAS ---
st.markdown('<div class="panel-vip"><h3>🚀 Radar de Oportunidades VIP</h3>', unsafe_allow_html=True)
activos_dict = {
    "Índices": {"Nasdaq": "^IXIC", "S&P 500": "^SPX", "IBEX 35": "^IBEX", "DAX 40": "^GDAXI"},
    "Acciones": {"NVDA": "NVDA", "Tesla": "TSLA", "Apple": "AAPL", "Iberdrola": "IBE.MC"},
    "Materias/FX": {"Oro": "GC=F", "Brent": "BZ=F", "Bitcoin": "BTC-USD", "EUR/USD": "EURUSD=X"}
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
st.markdown('</div>', unsafe_allow_html=True)

# --- 5. GRÁFICA ---
df = yf.download(st.session_state.ticker_sel, period="5d", interval="1h", progress=False)
if not df.empty:
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(plot_bgcolor='#1e212b', paper_bgcolor='#fdf6e3', height=400, xaxis_rangeslider_visible=False, margin=dict(t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# --- 6. ESTRATEGIAS AUTOMÁTICAS (LAS 3 POSICIONES) ---
if st.session_state.analisis_auto:
    st.subheader(f"⚡ Estrategias Sugeridas: {st.session_state.activo_sel}")
    cols_ia = st.columns(3)
    res = st.session_state.analisis_auto
    for i, tag in enumerate(["intra", "medio", "largo"]):
        s = res[tag]
        with cols_ia[i]:
            st.markdown(f"""<div class="card-ia">
                <h4 style="text-align:center;">{tag.upper()}</h4>
                <p>🎯 Probabilidad: <b>{s[0]}</b></p>
                <p>⚡ Acción: <b class="{'val-buy' if 'COMPRA' in s[1] else 'val-sell'}">{s[1]}</b></p>
                <p>📦 Lotes: {s[2]} | In: {s[3]} {res['moneda']}</p>
                <p>🏁 TP: <span class="val-buy">{s[4]}</span> | 🛡️ SL: <span class="val-sell">{s[5]}</span></p>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Abrir {tag.capitalize()}", key=f"op_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "tipo": s[1], "lotes": s[2], "entrada": s[3], "tp": s[4], "sl": s[5], 
                    "valor_nominal": s[6], "ticker": st.session_state.ticker_sel, "moneda": res['moneda']
                })
                guardar_en_csv()
                st.rerun()

# --- 7. SIDEBAR: CONTROL FINANCIERO ---
with st.sidebar:
    st.header("🏢 Balance Jacar")
    # Cálculo de margen
    v_total = sum([float(str(p['valor_nominal']).replace('EUR','').strip()) for p in st.session_state.cartera_abierta]) if st.session_state.cartera_abierta else 0
    margen = v_total / 20
    st.metric("Equity (EUR)", f"{st.session_state.wallet:,.2f} €")
    st.write(f"**Margen Utilizado:** {margen:,.2f} €")
    st.write(f"**Disponible:** {(st.session_state.wallet - margen):,.2f} €")
    
    st.divider()
    st.subheader("💼 Posiciones Abiertas")
    for i, pos in enumerate(st.session_state.cartera_abierta):
        with st.container(border=True):
            st.write(f"**{pos['activo']}** ({pos['tipo']})")
            st.caption(f"In: {pos['entrada']} {pos.get('moneda','$')}")
            pnl = st.number_input("PnL (€)", key=f"pnl_{pos['id']}", value=0.0)
            if st.button("Cerrar", key=f"c_{pos['id']}", type="primary"):
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                guardar_en_csv()
                st.rerun()
