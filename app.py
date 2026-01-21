import streamlit as st
import pandas as pd
import numpy as np
import json
import time
import websocket
import threading
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v9.7.1: X-STREAM SNIPER (PROD)
# Repositorio: GitHub -> Streamlit Cloud
# ==========================================

st.set_page_config(page_title="SENTINEL v9.7 - SNIPER", layout="wide", page_icon="🎯")

# Refresco visual forzado cada 2 segundos para actualizar métricas
st_autorefresh(interval=2000, key="uipulsar")

# --- SEGURIDAD: CARGA DE CREDENCIALES ---
try:
    XTB_USER_ID = st.secrets["XTB_USER_ID"]
    XTB_PASSWORD = st.secrets["XTB_PASSWORD"]
    XTB_HOST = st.secrets["XTB_HOST"]
    XTB_STREAM_HOST = st.secrets["XTB_STREAM_HOST"]
except KeyError:
    st.error("⚠️ Faltan las credenciales en Streamlit Secrets. Configura XTB_USER_ID, XTB_PASSWORD, XTB_HOST y XTB_STREAM_HOST.")
    st.stop()

tz_chile = pytz.timezone('America/Santiago')

# --- PUENTE TÉCNICO XTB ---
class XTBBridge:
    def __init__(self):
        self.price_history = []
        self.current_bid = 0.0
        self.current_ask = 0.0
        self.spread = 0.0
        self.last_update = "Esperando data..."
        self.connected = False
        self.stream_session_id = ""
        self.error_log = ""

    def login_and_stream(self):
        try:
            # 1. Login Command
            ws = websocket.create_connection(XTB_HOST)
            login_cmd = {
                "command": "login",
                "arguments": {"userId": XTB_USER_ID, "password": XTB_PASSWORD}
            }
            ws.send(json.dumps(login_cmd))
            resp = json.loads(ws.recv())
            
            if resp.get("status"):
                self.stream_session_id = resp["streamSessionId"]
                self.connected = True
                # Iniciar hilo de streaming
                threading.Thread(target=self._maintain_stream, daemon=True).start()
                return True
            else:
                self.error_log = resp.get("errorCode", "Unknown Login Error")
                return False
        except Exception as e:
            self.error_log = str(e)
            return False

    def _maintain_stream(self):
        try:
            ws_stream = websocket.create_connection(XTB_STREAM_HOST)
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
                    self.current_bid = tick["bid"]
                    self.current_ask = tick["ask"]
                    self.spread = self.current_ask - self.current_bid
                    self.price_history.append(self.current_bid)
                    
                    if len(self.price_history) > 150: # Ventana de 150 ticks
                        self.price_history.pop(0)
                    
                    self.last_update = datetime.now(tz_chile).strftime("%H:%M:%S.%f")[:-3]
        except Exception as e:
            self.connected = False
            self.error_log = f"Stream Error: {e}"

# --- GESTIÓN DE ESTADO ---
if 'xtb' not in st.session_state:
    st.session_state.xtb = XTBBridge()

xtb = st.session_state.xtb

# --- MOTOR SNIPER (Z-SCORE) ---
def calculate_sniper_v97(history, current_bid, spread):
    if len(history) < 50:
        return "⌛ CALIBRANDO SNIPER...", "#555", 0.0
    
    arr = np.array(history)
    mu = np.mean(arr)
    sigma = np.std(arr)
    
    # Ecuación Z-Score: $Z = \frac{x - \mu}{\sigma}$
    z_score = (current_bid - mu) / sigma if sigma > 0 else 0
    
    # Umbrales Sniper
    # Solo dispara si Z > 2.5 y el movimiento cubre 3x el spread
    if z_score > 2.5 and (current_bid - mu) > (spread * 3):
        return "🎯 SNIPER: VENTA (IMPULSO)", "#ff4b4b", z_score
    elif z_score < -2.5 and (mu - current_bid) > (spread * 3):
        return "🎯 SNIPER: COMPRA (IMPULSO)", "#00ff00", z_score
    
    return "⚖️ BUSCANDO OBJETIVO", "#3399ff", z_score

# --- INTERFAZ ---
st.title("🛡️ SENTINEL v9.7.1: X-STREAM SNIPER")

with st.sidebar:
    st.header("🕹️ Control de Enlace")
    if not xtb.connected:
        if st.button("CONECTAR XTB REAL"):
            with st.spinner("Autenticando con XOpenHub..."):
                if xtb.login_and_stream():
                    st.success("Conectado")
                    st.rerun()
                else:
                    st.error(f"Error: {xtb.error_log}")
    else:
        st.success("🟢 STREAMING ACTIVO")
        if st.button("DESCONECTAR"):
            xtb.connected = False
            st.rerun()
    
    st.divider()
    st.info(f"Capital SpA: $100.000 CLP")
    st.write(f"Última señal: {xtb.last_update}")

# Lógica Sniper
sig_text, sig_color, z_val = calculate_sniper_v97(xtb.price_history, xtb.current_bid, xtb.spread)

# Dashboard Visual
st.markdown(f"""<div style="background-color: {sig_color}; padding: 35px; border-radius: 20px; text-align: center; border: 3px solid #fff;">
    <h1 style="margin: 0; color: #fff; font-size: 4rem; font-weight: bold; text-shadow: 2px 2px 5px #000;">{sig_text}</h1>
    <p style="color: #fff; font-size: 1.2rem; margin-top: 10px;">Z-Score Sniper: {z_val:.2f} | Ticks en Memoria: {len(xtb.price_history)}</p>
</div>""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("BID (Venta)", f"${xtb.current_bid:,.2f}")
m2.metric("ASK (Compra)", f"${xtb.current_ask:,.2f}")
m3.metric("SPREAD REAL", f"${xtb.spread:.4f}")
m4.metric("VOLATILIDAD", f"{np.std(xtb.price_history):.4f}" if xtb.price_history else "0")

# Gráfico de Alta Frecuencia
if len(xtb.price_history) > 10:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=xtb.price_history, name="Tick Path", line=dict(color='#00ff00', width=2)))
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0),
                      xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Aún no hay suficientes ticks para graficar. Mantén la conexión abierta.")
