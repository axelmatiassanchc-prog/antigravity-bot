import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
import requests
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. INFRAESTRUCTURA
st.set_page_config(page_title="Antigravity Pro v4.2.2", layout="wide")
st_autorefresh(interval=2000, key="datarefresh") 

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"

if 'alarma_activa' not in st.session_state:
    st.session_state.alarma_activa = True

# 2. MOTORES DE DATOS BLINDADOS (TYPE-SAFE)
@st.cache_data(ttl=2)
def fetch_usd_clp(engine):
    price = 0.0
    if engine == "Turbo (Finnhub API)":
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}"
            r = requests.get(url, timeout=2).json()
            price = float(r.get('c', 0.0))
        except: price = 0.0
    
    if price <= 0: # Failover a Yahoo con limpieza de Index
        try:
            data = yf.download("USDCLP=X", period="1d", interval="1m", progress=False)
            if not data.empty:
                # Extraemos el valor de cierre asegurando que sea un escalar
                val = data['Close'].iloc[-1]
                price = float(val.iloc[0]) if hasattr(val, "__iter__") else float(val)
            else: price = 0.0
        except: price = 0.0
    return price

@st.cache_data(ttl=30)
def fetch_others(engine):
    data = {"oro": 0.0, "cobre": 0.0, "euro": 0.0}
    if engine == "Turbo (Finnhub API)":
        symbols = {"oro": "XAUUSD", "cobre": "CPER", "euro": "FX:EURUSD"}
        for k, v in symbols.items():
            try:
                url = f"https://finnhub.io/api/v1/quote?symbol={v}&token={FINNHUB_KEY}"
                r = requests.get(url, timeout=2).json()
                data[k] = float(r.get('c', 0.0))
            except: pass
    
    if data["oro"] <= 0: # Fallback Yahoo
        try:
            y_data = yf.download(["GC=F", "HG=F", "EURUSD=X"], period="1d", interval="1m", progress=False)
            if not y_data.empty:
                # Limpieza de datos MultiIndex para commodities
                for ticker, key in zip(["GC=F", "HG=F", "EURUSD=X"], ["oro", "cobre", "euro"]):
                    val = y_data['Close'][ticker].iloc[-1]
                    data[key] = float(val.iloc[0]) if hasattr(val, "__iter__") else float(val)
        except: pass
    return data

# 3. BITÁCORA DUAL
def log_trade(operador, signal_type, p_bot, p_xtb, tp, sl):
    log_file = f'bitacora_{operador.lower()}.csv'
    new_entry = pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': operador, 'Tipo': signal_type,
        'Precio_Bot': p_bot, 'Precio_XTB': p_xtb,
        'Lag_CLP': round(abs(p_bot - p_xtb), 2),
        'TP': tp, 'SL': sl
    }])
    if not os.path.isfile(log_file):
        new_entry.to_csv(log_file, index=False)
    else:
        new_entry.to_csv(log_file, mode='a', header=False, index=False)

# --- PANEL LATERAL ---
st.sidebar.title("⚙️ Sentinel Cloud v4.2.2")
engine_type = st.sidebar.selectbox("Motor de Datos", ["Turbo (Finnhub API)", "Standard (Yahoo)"])
operador_activo = st.sidebar.radio("Operador actual:", ["Papa", "Axel"])

# Obtención de datos con validación de tipo
usd_actual = float(fetch_usd_clp(engine_type))
otros = fetch_others(engine_type)

# ---------------------------------------------------------
# DASHBOARD: EAGLE EYE GIGANTE (BLINDADO)
# ---------------------------------------------------------
st.title("🚀 Antigravity Pro v4.2.2")

# Verificación de datos antes de renderizar para evitar el TypeError
if usd_actual > 0:
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 25px; border-radius: 12px; border-left: 10px solid #00ff00; text-align: center; margin-bottom: 25px;">
            <h1 style="margin: 0; color: #888; font-size: 1.4rem; letter-spacing: 2px;">USD/CLP ACTUAL</h1>
            <p style="margin: 0; color: #00ff00; font-size: 7rem; font-weight: bold; line-height: 1;">${usd_actual:,.2f}</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.error("📡 Error de conexión con el feed de datos. Reintentando...")

tab1, tab2 = st.tabs(["📊 Análisis Mercado", "🇪🇺 Euro & Capital"])

with tab1:
    col_a, col_b = st.columns(2)
    col_a.metric("ORO (XAU/USD)", f"${float(otros['oro']):,.2f}")
    col_b.metric("COBRE (HG/CPER)", f"${float(otros['cobre']):,.2f}")

with tab2:
    st.metric("EUR/USD Actual", f"{float(otros['euro']):,.4f}")
    st.divider()
    m_v = (0.01 * 1000 * usd_actual) / 100
    st.write(f"Margen Verde (0.01): **${m_v:,.0f} CLP**")

# ---------------------------------------------------------
# LÓGICA DE SEÑALES Y ALARMA
# ---------------------------------------------------------
st.divider()
es_hora = 10 <= hora_chile.hour < 13
conf_usd, conf_gold = 0.78, 0.72 # Simulación

if es_hora and usd_actual > 0:
    if conf_usd > 0.75 and conf_gold > 0.70:
        tp, sl = usd_actual + 3.50, usd_actual - 2.00
        st.info("💎 SÚPER VERDE DETECTADO: **0.03 Lotes**")
        c1, c2, c3 = st.columns([2,2,1])
        c1.success(f"📈 TAKE PROFIT: {tp:,.2f}")
        c2.error(f"🛡️ STOP LOSS: {sl:,.2f}")
        if c3.button("STOP 🔇"):
            st.session_state.alarma_activa = False
            st.rerun()
        if st.session_state.alarma_activa:
            st.components.v1.html("""<audio autoplay loop><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>""", height=0)

# SIDEBAR: REGISTRO
st.sidebar.divider()
p_xtb = st.sidebar.number_input("Precio en XTB:", value=usd_actual, step=0.01)
if st.sidebar.button(f"💾 Guardar Trade {operador_activo}"):
    log_trade(operador_activo, "Super Verde", usd_actual, p_xtb, usd_actual+3.5, usd_actual-2)
    st.toast(f"✅ Bitácora de {operador_activo} actualizada.")
