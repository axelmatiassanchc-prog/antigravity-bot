import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import yfinance as yf
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v9.9: BULLETPROOF SNIPER
# Fix: API Rate Limit + Hybrid Failover + SL/TP
# ==========================================

st.set_page_config(page_title="SENTINEL v9.9 - BULLETPROOF", layout="wide", page_icon="🎯")

# Refresco de 3 segundos: El balance ideal entre Sniper y límites de API
st_autorefresh(interval=3000, key="snipersync") 

TD_KEY = "5028b1741eef4937a359ed068f95296d"
tz_chile = pytz.timezone('America/Santiago')

# --- MOTOR DE DATOS HÍBRIDO ---
@st.cache_data(ttl=2)
def fetch_bulletproof_data():
    # Intentar Twelve Data primero (Alta velocidad)
    try:
        url = f"https://api.twelvedata.com/price?symbol=USD/CLP&apikey={TD_KEY}"
        r = requests.get(url, timeout=1.5)
        if r.status_code == 200 and "price" in r.json():
            return float(r.json()["price"]), "TWELVE DATA (RT)"
    except:
        pass
    
    # Failover a Yahoo Finance (Sin límites estrictos)
    try:
        ticker = yf.Ticker("USDCLP=X")
        price = ticker.fast_info['last_price']
        return float(price), "⚠️ YAHOO (FAILOVER)"
    except:
        return 0.0, "❌ CONN ERROR"

# --- PERSISTENCIA DE DATOS ---
if 'history' not in st.session_state:
    st.session_state.history = []
if 'last_signal' not in st.session_state:
    st.session_state.last_signal = "⚖️"

usd_val, source = fetch_bulletproof_data()

if usd_val > 0:
    st.session_state.history.append(usd_val)
    if len(st.session_state.history) > 60: # Ventana de 3 min para estabilidad
        st.session_state.history.pop(0)

# --- CÁLCULO SNIPER + STOP LOSS ---
def get_sniper_logic(history, current):
    if len(history) < 30: return 0.0, "⌛ CALIBRANDO", "#555", 0.0, 0.0
    
    mu = np.mean(history)
    sigma = np.std(history)
    z = (current - mu) / sigma if sigma > 0 else 0
    
    # Cálculo de SL/TP dinámico (0.2% de volatilidad)
    tp = current + 1.5 if z < -2.2 else current - 1.5
    sl = current - 0.8 if z < -2.2 else current + 0.8
    
    if z > 2.2: return z, "🎯 SNIPER: VENTA", "#ff4b4b", sl, tp
    if z < -2.2: return z, "🎯 SNIPER: COMPRA", "#00ff00", sl, tp
    
    return z, "⚖️ BUSCANDO OBJETIVO", "#3399ff", 0.0, 0.0

z_score, status_text, color, sl_val, tp_val = get_sniper_logic(st.session_state.history, usd_val)

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v9.9: BULLETPROOF SNIPER")

# Alerta de Audio (Solo si hay señal)
if "SNIPER" in status_text:
    st.components.v1.html("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>""", height=0)

st.markdown(f"""
    <div style="background-color: {color}; padding: 25px; border-radius: 15px; text-align: center; color: white; border: 3px solid rgba(255,255,255,0.2);">
        <h1 style="margin:0; font-size: 3.5rem; font-weight: bold;">{status_text}</h1>
        <p style="margin:0; font-size: 1.2rem;">Z-Score: {z_score:.2f} | Fuente: {source}</p>
    </div>
""", unsafe_allow_html=True)

# Indicadores Sniper
c1, c2, c3, c4 = st.columns(4)
c1.metric("USD/CLP", f"${usd_val:,.2f}")
c2.metric("Impulso Z", f"{z_score:.2f}")
c3.metric("Take Profit Sugerido", f"${tp_val:,.2f}" if tp_val > 0 else "---")
c4.metric("Stop Loss Sugerido", f"${sl_val:,.2f}" if sl_val > 0 else "---")

# Gráfico de Alta Resolución
if len(st.session_state.history) > 1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.history, mode='lines+markers', name="Tick", line=dict(color='#00ff00', width=2)))
    # Añadir línea de promedio móvil (Regresión a la media)
    avg_line = [np.mean(st.session_state.history)] * len(st.session_state.history)
    fig.add_trace(go.Scatter(y=avg_line, name="Media", line=dict(color='gray', dash='dash')))
    
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=10,b=0),
                     xaxis_title="Ticks (Últimos 3 min)", yaxis_title="CLP")
    st.plotly_chart(fig, use_container_width=True)

# Sidebar de Gestión SpA
with st.sidebar:
    st.header("🕹️ Control de Riesgo")
    st.write(f"Capital: **$100,000 CLP**")
    st.write(f"Hora Local: {datetime.now(tz_chile).strftime('%H:%M:%S')}")
    if st.button("♻️ Reset Historial"):
        st.session_state.history = []
        st.rerun()
