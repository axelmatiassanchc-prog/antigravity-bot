import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. SETUP PROFESIONAL
st.set_page_config(page_title="SENTINEL v7.6 - REAL", layout="wide", page_icon="🛡️")
st_autorefresh(interval=3000, key="datarefresh") 

FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"
tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. MOTOR DE DATOS CON FAILOVER INTELIGENTE
@st.cache_data(ttl=2)
def fetch_fast_usd():
    try:
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}", timeout=1.5).json()
        return float(r.get('c', 0.0))
    except: return 0.0

@st.cache_data(ttl=30)
def fetch_market_context():
    res = {"oro": 0.0, "cobre": 0.0, "euro": 0.0, "std": 0.0, "df": pd.DataFrame()}
    try:
        raw = yf.download(["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"], period="1d", interval="1m", progress=False)
        if not raw.empty:
            c = raw['Close'].ffill()
            res["df"] = c
            res["oro"] = float(c["GC=F"].iloc[-1])
            res["cobre"] = float(c["HG=F"].iloc[-1])
            res["euro"] = float(c["EURUSD=X"].iloc[-1])
            res["std"] = c["USDCLP=X"].tail(15).std()
    except: pass
    return res

# 3. MÓDULO DE CORRELACIÓN DUAL
def get_correlations(df):
    if df.empty or len(df) < 10: return 0.0, 0.0
    c_cu = df['USDCLP=X'].tail(20).corr(df['HG=F'].tail(20))
    c_au = df['USDCLP=X'].tail(20).corr(df['GC=F'].tail(20))
    return c_cu, c_au

# --- PROCESAMIENTO ---
t0 = time.time()
usd_val = fetch_fast_usd()
ctx = fetch_market_context()
lat = int((time.time()-t0)*1000)

if usd_val <= 0 and not ctx["df"].empty:
    usd_val = float(ctx["df"]["USDCLP=X"].iloc[-1])
    lat_status = "⚠️ FAILOVER"
else: lat_status = "🟢 ÓPTIMO"

corr_cu, corr_au = get_correlations(ctx["df"])

# --- INTERFAZ BATTLE MODE ---
st.title("🛡️ SENTINEL v7.6: REAL MONEY MONITOR")

# Métricas Superiores
m1, m2, m3, m4 = st.columns(4)
m1.metric("USD/CLP", f"${usd_val:,.2f}", delta_color="inverse")
m2.metric("CORR. COBRE", f"{corr_cu:.2f}", help="Ideal: < -0.70")
m3.metric("CORR. ORO", f"{corr_au:.2f}", help="Ideal: < -0.70")
m4.metric("LATENCIA", f"{lat}ms", delta=lat_status)

# Eagle Eye Principal
stress = (corr_cu > 0.20 or corr_au > 0.20) # Alerta si hay correlación positiva (anomalía)
d_color = "#ff4b4b" if stress else "#00ff00"
st.markdown(f"""
    <div style="background-color: #111; padding: 20px; border-radius: 15px; border-left: 10px solid {d_color}; text-align: center;">
        <h1 style="margin: 0; color: #888; font-size: 1.2rem;">SISTEMA DE CONFLUENCIA {"(STRESS DETECTADO)" if stress else ""}</h1>
        <p style="margin: 0; color: {d_color}; font-size: 5.5rem; font-weight: bold;">${usd_val:,.2f}</p>
    </div>
""", unsafe_allow_html=True)

# Gráfico Triple Eje (USD, Oro, Cobre)
if not ctx["df"].empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD", line=dict(color='#00ff00', width=3)))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["GC=F"], name="Oro", yaxis="y2", line=dict(color='#ffbf00', dash='dot')))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["HG=F"], name="Cobre", yaxis="y3", line=dict(color='#ff4b4b', dash='dash')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=5, r=5, t=5, b=5),
                      yaxis2=dict(anchor="free", overlaying="y", side="right", position=0.85),
                      yaxis3=dict(anchor="free", overlaying="y", side="right", position=0.95))
    st.plotly_chart(fig, use_container_width=True)

# CALCULADORA "FLIGHT CONTROL" $100K
st.divider()
st.subheader("🕹️ Monitor de Operación en Vivo")
c_calc1, c_calc2 = st.columns([1, 2])

with c_calc1:
    entry_price = st.number_input("Precio de Entrada XTB:", value=usd_val, format="%.2f")
    tipo_op = st.radio("Dirección:", ["COMPRA (Long)", "VENTA (Short)"], horizontal=True)

with c_calc2:
    if tipo_op == "COMPRA (Long)":
        pnl = (usd_val - entry_price) * 1000
        dist_meta = entry_price + 4.00
        dist_sl = entry_price - 2.00
    else:
        pnl = (entry_price - usd_val) * 1000
        dist_meta = entry_price - 4.00
        dist_sl = entry_price + 2.00
    
    pnl_color = "green" if pnl >= 0 else "red"
    st.markdown(f"""
        <div style="background-color: #1a1a1a; padding: 15px; border-radius: 10px; border: 1px solid #333;">
            <h3 style="margin: 0; color: {pnl_color}; text-align: center;">PnL: ${pnl:,.0f} CLP</h3>
            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                <span style="color: #00ff00;">🎯 Meta ($4.000) en: <b>${dist_meta:.2f}</b></span>
                <span style="color: #ff4b4b;">🛡️ Stop Loss ($2.000) en: <b>${dist_sl:.2f}</b></span>
            </div>
        </div>
    """, unsafe_allow_html=True)
