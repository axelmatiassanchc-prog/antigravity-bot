import streamlit as st
import pandas as pd
import numpy as np
import json
import time
import websocket
import threading
import ssl  # Añadido para robustez en Handshake SSL
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v9.7.5: ULTRA-RESILIENT SNIPER
# Optimización: SSL Context, Thread Guard & Keep-Alive
# ==========================================

st.set_page_config(page_title="SENTINEL v9.7.5 - SNIPER", layout="wide", page_icon="🎯")
st_autorefresh(interval=1500, key="uisync")

# --- CARGA SEGURA DE SECRETOS ---
try:
    XTB_USER_ID = st.secrets["XTB_USER_ID"]
    XTB_PASSWORD = st.secrets["XTB_PASSWORD"]
    XTB_HOST = st.secrets["XTB_HOST"].strip().rstrip('/') + "/"
    XTB_STREAM_HOST = st.secrets["XTB_STREAM_HOST"].strip().rstrip('/') + "/"
except Exception:
    st.error("⚠️ Configuración incompleta en Secrets.")
    st.stop()

tz_chile = pytz.timezone('America/Santiago')

class XTBBridge:
    def __init__(self):
        self.price_history = []
        self.current_bid = 0.0
        self.current_ask = 0.0
        self.spread = 0.0
        self.last_update = "---"
        self.connected = False
        self.stream_session_id = ""
        self.error_log = "Sistema listo."
        self._lock = threading.Lock() # Guard para evitar race conditions

    def login(self):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.error_log = f"🔄 Handshake intento {attempt + 1}/{max_attempts}..."
                # Usamos SSL context por defecto para evitar rechazos del servidor
                ws = websocket.create_connection(
                    XTB_HOST, 
                    timeout=20,
                    sslopt={"cert_reqs": ssl.CERT_NONE} # Evita fallos de cert en nubes públicas
                )
                login_cmd = {
                    "command": "login",
                    "arguments": {
                        "userId": XTB_USER_ID, 
                        "password": XTB_PASSWORD,
                        "appName": "xStation5"
                    }
                }
                ws.send(json.dumps(login_cmd))
                resp = json.loads(ws.recv())
                
                if resp.get("status"):
                    self.stream_session_id = resp["streamSessionId"]
                    self.connected = True
                    self.error_log = "🟢 Conexión Institucional Activa"
                    # Iniciar stream en hilo dedicado si no existe uno activo
                    t = threading.Thread(target=self._run_stream, daemon=True)
                    t.start()
                    return True
                else:
                    self.error_log = f"❌ Error {resp.get('errorCode')}"
                    return False
            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(3)
                else:
                    self.error_log = f"⚠️ Timeout persistente: {str(e)}"
                    return False

    def _run_stream(self):
        try:
            ws_stream = websocket.create_connection(
                XTB_STREAM_HOST, 
                timeout=None,
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )
            subscribe_cmd = {
                "command": "getTickPrices",
                "streamSessionId": self.stream_session_id,
                "symbol": "USDCLP",
                "minSpread": 1
            }
            ws_stream.send(json.dumps(subscribe_cmd))
            
            while self.connected:
                data = json.loads(ws_stream.recv())
                if data.get("command") == "tickPrices":
                    tick = data["data"]
                    with self._lock:
                        self.current_bid = tick["bid"]
                        self.current_ask = tick["ask"]
                        self.spread = self.current_ask - self.current_bid
                        self.price_history.append(self.current_bid)
                        if len(self.price_history) > 150:
                            self.price_history.pop(0)
                        self.last_update = datetime.now(tz_chile).strftime("%H:%M:%S.%f")[:-3]
        except:
            self.connected = False
            self.error_log = "🛑 Socket cerrado. Reintente login."

# --- SINGLETON PATTERN PARA STREAMLIT ---
if 'xtb' not in st.session_state:
    st.session_state.xtb = XTBBridge()

xtb = st.session_state.xtb

# --- MOTOR DE CÁLCULO SNIPER ---
def get_sniper_logic(history, current_bid, spread):
    if len(history) < 50:
        return "⌛ CALIBRANDO...", "#555", 0.0
    
    arr = np.array(history)
    mu, sigma = np.mean(arr), np.std(arr)
    # Z-Score Formula: $Z = \frac{x - \mu}{\sigma}$
    z = (current_bid - mu) / sigma if sigma > 0 else 0
    
    # Umbral Sniper: 2.5 Sigmas + Filtro de viabilidad (3x spread)
    if z > 2.5 and (current_bid - mu) > (spread * 3):
        return "🎯 SNIPER: VENTA", "#ff4b4b", z
    elif z < -2.5 and (mu - current_bid) > (spread * 3):
        return "🎯 SNIPER: COMPRA", "#00ff00", z
    
    return "⚖️ BUSCANDO OBJETIVO", "#3399ff", z

# --- INTERFAZ DE USUARIO ---
st.title("🛡️ SENTINEL v9.7.5: X-STREAM SNIPER")

with st.sidebar:
    st.header("🕹️ Centro de Mando")
    if not xtb.connected:
        if st.button("CONECTAR XTB REAL"):
            xtb.login()
            st.rerun()
    else:
        st.success("🟢 ONLINE")
        if st.button("DESCONECTAR"):
            xtb.connected = False
            st.rerun()
    
    st.write(f"**Status:** {xtb.error_log}")
    st.divider()
    st.write("**Capital SpA:** $96.330 CLP")
    st.write(f"**Ticks en Buffer:** {len(xtb.price_history)}")

sig_text, sig_color, z_val = get_sniper_logic(xtb.price_history, xtb.current_bid, xtb.spread)

# Dashboard Visual
st.markdown(f"""<div style="background-color: {sig_color}; padding: 35px; border-radius: 15px; text-align: center; border: 3px solid #fff;">
    <h1 style="margin: 0; color: #fff; font-size: 3.5rem; font-weight: bold;">{sig_text}</h1>
    <p style="color: #fff; margin-top: 10px; font-size: 1.2rem;">Z-Score Sniper: {z_val:.2f} | Ticks: {len(xtb.price_history)}</p>
</div>""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("BID (Venta)", f"${xtb.current_bid:,.2f}")
m2.metric("ASK (Compra)", f"${xtb.current_ask:,.2f}")
m3.metric("SPREAD", f"${xtb.spread:.4f}")
m4.metric("SIGMA (σ)", f"{np.std(xtb.price_history):.4f}" if xtb.price_history else "0")

# Visualización de Ticks
if len(xtb.price_history) > 10:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=xtb.price_history, name="Price Path", line=dict(color='#00ff00', width=2)))
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, width='stretch')
else:
    st.info("Esperando flujo de datos de XTB para graficar...")
