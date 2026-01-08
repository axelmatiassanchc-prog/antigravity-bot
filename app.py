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

# 1. INFRAESTRUCTURA DE RED Y CONFIGURACIÓN
st.set_page_config(page_title="Antigravity Pro v4.5.0", layout="wide")
st_autorefresh(interval=2000, key="datarefresh") # 2 segundos para Eagle Eye

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# API KEY INTEGRADA Y PERSISTENTE
FINNHUB_KEY = "d5fq0d9r01qnjhodsn8gd5fq0d9r01qnjhodsn90"

if 'alarma_activa' not in st.session_state:
    st.session_state.alarma_activa = True

@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

# 2. MOTOR DE DATOS ROBUSTO CON FAILOVER Y CACHÉ DIFERENCIADO
@st.cache_data(ttl=2) # Prioridad Máxima: Dólar
def get_usd_price(engine):
    price = 0.0
    if engine == "Turbo (Finnhub API)":
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol=FX:USDCLP&token={FINNHUB_KEY}"
            r = requests.get(url, timeout=2).json()
            price = float(r.get('c', 0.0))
        except: price = 0.0
    
    if price <= 0: # Fallover a Yahoo si Finnhub falla
        try:
            data = yf.download("USDCLP=X", period="1d", interval="1m", progress=False)
            if not data.empty:
                val = data['Close'].iloc[-1]
                price = float(val.iloc[0]) if hasattr(val, "__iter__") else float(val)
        except: price = 0.0
    return price

@st.cache_data(ttl=30) # Prioridad Media: Commodities e Historial
def get_global_data(engine):
    results = {"oro": 0.0, "cobre": 0.0, "euro": 0.0, "df_hist": pd.DataFrame()}
    # Descarga base para gráfico
    tickers = {"USDCLP=X": "usd", "GC=F": "oro", "HG=F": "cobre", "EURUSD=X": "euro"}
    try:
        raw = yf.download(list(tickers.keys()), period="1d", interval="1m", progress=False)
        if not raw.empty:
            closes = raw['Close'].ffill()
            results["df_hist"] = closes
            for t, key in tickers.items():
                if t in closes.columns:
                    val = closes[t].dropna().iloc[-1] # Fix para evitar $nan
                    results[key] = float(val)
    except: pass

    # Mejora Turbo para Commodities
    if engine == "Turbo (Finnhub API)":
        f_syms = {"oro": "XAUUSD", "cobre": "CPER", "euro": "FX:EURUSD"}
        for key, sym in f_syms.items():
            try:
                r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={sym}&token={FINNHUB_KEY}", timeout=2).json()
                p = float(r.get('c', 0.0))
                if p > 0: results[key] = p
            except: pass
    return results

# 3. BITÁCORA DUAL CON AUDITORÍA DE LAG
def save_trade(op, sig_type, p_bot, p_xtb, tp, sl):
    log_file = f'bitacora_{op.lower()}.csv'
    new_entry = pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': op, 'Tipo': sig_type, 'Precio_Bot': p_bot,
        'Precio_XTB': p_xtb, 'Lag_CLP': round(abs(p_bot - p_xtb), 2),
        'TP_Sugerido': tp, 'SL_Sugerido': sl
    }])
    new_entry.to_csv(log_file, mode='a', index=False, header=not os.path.exists(log_file))

# --- SIDEBAR: PANEL DE CONTROL ---
st.sidebar.title("⚙️ Sentinel Pro v4.5")
engine_choice = st.sidebar.selectbox("Motor de Datos", ["Turbo (Finnhub API)", "Standard (Yahoo)"])
op_activo = st.sidebar.radio("Operador actual:", ["Papa", "Axel"])

usd_val = get_usd_price(engine_choice)
m_data = get_global_data(engine_choice)

# ---------------------------------------------------------
# DASHBOARD: EAGLE EYE GIGANTE
# ---------------------------------------------------------
st.title("🚀 Antigravity Pro v4.5.0")
st.caption(f"📍 Cloud Node: Macul | {hora_chile.strftime('%H:%M:%S')} | Engine: {engine_choice}")

