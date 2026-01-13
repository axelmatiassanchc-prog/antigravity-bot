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
# SENTINEL v9.4.3: HYBRID ENGINE
# Proyecto: GitHub (USD/CLP) - Independiente
# ==========================================

st.set_page_config(page_title="SENTINEL v9.4.3 - MONOLITH", layout="wide", page_icon="🛡️")

# OPTIMIZACIÓN DE TRÁFICO: 10 seg para asegurar estabilidad de API Free (6 RPM)
st_autorefresh(interval=10000, key="datarefresh") 

# CREDENCIALES
TD_KEY = "5028b1741eef4937a359ed068f95296d"
tz_chile = pytz.timezone('America/Santiago')

# 1. CAPA DE DATOS HÍBRIDA (Twelve Data + Yahoo)
@st.cache_data(ttl=5)
def fetch_data_monolith():
    fast_price, latency, source = 0.0, 0, "TWELVE DATA (RT)"
    t0 = time.time()
    
    # A. Precio Rápido: Solo USD/CLP (Símbolo gratuito en Twelve Data)
    try:
        url = f"https://api.twelvedata.com/price?symbol=USD/CLP&apikey={TD_KEY}"
        r_raw = requests.get(url, timeout=3.5)
        if r_raw.status_code == 200:
            res_json = r_raw.json()
            fast_price = float(res_json.get("price", 0.0))
            latency = int((time.time() - t0) * 1000)
        elif r_raw.status_code == 429:
            source = "⚠️ RATE LIMIT (BUSY)"
        else:
            source = f"API ERROR {r_raw.status_code}"
    except:
        source = "ERROR CONEXIÓN"

    ctx = {"oro": 0.0, "cobre": 0.0, "euro": 0.0, "df": pd.DataFrame(), "source": source, "spread_est": 0.45}
    
    # B. Contexto Metales y Historial (Yahoo Finance)
    try:
        raw = yf.download(["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"], period="1d", interval="1m", progress=False)
        if not raw.empty:
            c = raw['Close'].ffill().bfill()
            ctx["df"] = c
            ctx["oro"] = float(c["GC=F"].iloc[-1])
            ctx["cobre"] = float(c["HG=F"].iloc[-1])
            ctx["euro"] = float(c["EURUSD=X"].iloc[-1])
            
            # FAILOVER: Si Twelve Data no responde, usamos Yahoo
            if fast_price <= 1.0:
                fast_price = float(c["USDCLP=X"].iloc[-1])
                if "LIMIT" not in ctx["source"]:
                    ctx["source"] = "⚠️ YAHOO (FAILOVER)"
            
            # Spread Estimado Original
            high_v = raw['High']["USDCLP=X"].iloc[-1]
            low_v = raw['Low']["USDCLP=X"].iloc[-1]
            ctx["spread_est"] = 0.40 + ((high_v - low_v) * 0.1)
    except:
        st.sidebar.error("Falla crítica en descarga Yahoo")
    
    return fast_price, ctx, latency

