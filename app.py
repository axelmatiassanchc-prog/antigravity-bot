import streamlit as st
import pandas as pd
import numpy as np
import json
import requests
import websocket # pip install websocket-client
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v10.0: XTB PURE SNIPER
# Protocolo: xOpenHub JSON Sync (No Stream)
# ==========================================

st.set_page_config(page_title="SENTINEL v10.0 - XTB", layout="wide", page_icon="🎯")

# Refresco cada 2 segundos para no saturar el socket
st_autorefresh(interval=2000, key="xtbsync") 

tz_chile = pytz.timezone('America/Santiago')

# --- CONFIGURACIÓN DE SEGURIDAD (STREAMLIT SECRETS) ---
# En la nube usa st.secrets, localmente usa strings
USER_ID = st.secrets["XTB_USER_ID"]
PASSWORD = st.secrets["XTB_PASSWORD"]
XTB_URL = "wss://ws.xtb.com/real" # O /demo

# --- MOTOR DE CONEXIÓN XTB ---
def get_xtb_price():
    try:
        ws = websocket.create_connection(XTB_URL, timeout=3)
        # 1. LOGIN
        login_cmd = {
            "command": "login",
            "arguments": {"userId": USER_ID, "password": PASSWORD}
        }
        ws.send(json.dumps(login_cmd))
        auth_resp = json.loads(ws.recv())
        
        if not auth_resp["status"]:
            return 0.0, 0.0, "❌ Error Auth"

        # 2. PEDIR PRECIO (getTickPrices)
        # Pedimos el tick actual de forma puntual
        price_cmd = {
            "command": "getTickPrices",
            "arguments": {
                "level": 0,
                "symbols": ["USDCLP"],
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
        }
        ws.send(json.dumps(price_cmd))
        price_resp = json.loads(ws.recv())
        
        # 3. LOGOUT (Para no dejar sesiones colgadas en la nube)
        ws.send(json.dumps({"command": "logout"}))
        ws.close()

        if price_resp["status"]:
            tick = price_resp["returnData"]["quotations"][0]
            return float(tick["bid"]), float(tick["ask"]), "🟢 XTB REAL-TIME"
        
        return 0.0, 0.0, "⚠️ No Data"
    except Exception as e:
        return 0.0, 0.0, f"❌ {str(e)}"

# --- PERSISTENCIA Y CÁLCULO SNIPER ---
if 'history' not in st.session_state:
    st.session_state.history = []

bid, ask, status = get_xtb_price()
spread = ask - bid if bid > 0 else 0

if bid > 0:
    st.session_state.history.append(bid)
    if len(st.session_state.history) > 40:
        st.session_state.history.pop(0)

def calculate_sniper(history, current):
    if len(history) < 20: return 0.0, "⌛ CALIBRANDO", "#555"
    arr = np.array(history)
    mu = np.mean(arr)
    sigma = np.std(arr)
    z = (current - mu) / sigma if sigma > 0 else 0
    
    if z > 2.2: return z, "🎯 SNIPER: VENTA", "#ff4b4b"
    if z < -2.2: return z, "🎯 SNIPER: COMPRA", "#00ff00"
    return z, "⚖️ BUSCANDO OBJETIVO", "#3399ff"

z_score, sig_text, color = calculate_sniper(st.session_state.history, bid)

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v10.0: XTB PURE SNIPER")

st.markdown(f"""
    <div style="background-color: {color}; padding: 25px; border-radius: 15px; text-align: center; color: white;">
        <h1 style="margin:0; font-size: 3.5rem;">{sig_text}</h1>
        <p style="margin:0;">Z-Score: {z_score:.2f} | Status: {status}</p>
    </div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
col1.metric("XTB BID (Venta)", f"${bid:,.2f}")
col2.metric("XTB ASK (Compra)", f"${ask:,.2f}")
col3.metric("SPREAD XTB", f"${spread:.4f}")

# Visualización Sniper
if len(st.session_state.history) > 1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.history, name="XTB Price", line=dict(color='#00ff00')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
