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

# --- 1. CONFIGURACIÓN Y PERSISTENCIA ---
st.set_page_config(page_title="Jacar Pro V41", layout="wide", page_icon="🏦")

CSV_FILE = 'cartera_jacar.csv'
HIST_FILE = 'historial_jacar.csv'

def guardar_datos(lista, archivo):
    if lista: pd.DataFrame(lista).to_csv(archivo, index=False)
    elif os.path.exists(archivo): os.remove(archivo)

def cargar_datos(archivo):
    if os.path.exists(archivo):
        try: return pd.read_csv(archivo).to_dict('records')
        except: return []
    return []

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'activo_sel' not in st.session_state: st.session_state.activo_sel, st.session_state.ticker_sel = "US100", "NQ=F"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. MOTOR DE DATOS ---
@st.cache_data(ttl=60)
def obtener_datos(ticker, periodo, intervalo):
    try:
        df = yf.download(ticker, period=periodo, interval=intervalo, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return df
    except: return pd.DataFrame()

def auto_analizar(t, n):
    try:
        df_t = obtener_datos(t, "5d", "15m")
        if df_t.empty: return None
        rsi_val = ta.rsi(df_t['Close']).iloc[-1]
        p_actual = float(df_t['Close'].iloc[-1])
        moneda = "€" if any(x in t for x in [".MC", "GDAXI", "IBEX"]) else "$"

        prompt = f"Activo:{n} Precio:{p_actual} RSI:{rsi_val:.1f}. Genera 3 planes: INTRA, MEDIO, LARGO. Formato: TAG: Prob% | Accion | Lotes | Entrada | TP | SL | Nominal"
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0)
        res_ia = resp.choices[0].message.content
        
        def extraer(tag):
            for line in res_ia.split('\n'):
                if tag in line.upper():
                    data = line.split(':')[-1].replace('[','').replace(']','').split('|')
                    if len(data) >= 7: return [d.strip() for d in data]
            return ["---","---","0","0","0","0","0"]

        return {"intra": extraer("INTRA"), "medio": extraer("MEDIO"), "largo": extraer("LARGO"), "moneda": moneda}
    except: return None

# --- 3. INTERFAZ: CATEGORÍAS (CON FIX DE LLAVES DUPLICADAS) ---
st.markdown('<div style="background-color:#ffffff; padding:15px; border-radius:10px; border:2px solid #268bd2; margin-bottom:20px;"><h3>🚀 Radar VIP</h3>', unsafe_allow_html=True)
vip = {"🏙️ US100": "NQ=F", "📀 ORO": "GC=F", "💡 NVDA": "NVDA", "₿ BTC": "BTC-USD"}
cv = st.columns(4)
for i, (n, t) in enumerate(vip.items()):
    if cv[i].button(f"{n}", key=f"vip_{t}", use_container_width=True):
        st.session_state.activo_sel, st.session_state.ticker_sel = n, t
        st.session_state.analisis_auto = auto_analizar(t, n)
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

t_main = st.tabs(["📈 Stocks", "📊 Indices", "🏗️ Material", "💱 Divisas"])

# Función grid mejorada con prefijo para evitar errores de duplicados
def grid(d, prefix=""):
    cols = st.columns(4)
    for i, (n, t) in enumerate(d.items()):
        # El key ahora es único combinando prefijo + ticker
        if cols[i % 4].button(n, key=f"btn_{prefix}_{t}", use_container_width=True):
            st.session_state.activo_sel, st.session_state.ticker_sel = n, t
            st.session_state.analisis_auto = auto_analizar(t, n)
            st.rerun()

