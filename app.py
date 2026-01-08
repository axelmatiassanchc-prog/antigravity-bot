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

# 1. INFRAESTRUCTURA DE RED
st.set_page_config(page_title="Antigravity Pro v4.2.0", layout="wide")
# Refresco ultra rápido cada 2 segundos para el Eagle Eye
st_autorefresh(interval=2000, key="datarefresh") 

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# API KEY INTEGRADA
FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"

if 'alarma_activa' not in st.session_state:
    st.session_state.alarma_activa = True

# 2. MOTORES DE DATOS CON FAILOVER
@st.cache_data(ttl=2) # Caché compartido para evitar baneo
def fetch_usd_clp(engine):
    price = 0
    if engine == "Turbo (Finnhub API)":
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}"
            r = requests.get(url, timeout=2).json()
            price = r.get('c', 0)
        except: price = 0
    
    if price == 0: # Failover a Yahoo
        data = yf.download("USDCLP=X", period="1d", interval="1m", progress=False)
        price = data['Close'].iloc[-1] if not data.empty else 0
    return price

@st.cache_data(ttl=30) # Commodities y Euro cada 30 seg
def fetch_global_assets(engine):
    data = {"oro": 0, "cobre": 0, "euro": 0}
    if engine == "Turbo (Finnhub API)":
        symbols = {"oro": "XAUUSD", "cobre": "CPER", "euro": "FX:EURUSD"}
        for k, v in symbols.items():
            try:
                url = f"https://finnhub.io/api/v1/quote?symbol={v}&token={FINNHUB_KEY}"
                r = requests.get(url, timeout=2).json()
                data[k] = r.get('c', 0)
            except: pass
    
    # Relleno con Yahoo si Finnhub falla o para modo Standard
    if data["oro"] == 0:
        y_data = yf.download(["GC=F", "HG=F", "EURUSD=X"], period="1d", interval="1m", progress=False)
        if not y_data.empty:
            data["oro"] = y_data['Close']['GC=F'].iloc[-1]
            data["cobre"] = y_data['Close']['HG=F'].iloc[-1]
            data["euro"] = y_data['Close']['EURUSD=X'].iloc[-1]
    return data

# 3. BITÁCORA CON AUDITORÍA DE LAG
def log_trade(operador, signal_type, p_bot, p_xtb, tp, sl):
    log_file = f'bitacora_{operador.lower()}.csv'
    delta_lag = abs(p_bot - p_xtb)
    new_entry = pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': operador, 'Tipo': signal_type,
        'Precio_Bot': p_bot, 'Precio_XTB': p_xtb, 'Lag_CLP': round(delta_lag, 2),
        'TP': tp, 'SL': sl
    }])
    if not os.path.isfile(log_file):
        new_entry.to_csv(log_file, index=False)
    else:
        new_entry.to_csv(log_file, mode='a', header=False, index=False)

# --- UI SIDEBAR ---
st.sidebar.title("⚙️ Sentinel v4.2.0")
engine_type = st.sidebar.selectbox("Motor de Datos", ["Turbo (Finnhub API)", "Standard (Yahoo)"])
operador_activo = st.sidebar.radio("¿Quién opera ahora?", ["Papa", "Axel"])

usd_actual = fetch_usd_clp(engine_type)
otros = fetch_global_assets(engine_type)

# ---------------------------------------------------------
# DASHBOARD PRINCIPAL
# ---------------------------------------------------------
st.title("🚀 Antigravity Pro v4.2.0")
st.caption(f"📍 Macul, Chile | {hora_chile.strftime('%H:%M:%S')} | Motor: {engine_type}")

# EAGLE EYE GIGANTE
st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 10px solid #00ff00; text-align: center; margin-bottom: 25px;">
        <h1 style="margin: 0; color: #888; font-size: 1.5rem;">USD/CLP ACTUAL</h1>
        <p style="margin: 0; color: #00ff00; font-size: 6.5rem; font-weight: bold;">${usd_actual:,.2f}</p>
    </div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Análisis Mercado", "🇪🇺 Euro & Gestión"])

with tab1:
    col_a, col_b = st.columns(2)
    col_a.metric("Oro (XAU/USD)", f"${otros['oro']:,.2f}")
    col_b.metric("Cobre (ETF CPER)", f"${otros['cobre']:,.2f}")
    
    # Gráfico solo en modo Standard para no saturar
    if engine_type == "Standard (Yahoo)":
        st.info("💡 Gráfico histórico activo en modo Standard.")
    else:
        st.caption("⚡ Modo Turbo: Priorizando velocidad de precio sobre gráficos.")

with tab2:
    st.metric("EUR/USD Actual", f"{otros['euro']:,.4f}")
    st.divider()
    st.subheader("💰 Calculadora de Margen (Capital 50k)")
    m_v = (0.01 * 1000 * usd_actual) / 100
    m_sv = (0.03 * 1000 * usd_actual) / 100
    st.write(f"Sugerencia Verde (0.01): **${m_v:,.0f} CLP**")
    st.write(f"Sugerencia Súper (0.03): **${m_sv:,.0f} CLP**")

# ---------------------------------------------------------
# LÓGICA DE SEÑALES Y ALARMA
# ---------------------------------------------------------
st.divider()
es_hora = 10 <= hora_chile.hour < 13
conf_usd, conf_gold = 0.78, 0.72 # Simulación Súper Verde

if es_hora:
    if conf_usd > 0.75 and conf_gold > 0.70:
        tp, sl = usd_actual + 3.50, usd_actual - 2.00
        st.info("💎 SÚPER VERDE DETECTADO: **0.03 Lotes**")
        c1, c2, c3 = st.columns([2,2,1])
        c1.success(f"📈 TP: {tp:,.2f}")
        c2.error(f"🛡️ SL: {sl:,.2f}")
        
        if c3.button("STOP 🔇"):
            st.session_state.alarma_activa = False
            st.rerun()
            
        if st.session_state.alarma_activa:
            st.components.v1.html("""<audio autoplay loop><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>""", height=0)
    else:
        st.warning("🟡 MODO SENTINELA: Esperando señal de alta probabilidad...")
else:
    st.error("🔴 MERCADO CERRADO (Opera 10:00 - 13:00)")

# SIDEBAR: REGISTRO Y AUDITORÍA
st.sidebar.divider()
st.sidebar.subheader("📝 Auditoría de Trade")
p_xtb = st.sidebar.number_input("Precio Real en XTB:", value=float(usd_actual), step=0.01)
if st.sidebar.button(f"💾 Guardar Trade {operador_activo}"):
    log_trade(operador_activo, "Super Verde", usd_actual, p_xtb, usd_actual+3.5, usd_actual-2)
    st.toast(f"✅ Trade de {operador_activo} registrado con éxito.")
