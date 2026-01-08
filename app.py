import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
import requests
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURACIÓN E INFRAESTRUCTURA
st.set_page_config(page_title="Antigravity Pro v4.0.0", layout="wide")
st_autorefresh(interval=10000, key="datarefresh") # 10s para baja latencia

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# --- CREDENCIALES INTEGRADAS ---
FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"

if 'alarma_activa' not in st.session_state:
    st.session_state.alarma_activa = True

@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

# 2. MOTORES DE DATOS (Detección de Engine)
def fetch_data_yahoo():
    tickers = ["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        return data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
    except: return pd.DataFrame()

def fetch_data_finnhub(api_key):
    # Diccionario de símbolos: Yahoo -> Finnhub
    symbols = {"USDCLP=X": "OANDA:USD_CLP", "GC=F": "GOLD", "HG=F": "COPPER", "EURUSD=X": "OANDA:EUR_USD"}
    results = {}
    try:
        for y_sym, f_sym in symbols.items():
            url = f"https://finnhub.io/api/v1/quote?symbol={f_sym}&token={api_key}"
            r = requests.get(url).json()
            results[y_sym] = r.get('c', 0)
        return pd.DataFrame([results])
    except: return pd.DataFrame()

# 3. BITÁCORA DE ENTRENAMIENTO
def log_trade(operador, asset, signal_type, confidence, p_bot, p_xtb, tp, sl):
    log_file = f'bitacora_{operador.lower()}.csv'
    delta_lag = abs(p_bot - p_xtb)
    new_entry = pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': operador, 'Tipo': signal_type, 'Precio_Bot': p_bot,
        'Precio_XTB': p_xtb, 'Lag_CLP': round(delta_lag, 2),
        'Confianza': f"{confidence*100:.1f}%", 'TP': tp, 'SL': sl
    }])
    if not os.path.isfile(log_file):
        new_entry.to_csv(log_file, index=False)
    else:
        new_entry.to_csv(log_file, mode='a', header=False, index=False)

# --- PANEL LATERAL: CONFIGURACIÓN ---
st.sidebar.title("⚙️ Sistema Sentinel v4.0")
engine = st.sidebar.selectbox("Motor de Datos", ["Turbo (Finnhub API)", "Standard (Yahoo)"])

# Selección de motor
if engine == "Turbo (Finnhub API)":
    df_market = fetch_data_finnhub(FINNHUB_KEY)
    mode_label = "⚡ TURBO API ACTIVE"
else:
    df_market = fetch_data_yahoo()
    mode_label = "🐢 STANDARD MODE"

st.sidebar.divider()
operador_activo = st.sidebar.radio("¿Quién opera?", ["Papa", "Axel"])

# ---------------------------------------------------------
# DASHBOARD PRINCIPAL
# ---------------------------------------------------------
st.title("🚀 Antigravity Pro v4.0.0")
st.caption(f"{mode_label} | {hora_chile.strftime('%H:%M:%S')}")

if not df_market.empty:
    usd_col = "USDCLP=X"
    usd_actual = df_market[usd_col].iloc[-1]
    
    # Manejo de tendencia para color (Yahoo tiene historial, Finnhub solo el último)
    d_color = "#00ff00"
    if engine == "Standard (Yahoo)" and len(df_market) > 1:
        usd_prev = df_market[usd_col].iloc[-2]
        d_color = "#00ff00" if usd_actual >= usd_prev else "#ff4b4b"
    
    # EAGLE EYE
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 10px solid {d_color}; text-align: center;">
            <h1 style="margin: 0; color: #888; font-size: 1.5rem;">USD/CLP ACTUAL ({engine.split(' ')[0]})</h1>
            <p style="margin: 0; color: {d_color}; font-size: 5.5rem; font-weight: bold;">${usd_actual:,.2f}</p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📊 Dólar & Commodities", "🇪🇺 Euro Trading"])

    with tab1:
        gold_col, cop_col = "GC=F", "HG=F"
        # Nota: El gráfico histórico completo solo se ve en modo Standard. 
        # El modo Turbo es para precisión de disparo inmediato.
        if engine == "Standard (Yahoo)":
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))
            if gold_col in df_market.columns:
                fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
            if cop_col in df_market.columns:
                fig.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))
            
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10),
                              xaxis=dict(domain=[0, 0.75]),
                              yaxis=dict(title="Dólar", tickfont=dict(color="#00ff00")),
                              yaxis2=dict(title="Oro", anchor="free", overlaying="y", side="right", position=0.82, tickfont=dict(color="#ffbf00")),
                              yaxis3=dict(title="Cobre", anchor="free", overlaying="y", side="right", position=0.92, tickfont=dict(color="#ff4b4b")))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 Modo Turbo activo: Priorizando latencia cero sobre gráficos históricos.")
            st.metric("Oro Actual", f"${df_market.get(gold_col, [0]).iloc[-1]:,.2f}")
            st.metric("Cobre Actual", f"${df_market.get(cop_col, [0]).iloc[-1]:,.2f}")

    with tab2:
        eur_col = "EURUSD=X"
        if eur_col in df_market.columns:
            st.metric("EUR/USD Actual", f"{df_market[eur_col].iloc[-1]:,.4f}")

    # ---------------------------------------------------------
    # LÓGICA DE SEÑALES Y TP/SL
    # ---------------------------------------------------------
    st.divider()
    es_hora = 10 <= hora_chile.hour < 13
    conf_usd, conf_gold = 0.78, 0.72 # Simulación Súper Verde activa para prueba
    c_tp, c_sl, c_type = 0.0, 0.0, "Ninguna"

    if es_hora:
        if conf_usd > 0.75 and conf_gold > 0.70:
            c_type, c_tp, c_sl = "Super Verde", usd_actual + 3.50, usd_actual - 2.00
            st.info("💎 SÚPER VERDE: **0.03 Lotes**")
            col1, col2, col3 = st.columns([2,2,1])
            col1.success(f"📈 TAKE PROFIT: {c_tp:,.2f}")
            col2.error(f"🛡️ STOP LOSS: {c_sl:,.2f}")
            if col3.button("STOP 🔇"):
                st.session_state.alarma_activa = False
                st.rerun()
            if st.session_state.alarma_activa:
                st.components.v1.html(f"""<audio autoplay loop><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>""", height=0)
        
        elif conf_usd > 0.65:
            c_type, c_tp, c_sl = "Verde", usd_actual + 2.50, usd_actual - 1.50
            st.success("🟢 SEÑAL VERDE: **0.01 Lotes**")
            st.write(f"TP Sugerido: {c_tp:,.2f} | SL Sugerido: {c_sl:,.2f}")
    else:
        st.error("🔴 MERCADO CERRADO (10:00 - 13:00)")

    # SIDEBAR: MARGEN & REGISTRO
    st.sidebar.divider()
    st.sidebar.subheader("📉 Margen & Registro")
    p_xtb = st.sidebar.number_input("Precio Real XTB:", value=float(usd_actual), step=0.01)
    if st.sidebar.button(f"💾 Guardar Trade {operador_activo}"):
        log_trade(operador_activo, "USD/CLP", c_type, conf_usd, usd_actual, p_xtb, c_tp, c_sl)
        st.toast(f"✅ Registro completado para {operador_activo}")
else:
    st.warning("⚠️ Iniciando motores de datos...")
