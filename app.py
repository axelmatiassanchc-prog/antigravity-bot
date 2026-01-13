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
# SENTINEL v9.3.1: THE MONOLITH (FULL RESTORE)
# Proyecto: GitHub (USD/CLP) - No AUD/GCP
# ==========================================

# 1. SETUP DE INFRAESTRUCTURA
st.set_page_config(page_title="SENTINEL v9.3.1 - MONOLITH", layout="wide", page_icon="🛡️")
st_autorefresh(interval=3000, key="datarefresh") 

FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"
tz_chile = pytz.timezone('America/Santiago')

# 2. CAPA DE DATOS CON LIMPIEZA TOTAL
@st.cache_data(ttl=2)
def fetch_data_monolith():
    fast_price = 0.0
    latency = 0
    t0 = time.time()
    
    try:
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}", timeout=1.2).json()
        fast_price = float(r.get('c', 0.0))
        latency = int((time.time() - t0) * 1000)
        source = "FINNHUB"
    except:
        fast_price, latency, source = 0.0, 9999, "ERROR"

    ctx = {"oro": 0.0, "cobre": 0.0, "euro": 0.0, "df": pd.DataFrame(), "source": source, "spread_est": 0.45}
    
    try:
        raw = yf.download(["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"], period="1d", interval="1m", progress=False)
        if not raw.empty:
            # Fix Neutro: Relleno bidireccional para que Pearson no falle
            c = raw['Close'].ffill().bfill() 
            ctx["df"] = c
            ctx["oro"] = float(c["GC=F"].iloc[-1])
            ctx["cobre"] = float(c["HG=F"].iloc[-1])
            ctx["euro"] = float(c["EURUSD=X"].iloc[-1])
            
            # Spread Est.
            high_v = raw['High']["USDCLP=X"].iloc[-1]
            low_v = raw['Low']["USDCLP=X"].iloc[-1]
            ctx["spread_est"] = 0.40 + ((high_v - low_v) * 0.1)
            
            if fast_price <= 1.0 or latency > 2500:
                fast_price = float(c["USDCLP=X"].iloc[-1])
                ctx["source"] = "⚠️ YAHOO (FAILOVER)"
    except Exception as e:
        st.sidebar.error(f"Data Error: {e}")
    
    return fast_price, ctx, latency

# 3. BITÁCORA
def log_trade(action, price, pnl_est):
    file_name = 'bitacora_real_100k.csv'
    data = {'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"), 'Accion': action, 'Precio': price, 'PnL': pnl_est}
    pd.DataFrame([data]).to_csv(file_name, mode='a', index=False, header=not os.path.exists(file_name))

usd_val, ctx, lat = fetch_data_monolith()

# 4. MOTOR DE DECISIÓN (Pearson v9.0 Logic)
def get_final_verdict(df, trend_cu, trend_au):
    if df.empty or len(df) < 15: return "⌛ INICIALIZANDO...", "#555", False
    
    try:
        series_usd = df['USDCLP=X'].tail(20)
        series_cu = df['HG=F'].tail(20)
        series_au = df['GC=F'].tail(20)
        corr_cu = series_usd.corr(series_cu)
        corr_au = series_usd.corr(series_au)
        st.sidebar.write(f"📊 Corr Cu: {corr_cu:.2f} | Au: {corr_au:.2f}")
    except:
        return "⚙️ ERROR CÁLCULO", "#555", False
    
    if corr_cu > 0.20 or corr_au > 0.20: return "⚠️ STRESS / DIVERGENCIA", "#ff9900", False
    
    avg_cu = series_cu.tail(10).mean()
    val_cu = trend_cu - avg_cu 
    
    # SEÑAL MAESTRA
    if corr_cu < -0.60:
        if val_cu < 0: return "💎 SÚPER VERDE (COMPRA)", "#00ff00", True
        if val_cu > 0: return "🔥 SÚPER ROJO (VENTA)", "#ff4b4b", True
        
    return "⚖️ NEUTRO / ESPERA", "#3399ff", False

sig_text, sig_color, play_audio = get_final_verdict(ctx["df"], ctx["cobre"], ctx["oro"])

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v9.3.1: THE MONOLITH")

if play_audio:
    st.components.v1.html(f"""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", height=0)

st.markdown(f"""<div style="background-color: {sig_color}; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 15px;">
    <h1 style="margin: 0; color: #000; font-size: 2.8rem; font-weight: bold;">{sig_text}</h1></div>""", unsafe_allow_html=True)

# 5 Columnas para incluir el Oro
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("USD/CLP", f"${usd_val:,.2f}", delta=ctx["source"])
k2.metric("ORO (GC=F)", f"${ctx['oro']:,.1f}")
k3.metric("EURO/USD", f"{ctx['euro']:.4f}")
k4.metric("Spread Est.", f"${ctx['spread_est']:.2f}")
k5.metric("Latencia", f"{lat}ms")

# 5. GRÁFICO TÉCNICO CON 3 EJES (RESTORED)
if not ctx["df"].empty:
    fig = go.Figure()
    # Eje USD
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD", line=dict(color='#00ff00', width=2)))
    # Eje Cobre
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["HG=F"], name="Cobre", yaxis="y2", line=dict(color='#ff4b4b', dash='dash')))
    # Eje Oro
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["GC=F"], name="Oro", yaxis="y3", line=dict(color='#ffd700', dash='dot')))
    
    fig.update_layout(
        template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0),
        yaxis2=dict(anchor="free", overlaying="y", side="right", position=0.98),
        yaxis3=dict(anchor="free", overlaying="y", side="right", position=0.93),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

# Sidebar: Control Operativo
st.sidebar.header("🕹️ Operación Real ($100k)")
entry = st.sidebar.number_input("Precio Entrada XTB:", value=usd_val)
op_side = st.sidebar.radio("Dirección:", ["COMPRA", "VENTA"], horizontal=True)

if st.sidebar.checkbox("🔴 EJECUTAR CÁLCULO PnL"):
    pnl = (usd_val - entry) * 1000 if op_side == "COMPRA" else (entry - usd_val) * 1000
    st.sidebar.metric("PnL VIVO", f"${pnl:,.0f} CLP", delta=f"{usd_val-entry:.2f}")
    if pnl <= -2000: st.sidebar.error("🛑 STOP LOSS (-$2.000)")
    elif pnl >= 4000: st.sidebar.success("🎯 TAKE PROFIT")
    if st.sidebar.button("💾 Guardar en Bitácora"):
        log_trade(op_side, entry, pnl)
        st.sidebar.toast("Guardado!")
