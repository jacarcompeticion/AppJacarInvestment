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
st.set_page_config(page_title="Jacar Pro V52", layout="wide", page_icon="🏦")

CSV_FILE = 'cartera_jacar.csv'
HIST_FILE = 'historial_jacar.csv'

def limpiar_numero(valor):
    if isinstance(valor, (int, float)): return float(valor)
    clean = re.sub(r'[^\d.]', '', str(valor).replace(',', '.'))
    try: return float(clean) if clean else 0.0
    except: return 0.0

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

if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'cartera_abierta' not in st.session_state: st.session_state.cartera_abierta = cargar_datos(CSV_FILE)
if 'historial' not in st.session_state: st.session_state.historial = cargar_datos(HIST_FILE)
if 'activo_sel' not in st.session_state: st.session_state.activo_sel, st.session_state.ticker_sel = "US100", "NQ=F"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- 2. CÁLCULOS DE CUENTA ---
def calcular_metricas():
    nominal_total = 0
    for p in st.session_state.cartera_abierta:
        nominal_total += limpiar_numero(p.get('valor_nominal', 0))
    margen_usado = nominal_total * 0.05
    margen_disponible = float(st.session_state.wallet) - margen_usado
    win_rate = 50.0
    if st.session_state.historial:
        try:
            ganadas = len([h for h in st.session_state.historial if limpiar_numero(h['pnl']) > 0])
            win_rate = (ganadas / len(st.session_state.historial)) * 100
        except: pass
    return margen_usado, margen_disponible, win_rate

m_usado, m_disponible, wr_actual = calcular_metricas()

# --- 3. MOTOR DE DATOS E IA ---
@st.cache_data(ttl=60)
def obtener_datos(ticker, periodo, intervalo):
    try:
        df = yf.download(ticker, period=periodo, interval=intervalo, progress=False)
        if df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        # Cálculo de Indicadores
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df
    except: return pd.DataFrame()

def auto_analizar(t, n):
    try:
        df_t = obtener_datos(t, "5d", "15m")
        if df_t.empty: return None
        p_act = round(float(df_t['Close'].iloc[-1]), 2)
        moneda = "€" if any(x in t for x in [".MC", "GDAXI", "IBEX"]) else "$"

        prompt = f"""Analiza {n} (Ticker: {t}) con precio actual {p_act}. 
        Dirección clara (COMPRA o VENTA). 
        Calcula Take Profit y Stop Loss realistas.
        Responde EXACTAMENTE con 3 líneas:
        INTRA: [Probabilidad]% | [ACCION] | [Lotes] | {p_act} | [Take Profit] | [Stop Loss] | [Nominal]
        MEDIO: [Probabilidad]% | [ACCION] | [Lotes] | {p_act} | [Take Profit] | [Stop Loss] | [Nominal]
        LARGO: [Probabilidad]% | [ACCION] | [Lotes] | {p_act} | [Take Profit] | [Stop Loss] | [Nominal]"""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.5)
        lineas = resp.choices[0].message.content.split('\n')
        
        data_final = {"moneda": moneda, "p_actual": p_act}
        for tag in ["INTRA", "MEDIO", "LARGO"]:
            linea_encontrada = False
            for line in lineas:
                if tag in line.upper() and '|' in line:
                    parts = [p.strip().replace('*','').replace('[','').replace(']','') for p in line.split('|')]
                    parts[0] = parts[0].split(':')[-1].strip()
                    if len(parts) >= 6:
                        data_final[tag.lower()] = parts
                        linea_encontrada = True
                        break
            if not linea_encontrada:
                data_final[tag.lower()] = ["65%", "COMPRA", "0.10", str(p_act), str(round(p_act*1.03,2)), str(round(p_act*0.97,2)), "0"]
        return data_final
    except: return None

# --- 4. INTERFAZ: CATEGORÍAS ---
st.markdown(f"""<div style="background-color:#1e212b; padding:15px; border-radius:10px; color:white; border-left: 5px solid #268bd2;">
    💰 <b>Margen Disponible: {m_disponible:,.2f} €</b> | 🎯 WinRate: {wr_actual:.1f}% | ⚠️ Usado: {m_usado:,.2f} €
</div>""", unsafe_allow_html=True)

t_main = st.tabs(["📈 Stocks", "📊 Indices", "🏗️ Material", "💱 Divisas"])

def grid(d, pref=""):
    cols = st.columns(4)
    for i, (n, t) in enumerate(d.items()):
        if cols[i % 4].button(n, key=f"{pref}_{t}", use_container_width=True):
            st.session_state.activo_sel, st.session_state.ticker_sel = n, t
            st.session_state.analisis_auto = auto_analizar(t, n)
            st.rerun()

with t_main[0]: # STOCKS
    s1, s2, s3, s4, s5, s6 = st.tabs(["🔥 High Alpha", "💻 Tecnología", "⛽ Energía", "🏦 Banca", "🛒 Consumo", "🇪🇸 España"])
    with s1: grid({"🚀 MSTR":"MSTR", "🪙 COIN":"COIN", "🧠 PLTR":"PLTR", "⚡ SMCI":"SMCI", "🧬 LLY":"LLY", "🖥️ AMD":"AMD", "🛰️ TSLA":"TSLA", "💳 ADYEN":"ADYEN.AS", "💉 MRNA":"MRNA", "🕹️ RBLX":"RBLX"}, "alpha")
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

