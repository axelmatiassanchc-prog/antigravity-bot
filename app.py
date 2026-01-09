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

# 1. SETUP DE ALTA DISPONIBILIDAD
st.set_page_config(page_title="SENTINEL v8.1 - AUDITED", layout="wide", page_icon="🛡️")
st_autorefresh(interval=3000, key="datarefresh") 

FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"
tz_chile = pytz.timezone('America/Santiago')

# 2. MOTOR DE DATOS (Optimizado)
@st.cache_data(ttl=2)
def fetch_data_layer():
    # A. Intentamos obtener precio rápido (Finnhub)
    fast_price = 0.0
    latency = 0
    t0 = time.time()
    try:
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}", timeout=1.0).json()
        fast_price = float(r.get('c', 0.0))
        latency = int((time.time() - t0) * 1000)
    except: 
        latency = 9999

    # B. Obtenemos contexto pesado (Yahoo) - SIEMPRE necesario para Pearson y Gráficos
    context = {"oro": 0.0, "cobre": 0.0, "euro": 0.0, "df": pd.DataFrame(), "source": "FINNHUB"}
    try:
        raw = yf.download(["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"], period="1d", interval="1m", progress=False)
        if not raw.empty:
            c = raw['Close'].ffill()
            context["df"] = c
            context["oro"] = float(c["GC=F"].iloc[-1])
            context["cobre"] = float(c["HG=F"].iloc[-1])
            context["euro"] = float(c["EURUSD=X"].iloc[-1])
            
            # C. Lógica de Failover: Si Finnhub falló, usamos Yahoo
            if fast_price <= 0:
                fast_price = float(c["USDCLP=X"].iloc[-1])
                context["source"] = "⚠️ YAHOO (FAILOVER)"
    except: pass
    
    return fast_price, context, latency

# 3. BITÁCORA DE TRANSACCIONES (Reintegrado)
def log_trade(action, price, pnl_est):
    file_name = 'bitacora_100k.csv'
    data = {
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Accion': action,
        'Precio': price,
        'PnL_Estimado': pnl_est
    }
    pd.DataFrame([data]).to_csv(file_name, mode='a', index=False, header=not os.path.exists(file_name))

# --- EJECUCIÓN ---
usd_val, ctx, lat = fetch_data_layer()

# 4. EL CEREBRO DE DECISIÓN (Ahora incluye Oro)
def get_decision_semaphore(df, trend_cu, trend_au):
    if df.empty or len(df) < 15: return "⌛ INICIALIZANDO...", "#555"
    
    # Correlaciones de Pearson (Últimos 20 min)
    corr_cu = df['USDCLP=X'].tail(20).corr(df['HG=F'].tail(20))
    corr_au = df['USDCLP=X'].tail(20).corr(df['GC=F'].tail(20))
    
    # Lógica de Seguridad
    if corr_cu > 0.20: return "⚠️ STRESS: DIVERGENCIA (Cobre sube, Dólar sube)", "#ff9900"
    
    # Señales de Entrada
    # Súper Verde: Cobre baja (negativo para CLP) + Correlación fuerte + Oro no molesta
    trend_cu_val = trend_cu - df['HG=F'].tail(10).mean()
    
    if corr_cu < -0.60 and trend_cu_val < 0: 
        return "💎 SÚPER VERDE (COMPRA)", "#00ff00"
    
    if corr_cu < -0.60 and trend_cu_val > 0:
        return "🔥 SÚPER ROJO (VENTA)", "#ff4b4b"
        
    return "⚖️ ZONA NEUTRA / ESPERA", "#3399ff"

sig_text, sig_color = get_decision_semaphore(ctx["df"], ctx["cobre"], ctx["oro"])

# --- INTERFAZ ---
st.title("🛡️ SENTINEL v8.1: AUDITED")

# Semáforo
st.markdown(f"""
    <div style="background-color: {sig_color}; padding: 20px; border-radius: 10px; text-align: center;">
        <h2 style="margin:0; color:black; font-weight:bold;">{sig_text}</h2>
    </div>
""", unsafe_allow_html=True)

# Métricas Principales
k1, k2, k3, k4 = st.columns(4)
k1.metric("USD/CLP", f"${usd_val:,.2f}", delta=ctx["source"])
if not ctx["df"].empty:
    corr_c = ctx['df']['USDCLP=X'].tail(20).corr(ctx['df']['HG=F'].tail(20))
    corr_g = ctx['df']['USDCLP=X'].tail(20).corr(ctx['df']['GC=F'].tail(20))
    k2.metric("Corr COBRE", f"{corr_c:.2f}")
    k3.metric("Corr ORO", f"{corr_g:.2f}")
k4.metric("Latencia", f"{lat}ms")

# Gráfico
if not ctx["df"].empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD", line=dict(color='#00ff00', width=2)))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["HG=F"], name="Cobre", yaxis="y2", line=dict(color='#ff4b4b', dash='dot')))
    fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=0,b=0),
                      yaxis2=dict(anchor="free", overlaying="y", side="right", position=1))
    st.plotly_chart(fig, use_container_width=True)

# 5. GESTIÓN DE ORDEN + LOGS (Sidebar)
st.sidebar.header("🕹️ Operación Real")
entry = st.sidebar.number_input("Entrada:", value=usd_val)
direction = st.sidebar.selectbox("Dirección", ["COMPRA", "VENTA"])

if st.sidebar.checkbox("🔴 TRADE ACTIVO"):
    pnl = (usd_val - entry) * 1000 if direction == "COMPRA" else (entry - usd_val) * 1000
    st.sidebar.metric("PnL Vivo", f"${pnl:,.0f}", delta_color="normal")
    
    if pnl <= -2000: st.sidebar.error("🛑 STOP LOSS (-$2k)")
    elif pnl >= 4000: st.sidebar.success("✅ TAKE PROFIT (+$4k)")
    
    if st.sidebar.button("💾 Guardar en Bitácora"):
        log_trade(direction, entry, pnl)
        st.sidebar.info("Guardado.")
