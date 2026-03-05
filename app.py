import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime
import os

# --- 1. CONFIGURACIÓN Y PERSISTENCIA ---
st.set_page_config(page_title="Jacar Pro V47", layout="wide", page_icon="🏦")

CSV_FILE = 'cartera_jacar.csv'
HIST_FILE = 'historial_jacar.csv'

def guardar_datos(lista, archivo):
    if lista: pd.DataFrame(lista).to_csv(archivo, index=False)
    elif os.path.exists(archivo): 
        try: os.remove(archivo)
        except: pass

def cargar_datos(archivo):
    if os.path.exists(archivo):
        try: return pd.read_csv(archivo).to_dict('records')
        except: return []
    return []

# Inicialización de estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'activo_sel' not in st.session_state: st.session_state.activo_sel, st.session_state.ticker_sel = "US100", "NQ=F"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. MOTOR DE CÁLCULO DE CUENTA (RIESGO Y MARGEN) ---
def calcular_metricas():
    # Estimamos el valor nominal total de las posiciones abiertas
    # Margen requerido: 5% del nominal (Apalancamiento 1:20)
    nominal_total = 0
    for p in st.session_state.cartera_abierta:
        try: nominal_total += float(p.get('valor_nominal', 0))
        except: pass
    
    margen_usado = nominal_total * 0.05
    margen_disponible = st.session_state.wallet - margen_usado
    
    # Win Rate e Historial
    win_rate = 50.0
    if st.session_state.historial:
        ganadas = len([h for h in st.session_state.historial if float(h['pnl']) > 0])
        win_rate = (ganadas / len(st.session_state.historial)) * 100
    
    return margen_usado, margen_disponible, win_rate

m_usado, m_disponible, wr_actual = calcular_metricas()

# --- 3. MOTOR DE DATOS E IA ---
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
        p_actual = float(df_t['Close'].iloc[-1])
        moneda = "€" if any(x in t for x in [".MC", "GDAXI", "IBEX"]) else "$"

        prompt = f"""Analiza {n} a {p_actual}. WinRate actual: {wr_actual:.1f}%.
        Responde estrictamente en este formato (3 líneas):
        INTRA: Probabilidad% | Accion | Lotes | Entrada | TP | SL | Nominal
        MEDIO: Probabilidad% | Accion | Lotes | Entrada | TP | SL | Nominal
        LARGO: Probabilidad% | Accion | Lotes | Entrada | TP | SL | Nominal"""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0)
        res_ia = resp.choices[0].message.content
        
        def extraer(tag):
            for line in res_ia.split('\n'):
                if tag in line.upper():
                    parts = line.replace('*','').split(':')[-1].split('|')
                    if len(parts) >= 7: return [p.strip() for p in parts]
            return ["---", "ESPERAR", "0.10", str(p_actual), "0", "0", "0"]

        return {"intra": extraer("INTRA"), "medio": extraer("MEDIO"), "largo": extraer("LARGO"), "moneda": moneda, "p_actual": p_actual}
    except: return None

# --- 4. INTERFAZ: CABECERA Y CATEGORÍAS ---
st.markdown(f"""
    <div style="background-color:#1e212b; padding:15px; border-radius:10px; color:white; border-left: 5px solid #268bd2;">
        <span style="font-size:1.2em;">💰 <b>Margen Disponible: {m_disponible:,.2f} €</b></span> 
        <span style="margin-left:30px; color:#00ff00;">🎯 WinRate: {wr_actual:.1f}%</span>
        <span style="margin-left:30px; color:#ff8c00;">⚠️ Margen Usado: {m_usado:,.2f} €</span>
    </div>
""", unsafe_allow_html=True)

t_main = st.tabs(["📈 Stocks", "📊 Indices", "🏗️ Material", "💱 Divisas"])

def grid(d, prefix=""):
    cols = st.columns(4)
    for i, (n, t) in enumerate(d.items()):
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
    i1, i2 = st.tabs(["🇺🇸 EE.UU", "🇪🇺 Europa"])
    with i1: grid({"🇺🇸 US100":"NQ=F", "📈 S&P 500":"ES=F", "🏭 Dow Jones":"YM=F"}, "idx_usa")
    with i2: grid({"🇩🇪 DAX 40":"^GDAXI", "🇪🇸 IBEX 35":"^IBEX", "🇫🇷 CAC 40":"^FCHI"}, "idx_eu")

with t_main[2]: # MATERIAL
    grid({"🥇 Oro":"GC=F", "🥈 Plata":"SI=F", "🛢️ Brent":"BZ=F", "🛢️ WTI":"CL=F", "🔥 Gas Nat":"NG=F"}, "mat")

with t_main[3]: # DIVISAS (Divisas)
    grid({"🇪🇺 EUR/USD":"EURUSD=X", "🇬🇧 GBP/USD":"GBPUSD=X", "🇯🇵 USD/JPY":"JPY=X", "₿ Bitcoin":"BTC-USD", "💎 Ethereum":"ETH-USD"}, "div")

