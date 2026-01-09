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

# 1. SETUP DE INFRAESTRUCTURA
st.set_page_config(page_title="SENTINEL v9.0 - MONOLITH", layout="wide", page_icon="🏛️")
st_autorefresh(interval=3000, key="datarefresh") 

FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"
tz_chile = pytz.timezone('America/Santiago')

# 2. CAPA DE DATOS UNIFICADA (Con Failover y Contexto Total)
@st.cache_data(ttl=2)
def fetch_data_monolith():
    fast_price = 0.0
    latency = 0
    t0 = time.time()
    
    # A. Precio Rápido
    try:
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}", timeout=1.0).json()
        fast_price = float(r.get('c', 0.0))
        latency = int((time.time() - t0) * 1000)
    except: latency = 9999

    # B. Contexto Global (Yahoo)
    ctx = {"oro": 0.0, "cobre": 0.0, "euro": 0.0, "df": pd.DataFrame(), "source": "FINNHUB", "spread_est": 0.45}
    try:
        raw = yf.download(["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"], period="1d", interval="1m", progress=False)
        if not raw.empty:
            c = raw['Close'].ffill()
            ctx["df"] = c
            ctx["oro"] = float(c["GC=F"].iloc[-1])
            ctx["cobre"] = float(c["HG=F"].iloc[-1])
            ctx["euro"] = float(c["EURUSD=X"].iloc[-1])
            
            # Cálculo de Spread Estimado (Basado en volatilidad del minuto)
            high = raw['High']["USDCLP=X"].iloc[-1]
            low = raw['Low']["USDCLP=X"].iloc[-1]
            volatility = high - low
            ctx["spread_est"] = 0.40 + (volatility * 0.1) # Proxy de spread dinámico
            
            # Failover
            if fast_price <= 0:
                fast_price = float(c["USDCLP=X"].iloc[-1])
                ctx["source"] = "⚠️ YAHOO (FAILOVER)"
    except: pass
    
    return fast_price, ctx, latency

# 3. SISTEMA DE BITÁCORA
def log_trade(action, price, pnl_est):
    file_name = 'bitacora_real_100k.csv'
    data = {'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"), 'Accion': action, 'Precio': price, 'PnL': pnl_est}
    pd.DataFrame([data]).to_csv(file_name, mode='a', index=False, header=not os.path.exists(file_name))

# --- PROCESAMIENTO ---
usd_val, ctx, lat = fetch_data_monolith()

# 4. MOTOR DE DECISIÓN (Pearson + Oro + Tendencia)
def get_final_verdict(df, trend_cu, trend_au):
    if df.empty or len(df) < 15: return "⌛ INICIALIZANDO...", "#555", False
    
    # Correlaciones
    corr_cu = df['USDCLP=X'].tail(20).corr(df['HG=F'].tail(20))
    corr_au = df['USDCLP=X'].tail(20).corr(df['GC=F'].tail(20))
    
    # Lógica de Seguridad (Stress)
    if corr_cu > 0.20 or corr_au > 0.20: 
        return "⚠️ STRESS / DIVERGENCIA", "#ff9900", False
    
    # Tendencias
    val_cu = trend_cu - df['HG=F'].tail(10).mean()
    
    # Señales (Solo si Pearson aprueba)
    if corr_cu < -0.60 and val_cu < 0: 
        return "💎 SÚPER VERDE (COMPRA)", "#00ff00", True # Audio ON
    
    if corr_cu < -0.60 and val_cu > 0:
        return "🔥 SÚPER ROJO (VENTA)", "#ff4b4b", True # Audio ON
        
    return "⚖️ NEUTRO / ESPERA", "#3399ff", False

sig_text, sig_color, play_audio = get_final_verdict(ctx["df"], ctx["cobre"], ctx["oro"])

# --- DASHBOARD DE COMBATE ---
st.title("🛡️ SENTINEL v9.0: THE MONOLITH")

# Alerta Sonora (Solo si entra en modo Súper)
if play_audio:
    st.components.v1.html("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", height=0)

# Semáforo Principal
st.markdown(f"""
    <div style="background-color: {sig_color}; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 15px;">
        <h1 style="margin: 0; color: #000; font-size: 2.8rem; font-weight: bold;">{sig_text}</h1>
    </div>
""", unsafe_allow_html=True)

# Panel de Instrumentos (Recuperamos Euro y Spread)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("USD/CLP", f"${usd_val:,.2f}", delta=ctx["source"])
if not ctx["df"].empty:
    corr_c = ctx['df']['USDCLP=X'].tail(20).corr(ctx['df']['HG=F'].tail(20))
    k2.metric("Corr COBRE", f"{corr_c:.2f}", help="Debe ser negativo")
    k3.metric("EURO/USD", f"{ctx['euro']:.4f}", help="Si sube, ayuda a que el dólar baje")
    k4.metric("Spread Est.", f"${ctx['spread_est']:.2f}", delta="OK" if ctx['spread_est'] < 0.6 else "ALTO")
k5.metric("Latencia", f"{lat}ms")

# Gráfico de 3 Ejes (USD, Cobre, Oro)
if not ctx["df"].empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD", line=dict(color='#00ff00', width=2)))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["HG=F"], name="Cobre", yaxis="y2", line=dict(color='#ff4b4b', dash='dash')))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["GC=F"], name="Oro", yaxis="y3", line=dict(color='#ffd700', dash='dot')))
    
    fig.update_layout(template="plotly_dark", height=380, margin=dict(l=0,r=0,t=0,b=0),
                      yaxis2=dict(anchor="free", overlaying="y", side="right", position=0.95),
                      yaxis3=dict(anchor="free", overlaying="y", side="right", position=0.90))
    st.plotly_chart(fig, use_container_width=True)

# Sidebar: Control de Misión
st.sidebar.header("🕹️ Operación Real ($100k)")
st.sidebar.warning(f"Spread Estimado: ${ctx['spread_est']:.2f} (Tu SL es $2.00)")

entry = st.sidebar.number_input("Precio Entrada XTB:", value=usd_val)
op_side = st.sidebar.radio("Dirección:", ["COMPRA", "VENTA"], horizontal=True)

if st.sidebar.checkbox("🔴 EJECUTAR CÁLCULO PnL"):
    pnl = (usd_val - entry) * 1000 if op_side == "COMPRA" else (entry - usd_val) * 1000
    st.sidebar.metric("PnL VIVO", f"${pnl:,.0f} CLP", delta=f"{usd_val-entry:.2f}")
    
    if pnl <= -2000: st.sidebar.error("🛑 STOP LOSS (-$2.000)")
    elif pnl >= 4000: st.sidebar.balloons()
    
    if st.sidebar.button("💾 Guardar en Bitácora"):
        log_trade(op_side, entry, pnl)
        st.sidebar.success("Guardado en CSV")