with t_main[0]: # STOCKS
    s1, s2, s3, s4, s5, s6 = st.tabs(["🔥 High Alpha", "💻 Tecnología", "⛽ Energía", "🏦 Banca", "🛒 Consumo", "🇪🇸 España"])
    with s1: grid({"🚀 MicroStrategy":"MSTR", "🪙 Coinbase":"COIN", "🧠 Palantir":"PLTR", "⚡ SMCI":"SMCI", "🧬 Eli Lilly":"LLY", "🖥️ AMD":"AMD", "🛰️ SpaceX (Tesla)":"TSLA", "💳 Adyen":"ADYEN.AS", "💉 Moderna":"MRNA", "🕹️ Roblox":"RBLX"}, "alpha")
    with s2: grid({"🍏 Apple":"AAPL", "🤖 NVDA":"NVDA", "🚗 Tesla":"TSLA", "🔍 Google":"GOOGL", "📦 Amazon":"AMZN"}, "tech")
    with s3: grid({"⛽ Exxon":"XOM", "🐚 Shell":"SHEL", "🔥 Chevron":"CVX"}, "ener")
    with s4: grid({"💳 Visa":"V", "🏦 JPMorgan":"JPM", "📈 Goldman":"GS"}, "bank")
    with s5: grid({"🥤 Coca-Cola":"KO", "🍔 McDonald's":"MCD", "🛒 Walmart":"WMT"}, "cons")
    with s6: grid({"👕 Inditex":"ITX.MC", "⚡ Iberdrola":"IBE.MC", "🏦 Santander":"SAN.MC", "🏦 BBVA":"BBVA.MC"}, "esp")

with t_main[1]: # INDICES
    i1, i2, i3 = st.tabs(["🇺🇸 EE.UU", "🇪🇺 Europa", "🌏 Asia"])
    with i1: grid({"🇺🇸 US100":"NQ=F", "📈 S&P 500":"ES=F", "🏭 Dow Jones":"YM=F"}, "idx_usa")
    with i2: grid({"🇩🇪 DAX 40":"^GDAXI", "🇪🇸 IBEX 35":"^IBEX", "🇫🇷 CAC 40":"^FCHI"}, "idx_eu")
    with i3: grid({"🇯🇵 Nikkei":"^N225", "🇭🇰 Hang Seng":"^HSI"}, "idx_as")

