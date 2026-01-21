import streamlit as st
import pandas as pd
import numpy as np
import json
import websocket
import time
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v10.1.1: ATOMIC XTB (FIXED LOGIN)
# Optimización: Handshake + Auth Check
# ==========================================

st.set_page_config(page_title="SENTINEL v10.1.1 - ATOMIC", layout="wide", page_icon="🎯")

# Refresco cada 2 segundos para balancear velocidad y estabilidad en la nube
st_autorefresh(interval=2000, key="xtb_atomic_sync") 

tz_chile = pytz.timezone('America/Santiago')

# Credenciales desde Secrets
USER_ID = st.secrets["XTB_USER_ID"]
PASSWORD = st.secrets["XTB_PASSWORD"]
# IMPORTANTE: Verifica si es /real o /demo según tu cuenta
XTB_URL = "wss://ws.xtb.com/real" 

def fetch_xtb_atomic():
    try:
        # 1. Establecer conexión con timeout extendido
        ws = websocket.create_connection(XTB_URL, timeout=5)
        
        # 2. COMANDO DE LOGIN (Indispensable)
        login_cmd = {
            "command": "login",
            "arguments": {"userId": USER_ID, "password": PASSWORD}
        }
        ws.send(json.dumps(login_cmd))
        
        # Esperar y validar respuesta de login
        login_resp = json.loads(ws.recv())
        if not login_resp.get("status"):
            ws.close()
            return 0.0, 0.0, f"❌ Auth Failed: {login_resp.get('errorCode', 'Unknown')}"

        # 3. COMANDO DE DATOS (Una vez logueado)
        price_cmd = {
            "command": "getSymbol",
            "arguments": {"symbol": "USDCLP"}
        }
        ws.send(json.dumps(price_cmd))
        price_resp = json.loads(ws.recv())
        
        # 4. CIERRE LIMPIO
        ws.close()

        if price_resp.get("status"):
            data = price_resp["returnData"]
            return float(data["bid"]), float(data["ask"]), "🟢 XTB REAL-TIME"
        
        return 0.0, 0.0, "⚠️ Symbol Error"
        
    except Exception as e:
        # Captura el error específico para diagnóstico en el banner
        return 0.0, 0.0, f"❌ Connection Error: {str(e)[:15]}"

# --- PERSISTENCIA Y MOTOR SNIPER ---
if 'history' not in st.session_state:
    st.session_state.history = []

bid, ask, status = fetch_xtb_atomic()

if bid > 0:
    st.session_state.history.append(bid)
    if len(st.session_state.history) > 40:
        st.session_state.history.pop(0)

def get_sniper_verdict(history, current):
    if len(history) < 20: return 0.0, "⌛ CALIBRANDO...", "#555"
    mu, sigma = np.mean(history), np.std(history)
    z = (current - mu) / sigma if sigma > 0 else 0
    
    if z > 2.2: return z, "🎯 SNIPER: VENTA", "#ff4b4b"
    if z < -2.2: return z, "🎯 SNIPER: COMPRA", "#00ff00"
    return z, "⚖️ BUSCANDO OBJETIVO", "#3399ff"

z_val, sig_text, sig_color = get_sniper_verdict(st.session_state.history, bid)

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v10.1.1: ATOMIC XTB")

st.markdown(f"""
    <div style="background-color: {sig_color}; padding: 25px; border-radius: 15px; text-align: center; color: white; border: 2px solid white;">
        <h1 style="margin:0; font-size: 3rem; font-weight: bold;">{sig_text}</h1>
        <p style="margin:0;">Z-Score: {z_val:.2f} | Status: {status}</p>
    </div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("XTB BID", f"${bid:,.2f}")
c2.metric("XTB ASK", f"${ask:,.2f}")
c3.metric("SPREAD", f"${(ask-bid):.4f}")

if len(st.session_state.history) > 1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.history, name="XTB Price", line=dict(color='#00ff00', width=2)))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
