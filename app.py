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

# 1. CONFIGURACIÓN DE SISTEMA
st.set_page_config(page_title="SENTINEL v7.5 - REAL", layout="wide", page_icon="🛡️")
st_autorefresh(interval=3000, key="datarefresh") 

FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"
tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. MOTORES DE DATOS CON FAILOVER (EVITA EL $0.00)
@st.cache_data(ttl=2)
def fetch_fast_usd():
    try:
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}", timeout=1.5).json()
        val = float(r.get('c', 0.0))
        return val
    except:
        return 0.0

@st.cache_data(ttl=30)
def fetch_market_context():
    res = {"oro": 0.0, "cobre": 0.0, "euro": 0.0, "std": 0.0, "df": pd.DataFrame()}
    try:
        # Descarga consolidada para optimizar API
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

# 3. MÓDULO DE CORRELACIÓN MATEMÁTICA (PEARSON)
def get_market_correlation(df):
    if df.empty or len(df) < 10: return 0.0
    # Calculamos la correlación de los últimos 20 minutos entre Dólar y Cobre
    # En Chile, esperamos una correlación NEGATIVA (Si Cobre sube, Dólar baja)
    correlation = df['USDCLP=X'].tail(20).corr(df['HG=F'].tail(20))
    return correlation

# --- PROCESAMIENTO DE SEÑAL ---
t0 = time.time()
usd_val = fetch_fast_usd()
ctx = fetch_market_context()
lat = int((time.time()-t0)*1000)

# FAILOVER CRÍTICO: Si Finnhub falla, rescatamos de Yahoo
if usd_val <= 0 and not ctx["df"].empty:
    usd_val = float(ctx["df"]["USDCLP=X"].iloc[-1])
    lat_status = "⚠️ FAILOVER"
else:
    lat_status = "🟢 ÓPTIMO" if lat < 600 else "🟡 LAG"

corr_val = get_market_correlation(ctx["df"])

# --- INTERFAZ ---
st.title("🛡️ SENTINEL v7.5: PEARSON REAL-TIME")

# Sidebar de Control
view_mode = st.sidebar.selectbox("Modo de Interfaz", ["⚔️ BATTLE (Operación)", "📈 PLAN (Simulación)"])
st.sidebar.divider()
st.sidebar.header("🛡️ Parámetros $100k")
st.sidebar.write("Lote: **0.01** | Meta: **+$4.000** | SL: **-$2.000**")

if view_mode == "⚔️ BATTLE (Operación)":
    # Eagle Eye
    stress = (usd_val > ctx["df"]["USDCLP=X"].tail(5).mean() and ctx["cobre"] > ctx["df"]["HG=F"].tail(5).mean()) if not ctx["df"].empty else False
    d_color = "#ff4b4b" if stress else "#00ff00"
    
    c_eye, c_metrics = st.columns([3, 1])
    with c_eye:
        st.markdown(f"""
            <div style="background-color: #111; padding: 25px; border-radius: 15px; border-left: 10px solid {d_color}; text-align: center;">
                <h1 style="margin: 0; color: #888; font-size: 1.2rem;">USD/CLP ACTUAL {"(DIVERGENCIA)" if stress else ""}</h1>
                <p style="margin: 0; color: {d_color}; font-size: 6.5rem; font-weight: bold;">${usd_val:,.2f}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with c_metrics:
        st.metric("CORRELACIÓN (Cu/USD)", f"{corr_val:.2f}", help="Ideal: -0.70 a -1.00")
        st.metric("LATENCIA", f"{lat}ms", delta=lat_status)

    # Gráfico de Confluencia
    if not ctx["df"].empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["HG=F"], name="Cobre", yaxis="y2", line=dict(color='#ff4b4b', dash='dash')))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=5, r=5, t=5, b=5),
                          yaxis2=dict(anchor="free", overlaying="y", side="right", position=0.95))
        st.plotly_chart(fig, use_container_width=True)

    # Calculadora en Vivo
    if st.checkbox("Simular Trade en Curso"):
        entry = st.number_input("Precio Entrada XTB:", value=usd_val)
        neta = (usd_val - entry) * 1000
        st.metric("RESULTADO NETO", f"${neta:,.0f} CLP", delta=f"{usd_val-entry:.2f} CLP")
        if neta <= -2000: st.error("🚨 STOP LOSS: CIERRA AHORA")

else:
    st.header("📈 Modo Planificación y Resiliencia")
    st.info("Aquí puedes revisar tu bitácora y proyecciones fuera del horario de mercado.")