with t_main[2]: # MATERIAL
    m1, m2, m3 = st.tabs(["🥇 Metales", "🛢️ Energía", "🌾 Agro"])
    with m1: grid({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🥉 Cobre":"HG=F"}, "mat_met")
    with m2: grid({"🛢️ Brent":"BZ=F", "🛢️ WTI":"CL=F", "🔥 Gas Nat":"NG=F"}, "mat_ene")
    with m3: grid({"🌾 Trigo":"ZW=F", "☕ Café":"KC=F", "🌽 Maíz":"ZC=F"}, "mat_agr")

with t_main[3]: # DIVISAS
    d1, d2 = st.tabs(["💵 Principales", "🪙 Cripto"])
    with d1: grid({"🇪🇺 EUR/USD":"EURUSD=X", "🇬🇧 GBP/USD":"GBPUSD=X", "🇯🇵 USD/JPY":"JPY=X"}, "div_maj")
    with d2: grid({"₿ Bitcoin":"BTC-USD", "💎 Ethereum":"ETH-USD", "🐕 Doge":"DOGE-USD"}, "div_cry")

# --- 4. GRÁFICA (EMA NARANJA) ---
st.divider()
c_graf, c_sel = st.columns([8, 2])
with c_sel:
    franja = st.selectbox("Franja", ["1h", "6h", "12h", "1d", "2d", "3d", "4d"], index=3)
    config_map = {"1h":{"p":"1d","i":"1m"},"6h":{"p":"1d","i":"2m"},"12h":{"p":"1d","i":"5m"},"1d":{"p":"1d","i":"5m"},"2d":{"p":"2d","i":"15m"},"3d":{"p":"3d","i":"15m"},"4d":{"p":"5d","i":"30m"}}

df = obtener_datos(st.session_state.ticker_sel, config_map[franja]['p'], config_map[franja]['i'])
if not df.empty:
    df['EMA20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    res_act, sop_act = df['High'].tail(30).max(), df['Low'].tail(30).min()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    
    # EMA NARANJA RESALTADA
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='#FF8C00', width=2), name="EMA 20"), row=1, col=1)
    
    fig.add_hline(y=res_act, line_dash="dash", line_color="red", opacity=0.5, annotation_text="RES", row=1, col=1)
    fig.add_hline(y=sop_act, line_dash="dash", line_color="green", opacity=0.5, annotation_text="SOP", row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#6c71c4'), name="RSI"), row=2, col=1)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(plot_bgcolor='#1e212b', paper_bgcolor='#fdf6e3', height=500, xaxis_rangeslider_visible=False, margin=dict(t=5, b=5))
    st.plotly_chart(fig, use_container_width=True)

# --- 5. PLAN ESTRATÉGICO (FONDO SEMÁFORO) ---
if st.session_state.analisis_auto:
    st.subheader(f"🛡️ Estrategia: {st.session_state.activo_sel}")
    cols_ia = st.columns(3)
    res = st.session_state.analisis_auto
    for i, tag in enumerate(["intra", "medio", "largo"]):
        s = res[tag]
        # Colores dinámicos
        es_compra = "COMPRA" in s[1].upper()
        bg_color = "#e8f5e9" if es_compra else "#ffebee" if "VENTA" in s[1].upper() else "#ffffff"
        border_color = "#4caf50" if es_compra else "#f44336" if "VENTA" in s[1].upper() else "#ddd"
        
        with cols_ia[i]:
            st.markdown(f"""<div style="background-color:{bg_color}; padding:15px; border-radius:10px; border:2px solid {border_color}; height:185px;">
                <h4 style="text-align:center; color:#333; margin:0;">{tag.upper()} ({s[0]})</h4>
                <p style="text-align:center; font-weight:bold; font-size:1.1em; color:{border_color}; margin:5px;">{s[1]}</p>
                <p style="margin:2px;">📦 Lotes: {s[2]} | In: <b>{s[3]}</b></p>
                <p style="margin:2px;">🏁 TP: <span style="color:green; font-weight:bold;">{s[4]}</span> | 🛡️ SL: <span style="color:red; font-weight:bold;">{s[5]}</span></p>
                <p style="font-size:0.8em; color:grey;">Nominal: {s[6]} {res['moneda']}</p>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Ejecutar {tag.title()}", key=f"op_{tag}"):
                st.session_state.cartera_abierta.append({"id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel, "tipo": s[1], "lotes": s[2], "entrada": s[3], "tp": s[4], "sl": s[5], "valor_nominal": s[6], "ticker": st.session_state.ticker_sel, "moneda": res['moneda']})
                guardar_datos(st.session_state.cartera_abierta, CSV_FILE); st.rerun()

# --- 6. SIDEBAR (CARTERA + HISTÓRICO) ---
with st.sidebar:
    st.header("🏢 Terminal Jacar")
    st.metric("Balance Equity", f"{st.session_state.wallet:,.2f} €")
    tab_side = st.tabs(["💼 Abiertas", "📜 Histórico"])
    with tab_side[0]:
        for i, pos in enumerate(list(st.session_state.cartera_abierta)):
            with st.expander(f"📌 {pos['activo']} ({pos['tipo']})"):
                pnl = st.number_input("PnL (€)", key=f"pnl_{pos['id']}", value=0.0)
                if st.button("Cerrar", key=f"c_{pos['id']}", use_container_width=True):
                    st.session_state.historial.append({"fecha": datetime.now().strftime("%d/%m %H:%M"), "activo": pos['activo'], "pnl": pnl})
                    st.session_state.wallet += pnl; st.session_state.cartera_abierta.pop(i)
                    guardar_datos(st.session_state.cartera_abierta, CSV_FILE); guardar_datos(st.session_state.historial, HIST_FILE); st.rerun()
    with tab_side[1]:
        if st.session_state.historial:
            st.dataframe(pd.DataFrame(st.session_state.historial).iloc[::-1], hide_index=True)
            if st.button("Limpiar"): st.session_state.historial = []; guardar_datos([], HIST_FILE); st.rerun()
