import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from openai import OpenAI
from datetime import datetime

# 1. CONFIGURACIÓN E INICIO (Puntos 5 y 8)
st.set_page_config(page_title="Jacar Pro Terminal", layout="wide")

# Inicializar estados de memoria (Para que no se borren al interactuar)
if 'wallet' not in st.session_state:
    st.session_state.wallet = 18000.0
if 'historial' not in st.session_state:
    st.session_state.historial = []

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 2. PANEL LATERAL (Puntos 5, 8, 9, 10)
with st.sidebar:
    st.title(f"💰 Balance: {st.session_state.wallet:,.2f} USD")
    st.divider()
    st.header("⚙️ Estrategia")
    obj_diario = st.number_input("Objetivo Diario ($)", value=200.0)
    perfil = st.radio("Frecuencia (Punto 9)", ["Scalping (Muchas/Poco)", "Swing (Pocas/Mucho)"])
    tf_visual = st.selectbox("Temporalidad (Punto 10)", ["1m", "5m", "15m", "1h", "1d"], index=2)
    
    st.divider()
    activos = {"Oro": "GC=F", "Nasdaq": "^IXIC", "EUR/USD": "EURUSD=X", "Brent": "BZ=F", "Bitcoin": "BTC-USD"}
    seleccion = st.selectbox("Activo a analizar", list(activos.keys()))

# 3. OBTENCIÓN Y ANÁLISIS DE DATOS (Puntos 2, 6, 7 corregidos)
ticker = activos[seleccion]

# Lógica de ajuste automático de temporalidad
ajuste_temporal = {
    "1m": "1d",    # Si quieres velas de 1m, bajamos solo 1 día
    "5m": "5d",    # Si quieres velas de 5m, bajamos 5 días
    "15m": "5d",
    "1h": "1mo",   # Si quieres velas de 1h, bajamos 1 mes
    "1d": "max"    # Si quieres velas diarias, bajamos todo el historial
}

periodo_ajustado = ajuste_temporal.get(tf_visual, "5d")

# Descarga con el ajuste dinámico
df = yf.download(ticker, period=periodo_ajustado, interval=tf_visual)

if isinstance(df.columns, pd.MultiIndex): 
    df.columns = df.columns.get_level_values(0)

df = df.dropna()

if not df.empty:
    # Recalcular indicadores con los nuevos datos
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # Soportes y resistencias basados en la temporalidad visible
    resistencia = float(df['High'].tail(40).max())
    soporte = float(df['Low'].tail(40).min())
    precio_act = float(df['Close'].iloc[-1])

    # 4. PANEL DE OPORTUNIDADES (Punto 1)
    st.subheader("🚀 Monitor de Oportunidades")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Precio {seleccion}", f"{precio_act:.4f}")
    c2.metric("RSI (Fuerza)", f"{df['RSI'].iloc[-1]:.2f}")
    c3.metric("Resistencia", f"{resistencia:.4f}")
    c4.metric("Soporte", f"{soporte:.4f}")

 # 5. GRÁFICO PROFESIONAL CON VOLUMEN Y AUTO-AJUSTE (Puntos 10 y 11)
    from plotly.subplots import make_subplots

    # Creamos un gráfico con dos filas: una para velas (80% espacio) y otra para volumen (20%)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'Velas {tf_visual}', 'Volumen'), 
                        row_width=[0.2, 0.8])

    # Añadir Velas Japonesas
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name="Precio"
    ), row=1, col=1)

    # Añadir Barras de Volumen
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volumen", marker_color='rgba(100,100,100,0.5)'), row=2, col=1)

    # Dibujar líneas de Soporte/Resistencia (Punto 11)
    fig.add_hline(y=resistencia, line_dash="dash", line_color="cyan", opacity=0.3, annotation_text="Resistencia", row=1, col=1)
    fig.add_hline(y=soporte, line_dash="dash", line_color="orange", opacity=0.3, annotation_text="Soporte", row=1, col=1)

    # --- EL TRUCO DEL AUTO-AJUSTE ---
    fig.update_layout(
        template="plotly_dark",
        height=700,
        xaxis_rangeslider_visible=False,
        showlegend=False,
        margin=dict(l=10, r=50, t=30, b=10)
    )

    # Forzar el zoom en el eje Y del gráfico de velas
    fig.update_yaxes(autorange=True, fixedrange=False, side="right", row=1, col=1)
    # Eje Y del volumen más discreto
    fig.update_yaxes(showticklabels=False, row=2, col=1)

    # --- DIBUJO TÉCNICO DE LA ORDEN (Punto 11) ---
    if 'trade_coords' in st.session_state:
        tc = st.session_state.trade_coords
        # Color verde para compra, rojo para venta
        color_zona = "rgba(0, 255, 0, 0.2)" if "COMPRA" in tc['tipo'].upper() else "rgba(255, 0, 0, 0.2)"
        
        # Dibujar área proyectada de beneficio
        fig.add_hrect(y0=tc['entrada'], y1=tc['tp'], fillcolor=color_zona, line_width=0, layer="below", row=1, col=1)
        # Dibujar línea de Stop Loss
        fig.add_hline(y=tc['sl'], line_color="red", line_width=2, line_dash="dash", row=1, col=1)
        # Dibujar línea de Entrada
        fig.add_hline(y=tc['entrada'], line_color="white", line_width=1, row=1, col=1)
        
    st.plotly_chart(fig, use_container_width=True)
    
   El error ocurre porque la IA, al intentar ser "creativa", a veces añade una introducción o pequeñas variaciones en el texto (como "Aquí tienes tu orden:") y eso rompe el sistema de lectura que instalamos.

