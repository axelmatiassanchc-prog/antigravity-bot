import streamlit as st
import pandas as pd
import numpy as np
import json
import websocket # Requerido: websocket-client
import time
from datetime import datetime
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v10.3: FINAL ATOMIC (FIXED LINK)
# Solución al error 404 y Link Error
# ==========================================

st.set_page_config(page_title="SENTINEL v10.3", layout="wide", page_icon="🎯")

# Refresco de 3 segundos para evitar bloqueos por IP
st_autorefresh(interval=3000, key="xtb_v103_sync") 

# Credenciales desde Streamlit Secrets
USER_ID = st.secrets["XTB_USER_ID"]
PASSWORD = st.secrets["XTB_PASSWORD"]
# URL Corregida para Real (wss://ws.xtb.com/real)
XTB_URL = "wss://ws.xtb.com/real"

def fetch_xtb_atomic():
    ws = None
    try:
        # 1. Conexión limpia con Timeout
        ws = websocket.create_connection(XTB_URL, timeout=5)
        
        # 2. Login obligatorio
        ws.send(json.dumps({
            "command": "login",
            "arguments": {"userId": USER_ID, "password": PASSWORD}
        }))
        
        login_resp = json.loads(ws.recv())
        if not login_resp.get("status"):
            ws.close()
            return 0.0, 0.0, f"❌ Error Auth: {login_resp.get('errorCode')}"

        # 3. Pedir símbolo (USDCLP)
        ws.send(json.dumps({
            "command": "getSymbol",
            "arguments": {"symbol": "USDCLP"}
        }))
        price_resp = json.loads(ws.recv())
        
        # 4. Cerrar sesión (Logout)
        ws.send(json.dumps({"command": "logout"}))
        ws.close()

        if price_resp.get("status"):
            d = price_resp["returnData"]
            return float(d["bid"]), float(d["ask"]), "🟢 XTB ONLINE"
        
        return 0.0, 0.0, "⚠️ Símbolo no encontrado"
        
    except Exception as e:
        if ws: ws.close()
        return 0.0, 0.0, f"❌ Link Error: {str(e)[:20]}"

# --- MOTOR SNIPER (Z-SCORE) ---
if 'history' not in st.session_state:
    st.session_state.history = []

bid, ask, status = fetch_xtb_atomic()

if bid > 0:
    st.session_state.history.append(bid)
    if len(st.session_state.history) > 50:
        st.session_state.history.pop(0)

def get_verdict(hist, curr):
    if len(hist) < 20: return 0.0, "⌛ CALIBRANDO", "#555"
    z = (curr - np.mean(hist)) / np.std(hist) if np.std(hist) > 0 else 0
    if z > 2.2: return z, "🎯 SNIPER: VENTA", "#ff4b4b"
    if z < -2.2: return z, "🎯 SNIPER: COMPRA", "#00ff00"
    return z, "⚖️ NEUTRO", "#3399ff"

z_val, sig_text, sig_color = get_verdict(st.session_state.history, bid)

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v10.3: ATOMIC SNIPER")

st.markdown(f"""<div style="background-color: {sig_color}; padding: 25px; border-radius: 15px; text-align: center; color: white;">
    <h1 style="margin:0; font-size: 3rem;">{sig_text}</h1>
    <p style="margin:0;">Z-Score: {z_val:.2f} | {status}</p></div>""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("XTB BID", f"${bid:,.2f}")
c2.metric("XTB ASK", f"${ask:,.2f}")
c3.metric("SPREAD", f"${(ask-bid):.4f}")

if len(st.session_state.history) > 1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.history, name="XTB Ticks", line=dict(color='#00ff00')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
