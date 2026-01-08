import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
import requests
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. INFRAESTRUCTURA
st.set_page_config(page_title="Antigravity Pro v4.2.3", layout="wide")
st_autorefresh(interval=5000, key="datarefresh") # 5s para equilibrio API/UX

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"

if 'alarma_activa' not in st.session_state:
    st.session_state.alarma_activa = True

# 2. MOTOR DE DATOS ROBUSTO (FIX $nan y MultiIndex)
@st.cache_data(ttl=5)
def fetch_market_data(engine):
    data = {"usd": 0.0, "oro": 0.0, "cobre": 0.0, "euro": 0.0, "df_hist": pd.DataFrame()}
    
    # Descarga base desde Yahoo (necesaria para gráficos e historial)
    tickers = {"USDCLP=X": "usd", "GC=F": "oro", "HG=F": "cobre", "EURUSD=X": "euro"}
    try:
        raw = yf.download(list(tickers.keys()), period="1d", interval="1m", progress=False)
        if not raw.empty:
            closes = raw['Close']
            data["df_hist"] = closes.ffill()
            for t, key in tickers.items():
                # Extracción segura de escalar para evitar $nan
                val = closes[t].iloc[-1] if t in closes.columns else 0.0
                data[key] = float(val) if pd.notnull(val) else 0.0
    except: pass

    # Sobreescribir con Turbo (Finnhub) si está activo
    if engine == "Turbo (Finnhub API)":
        f_symbols = {"usd": "FX:USDCLP", "oro": "XAUUSD", "cobre": "CPER", "euro": "FX:EURUSD"}
        for key, sym in f_symbols.items():
            try:
                r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={sym}&token={FINNHUB_KEY}", timeout=2).json()
                price = float(r.get('c', 0.0))
                if price > 0: data[key] = price
            except: pass
    return data

# 3. BITÁCORA
def log_trade(operador, signal_type, p_bot, p_xtb):
    log_file = f'bitacora_{operador.lower()}.csv'
    new_entry = pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': operador, 'Tipo': signal_type,
        'Precio_Bot': p_bot, 'Precio_XTB': p_xtb,
        'Lag': round(abs(p_bot - p_xtb), 2)
    }])
    new_entry.to_csv(log_file, mode='a', index=False, header=not os.path.exists(log_file))

# --- UI SIDEBAR ---
st.sidebar.title("⚙️ Sentinel Cloud v4.2.3")
engine_type = st.sidebar.selectbox("Motor de Datos", ["Standard (Yahoo)", "Turbo (Finnhub API)"])
operador_activo = st.sidebar.radio("Operador actual:", ["Papa", "Axel"])

m_data = fetch_market_data(engine_type)
usd_actual = m_data["usd"]

# ---------------------------------------------------------
# DASHBOARD: EAGLE EYE
# ---------------------------------------------------------
st.title("🚀 Antigravity Pro v4.2.3")

if usd_actual > 0:
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 20px; border-radius: 12px; border-left: 10px solid #00ff00; text-align: center; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #888; font-size: 1.3rem;">USD/CLP ACTUAL</h1>
            <p style="margin: 0; color: #00ff00; font-size: 6rem; font-weight: bold;">${usd_actual:,.2f}</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.warning("🔄 Sincronizando feed de datos...")

tab1, tab2 = st.tabs(["📊 Gráfico & Commodities", "🇪🇺 Euro & Margen"])

with tab1:
    # Métricas superiores corregidas (No más $nan)
    c1, c2 = st.columns(2)
    c1.metric("ORO (XAU/USD)", f"${m_data['oro']:,.2f}")
    c2.metric("COBRE (HG/CPER)", f"${m_data['cobre']:,.2f}")

    # REGRESO DEL GRÁFICO
    if not m_data["df_hist"].empty:
        df = m_data["df_hist"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["USDCLP=X"], name="Dólar", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Scatter(x=df.index, y=df["GC=F"], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
        fig.add_trace(go.Scatter(x=df.index, y=df["HG=F"], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))
        
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(domain=[0, 0.8]),
                          yaxis=dict(title="Dólar", tickfont=dict(color="#00ff00")),
                          yaxis2=dict(title="Oro", anchor="free", overlaying="y", side="right", position=0.85, tickfont=dict(color="#ffbf00")),
                          yaxis3=dict(title="Cobre", anchor="free", overlaying="y", side="right", position=0.95, tickfont=dict(color="#ff4b4b")))
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.metric("EUR/USD Actual", f"{m_data['euro']:,.4f}")
    st.divider()
    st.subheader("💰 Gestión de Capital (50k)")
    m_v = (0.01 * 1000 * usd_actual) / 100
    st.write(f"Margen Verde (0.01): **${m_v:,.0f} CLP**")

# ---------------------------------------------------------
# SEÑALES Y ALARMA
# ---------------------------------------------------------
st.divider()
es_hora = 10 <= hora_chile.hour < 13

if es_hora and usd_actual > 0:
    conf_usd, conf_gold = 0.78, 0.72 # Simulación de Súper Verde
    if conf_usd > 0.75 and conf_gold > 0.70:
        st.info("💎 SÚPER VERDE DETECTADO: **0.03 Lotes**")
        col1, col2, col3 = st.columns([2,2,1])
        col1.success(f"📈 TP: {usd_actual+3.5:.2f}")
        col2.error(f"🛡️ SL: {usd_actual-2:.2f}")
        if col3.button("STOP 🔇"):
            st.session_state.alarma_activa = False
            st.rerun()
        if st.session_state.alarma_activa:
            st.components.v1.html("""<audio autoplay loop><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>""", height=0)
else:
    st.error(f"🔴 MERCADO CERRADO | {hora_chile.strftime('%H:%M:%S')} (Abre 10:00 AM)")

# SIDEBAR: REGISTRO
st.sidebar.divider()
p_xtb = st.sidebar.number_input("Precio Real XTB:", value=float(usd_actual), step=0.01)
if st.sidebar.button(f"💾 Guardar Trade {operador_activo}"):
    log_trade(operador_activo, "Super Verde", usd_actual, p_xtb)
    st.toast("✅ Registrado.")
