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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Jacar Pro V31", layout="wide", page_icon="🏦")

CSV_FILE = 'cartera_jacar.csv'

def guardar_en_csv():
    if st.session_state.cartera_abierta:
        pd.DataFrame(st.session_state.cartera_abierta).to_csv(CSV_FILE, index=False)
    elif os.path.exists(CSV_FILE): os.remove(CSV_FILE)

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
    .card-ia { background-color: #ffffff !important; padding: 20px; border-radius: 12px; border: 1px solid #dcd3b6; margin-bottom: 10px; color: #586e75 !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .panel-vip { background-color: #ffffff; border: 2px solid #268bd2; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
    .val-buy { color: #859900 !important; font-weight: bold; }
    .val-sell { color: #dc322f !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MOTOR DE ANÁLISIS ---
def auto_analizar(t, n):
    try:
        df_t = yf.download(t, period="60d", interval="1h", progress=False)
        if df_t.empty: return None
        if isinstance(df_t.columns, pd.MultiIndex): df_t.columns = df_t.columns.get_level_values(0)
        
        rsi_val = ta.rsi(df_t['Close']).iloc[-1]
        ema_20 = ta.ema(df_t['Close'], length=20).iloc[-1]
        atr = ta.atr(df_t['High'], df_t['Low'], df_t['Close'], length=14).iloc[-1]
        p_actual = float(df_t['Close'].iloc[-1])
        moneda = "€" if any(x in t for x in [".MC", "GDAXI", "IBEX"]) else "$"

        prompt = f"Trader Senior. Activo: {n}. Precio: {p_actual}. RSI: {rsi_val:.1f}. ATR: {atr:.4f}. Genera 3 señales DIFERENTES (INTRA, MEDIO, LARGO). Formato: TAG: [Prob%]|[Accion]|[Lotes]|[Entrada]|[TP]|[SL]|[Nominal EUR]"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        res_ia = resp.choices[0].message.content
        
        def p_tag(tag):
            m = re.search(rf"{tag}:\s*\[?(.*?)\]?(\n|$)", res_ia)
            if m:
                parts = [p.strip().replace('[','').replace(']','') for p in m.group(1).split('|')]
                if len(parts) >= 7: return parts
            return ["---","---","0","0","0","0","0"]
        return {"intra": p_tag("INTRA"), "medio": p_tag("MEDIO"), "largo": p_tag("LARGO"), "moneda": moneda}
    except: return None

# --- 4. RADAR VIP ---
st.markdown('<div class="panel-vip"><h3>🚀 Radar VIP</h3>', unsafe_allow_html=True)
vip = {"Nasdaq": "^IXIC", "Oro": "GC=F", "NVDA": "NVDA", "Bitcoin": "BTC-USD"}
cv = st.columns(4)
for i, (n, t) in enumerate(vip.items()):
    if cv[i].button(f"🔥 {n}", key=f"v_{t}", use_container_width=True):
        st.session_state.activo_sel, st.session_state.ticker_sel = n, t
        st.session_state.analisis_auto = auto_analizar(t, n)
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 5. CATEGORÍAS DETALLADAS ---
t_acc, t_ind, t_mat, t_div = st.tabs(["Acciones", "Indices", "Materiales", "Divisas"])

def render_grid(d):
    cols = st.columns(4)
    for i, (n, t) in enumerate(d.items()):
        if cols[i % 4].button(n, key=f"btn_{t}", use_container_width=True):
            st.session_state.activo_sel, st.session_state.ticker_sel = n, t
            st.session_state.analisis_auto = auto_analizar(t, n)
            st.rerun()

with t_acc:
    s_acc = st.tabs(["Tecnología", "Energía", "Banca", "Consumo"])
    with s_acc[0]: render_grid({"NVDA":"NVDA", "Apple":"AAPL", "Tesla":"TSLA", "Google":"GOOGL"})
    with s_acc[1]: render_grid({"Iberdrola":"IBE.MC", "Repsol":"REP.MC", "Exxon":"XOM"})
    with s_acc[2]: render_grid({"Santander":"SAN.MC", "BBVA":"BBVA.MC", "JPMorgan":"JPM"})
    with s_acc[3]: render_grid({"Amazon":"AMZN", "Inditex":"ITX.MC", "Walmart":"WMT"})

with t_ind:
    s_ind = st.tabs(["Europa", "EE.UU", "Asia"])
    with s_ind[0]: render_grid({"IBEX 35":"^IBEX", "DAX 40":"^GDAXI", "CAC 40":"^FCHI"})
    with s_ind[1]: render_grid({"Nasdaq 100":"^IXIC", "S&P 500":"^SPX", "Dow Jones":"^DJI"})
    with s_ind[2]: render_grid({"Nikkei 225":"^N225", "Hang Seng":"^HSI"})

with t_mat:
    s_mat = st.tabs(["Minerales", "Energéticos", "Otros"])
    with s_mat[0]: render_grid({"Oro":"GC=F", "Plata":"SI=F", "Cobre":"HG=F"})
    with s_mat[1]: render_grid({"Brent":"BZ=F", "WTI":"CL=F", "Gas Nat":"NG=F"})
    with s_mat[2]: render_grid({"Trigo":"ZW=F", "Café":"KC=F"})

with t_div:
    render_grid({"EUR/USD":"EURUSD=X", "GBP/USD":"GBPUSD=X", "USD/JPY":"JPY=X", "BTC/USD":"BTC-USD"})

# --- 6. GRÁFICA (CORREGIDA) ---
st.divider()
st.subheader(f"📊 Gráfico de Análisis: {st.session_state.activo_sel}")

# Selector de tiempo fuera del bloque condicional para que no desaparezca
periodo_sel = st.select_slider("Rango Temporal", options=["1D", "5D", "1M", "6M", "1Y", "5Y"], value="1M")
map_int = {"1D": "5m", "5D": "30m", "1M": "1h", "6M": "1d", "1Y": "1d", "5Y": "1wk"}

df = yf.download(st.session_state.ticker_sel, period=periodo_sel.lower(), interval=map_int[periodo_sel], progress=False)

if not df.empty:
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # Calcular indicadores solo si hay datos suficentes
    df['EMA20'] = ta.ema(df['Close'], length=20) if len(df) > 20 else df['Close']
    df['RSI'] = ta.rsi(df['Close'], length=14) if len(df) > 14 else 50

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    
    # Velas y EMA
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Velas"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#268bd2', width=1.5), name="EMA 20"), row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#6c71c4'), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)

    fig.update_layout(plot_bgcolor='#1e212b', paper_bgcolor='#fdf6e3', height=500, xaxis_rangeslider_visible=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No se han podido cargar datos para este rango temporal. Prueba con uno mayor (ej: 1M).")



# --- 7. ESTRATEGIAS ---
if st.session_state.analisis_auto:
    st.subheader(f"🛡️ Señales Jacar: {st.session_state.activo_sel}")
    cols_ia = st.columns(3)
    res = st.session_state.analisis_auto
    for i, tag in enumerate(["intra", "medio", "largo"]):
        s = res[tag]
        with cols_ia[i]:
            st.markdown(f"""<div class="card-ia">
                <h4 style="text-align:center;">{tag.upper()}</h4>
                <p>🎯 Prob: <b>{s[0]}</b> | Acción: <b class="{'val-buy' if 'COMPRA' in s[1].upper() else 'val-sell'}">{s[1]}</b></p>
                <p>📦 Lotes: {s[2]} | Entrada: {s[3]} {res['moneda']}</p>
                <p>🏁 TP: <span class="val-buy">{s[4]}</span> | 🛡️ SL: <span class="val-sell">{s[5]}</span></p>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Abrir {tag.title()}", key=f"op_{tag}"):
                st.session_state.cartera_abierta.append({
                    "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                    "tipo": s[1], "lotes": s[2], "entrada": s[3], "tp": s[4], "sl": s[5], 
                    "valor_nominal": s[6], "ticker": st.session_state.ticker_sel, "moneda": res['moneda']
                })
                guardar_en_csv()
                st.rerun()

# --- 8. SIDEBAR ---
with st.sidebar:
    st.header("🏢 Cartera Jacar")
    v_total = 0
    for p in st.session_state.cartera_abierta:
        try: v_total += float(str(p['valor_nominal']).replace('EUR','').replace(',','').strip())
        except: pass
    
    margen = v_total / 20
    porcentaje_margen = (margen / st.session_state.wallet) * 100
    st.metric("Equity", f"{st.session_state.wallet:,.2f} €")
    st.write(f"**Margen:** {margen:,.2f} € ({porcentaje_margen:.1f}%)")
    
    if porcentaje_margen > 50:
        st.markdown('<div class="alerta-roja">⚠️ RIESGO ALTO</div>', unsafe_allow_html=True)
    
    st.divider()
    st.subheader("💼 Posiciones")
    for i, pos in enumerate(list(st.session_state.cartera_abierta)):
        with st.expander(f"📌 {pos['activo']} ({pos['tipo']})"):
            pnl = st.number_input("PnL (€)", key=f"pnl_{pos['id']}", value=0.0)
            if st.button("Cerrar", key=f"c_{pos['id']}", use_container_width=True):
                st.session_state.wallet += pnl
                st.session_state.cartera_abierta.pop(i)
                guardar_en_csv()
                st.rerun()