# --- 5. GRÁFICO TÉCNICO AVANZADO ---
st.divider()
df = obtener_datos(st.session_state.ticker_sel, "5d", "15m")
if not df.empty:
    p_actual = df['Close'].iloc[-1]
    soporte_val = df['Low'].tail(30).min()
    resistencia_val = df['High'].tail(30).max()

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Precio", f"{p_actual:,.2f}")
    m2.metric("EMA 20", f"{df['EMA_20'].iloc[-1]:,.2f}")
    m3.metric("RSI", f"{df['RSI'].iloc[-1]:,.2f}")
    m4.metric("Soporte", f"{soporte_val:,.2f}")
    m5.metric("Resist.", f"{resistencia_val:,.2f}")
    m6.metric("ATR", f"{ta.atr(df['High'], df['Low'], df['Close']).iloc[-1]:,.2f}")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    
    # Velas y Media Móvil (EMA)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='royalblue', width=1.5), name="EMA 20"), row=1, col=1)
    
    # Líneas de Soporte y Resistencia
    fig.add_hline(y=resistencia_val, line_dash="dash", line_color="red", annotation_text="Resistencia", row=1, col=1)
    fig.add_hline(y=soporte_val, line_dash="dash", line_color="green", annotation_text="Soporte", row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.5), name="RSI (14)"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)

    fig.update_layout(height=600, xaxis_rangeslider_visible=False, template="plotly_white", margin=dict(t=5,b=5))
    st.plotly_chart(fig, use_container_width=True)

# --- 6. ESTRATEGIAS ---
if st.session_state.analisis_auto:
    st.subheader(f"🛡️ Plan Estratégico: {st.session_state.activo_sel}")
    res = st.session_state.analisis_auto
    cols_ia = st.columns(3)
    for i, tag in enumerate(["intra", "medio", "largo"]):
        s = res[tag]
        es_compra = "COMPRA" in s[1].upper()
        bg, b_col = ("#e8f5e9", "#4caf50") if es_compra else ("#ffebee", "#f44336")
        ent_vis, tp_vis, sl_vis = round(limpiar_numero(s[3]), 2), round(limpiar_numero(s[4]), 2), round(limpiar_numero(s[5]), 2)
        with cols_ia[i]:
            st.markdown(f"""<div style="background-color:{bg}; padding:15px; border-radius:12px; border:2px solid {b_col}; min-height:220px;">
                <h4 style="margin:0;">{tag.upper()} <span style="float:right; color:#1a73e8;">🎯 {s[0]}</span></h4>
                <p style="text-align:center; font-weight:bold; font-size:1.3em; color:#333; margin:12px 0;">{s[1]}</p>
                <p style="margin:2px;">Entrada: <b>{ent_vis}</b> | Lotes: <b>{s[2]}</b></p>
                <p style="margin:2px; color:#2e7d32;"><b>Take Profit:</b> {tp_vis}</p>
                <p style="margin:2px; color:#c62828;"><b>Stop Loss:</b> {sl_vis}</p>
            </div>""", unsafe_allow_html=True)
            with st.popover(f"🚀 Ejecutar {tag.upper()}", use_container_width=True):
                l_f = st.number_input("Lotes", value=limpiar_numero(s[2]), step=0.01, key=f"l_{tag}")
                p_f = st.number_input("Entrada", value=ent_vis, key=f"p_{tag}")
                if st.button("Confirmar", key=f"conf_{tag}", use_container_width=True):
                    st.session_state.cartera_abierta.append({
                        "id": datetime.now().strftime("%H%M%S"), "activo": st.session_state.activo_sel,
                        "tipo": s[1], "lotes": l_f, "entrada": p_f, "tp": tp_vis, "sl": sl_vis, 
                        "valor_nominal": l_f * p_f, "ticker": st.session_state.ticker_sel, "moneda": res['moneda']
                    })
                    guardar_datos(st.session_state.cartera_abierta, CSV_FILE); st.rerun()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.header("🏢 Terminal Jacar")
    st.metric("Balance Equity", f"{st.session_state.wallet:,.2f} €")
    st.divider()
    tab_side = st.tabs(["💼 Abiertas", "📜 Histórico"])
    with tab_side[0]:
        pnl_total_curso = 0
        for i, pos in enumerate(list(st.session_state.cartera_abierta)):
            with st.expander(f"📌 {pos['activo']} ({pos['lotes']} L)"):
                ent_v, lot_v = limpiar_numero(pos['entrada']), limpiar_numero(pos['lotes'])
                p_out = st.number_input("Precio Cierre", value=ent_v, key=f"out_{pos['id']}", format="%.2f")
                es_buy = "COMPRA" in str(pos['tipo']).upper()
                pnl_op = (p_out - ent_v) * lot_v * 100 if es_buy else (ent_v - p_out) * lot_v * 100
                pnl_total_curso += pnl_op
                st.write(f"PnL: **{pnl_op:,.2f} €**")
                if st.button("Cerrar", key=f"close_{pos['id']}", use_container_width=True):
                    st.session_state.historial.append({"fecha": datetime.now().strftime("%d/%m %H:%M"), "activo": pos['activo'], "pnl": pnl_op})
                    st.session_state.wallet = float(st.session_state.wallet) + pnl_op
                    st.session_state.cartera_abierta.pop(i)
                    guardar_datos(st.session_state.cartera_abierta, CSV_FILE); guardar_datos(st.session_state.historial, HIST_FILE); st.rerun()
        st.markdown(f"**PnL en Curso:** `{pnl_total_curso:,.2f} €`")
    with tab_side[1]:
        if st.session_state.historial:
            st.dataframe(pd.DataFrame(st.session_state.historial).iloc[::-1], hide_index=True)
            if st.button("Limpiar Historial"): 
                st.session_state.historial = []; guardar_datos([], HIST_FILE); st.rerun()