# 2. SISTEMA DE BITÁCORA
def log_trade(action, price, pnl_est):
    file_name = 'bitacora_real_100k.csv'
    data = {'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"), 'Accion': action, 'Precio': price, 'PnL': pnl_est}
    pd.DataFrame([data]).to_csv(file_name, mode='a', index=False, header=not os.path.exists(file_name))

# --- EJECUCIÓN ---
usd_val, ctx, lat = fetch_data_monolith()

# 3. MOTOR DE DECISIÓN (Gatillo Inclusivo <=)
def get_final_verdict(df, rt_cobre):
    if df.empty or len(df) < 15: 
        return "⌛ INICIALIZANDO...", "#555", False, 0.0, 0.0
    
    try:
        s_usd = df['USDCLP=X'].tail(20)
        s_cu = df['HG=F'].tail(20)
        s_au = df['GC=F'].tail(20)
        c_cu = s_usd.corr(s_cu)
        c_au = s_usd.corr(s_au)
    except:
        return "⚙️ ERROR CÁLCULO", "#555", False, 0.0, 0.0
    
    # Lógica de Divergencia
    if c_cu > 0.20: return "⚠️ STRESS / DIVERGENCIA", "#ff9900", False, c_cu, c_au
    
    # Tendencia de Cobre
    avg_cu_hist = s_cu.tail(10).mean()
    val_cu = rt_cobre - avg_cu_hist 
    
    # GATILLO MAESTRO (Fix Inclusivo)
    umbral = -0.58
    if c_cu <= umbral:
        if val_cu < 0: return "💎 SÚPER VERDE (COMPRA)", "#00ff00", True, c_cu, c_au
        if val_cu > 0: return "🔥 SÚPER ROJO (VENTA)", "#ff4b4b", True, c_cu, c_au
        
    return "⚖️ NEUTRO / ESPERA", "#3399ff", False, c_cu, c_au

res = get_final_verdict(ctx["df"], ctx["cobre"])
sig_text, sig_color, play_audio, corr_cu_val, corr_au_val = res

# --- DASHBOARD ---
st.title("🛡️ SENTINEL v9.4.3: THE MONOLITH")

# Alerta Sonora
if play_audio:
    st.components.v1.html(f"""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mp3"></audio>""", height=0)

# Semáforo Principal
st.markdown(f"""<div style="background-color: {sig_color}; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 20px; border: 2px solid rgba(255,255,255,0.1);">
    <h1 style="margin: 0; color: #000; font-size: 3rem; font-weight: bold;">{sig_text}</h1></div>""", unsafe_allow_html=True)

# Panel de Instrumentos
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("USD/CLP", f"${usd_val:,.2f}", delta=ctx["source"])
k2.metric("Corr Cobre", f"{corr_cu_val:.2f}", delta="OK" if corr_cu_val <= -0.58 else "OUT")
k3.metric("ORO (GC=F)", f"${ctx['oro']:,.1f}")
k4.metric("EURO/USD", f"{ctx['euro']:.4f}")
k5.metric("Spread Est.", f"${ctx['spread_est']:.2f}")
k6.metric("Latencia", f"{lat}ms")

# Gráfico Triádico (USD, Cobre, Oro)
if not ctx["df"].empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD", line=dict(color='#00ff00', width=2.5)))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["HG=F"], name="Cobre", yaxis="y2", line=dict(color='#ff4b4b', dash='dash')))
    fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["GC=F"], name="Oro", yaxis="y3", line=dict(color='#ffd700', dash='dot')))
    
    fig.update_layout(template="plotly_dark", height=420, margin=dict(l=0,r=0,t=10,b=0),
        yaxis2=dict(anchor="free", overlaying="y", side="right", position=0.98),
        yaxis3=dict(anchor="free", overlaying="y", side="right", position=0.93),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

# Sidebar: Control de Misión
st.sidebar.header("🕹️ Operación Real ($100k)")
st.sidebar.write(f"**Data Status:** {ctx['source']}")
st.sidebar.write(f"**Corr Au:** {corr_au_val:.2f}")

entry = st.sidebar.number_input("Precio Entrada XTB:", value=usd_val, step=0.01)
op_side = st.sidebar.radio("Dirección:", ["COMPRA", "VENTA"], horizontal=True)

if st.sidebar.checkbox("🔴 MOSTRAR PnL VIVO"):
    pnl = (usd_val - entry) * 1000 if op_side == "COMPRA" else (entry - usd_val) * 1000
    st.sidebar.metric("PnL VIVO", f"${pnl:,.0f} CLP", delta=f"{usd_val-entry:.2f}")
    if pnl <= -2000: st.sidebar.error("🛑 STOP LOSS (-$2.000)")
    elif pnl >= 4000: st.sidebar.success("🎯 TAKE PROFIT SUGERIDO")
    
    if st.sidebar.button("💾 Guardar en Bitácora"):
        log_trade(op_side, entry, pnl)
        st.sidebar.toast("Operación registrada en CSV")
