import streamlit as st
import pandas as pd
import numpy as np
import json
import websocket # websocket-client
import ssl
from datetime import datetime
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v10.5: THE HANDSHAKE FIX
# Objetivo: Eliminar el 404 y Link Error
# ==========================================

st.set_page_config(page_title="SENTINEL v10.5", layout="wide", page_icon="🎯")

# Refresco de 3 segundos (Igual que la v9.8 que funcionó)
st_autorefresh(interval=3000, key="xtb_v105_sync") 

# Credenciales desde Secrets
USER_ID = st.secrets["XTB_USER_ID"]
PASSWORD = st.secrets["XTB_PASSWORD"]
XTB_URL = "wss://ws.xtb.com/real"

@st.cache_data(ttl=2)
def fetch_xtb_final():
    ws = None
    try:
        # FIX: Handshake con SSL relajado y Headers de Navegador
        ws = websocket.create_connection(
            XTB_URL, 
            timeout=7, 
            sslopt={"cert_reqs": ssl.CERT_NONE}, # Salta bloqueos de certificados en la nube
            header=[
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits"
            ]
        )
        
        # 1. LOGIN (Indispensable para que no dé 404 después)
        ws.send(json.dumps({
            "command": "login",
            "arguments": {"userId": USER_ID, "password": PASSWORD}
        }))
        login_resp = json.loads(ws.recv())
        
        if not login_resp.get("status"):
            ws.close()
            return 0.0, 0.0, f"❌ Auth Failed: {login_resp.get('errorCode')}"

        # 2. SOLICITUD ATÓMICA DE PRECIO
        ws.send(json.dumps({
            "command": "getSymbol",
            "arguments": {"symbol": "USDCLP"}
        }))
        price_resp = json.loads(ws.recv())
        
        # 3. CIERRE DE SESIÓN LIMPIO
        ws.send(json.dumps({"command": "logout"}))
        ws.close()

        if price_resp.get("status"):
            res = price_resp["returnData"]
            return float(res["bid"]), float(res["ask"]), "🟢 CONECTADO (XTB)"
        
        return 0.0, 0.0, "⚠️ Símbolo no encontrado"
    except Exception as e:
        if ws: ws.close()
        return 0.0, 0.0, f"❌ Link Error: {str(e)[:20]}"

# --- LÓGICA SNIPER (Z-SCORE) ---
if 'history' not in st.session_state:
    st.session_state.history = []

bid, ask, status = fetch_xtb_final()

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
st.title("🛡️ SENTINEL v10.5: XTB ATOMIC")

st.markdown(f"""<div style="background-color: {sig_color}; padding: 30px; border-radius: 15px; text-align: center; color: white;">
    <h1 style="margin:0; font-size: 3.5rem; font-weight: bold;">{sig_text}</h1>
    <p style="margin:0; font-size: 1.2rem;">Z-Score: {z_val:.2f} | Status: {status}</p></div>""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("BID XTB", f"${bid:,.2f}")
c2.metric("ASK XTB", f"${ask:,.2f}")
c3.metric("SPREAD", f"${(ask-bid):.4f}")

if len(st.session_state.history) > 1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=st.session_state.history, name="XTB Price", line=dict(color='#00ff00')))
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig, use_container_width=True)