# --- 5. GRÁFICO Y MÉTRICAS SUPERIORES ---
st.divider()
df = obtener_datos(st.session_state.ticker_sel, "5d", "15m")
if not df.empty:
    p_actual = df['Close'].iloc[-1]
    # Métricas de cabecera de gráfico
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Precio", f"{p_actual:,.2f}")
    m2.metric("Máximo", f"{df['High'].max():,.2f}")
    m3.metric("Mínimo", f"{df['Low'].min():,.2f}")
    m4.metric("Soporte", f"{df['Low'].tail(30).min():,.2f}")
    m5.metric("Resist.", f"{df['High'].tail(30).max():,.2f}")
    m6.metric("ATR", f"{ta.atr(df['High'], df['Low'], df['Close']).iloc[-1]:,.2f}")

    # Gráfico con Volumen Color-Coded
    df['VolColor'] = ['#00c805' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ff3b30' for i in range(len(df))]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=df['VolColor'], name="Volumen"), row=2, col=1)
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)

# --- 6. PLAN ESTRATÉGICO CON EJECUCIÓN MANUAL ---
if st.session_state.analisis_auto:
    st.subheader(f"🛡️ Plan Estratégico: {st.session_state.activo_sel}")
    res = st.session_state.analisis_auto
    cols_ia = st.columns(3)
    
    for i, tag in enumerate(["intra", "medio", "largo"]):
        s = res[tag]
        es_compra = "COMPRA" in s[1].upper()
        bg_color = "#e8f5e9" if es_compra else "#ffebee"
        border_color = "#4caf50" if es_compra else "#f44336"

        with cols_ia[i]:
            st.markdown(f"""
                <div style="background-color:{bg_color}; padding:15px; border-radius:12px; border:2px solid {border_color}; min-height:180px;">
                    <h4 style="margin:0;">{tag.upper()} <span style="float:right; color:blue;">🎯 {s[0]}</span></h4>
                    <p style="text-align:center; font-weight:bold; font-size:1.2em; color:#333; margin:10px 0;">{s[1]}</p>
                    <p style="font-size:0.9em; margin:2px;">In Sugerido: <b>{s[3]}</b> | Lotes: <b>{s[2]}</b></p>
                    <p style="font-size:0.8em; color:grey;">Riesgo sugerido según WinRate: {(wr_actual/100)*2:.1f}%</p>
                </div>
            """, unsafe_allow_html=True)
            
            with st.popover(f"🚀 Ejecutar {tag.upper()}", use_container_width=True):
                lotes_final = st.number_input("Ajustar Lotes", value=float(s[2]), step=0.01, key=f"l_{tag}")
                precio_final = st.number_input("Precio Entrada Real", value=float(s[3]), key=f"p_{tag}")
                if st.button("Confirmar Operación", key=f"conf_{tag}", use_container_width=True):
                    # Valor nominal = Lotes * Precio (Simplificado)
                    val_nominal = lotes_final * precio_final
                    st.session_state.cartera_abierta.append({
                        "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                        "tipo": s[1], "lotes": lotes_final, "entrada": precio_final, "tp": s[4], "sl": s[5], 
                        "valor_nominal": val_nominal, "ticker": st.session_state.ticker_sel, "moneda": res['moneda']
                    })
                    guardar_datos(st.session_state.cartera_abierta, CSV_FILE)
                    st.rerun()

# --- 7. SIDEBAR: TERMINAL Y CIERRE ---
with st.sidebar:
    st.header("🏢 Terminal Jacar")
    st.metric("Balance Equity", f"{st.session_state.wallet:,.2f} €")
    st.divider()
    
    tab_side = st.tabs(["💼 Abiertas", "📜 Histórico"])
    
    with tab_side[0]:
        # Balance de operaciones en curso
        pnl_total_curso = 0
        for i, pos in enumerate(list(st.session_state.cartera_abierta)):
            with st.expander(f"📌 {pos['activo']} ({pos['lotes']} L)"):
                p_cierre_real = st.number_input("Precio Cierre", value=float(pos['entrada']), key=f"out_{pos['id']}")
                
                # Cálculo PnL Real
                es_buy = "COMPRA" in pos['tipo'].upper()
                pnl_op = (p_cierre_real - pos['entrada']) * pos['lotes'] * 100 if es_buy else (pos['entrada'] - p_cierre_real) * pos['lotes'] * 100
                pnl_total_curso += pnl_op
                
                st.write(f"PnL: **{pnl_op:,.2f} {pos.get('moneda', '€')}**")
                if st.button("Cerrar Posición", key=f"close_{pos['id']}", use_container_width=True):
                    st.session_state.historial.append({"fecha": datetime.now().strftime("%d/%m %H:%M"), "activo": pos['activo'], "pnl": pnl_op})
                    st.session_state.wallet += pnl_op
                    st.session_state.cartera_abierta.pop(i)
                    guardar_datos(st.session_state.cartera_abierta, CSV_FILE); guardar_datos(st.session_state.historial, HIST_FILE)
                    st.rerun()
        
        st.markdown(f"**PnL Total en Curso:** `{pnl_total_curso:,.2f} €`")

    with tab_side[1]:
        if st.session_state.historial:
            st.dataframe(pd.DataFrame(st.session_state.historial).iloc[::-1], hide_index=True)
            if st.button("Limpiar Historial"): 
                st.session_state.historial = []; guardar_datos([], HIST_FILE); st.rerun()
