import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
import os
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. SETUP DE SEGURIDAD
st.set_page_config(page_title="SENTINEL v7.0 - REAL", layout="wide", page_icon="🛡️")
st_autorefresh(interval=3000, key="datarefresh") # 3s para estabilidad en tiempo real

FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"
tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. MOTOR DE DATOS HÍBRIDO (El "Corazón" del Sistema)
@st.cache_data(ttl=2)
def fetch_fast_usd():
    try: # Intento Turbo primero
        r = requests.get(f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}", timeout=1.5).json()
        return float(r.get('c', 0.0))
    except:
        return 0.0

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

# 3. LÓGICA DE AUDITORÍA
def log_real_trade(op, p_bot, p_xtb, lote, resultado):
    log_file = 'bitacora_real_100k.csv'
    pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': op, 'Precio_Bot': p_bot, 'Precio_XTB': p_xtb,
        'Lote': lote, 'Resultado_CLP': resultado
    }]).to_csv(log_file, mode='a', index=False, header=not os.path.exists(log_file))

# --- UI DASHBOARD ---
st.title("🛡️ SENTINEL v7.0: ESTRATEGIA $100K")

# Latency Check
t0 = time.time()
usd_val = fetch_fast_usd()
lat = int((time.time()-t0)*1000)
ctx = fetch_market_context()

# 4. EAGLE EYE INTEGRAL
stress = (usd_val > ctx["df"]["USDCLP=X"].tail(5).mean() and ctx["cobre"] > ctx["df"]["HG=F"].tail(5).mean()) if not ctx["df"].empty else False
d_color = "#ff4b4b" if stress else "#00ff00"

c_eye, c_info = st.columns([3, 1])
with c_eye:
    st.markdown(f"""
        <div style="background-color: #111; padding: 25px; border-radius: 15px; border-left: 10px solid {d_color}; text-align: center;">
            <h1 style="margin: 0; color: #888; font-size: 1.2rem;">USD/CLP REAL-TIME {"(DIVERGENCIA)" if stress else ""}</h1>
            <p style="margin: 0; color: {d_color}; font-size: 6.5rem; font-weight: bold;">${usd_val:,.2f}</p>
        </div>
    """, unsafe_allow_html=True)

with c_info:
    vol_lab = "❄️ BAJA" if ctx["std"] < 0.10 else "🟢 OK" if ctx["std"] < 0.25 else "🔥 ALTA"
    st.metric("VOLATILIDAD", vol_lab)
    st.metric("LATENCIA", f"{lat}ms", delta="ÓPTIMO" if lat < 600 else "LAG")

# 5. TABS DE ANÁLISIS (Reintegrados)
tab1, tab2, tab3 = st.tabs(["📊 Gráfico de Confluencia", "🌍 Contexto Global", "📝 Bitácora Real"])

with tab1:
    if not ctx["df"].empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["USDCLP=X"], name="USD", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["GC=F"], name="Oro", yaxis="y2", line=dict(color='#ffbf00', dash='dot')))
        fig.add_trace(go.Scatter(x=ctx["df"].index, y=ctx["df"]["HG=F"], name="Cobre", yaxis="y3", line=dict(color='#ff4b4b', dash='dash')))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=5, r=5, t=5, b=5),
                          yaxis2=dict(anchor="free", overlaying="y", side="right", position=0.85),
                          yaxis3=dict(anchor="free", overlaying="y", side="right", position=0.95))
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    col_a, col_b = st.columns(2)
    col_a.metric("EURO (EUR/USD)", f"{ctx['euro']:.4f}", help="Si el Euro sube, el Dólar global baja")
    col_b.metric("COBRE (HG)", f"${ctx['cobre']:.4f}")
    st.info("💡 Recordatorio: Si el Euro y el Cobre suben, la probabilidad de que el Dólar caiga es del 80%.")

with tab3:
    st.subheader("Registro de Operación $100k")
    p_xtb = st.number_input("Precio Real en XTB:", value=float(usd_val), step=0.01)
    if st.button("💾 Guardar Trade Real"):
        log_real_trade("Axel/Papa", usd_val, p_xtb, 0.01, (usd_val-p_xtb)*1000)
        st.success("Operación registrada en bitácora.")

# 6. PANEL DE RIESGO FIJO (Sidebar)
st.sidebar.header("🛡️ Parámetros $100k")
st.sidebar.write("Lote: **0.01**")
st.sidebar.success("🎯 Meta: +$4.000")
st.sidebar.error("🛡️ SL: -$2.000")

if st.sidebar.checkbox("Activar Calculador de Trade"):
    entry = st.sidebar.number_input("Precio Entrada:", value=usd_val)
    neta = (usd_val - entry) * 1000
    st.sidebar.metric("Ganancia/Pérdida", f"${neta:,.0f} CLP", delta=f"{usd_val-entry:.2f} CLP")
    if neta <= -2000: st.sidebar.warning("⚠️ ¡CIERRA SL!")
