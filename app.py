import streamlit as st
import pandas as pd
import numpy as np
import json
import websocket # IMPORTANTE: pip install websocket-client
import time
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="SENTINEL v10.2 - FINAL", layout="wide", page_icon="🎯")

# Refresco de 3 segundos: Seguridad total contra bloqueos de XTB
st_autorefresh(interval=3000, key="xtb_final_sync") 

tz_chile = pytz.timezone('America/Santiago')

# Credenciales (Streamlit Cloud Secrets)
USER_ID = st.secrets["XTB_USER_ID"]
PASSWORD = st.secrets["XTB_PASSWORD"]
XTB_URL = "wss://ws.xtb.com/real" 

def fetch_xtb_atomic():
    ws = None
    try:
        # 1. Conexión con Timeouts definidos para Starlink
        ws = websocket.create_connection(XTB_URL, timeout=5)
        
        # 2. Login
        ws.send(json.dumps({
            "command": "login",
            "arguments": {"userId": USER_ID, "password": PASSWORD}
        }))
        
        login_resp = json.loads(ws.recv())
        if not login_resp.get("status"):
            ws.close()
            return 0.0, 0.0, f"❌ Auth Fail: {login_resp.get('errorCode', 'Check Credentials')}"

        # 3. Pedir símbolo exacto
        ws.send(json.dumps({
            "command": "getSymbol",
            "arguments": {"symbol": "USDCLP"} # Cambiar a USDCLP.pro si falla
        }))
        price_resp = json.loads(ws.recv())
        
        # 4. Logout (Protocolo de cortesía con el servidor)
        ws.send(json.dumps({"command": "logout"}))
        ws.close()

        if price_resp.get("status"):
            data = price_resp["returnData"]
            return float(data["bid"]), float(data["ask"]), "🟢 XTB REAL-TIME"
        
        return 0.0, 0.0, "⚠️ Symbol Name Error"
        
    except Exception as e:
        if ws: ws.close()
        return 0.0, 0.0, f"❌ Link Error: {str(e)[:15]}"

# --- PERSISTENCIA SNIPER ---
if 'history' not in st.session_state:
    st.session_state.history = []

bid, ask, status = fetch_xtb_atomic()

if bid > 0:
    st.session_state.history.append(bid)
    if len(st.session_state.history) > 50:
        st.session_state.history.pop(0)

# --- MOTOR Z-SCORE ---
def get_sniper_verdict(history, current):
    if len(history) < 25: return 0.0, "⌛ CALIBRANDO...", "#555"
    mu, sigma = np.mean(history), np.std(history)
    z = (current - mu) / sigma if sigma > 0 else 0
    
    # Sensibilidad Sniper v10.2
    if z > 2.1: return z, "🎯 SNIPER: VENTA", "#ff4b4b"
    if z < -2.1: return z, "🎯 SNIPER: COMPRA", "#00ff00"
    return z, "⚖️ BUSCANDO OBJETIVO", "#3399ff"

z_val, sig_text, sig_color = get_sniper_verdict(st.session_state.history, bid)

# --- DASHBOARD FINAL ---
st.title("🛡️ SENTINEL v10.2: XTB ATOMIC")

st.markdown(f"""
    <div style="background-color: {sig_color}; padding: 30px; border-radius: 15px; text-align: center; color: white; border: 3px solid rgba(255,255,255,0.3);">
        <h1 style="margin:0; font-size: 3.5rem; font-weight: bold;">{sig_text}</h1>
        <p style="margin:0; font-size: 1.2rem;">Z-Score Tick: {z_val:.2f} | Status: {status}</p>
    </div>
""", unsafe_allow_html=True)

# Audio Alert (Opcional)
if "SNIPER" in sig_text:
    st.components.v1.html("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>""", height=0)

c1, c2, c3 = st.columns(3)
c1.metric("BID (Venta)", f"${bid:,.2f}")
c2.metric("ASK (Compra)", f"${ask:,.2f}")
c3.metric("SPREAD REAL", f"${(ask-bid):.4f}")



if len(st.session_state.history) > 1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.history, mode='lines+markers', name="XTB Ticks", line=dict(color='#00ff00')))
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=10,b=0),
                     xaxis_title="Ticks", yaxis_title="CLP")
    st.plotly_chart(fig, use_container_width=True)

with st.sidebar:
    st.header("📊 Gestión de Capital")
    st.write(f"Cuenta: **{USER_ID}**")
    st.write(f"Hora Local: {datetime.now(tz_chile).strftime('%H:%M:%S')}")
    if st.button("♻️ Reiniciar Sniper"):
        st.session_state.history = []
        st.rerun()
