import streamlit as st
import pandas as pd
import numpy as np
import json
import websocket # Asegúrate de tener 'websocket-client' en requirements.txt
from datetime import datetime
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v10.4: ATOMIC XTB (ESTRUCTURA v9.8)
# Solución definitiva al Handshake 404
# ==========================================

st.set_page_config(page_title="SENTINEL v10.4", layout="wide", page_icon="🎯")

# Refresco idéntico a la v9.8 (Cada 3 segundos para estabilidad)
st_autorefresh(interval=3000, key="xtb_v104_sync") 

# Credenciales (Streamlit Cloud Secrets)
USER_ID = st.secrets["XTB_USER_ID"]
PASSWORD = st.secrets["XTB_PASSWORD"]
XTB_URL = "wss://ws.xtb.com/real"

# --- LA FUNCIÓN QUE "CONCRETA" (Misma lógica v9.8) ---
@st.cache_data(ttl=2)
def fetch_xtb_data():
    ws = None
    try:
        # Abrimos conexión con headers de navegador para evitar el 404
        ws = websocket.create_connection(
            XTB_URL, 
            timeout=5, 
            header={"User-Agent": "Mozilla/5.0"}
        )
        
        # 1. Login
        ws.send(json.dumps({
            "command": "login",
            "arguments": {"userId": USER_ID, "password": PASSWORD}
        }))
        login_resp = json.loads(ws.recv())
        
        if not login_resp.get("status"):
            ws.close()
            return 0.0, 0.0, "❌ Error Auth"

        # 2. Pedir precio actual (Snapshot)
        ws.send(json.dumps({
            "command": "getSymbol",
            "arguments": {"symbol": "USDCLP"}
        }))
        price_resp = json.loads(ws.recv())
        
        # 3. Logout y Cierre (Atómico)
        ws.send(json.dumps({"command": "logout"}))
        ws.close()

        if price_resp.get("status"):
            res = price_resp["returnData"]
            return float(res["bid"]), float(res["ask"]), "🟢 XTB OK"
        
        return 0.0, 0.0, "⚠️ Symbol Error"
    except Exception as e:
        if ws: ws.close()
        return 0.0, 0.0, f"❌ Handshake Fail: {str(e)[:15]}"

# --- PERSISTENCIA SNIPER (Session State) ---
if 'history' not in st.session_state:
    st.session_state.history = []

bid, ask, status = fetch_xtb_data()

if bid > 0:
    st.session_state.history.append(bid)
    if len(st.session_state.history) > 40:
        st.session_state.history.pop(0)

# --- CÁLCULO Z-SCORE ---
def get_z_score(history, current):
    if len(history) < 20: return 0.0, "⌛ CALIBRANDO", "#555"
    z = (current - np.mean(history)) / np.std(history) if np.std(history) > 0 else 0
    if z > 2.2: return z, "🎯 SNIPER: VENTA", "#ff4b4b"
    if z < -2.2: return z, "🎯 SNIPER: COMPRA", "#00ff00"
    return z, "⚖️ NEUTRO", "#3399ff"

z_val, sig_text, sig_color = get_z_score(st.session_state.history, bid)

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v10.4: ATOMIC XTB")

st.markdown(f"""<div style="background-color: {sig_color}; padding: 25px; border-radius: 15px; text-align: center; color: white;">
    <h1 style="margin:0; font-size: 3rem; font-weight: bold;">{sig_text}</h1>
    <p style="margin:0;">Z-Score: {z_val:.2f} | Status: {status}</p></div>""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("BID XTB", f"${bid:,.2f}")
c2.metric("ASK XTB", f"${ask:,.2f}")
c3.metric("SPREAD", f"${(ask-bid):.4f}")

if len(st.session_state.history) > 1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.history, mode='lines+markers', name="Tick", line=dict(color='#00ff00')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
