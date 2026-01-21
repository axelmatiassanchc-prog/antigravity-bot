import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v9.8: STABLE SNIPER (HTTP POLLING)
# Optimización: Streamlit Cloud Stability
# ==========================================

st.set_page_config(page_title="SENTINEL v9.8 - STABLE", layout="wide", page_icon="🎯")

# Refresco cada 2 segundos: El límite seguro para no ser bloqueado por la API
st_autorefresh(interval=2000, key="snipersync") 

TD_KEY = "5028b1741eef4937a359ed068f95296d"
tz_chile = pytz.timezone('America/Santiago')

# --- MOTOR DE DATOS (POLLING OPTIMIZADO) ---
@st.cache_data(ttl=1) # Cache de 1 segundo para forzar la actualización
def fetch_fast_data():
    t0 = time.time()
    url = f"https://api.twelvedata.com/price?symbol=USD/CLP&apikey={TD_KEY}"
    try:
        r = requests.get(url, timeout=1.8)
        price = float(r.json().get("price", 0.0))
        lat = int((time.time() - t0) * 1000)
        return price, lat
    except:
        return 0.0, 0

# --- GESTIÓN DE HISTORIAL (PERSISTENCIA EN SESSION_STATE) ---
if 'history' not in st.session_state:
    st.session_state.history = []

usd_val, latency = fetch_fast_data()

if usd_val > 0:
    st.session_state.history.append(usd_val)
    if len(st.session_state.history) > 50: # Ventana de 50 registros para el Z-Score
        st.session_state.history.pop(0)

# --- CÁLCULO SNIPER (Z-SCORE) ---
# Fórmula: $Z = \frac{x - \mu}{\sigma}$
def calculate_sniper_metrics(history, current):
    if len(history) < 20: return 0.0, "⌛ CALIBRANDO", "#555"
    
    arr = np.array(history)
    mu = np.mean(arr)
    sigma = np.std(arr)
    z = (current - mu) / sigma if sigma > 0 else 0
    
    # Umbrales Sniper
    if z > 2.2: return z, "🎯 SNIPER: VENTA", "#ff4b4b"
    if z < -2.2: return z, "🎯 SNIPER: COMPRA", "#00ff00"
    return z, "⚖️ BUSCANDO OBJETIVO", "#3399ff"

z_score, status_text, status_color = calculate_sniper_metrics(st.session_state.history, usd_val)

# --- DASHBOARD ---
st.title("🎯 SENTINEL v9.8: STABLE SNIPER")

st.markdown(f"""
    <div style="background-color: {status_color}; padding: 20px; border-radius: 10px; text-align: center; color: white;">
        <h1 style="margin:0; font-size: 3rem;">{status_text}</h1>
        <p style="margin:0;">Z-Score: {z_score:.2f} | Latencia API: {latency}ms</p>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
col1.metric("USD/CLP (RT)", f"${usd_val:,.2f}")
col2.metric("Impulso (Z)", f"{z_score:.2f}")
col3.metric("Muestras", len(st.session_state.history))

# Gráfico de Micro-Tendencia
if len(st.session_state.history) > 1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.history, mode='lines+markers', name="Precio", line=dict(color='#00ff00')))
    fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

st.sidebar.header("🕹️ Sniper Control")
st.sidebar.write("Esta versión es compatible con Streamlit Cloud y Starlink.")
if st.sidebar.button("Limpiar Historial"):
    st.session_state.history = []
    st.rerun()