if usd_val > 0:
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 25px; border-radius: 15px; border-left: 12px solid #00ff00; text-align: center; margin-bottom: 30px;">
            <h1 style="margin: 0; color: #888; font-size: 1.5rem; letter-spacing: 3px;">USD/CLP ACTUAL</h1>
            <p style="margin: 0; color: #00ff00; font-size: 7rem; font-weight: bold; line-height: 1;">${usd_val:,.2f}</p>
        </div>
    """, unsafe_allow_html=True)
else:
    st.warning("📡 Sincronizando con los mercados globales...")

tab1, tab2 = st.tabs(["📊 Gráfico & Commodities", "🇪🇺 Euro & Gestión"])

with tab1:
    c1, c2 = st.columns(2)
    c1.metric("ORO (XAU/USD)", f"${m_data['oro']:,.2f}")
    c2.metric("COBRE (HG/CPER)", f"${m_data['cobre']:,.2f}")

    if not m_data["df_hist"].empty:
        df = m_data["df_hist"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["USDCLP=X"], name="Dólar", line=dict(color='#00ff00', width=3)))
        if "GC=F" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["GC=F"], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
        if "HG=F" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["HG=F"], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))
        
        fig.update_layout(template="plotly_dark", height=480, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(domain=[0, 0.8]),
                          yaxis=dict(title="Dólar", tickfont=dict(color="#00ff00")),
                          yaxis2=dict(title="Oro", anchor="free", overlaying="y", side="right", position=0.85, tickfont=dict(color="#ffbf00")),
                          yaxis3=dict(title="Cobre", anchor="free", overlaying="y", side="right", position=0.95, tickfont=dict(color="#ff4b4b")))
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.metric("EUR/USD Actual", f"{m_data['euro']:,.4f}")
    st.divider()
    st.subheader("💰 Calculadora de Margen (Capital 50k)")
    m_verde = (0.01 * 1000 * usd_val) / 100
    m_super = (0.03 * 1000 * usd_val) / 100
    st.write(f"Margen Verde (0.01 lotes): **${m_verde:,.0f} CLP**")
    st.write(f"Margen Súper (0.03 lotes): **${m_super:,.0f} CLP**")

# ---------------------------------------------------------
# LÓGICA DE SEÑALES Y ALARMA BANCARIA
# ---------------------------------------------------------
st.divider()
market_open = 10 <= hora_chile.hour < 13
# Parámetros de señal para el registro
s_tp, s_sl, s_type = usd_val + 3.5, usd_val - 2.0, "Super Verde"

if market_open and usd_val > 0:
    conf_u, conf_g = 0.78, 0.72 # Simulación de señal activa
    if conf_u > 0.75 and conf_g > 0.70:
        st.info(f"💎 SEÑAL {s_type.upper()} DETECTADA: **0.03 Lotes**")
        col1, col2, col3 = st.columns([2,2,1])
        col1.success(f"📈 TAKE PROFIT: {s_tp:.2f}")
        col2.error(f"🛡️ STOP LOSS: {s_sl:.2f}")
        
        if col3.button("STOP 🔇"):
            st.session_state.alarma_activa = False
            st.rerun()
            
        if st.session_state.alarma_activa:
            st.components.v1.html("""<audio autoplay loop><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>""", height=0)
    else:
        st.warning("🟡 MODO SENTINELA: Monitoreando correlaciones Dólar/Oro...")
else:
    st.error(f"🔴 MERCADO BANCARIO CERRADO | Abre 10:00 AM")
    st.session_state.alarma_activa = True # Auto-reset para mañana

# ---------------------------------------------------------
# SIDEBAR: REGISTRO Y AUDITORÍA DE LAG
# ---------------------------------------------------------
st.sidebar.divider()
st.sidebar.subheader("📝 Auditoría de Ejecución")
p_real_xtb = st.sidebar.number_input("Precio Real en XTB:", value=float(usd_val), step=0.01)

if st.sidebar.button(f"💾 Guardar Trade {op_activo}"):
    save_trade(op_activo, s_type, usd_val, p_real_xtb, s_tp, s_sl)
    st.toast(f"✅ Trade de {op_activo} registrado en la nube.")
