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
st.set_page_config(page_title="Jacar Pro V35", layout="wide", page_icon="🏦")

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
if 'activo_sel' not in st.session_state: st.session_state.activo_sel, st.session_state.ticker_sel = "US100 (Nasdaq)", "NQ=F"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. MOTOR DE DATOS OPTIMIZADO ---
@st.cache_data(ttl=60) # Caché de 60 segundos para evitar re-descargas innecesarias
def obtener_datos(ticker, periodo, intervalo):
    df = yf.download(ticker, period=periodo, interval=intervalo, progress=False)
    if df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex): 
        df.columns = df.columns.get_level_values(0)
    return df

def auto_analizar(t, n):
    try:
        # Descarga rápida de solo los puntos necesarios
        df_t = obtener_datos(t, "5d", "15m")
        if df_t.empty: return None
        
        rsi_val = ta.rsi(df_t['Close']).iloc[-1]
        p_actual = float(df_t['Close'].iloc[-1])
        moneda = "€" if any(x in t for x in [".MC", "GDAXI", "IBEX"]) else "$"

        # Prompt optimizado para respuesta corta (más rápido)
        prompt = f"Trader: {n}|{p_actual}|RSI:{rsi_val:.1f}. Responde solo: INTRA: [Prob%]|[Accion]|[Lotes]|[Entrada]|[TP]|[SL]|[Nominal] (repite para MEDIO y LARGO)"
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini", # Usamos mini para velocidad extrema si está disponible, o 4o
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0
        )
        res_ia = resp.choices[0].message.content
        
        def p_tag(tag):
            m = re.search(rf"{tag}:\s*\[?(.*?)\]?(\n|$)", res_ia, re.IGNORECASE)
            if m:
                parts = [p.strip().replace('[','').replace(']','') for p in m.group(1).split('|')]
                if len(parts) >= 7: return parts
            return ["70%","COMPRA","0.1",str(p_actual),str(p_actual*1.02),str(p_actual*0.99),"2000"]
        
        return {"intra": p_tag("INTRA"), "medio": p_tag("MEDIO"), "largo": p_tag("LARGO"), "moneda": moneda}
    except: return None

# --- 3. INTERFAZ Y RADAR ---
st.markdown('<div class="panel-vip"><h3>🚀 Radar VIP</h3>', unsafe_allow_html=True)
vip = {"US100 (Nasdaq)": "NQ=F", "Oro": "GC=F", "NVDA": "NVDA", "Bitcoin": "BTC-USD"}
cv = st.columns(4)
for i, (n, t) in enumerate(vip.items()):
    if cv[i].button(f"🔥 {n}", key=f"v_{t}", use_container_width=True):
        st.session_state.activo_sel, st.session_state.ticker_sel = n, t
        st.session_state.analisis_auto = auto_analizar(t, n)
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- 4. CATEGORÍAS (Stocks, Indices, Material, Currencies) ---
t_acc, t_ind, t_mat, t_div = st.tabs(["Stocks", "Indices", "Material", "Currencies"])

def render_grid(d):
    cols = st.columns(4)
    for i, (n, t) in enumerate(d.items()):
        if cols[i % 4].button(n, key=f"btn_{t}", use_container_width=True):
            st.session_state.activo_sel, st.session_state.ticker_sel = n, t
            st.session_state.analisis_auto = auto_analizar(t, n)
            st.rerun()

with t_acc: render_grid({"NVDA":"NVDA", "Apple":"AAPL", "Tesla":"TSLA", "Google":"GOOGL", "Amazon":"AMZN", "Inditex":"ITX.MC", "Iberdrola":"IBE.MC", "Santander":"SAN.MC"})
with t_ind: render_grid({"US100":"NQ=F", "S&P 500":"ES=F", "DAX 40":"^GDAXI", "IBEX 35":"^IBEX", "Nikkei 225":"^N225", "Dow Jones":"YM=F"})
with t_mat: render_grid({"Oro":"GC=F", "Plata":"SI=F", "Cobre":"HG=F", "Brent":"BZ=F", "WTI":"CL=F", "Gas Nat":"NG=F"})
with t_div: render_grid({"EUR/USD":"EURUSD=X", "GBP/USD":"GBPUSD=X", "USD/JPY":"JPY=X", "AUD/USD":"AUDUSD=X", "EUR/GBP":"EURGBP=X", "BTC/USD":"BTC-USD"})

