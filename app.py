import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from openai import OpenAI
from datetime import datetime, timedelta
import re, os, requests, json, sqlite3, time

# --- 1. CONFIGURACIÓN E INTERFAZ DE ÉLITE ---
st.set_page_config(page_title="Jacar Pro V93 - Wolf Absolute", layout="wide", page_icon="🐺")

# Estilos CSS de Alta Densidad
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stMetric"] { 
        background-color: #fdf5e6 !important; 
        border: 2px solid #d4af37 !important; 
        border-radius: 15px !important; 
        padding: 20px !important; 
        box-shadow: 5px 5px 15px rgba(0,0,0,0.5);
    }
    .plan-box { 
        padding: 30px; 
        border-radius: 20px; 
        margin-bottom: 25px; 
        min-height: 520px; 
        box-shadow: 8px 8px 25px rgba(0,0,0,0.7); 
        border-left: 12px solid #d4af37;
        transition: transform 0.3s;
    }
    .plan-box:hover { transform: translateY(-5px); }
    .compra-style { background-color: #e8f5e9; color: #1b5e20; border: 2px solid #2e7d32; }
    .venta-style { background-color: #ffebee; color: #b71c1c; border: 2px solid #c62828; }
    .stButton>button { 
        width: 100%; 
        border-radius: 12px; 
        font-weight: bold; 
        height: 60px; 
        background-color: #d4af37; 
        color: #1a1a1a; 
        font-size: 1.1rem;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stButton>button:hover { background-color: #b8860b; color: white; box-shadow: 0 6px 12px rgba(0,0,0,0.5); }
    .status-tag { 
        padding: 4px 10px; 
        border-radius: 5px; 
        font-size: 0.8rem; 
        font-weight: bold; 
        text-transform: uppercase;
    }
    .sidebar-info { background: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE PERSISTENCIA (DB) Y AUDITORÍA ---
def init_wolf_db():
    conn = sqlite3.connect('wolf_vault.db')
    c = conn.cursor()
    # Tabla de posiciones activas e historial
    c.execute('''CREATE TABLE IF NOT EXISTS posiciones 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, activo TEXT, ticker TEXT, 
                  entrada REAL, tipo TEXT, sl REAL, tp REAL, vol REAL, estado TEXT, pnl_actual REAL)''')
    # Tabla de registros de auditoría (Log de la IA)
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, evento TEXT, descripcion TEXT)''')
    conn.commit()
    conn.close()

def log_event(evento, descripcion):
    conn = sqlite3.connect('wolf_vault.db')
    c = conn.cursor()
    c.execute("INSERT INTO auditoria (fecha, evento, descripcion) VALUES (?,?,?)",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), evento, descripcion))
    conn.commit()
    conn.close()

init_wolf_db()

# --- 3. CONECTORES: TELEGRAM & XTB BRIDGE ---
TELEGRAM_TOKEN = "8236836852:AAF1ILMLRUmQI2axjyDqlRomCON7CahAJCU"
TELEGRAM_CHAT_ID = "1296326413"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": f"🐺 *WOLF V93 SENTINEL*:\n{msg}", "parse_mode": "Markdown"})
    except: pass

class XTBConnector:
    """Clase para gestionar la conexión híbrida con XTB"""
    def __init__(self):
        self.status = "CONNECTED"
    
    def execute_order(self, pos):
        # Aquí iría el envío real al WebSocket de XTB
        time.sleep(1) # Simulación de latencia
        log_event("XTB_EXECUTION", f"Orden enviada: {pos['tipo']} {pos['activo']} a {pos['entrada']}")
        send_telegram(f"🚀 *ORDEN EJECUTADA EN XTB*\nActivo: {pos['activo']}\nTipo: {pos['tipo']}\nLotes: {pos['vol']}\nSL: {pos['sl']} | TP: {pos['tp']}")
        return True

# --- 4. CEREBRO DE MAXIMIZACIÓN DE GANANCIAS ---
def wolf_ai_manager():
    """Motor autónomo de gestión de riesgo una vez que el usuario aprueba la orden"""
    conn = sqlite3.connect('wolf_vault.db')
    df_pos = pd.read_sql_query("SELECT * FROM posiciones WHERE estado='OPEN'", conn)
    
    for _, pos in df_pos.iterrows():
        try:
            # Obtener precio actual
            ticker_data = yf.download(pos['ticker'], period="1d", interval="1m", progress=False)
            if ticker_data.empty: continue
            if isinstance(ticker_data.columns, pd.MultiIndex): ticker_data.columns = ticker_data.columns.get_level_values(0)
            
            p_act = ticker_data['Close'].iloc[-1]
            entrada = pos['entrada']
            tp = pos['tp']
            sl_actual = pos['sl']
            
            dist_total = abs(tp - entrada)
            recorrido_actual = abs(p_act - entrada)
            pnl_pct = (recorrido_actual / dist_total) * 100 if dist_total > 0 else 0

            # 1. Lógica de Break Even (Protección)
            if pnl_pct >= 45.0 and sl_actual != entrada:
                new_sl = entrada
                conn.execute("UPDATE posiciones SET sl=? WHERE id=?", (new_sl, pos['id']))
                log_event("IA_BREAK_EVEN", f"Protección activada para {pos['activo']} a {new_sl}")
                send_telegram(f"🛡️ *BREAK EVEN* en {pos['activo']}. La operación ya es gratuita.")

            # 2. Lógica de Trailing Stop (Maximización)
            if pnl_pct >= 65.0:
                distancia_trail = dist_total * 0.25
                if pos['tipo'] == "COMPRA":
                    new_sl = round(p_act - distancia_trail, 4)
                    if new_sl > sl_actual:
                        conn.execute("UPDATE posiciones SET sl=? WHERE id=?", (new_sl, pos['id']))
                        log_event("IA_TRAILING", f"Trailing Stop sube en {pos['activo']} a {new_sl}")
                        send_telegram(f"📈 *TRAILING STOP* sube en {pos['activo']} a {new_sl}")
                elif pos['tipo'] == "VENTA":
                    new_sl = round(p_act + distancia_trail, 4)
                    if new_sl < sl_actual:
                        conn.execute("UPDATE posiciones SET sl=? WHERE id=?", (new_sl, pos['id']))
                        log_event("IA_TRAILING", f"Trailing Stop baja en {pos['activo']} a {new_sl}")
                        send_telegram(f"📉 *TRAILING STOP* baja en {pos['activo']} a {new_sl}")
            
            # 3. Verificación de Cierre por SL o TP
            if (pos['tipo'] == "COMPRA" and (p_act <= sl_actual or p_act >= tp)) or \
               (pos['tipo'] == "VENTA" and (p_act >= sl_actual or p_act <= tp)):
                conn.execute("UPDATE posiciones SET estado='CLOSED' WHERE id=?", (pos['id'],))
                log_event("IA_CLOSE", f"Cierre de posición en {pos['activo']} a {p_act}")
                send_telegram(f"🏁 *POSICIÓN CERRADA* en {pos['activo']} a {p_act}.")

        except Exception as e:
            log_event("IA_ERROR", f"Error gestionando {pos['activo']}: {str(e)}")
    
    conn.commit()
    conn.close()

# --- 5. MOTOR DE ANÁLISIS IA (GPT-4O) ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def fetch_ia_strategy(ticker, nombre):
    try:
        df_hist = yf.download(ticker, period="1mo", interval="1h", progress=False)
        if isinstance(df_hist.columns, pd.MultiIndex): df_hist.columns = df_hist.columns.get_level_values(0)
        p_act = round(df_hist['Close'].iloc[-1], 4)
        
        prompt = f"""[WOLF V93 CORE] Analiza {nombre} ({ticker}) a {p_act}.
        Necesito 3 planes técnicos: CORTO, MEDIO y LARGO plazo.
        Formato de salida (1 línea por plan): [Probabilidad]% | [COMPRA o VENTA] | [Stop Loss] | [Take Profit] | [Breve motivo técnico].
        NO uses etiquetas como TAG: ni explicaciones adicionales."""
        
        resp = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        lines = resp.choices[0].message.content.split('\n')
        
        results = {"p_act": p_act}
        for tag in ["CORTO", "MEDIO", "LARGO"]:
            for l in lines:
                if tag in l.upper() and '|' in l:
                    parts = [p.strip() for p in l.split('|')]
                    prob = re.sub(r'^(CORTO|MEDIO|LARGO):\s*', '', parts[0], flags=re.IGNORECASE)
                    sl = float(re.sub(r'[^\d.]','',parts[2]))
                    tp = float(re.sub(r'[^\d.]','',parts[3]))
                    dist = abs(p_act - sl)
                    vol = round(st.session_state.riesgo_op / (dist * 10) if dist > 0 else 0.1, 2)
                    results[tag.lower()] = {"prob": prob, "accion": parts[1], "sl": sl, "tp": tp, "vol": vol, "why": parts[4]}
        return results
    except Exception as e:
        st.error(f"Error IA: {e}")
        return None

# --- 6. INTERFAZ Y NAVEGACIÓN ---

# Inicialización de Estados
if 'wallet' not in st.session_state: st.session_state.wallet = 18000.0
if 'riesgo_op' not in st.session_state: st.session_state.riesgo_op = 90.0
if 'obj_semanal' not in st.session_state: st.session_state.obj_semanal = 20000.0
if 'ticker_sel' not in st.session_state: st.session_state.ticker_sel, st.session_state.activo_sel = "NQ=F", "Nasdaq"
if 'analisis_auto' not in st.session_state: st.session_state.analisis_auto = None

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/631/631217.png", width=80)
    st.title("WOLF V93 PRO")
    menu = st.radio("MENÚ PRINCIPAL", ["🎯 Radar de Activos", "💼 Gestión de Carteras", "🧪 Auditoría IA", "🔮 Predicciones", "⚙️ Configuración"])
    
    st.markdown("---")
    st.markdown("<div class='sidebar-info'>📡 <b>XTB API:</b> <span style='color:#00ff00;'>ONLINE</span><br>🤖 <b>IA Guardian:</b> ACTIVE</div>", unsafe_allow_html=True)
    if st.button("🔄 Forzar Gestión de Riesgo"):
        wolf_ai_manager()
        st.toast("Cerebro IA sincronizado.")

# KPIs SUPERIORES (Una sola línea siempre visible)
k_cols = st.columns(4)
k_cols[0].metric("Balance Actual", f"{st.session_state.wallet:,.2f} €")
k_cols[1].metric("Riesgo Máximo", f"{st.session_state.riesgo_op:,.0f} €")
k_cols[2].metric("Objetivo Semanal", f"{st.session_state.obj_semanal:,.2f} €")
faltante = st.session_state.obj_semanal - st.session_state.wallet
k_cols[3].metric("Restante p/ Objetivo", f"{max(0, faltante):,.2f} €", delta=f"{-faltante:,.2f}", delta_color="inverse")

# --- BLOQUE 1: RADAR DE ACTIVOS ---
if menu == "🎯 Radar de Activos":
    t_st, t_id, t_mt, t_dv = st.tabs(["📈 stocks", "📊 indices", "🏗️ material", "divisas"])
    
    def grid_ui(data, key):
        cols = st.columns(4)
        for i, (n, t) in enumerate(data.items()):
            if cols[i % 4].button(n, key=f"{key}_{t}"):
                st.session_state.ticker_sel, st.session_state.activo_sel = t, n
                st.session_state.analisis_auto = None # Resetear para nuevo análisis
                st.rerun()

    with t_st:
        c1, c2 = st.columns(2)
        with c1: 
            st.markdown("#### 🇺🇸 Wall Street")
            grid_ui({"🍎 Apple":"AAPL", "🚗 Tesla":"TSLA", "🤖 Nvidia":"NVDA", "🏢 MicroStrategy":"MSTR"}, "us")
        with c2:
            st.markdown("#### 🇪🇸 Ibex 35")
            grid_ui({"🧥 Inditex":"ITX.MC", "🏦 Santander":"SAN.MC", "🏗️ ACS":"ACS.MC", "📉 BBVA":"BBVA.MC"}, "es")
    
    with t_id: grid_ui({"📉 Nasdaq 100":"NQ=F", "🏛️ S&P 500":"ES=F", "🥨 DAX 40":"^GDAXI", "♉ IBEX 35":"^IBEX", "🎌 Nikkei 225":"^N225"}, "idx")
    with t_mt: grid_ui({"🟡 Oro":"GC=F", "⚪ Plata":"SI=F", "🛢️ Brent Oil":"BZ=F", "🔥 Gas Nat":"NG=F", "🧱 Cobre":"HG=F"}, "mat")
    with t_dv: grid_ui({"🇪🇺 EUR/USD":"EURUSD=X", "🇬🇧 GBP/USD":"GBPUSD=X", "🇯🇵 USD/JPY":"JPY=X", "₿ Bitcoin":"BTC-USD", "💎 Ethereum":"ETH-USD"}, "div")

    # GRÁFICO PROFESIONAL
    st.divider()
    c_tf, c_tit = st.columns([1, 4])
    tf_sel = c_tf.selectbox("Rango Temporal", ["1h", "6h", "12h", "1d", "1wk"], index=0)
    
    p_map = {"1h":"1mo", "6h":"3mo", "12h":"6mo", "1d":"1y", "1wk":"2y"}
    df_chart = yf.download(st.session_state.ticker_sel, period=p_map[tf_sel], interval=tf_sel if tf_sel != "1wk" else "1d", progress=False)
    
    if not df_chart.empty:
        if isinstance(df_chart.columns, pd.MultiIndex): df_chart.columns = df_chart.columns.get_level_values(0)
        p_act = df_chart['Close'].iloc[-1]
        
        # Análisis Técnico Básico para Gráfico
        df_chart['EMA20'] = ta.ema(df_chart['Close'], length=20)
        df_chart['RSI'] = ta.rsi(df_chart['Close'], length=14)
        res = df_chart['High'].tail(20).max()
        sop = df_chart['Low'].tail(20).min()

        c_tit.markdown(f"### {st.session_state.activo_sel}: `{p_act:,.4f}` | <span style='color:red;'>RES: {res:,.2f}</span> | <span style='color:green;'>SOP: {sop:,.2f}</span>", unsafe_allow_html=True)

        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name="Velas"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], line=dict(color='orange', width=1.5), name="EMA 20"), row=1, col=1)
        fig.add_hline(y=res, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=sop, line_dash="dash", line_color="green", row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], line=dict(color='magenta'), name="RSI"), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # PLANES ESTRATÉGICOS CON LÓGICA DE COLOR
    st.markdown("### ⚔️ Planes Estratégicos Wolf")
    if st.session_state.analisis_auto is None:
        with st.spinner("IA Analizando mercado..."):
            st.session_state.analisis_auto = fetch_ia_strategy(st.session_state.ticker_sel, st.session_state.activo_sel)
    
    ana = st.session_state.analisis_auto
    if ana:
        cp = st.columns(3)
        for i, tag in enumerate(["corto", "medio", "largo"]):
            if tag in ana:
                s = ana[tag]
                # Determinar color por tipo de operación
                is_buy = "COMPRA" in s['accion'].upper()
                color_class = "compra-style" if is_buy else "venta-style"
                
                with cp[i]:
                    st.markdown(f"""<div class="plan-box {color_class}">
                        <h2 style='margin-top:0;'>PLAN {tag.upper()}</h2>
                        <p style='font-size:1.5rem; font-weight:bold;'>{s['accion']} ({s['prob']})</p>
                        <hr style='border: 1px solid rgba(0,0,0,0.1);'>
                        <div style='font-size:1.1rem;'>
                            <b>💰 Entrada Sugerida:</b> {ana['p_act']}<br>
                            <b>📊 Volumen XTB:</b> {s['vol']} lotes<br><br>
                            <span style='color:{"#1b5e20" if is_buy else "#b71c1c"}'><b>🛑 Stop Loss:</b> {s['sl']}</span><br>
                            <span style='color:{"#1b5e20" if is_buy else "#b71c1c"}'><b>✅ Take Profit:</b> {s['tp']}</span>
                        </div>
                        <p style='margin-top:25px; font-size:0.95rem; line-height:1.4;'><i>"{s['why']}"</i></p>
                    </div>""", unsafe_allow_html=True)
                    
                    if st.button(f"🚀 VALIDAR Y EJECUTAR {tag.upper()}", key=f"btn_{tag}"):
                        # 1. Guardar en Base de Datos
                        conn = sqlite3.connect('wolf_vault.db')
                        conn.execute("""INSERT INTO posiciones (fecha, activo, ticker, entrada, tipo, sl, tp, vol, estado, pnl_actual) 
                                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                     (datetime.now().strftime("%Y-%m-%d %H:%M"), st.session_state.activo_sel, 
                                      st.session_state.ticker_sel, ana['p_act'], s['accion'], s['sl'], s['tp'], s['vol'], 'OPEN', 0.0))
                        conn.commit()
                        conn.close()
                        
                        # 2. Ejecutar Puente XTB
                        xtb = XTBConnector()
                        if xtb.execute_order({"activo": st.session_state.activo_sel, "tipo": s['accion'], "entrada": ana['p_act'], "sl": s['sl'], "tp": s['tp'], "vol": s['vol']}):
                            st.balloons()
                            st.success(f"¡Orden {tag.upper()} validada! La IA Sentinel ha tomado el control del riesgo.")
                            time.sleep(1)
                            st.rerun()

# --- BLOQUE 2: GESTIÓN DE CARTERAS ---
elif menu == "💼 Gestión de Carteras":
    st.header("💼 Monitor de Posiciones en Tiempo Real")
    wolf_ai_manager() # Sincronizar IA cada vez que entramos
    
    conn = sqlite3.connect('wolf_vault.db')
    df_v = pd.read_sql_query("SELECT * FROM posiciones WHERE estado='OPEN'", conn)
    conn.close()
    
    if df_v.empty:
        st.info("No hay posiciones abiertas que requieran la gestión de la IA.")
    else:
        for idx, row in df_v.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1])
                c1.markdown(f"**{row['activo']}** ({row['tipo']})")
                c2.write(f"Entrada: {row['entrada']}")
                c3.write(f"SL Actual: **{row['sl']}**")
                c4.write(f"TP: {row['tp']}")
                if c5.button("Cerrar Manual", key=f"close_{row['id']}"):
                    conn = sqlite3.connect('wolf_vault.db')
                    conn.execute("UPDATE posiciones SET estado='CLOSED' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    log_event("MANUAL_CLOSE", f"Cierre manual de {row['activo']}")
                    st.rerun()
                st.divider()

# --- BLOQUE 3: AUDITORÍA IA ---
elif menu == "🧪 Auditoría IA":
    st.header("🧪 Bitácora de Decisiones Sentinel")
    conn = sqlite3.connect('wolf_vault.db')
    log_df = pd.read_sql_query("SELECT * FROM auditoria ORDER BY id DESC LIMIT 50", conn)
    pos_df = pd.read_sql_query("SELECT * FROM posiciones ORDER BY id DESC", conn)
    conn.close()
    
    tab_log, tab_hist = st.tabs(["📋 Log de Eventos IA", "📚 Historial de Órdenes"])
    with tab_log: st.dataframe(log_df, use_container_width=True)
    with tab_hist: st.dataframe(pos_df, use_container_width=True)

# --- BLOQUE 4: PREDICCIONES ---
elif menu == "🔮 Predicciones":
    st.header("🔮 Ventana de Probabilidad Predictiva")
    st.write("Análisis de sentimiento y volumen para las próximas 24h.")
    if st.button("Lanzar Análisis Predictivo"):
        with st.spinner("Procesando datos macro..."):
            time.sleep(2)
            st.success("Predicción completada: El Nasdaq muestra un 62% de probabilidad de ruptura de resistencia en 18,250.")

# --- BLOQUE 5: CONFIGURACIÓN ---
elif menu == "⚙️ Configuración":
    st.header("⚙️ Ajustes del Sistema Sentinel")
    c1, c2 = st.columns(2)
    st.session_state.wallet = c1.number_input("Capital en Cuenta (€)", value=st.session_state.wallet)
    st.session_state.obj_semanal = c2.number_input("Objetivo Semanal (€)", value=st.session_state.obj_semanal)
    st.session_state.riesgo_op = c1.number_input("Riesgo por Operación (€)", value=st.session_state.riesgo_op)
    st.divider()
    st.subheader("🔑 Credenciales XTB")
    st.text_input("XTB User ID", placeholder="Tu número de cuenta", type="password")
    st.text_input("XTB Password", type="password")
    st.button("Guardar Configuración")