Para que no vuelva a fallar, vamos a hacer que el sistema de lectura sea mucho más "flexible" (que busque las palabras clave sin importar dónde estén) y, sobre todo, que siempre te muestre el texto de la IA, incluso si no puede dibujarlo.

🛠️ Paso 1: Sustituye la SECCIÓN 6 por este bloque "Inmune a Errores"
He rediseñado el lector para que sea mucho más inteligente y robusto. Sustituye todo el bloque del botón por este:

Python
    # 6. GENERACIÓN DE ORDEN Y EXTRACCIÓN FLEXIBLE
    if st.button("🧠 ANALIZAR Y GENERAR ORDEN"):
        with st.spinner('IA analizando tendencia y calculando niveles...'):
            prompt = f"""
            Actúa como un TRADER EJECUTOR.
            ACTIVO: {seleccion} a {precio_act:.4f}. RSI: {df['RSI'].iloc[-1]:.2f}.
            Contexto: Max {resistencia}, Min {soporte}. Estilo: {perfil}.
            
            DEBES incluir estas etiquetas exactamente en tu respuesta:
            ACCIÓN: [COMPRA o VENTA]
            ENTRADA: [Precio]
            SL: [Precio]
            TP: [Precio]
            LOTES: [Cantidad]
            MOTIVO: [Breve frase]
            """
            
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Eres un ejecutor de trading preciso. Solo proporcionas órdenes directas."},
                          {"role": "user", "content": prompt}]
            )
            
            respuesta = resp.choices[0].message.content
            st.session_state.ultima_orden = respuesta # Guardamos siempre el texto
            
            # --- Lector Flexible de Datos ---
            try:
                lineas = respuesta.upper().split('\n')
                datos_ext = {}
                for l in lineas:
                    if ':' in l:
                        clave = l.split(':')[0].strip()
                        valor = l.split(':')[1].strip()
                        datos_ext[clave] = valor

                # Extraemos los números limpiando símbolos como USD o puntos finales
                def limpiar_num(texto):
                    return float(''.join(c for c in texto if c.isdigit() or c == '.'))

                st.session_state.trade_coords = {
                    "entrada": limpiar_num(datos_ext.get('ENTRADA', str(precio_act))),
                    "sl": limpiar_num(datos_ext.get('SL', '0')),
                    "tp": limpiar_num(datos_ext.get('TP', '0')),
                    "tipo": datos_ext.get('ACCIÓN', 'ESPERAR')
                }
                st.rerun() 
            except Exception as e:
                # Si falla el dibujo, al menos mostramos el error técnico en consola
                print(f"Error de lectura visual: {e}")

    # MOSTRAR SIEMPRE LA ORDEN (Fuera del botón para que no desaparezca)
    if 'ultima_orden' in st.session_state:
        st.markdown("---")
        st.subheader("📋 Orden de Ejecución")
        st.info(st.session_state.ultima_orden)
        
    # 7. RESUMEN SEMANAL/MENSUAL (Punto 4)
    st.divider()
    st.subheader("📊 Historial de Operaciones")
    if st.session_state.historial:
        st.table(pd.DataFrame(st.session_state.historial))
    else:
        st.write("No hay operaciones registradas este mes.")
else:
    st.warning("No hay datos disponibles. Verifica la conexión o el mercado.")
