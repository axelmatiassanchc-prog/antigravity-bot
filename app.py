import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# SENTINEL v9.5: THE TREND HUNTER
# Híbrido: Correlación + DXY + Tendencia
# ==========================================

st.set_page_config(page_title="SENTINEL v9.5 - TREND HUNTER", layout="wide", page_icon="🏹")

# 12 segundos para estabilidad de API y procesamiento de múltiples sensores
st_autorefresh(interval=12000, key="datarefresh") 

TD_KEY = "5028b1741eef4937a359ed068f95296d"
tz_chile = pytz.timezone('America/Santiago')

@st.cache_data(ttl=5)
def fetch_data_v95():
    fast_price, latency, source = 0.0, 0, "TWELVE DATA (RT)"
    t0 = time.time()
    
    # A. Precio RT USD/CLP
    try:
        url = f"https://api.twelvedata.com/price?symbol=USD/CLP&apikey={TD_KEY}"
        r_raw = requests.get(url, timeout=3.5)
        if r_raw.status_code == 200:
            fast_price = float(r_raw.json().get("price", 0.0))
            latency = int((time.time() - t0) * 1000)
    except: fast_price, source = 0.0, "API ERROR"

    ctx = {"oro": 0.0, "cobre": 0.0, "dxy": 0.0, "df": pd.DataFrame(), "source": source}
    
    # B. Sensores Globales (Añadimos DXY: DX-Y.NYB)
    try:
        raw = yf.download(["USDCLP=X", "GC=F", "HG=F", "DX-Y.NYB"], period="2d", interval="1m", progress=False)
        if not raw.empty:
            c = raw['Close'].ffill().bfill()
            ctx["df"] = c
            ctx["oro"] = float(c["GC=F"].iloc[-1])
            ctx["cobre"] = float(c["HG=F"].iloc[-1])
            ctx["dxy"] = float(c["DX-Y.NYB"].iloc[-1]) # Sensor DXY
            
            if fast_price <= 1.0: fast_price = float(c["USDCLP=X"].iloc[-1])
    except: ctx["source"] = "⚠️ DATA ERROR"
    
    return fast_price, ctx, latency

usd_val, ctx, lat = fetch_data_v95()

# MOTOR DE DECISIÓN HÍBRIDO v9.5
def get_hybrid_verdict(df, rt_cobre):
    if df.empty or len(df) < 20: return "⌛ INICIALIZANDO...", "#555", False, 0.0, 0.0
    
    s_usd = df['USDCLP=X'].tail(25).ffill()
    s_cu = df['HG=F'].tail(25).ffill()
    s_dxy = df['DX-Y.NYB'].tail(25).ffill()
    
    corr_cu = s_usd.corr(s_cu)
    corr_dxy = s_usd.corr(s_dxy)
    
    # 1. LÓGICA DE CAUSALIDAD (Cobre - Modo Pesado)
    avg_cu = s_cu.tail(10).mean()
    val_cu = rt_cobre - avg_cu
    
    if corr_cu <= -0.58:
        if val_cu < 0: return "💎 SÚPER VERDE (COMPRA)", "#00ff00", True, corr_cu, corr_dxy
        if val_cu > 0: return "🔥 SÚPER ROJO (VENTA)", "#ff4b4b", True, corr_cu, corr_dxy

    # 2. LÓGICA DE TENDENCIA (DXY - Modo Ligero)
    # Si el Dólar Global acompaña el movimiento, ignoramos el Stress del Cobre
    if corr_dxy >= 0.70:
        dxy_trend = s_dxy.iloc[-1] - s_dxy.tail(10).mean()
        if dxy_trend < -0.05: return "📉 VENTA POR TENDENCIA (DXY)", "#ff4b4b", True, corr_cu, corr_dxy
        if dxy_trend > 0.05: return "📈 COMPRA POR TENDENCIA (DXY)", "#00ff00", True, corr_cu, corr_dxy

    if corr_cu > 0.20: return "⚠️ STRESS / DIVERGENCIA", "#ff9900", False, corr_cu, corr_dxy
    return "⚖️ NEUTRO / ESPERA", "#3399ff", False, corr_cu, corr_dxy

sig_text, sig_color, play_audio, c_cu, c_dxy = get_hybrid_verdict(ctx["df"], ctx["cobre"])

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v9.5: TREND HUNTER")

if play_audio:
    st.components.v1.html(f"""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", height=0)

st.markdown(f"""<div style="background-color: {sig_color}; padding: 25px; border-radius: 15px; text-align: center;">
    <h1 style="margin: 0; color: #000; font-size: 3rem;">{sig_text}</h1></div>""", unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("USD/CLP", f"${usd_val:,.2f}", delta=ctx["source"])
k2.metric("Corr Cobre", f"{c_cu:.2f}", delta="OK" if c_cu <= -0.58 else "OUT")
k3.metric("Dólar Global (DXY)", f"{ctx['dxy']:.2f}", delta=f"Corr: {c_dxy:.2f}")
k4.metric("Cobre (HG=F)", f"${ctx['cobre']:.2f}")
k5.metric("ORO (GC=F)", f"${ctx['oro']:,.1f}")

# Gráfico
if not ctx["df"].empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD", line=dict(color='#00ff00', width=2)))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["DX-Y.NYB"], name="DXY", yaxis="y2", line=dict(color='#3399ff')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=10,b=0), yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)

# Sidebar
st.sidebar.header("🕹️ Operación Híbrida")
st.sidebar.warning("Modo Tendencia: Activa si Corr DXY > 0.70")
entry = st.sidebar.number_input("Precio Entrada:", value=usd_val)
if st.sidebar.checkbox("🔴 PnL VIVO"):
    pnl = (usd_val - entry) * 1000
    st.sidebar.metric("PnL", f"${pnl:,.0f} CLP")
