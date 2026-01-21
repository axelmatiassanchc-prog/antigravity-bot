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
# SENTINEL v9.5.2: HUNTER MODE (CORREGIDO)
# Optimización: Reducción de Fricción Estadística
# ==========================================

st.set_page_config(page_title="SENTINEL v9.5.2 - HUNTER", layout="wide", page_icon="🏹")

# 12 segundos para evitar rate-limiting de Twelve Data
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
    except: fast_price, source = 0.0, "CONN ERROR"

    ctx = {"oro": 0, "cobre": 0, "dxy": 0, "euro": 0, "df": pd.DataFrame(), "source": source, "spread": 0.45}
    
    # B. Sensores Globales
    try:
        raw = yf.download(["USDCLP=X", "GC=F", "HG=F", "DX-Y.NYB", "EURUSD=X"], period="2d", interval="1m", progress=False)
        if not raw.empty:
            c = raw['Close'].ffill().bfill()
            ctx["df"] = c
            ctx["oro"] = float(c["GC=F"].iloc[-1])
            ctx["cobre"] = float(c["HG=F"].iloc[-1])
            ctx["dxy"] = float(c["DX-Y.NYB"].iloc[-1])
            ctx["euro"] = float(c["EURUSD=X"].iloc[-1])
            
            if fast_price <= 1.0:
                fast_price = float(c["USDCLP=X"].iloc[-1])
                ctx["source"] = "⚠️ YAHOO (FAILOVER)"
            
            h, l = raw['High']["USDCLP=X"].iloc[-1], raw['Low']["USDCLP=X"].iloc[-1]
            ctx["spread"] = 0.35 + ((h - l) * 0.15) # Spread dinámico ajustado
    except: ctx["source"] = "⚠️ DATA ERROR"
    
    return fast_price, ctx, latency

def get_hybrid_verdict(df, rt_cobre):
    if df.empty or len(df) < 15: return "⌛ CALIBRANDO SENSORES...", "#555", False, 0.0, 0.0
    
    # Ventana de análisis reducida para mayor reactividad (15 mins)
    s_usd = df['USDCLP=X'].tail(15).ffill()
    s_cu = df['HG=F'].tail(15).ffill()
    s_dxy = df['DX-Y.NYB'].tail(15).ffill()
    
    c_cu = s_usd.corr(s_cu)
    c_dxy = s_usd.corr(s_dxy)
    
    avg_cu = s_cu.tail(8).mean()
    val_cu = rt_cobre - avg_cu
    
    # --- LÓGICA DE DISPARO v9.5.2 ---
    
    # 1. Modo Arbitraje (Cobre) - Umbral bajado de -0.58 a -0.45
    if c_cu <= -0.45:
        if val_cu < -0.005: return "💎 SÚPER VERDE (COMPRA)", "#00ff00", True, c_cu, c_dxy
        if val_cu > 0.005: return "🔥 SÚPER ROJO (VENTA)", "#ff4b4b", True, c_cu, c_dxy

    # 2. Modo Trend Hunter (DXY) - Umbral bajado de 0.75 a 0.55
    # Delta bajado de 0.04 a 0.015 para captar micro-tendencias
    dxy_delta = s_dxy.iloc[-1] - s_dxy.tail(8).mean()
    if c_dxy >= 0.55:
        if dxy_delta < -0.015: return "📉 VENTA POR TENDENCIA (DXY)", "#ff4b4b", True, c_cu, c_dxy
        if dxy_delta > 0.015: return "📈 COMPRA POR TENDENCIA (DXY)", "#00ff00", True, c_cu, c_dxy

    # 3. Filtro de Stress Adaptativo (Subido a 0.40)
    if c_cu > 0.40: return "⚠️ STRESS / DIVERGENCIA", "#ff9900", False, c_cu, c_dxy
    
    return "⚖️ NEUTRO / ESPERA", "#3399ff", False, c_cu, c_dxy

# --- EJECUCIÓN ---
usd_val, ctx, lat = fetch_data_v95()
sig_text, sig_color, play_audio, corr_cu, corr_dxy = get_hybrid_verdict(ctx["df"], ctx["cobre"])

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v9.5.2: HUNTER MODE")

if play_audio:
    st.components.v1.html(f"""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", height=0)

st.markdown(f"""<div style="background-color: {sig_color}; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
    <h1 style="margin: 0; color: #000; font-size: 3rem; font-weight: bold;">{sig_text}</h1></div>""", unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("USD/CLP", f"${usd_val:,.2f}", delta=f"{lat}ms")
k2.metric("Corr Cu", f"{corr_cu:.2f}", delta="OK" if corr_cu <= -0.45 else "LOW")
k3.metric("Dólar Global", f"{ctx['dxy']:.2f}", delta=f"Corr: {corr_dxy:.2f}")
k4.metric("Cobre (HG)", f"${ctx['cobre']:.2f}")
k5.metric("ORO (GC)", f"${ctx['oro']:,.1f}")
k6.metric("EURO/USD", f"{ctx['euro']:.4f}")
k7.metric("Spread Est.", f"${ctx['spread']:.2f}")

if not ctx["df"].empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD/CLP", line=dict(color='#00ff00', width=2.5)))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["DX-Y.NYB"], name="DXY", yaxis="y2", line=dict(color='#3399ff', dash='dot')))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["HG=F"], name="Cobre", yaxis="y3", line=dict(color='#ff4b4b', dash='dash')))
    
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=10,b=0),
        yaxis2=dict(anchor="free", overlaying="y", side="right", position=0.98),
        yaxis3=dict(anchor="free", overlaying="y", side="right", position=0.93),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

st.sidebar.header("🕹️ Operación SpA ($100k)")
entry = st.sidebar.number_input("Precio Entrada:", value=usd_val, step=0.01)
op_side = st.sidebar.radio("Dirección:", ["COMPRA", "VENTA"], horizontal=True)

if st.sidebar.checkbox("🔴 MOSTRAR PnL VIVO"):
    pnl = (usd_val - entry) * 1000 if op_side == "COMPRA" else (entry - usd_val) * 1000
    st.sidebar.metric("PnL VIVO", f"${pnl:,.0f} CLP", delta=f"{usd_val-entry:.2f}")
    if pnl <= -2000: st.sidebar.error("🛑 STOP LOSS (-$2.000)")