# --- 5. GRÁFICA CON SOPORTES Y RESISTENCIAS ---
st.divider()
franja = st.select_slider("Franja Temporal", options=["1h", "6h", "12h", "1d", "2d", "3d", "4d"], value="1d")
config_map = {"1h":{"p":"1d","i":"1m"},"6h":{"p":"1d","i":"2m"},"12h":{"p":"1d","i":"5m"},"1d":{"p":"1d","i":"5m"},"2d":{"p":"2d","i":"15m"},"3d":{"p":"3d","i":"15m"},"4d":{"p":"5d","i":"30m"}}

df = obtener_datos(st.session_state.ticker_sel, config_map[franja]['p'], config_map[franja]['i'])

if not df.empty:
    df['EMA20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    res_act, sop_act = df['High'].tail(30).max(), df['Low'].tail(30).min()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#268bd2', width=1), name="EMA 20"), row=1, col=1)
    fig.add_hline(y=res_act, line_dash="dash", line_color="red", opacity=0.4, annotation_text="RES", row=1, col=1)
    fig.add_hline(y=sop_act, line_dash="dash", line_color="green", opacity=0.4, annotation_text="SOP", row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#6c71c4'), name="RSI"), row=2, col=1)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(plot_bgcolor='#1e212b', paper_bgcolor='#fdf6e3', height=550, xaxis_rangeslider_visible=False, margin=dict(t=5, b=5))
    st.plotly_chart(fig, use_container_width=True)

# --- 6. ESTRATEGIAS Y SIDEBAR ---
if st.session_state.analisis_auto:
    st.subheader(f"🛡️ Plan Estratégico: {st.session_state.activo_sel}")
    cols_ia = st.columns(3)
    res = st.session_state.analisis_auto
    for i, tag in enumerate(["intra", "medio", "largo"]):
        s = res[tag]
        with cols_ia[i]:
            st.markdown(f"""<div class="card-ia"><h4 style="text-align:center;">{tag.upper()}</h4>
                <p>🎯 Prob: <b>{s[0]}</b> | Acción: <b>{s[1]}</b></p>
                <p>📦 Lotes: {s[2]} | In: {s[3]} {res['moneda']}</p>
                <p>🏁 TP: <span style="color:green;">{s[4]}</span> | 🛡️ SL: <span style="color:red;">{s[5]}</span></p></div>""", unsafe_allow_html=True)
            if st.button(f"Abrir {tag.title()}", key=f"op_{tag}"):
                st.session_state.cartera_abierta.append({"id":datetime.now().strftime("%H%M%S"),"activo":st.session_state.activo_sel,"tipo":s[1],"lotes":s[2],"entrada":s[3],"tp":s[4],"sl":s[5],"valor_nominal":s[6],"ticker":st.session_state.ticker_sel,"moneda":res['moneda']})
                guardar_en_csv(); st.rerun()

with st.sidebar:
    st.header("🏢 Cartera Jacar")
    v_total = sum([float(str(p['valor_nominal']).replace('EUR','').replace(',','').strip()) for p in st.session_state.cartera_abierta]) if st.session_state.cartera_abierta else 0
    margen = v_total / 20
    st.metric("Balance Equity", f"{st.session_state.wallet:,.2f} €")
    st.write(f"**Margen:** {margen:,.2f} €")
    st.divider()
    for i, pos in enumerate(list(st.session_state.cartera_abierta)):
        with st.expander(f"📌 {pos['activo']} ({pos['tipo']})"):
            pnl = st.number_input("PnL (€)", key=f"pnl_{pos['id']}", value=0.0)
            if st.button("Cerrar", key=f"c_{pos['id']}", use_container_width=True):
                st.session_state.wallet += pnl; st.session_state.cartera_abierta.pop(i); guardar_en_csv(); st.rerun()
