import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURACIÓN E INFRAESTRUCTURA
st.set_page_config(page_title="Antigravity Pro v3.7.0", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") 

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# Estados de sesión para Alarmas
if 'alarma_activa' not in st.session_state:
    st.session_state.alarma_activa = True

@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

def log_trade(operador, asset, signal_type, confidence, price, tp, sl):
    log_file = f'bitacora_{operador.lower()}.csv'
    new_entry = pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': operador, 'Activo': asset, 'Tipo': signal_type,
        'Confianza': f"{confidence*100:.1f}%", 'Precio_Entrada': price,
        'TP': tp, 'SL': sl
    }])
    if not os.path.isfile(log_file):
        new_entry.to_csv(log_file, index=False)
    else:
        new_entry.to_csv(log_file, mode='a', header=False, index=False)

@st.cache_data(ttl=25)
def fetch_all_data():
    tickers = ["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

# --- PROCESAMIENTO INICIAL ---
model = load_brain()
df_market = fetch_all_data()

# ---------------------------------------------------------
# SIDEBAR: CONTROL TOTAL
# ---------------------------------------------------------
st.sidebar.title("👥 Control de Operadores")
operador_activo = st.sidebar.radio("Operador actual:", ["Papa", "Axel"])

st.sidebar.divider()
st.sidebar.subheader("💰 Gestión de Capital (50k)")
capital_total = 50000

if not df_market.empty:
    usd_val = df_market.iloc[-1].filter(like="USDCLP").iloc[0]
    # Calculadora de Margen v3.3.1 re-integrada
    st.sidebar.write("**Margen Sugerido (1:100):**")
    m_verde = (0.01 * 1000 * usd_val) / 100
    m_super = (0.03 * 1000 * usd_val) / 100
    st.sidebar.caption(f"Verde (0.01): ${m_verde:,.0f} CLP")
    st.sidebar.caption(f"Súper (0.03): ${m_super:,.0f} CLP")

st.sidebar.divider()
st.sidebar.subheader("🔔 Alertas")
st.session_state.alarma_activa = st.sidebar.toggle("Sonido Global", value=st.session_state.alarma_activa)
if st.sidebar.button("🔇 SILENCIO INMEDIATO"):
    st.session_state.alarma_activa = False
    st.rerun()

# ---------------------------------------------------------
# DASHBOARD PRINCIPAL
# ---------------------------------------------------------
st.title("🚀 Antigravity Pro v3.7.0")

if not df_market.empty:
    usd_col = next((c for c in df_market.columns if "USDCLP" in str(c)), None)
    usd_actual = df_market[usd_col].iloc[-1]
    usd_prev = df_market[usd_col].iloc[-2] if len(df_market) > 1 else usd_actual
    
    # EAGLE EYE: Precio gigante
    d_color = "#00ff00" if usd_actual >= usd_prev else "#ff4b4b"
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 15px; border-radius: 10px; border-left: 10px solid {d_color}; text-align: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #888; font-size: 1.2rem;">USD/CLP EN VIVO</h2>
            <p style="margin: 0; color: {d_color}; font-size: 4.5rem; font-weight: bold;">${usd_actual:,.2f}</p>
        </div>
    """, unsafe_allow_html=True)

    # TABS: El regreso del Euro
    tab1, tab2 = st.tabs(["💵 Dólar & Commodities", "🇪🇺 Euro (EUR/USD)"])

    with tab1:
        gold_col = next((c for c in df_market.columns if "GC=F" in str(c)), None)
        cop_col = next((c for c in df_market.columns if "HG=F" in str(c)), None)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(domain=[0, 0.8]),
                          yaxis=dict(title="Dólar", tickfont=dict(color="#00ff00")),
                          yaxis2=dict(anchor="free", overlaying="y", side="right", position=0.85, tickfont=dict(color="#ffbf00")),
                          yaxis3=dict(anchor="free", overlaying="y", side="right", position=0.95, tickfont=dict(color="#ff4b4b")))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        eur_col = next((c for c in df_market.columns if "EURUSD" in str(c)), None)
        if eur_col:
            eur_val = df_market[eur_col].iloc[-1]
            st.metric("EUR/USD", f"{eur_val:,.4f}")
            fig_eur = go.Figure(go.Scatter(x=df_market.index, y=df_market[eur_col], line=dict(color='#3399ff')))
            fig_eur.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_eur, use_container_width=True)

    # ---------------------------------------------------------
    # SECCIÓN DE SEÑALES Y TP/SL
    # ---------------------------------------------------------
    st.divider()
    es_hora = 10 <= hora_chile.hour < 13
    conf_usd, conf_gold = 0.78, 0.72 # Simulación Súper Verde activa

    if es_hora:
        # LÓGICA SÚPER VERDE
        if conf_usd > 0.75 and conf_gold > 0.70:
            tp, sl = usd_actual + 3.50, usd_actual - 2.00
            st.info("💎 SÚPER VERDE: 0.03 Lotes")
            c1, c2, c3 = st.columns([2,2,1])
            c1.success(f"📈 TAKE PROFIT: **{tp:,.2f}**")
            c2.error(f"🛡️ STOP LOSS: **{sl:,.2f}**")
            if c3.button("STOP 🔇"):
                st.session_state.alarma_activa = False
                st.rerun()
            st.balloons()
            if st.session_state.alarma_activa:
                st.components.v1.html("""<audio autoplay loop><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>""", height=0)
        
        # LÓGICA VERDE SIMPLE
        elif conf_usd > 0.65:
            tp, sl = usd_actual + 2.50, usd_actual - 1.50
            st.success("🟢 SEÑAL VERDE: 0.01 Lotes")
            c1, c2 = st.columns(2)
            c1.success(f"📈 TP: {tp:,.2f}")
            c2.warning(f"🛡️ SL: {sl:,.2f}")
        else:
            st.warning("🟡 MODO SENTINELA: Analizando correlaciones...")
    else:
        st.error("🔴 MERCADO CERRADO (10:00 - 13:00)")

    # REGISTRO DE BITÁCORA
    st.sidebar.divider()
    if st.sidebar.button(f"💾 Registrar Trade {operador_activo}"):
        log_trade(operador_activo, "USD/CLP", "Super Verde" if conf_usd > 0.75 else "Verde", conf_usd, usd_actual, 0, 0)
        st.sidebar.toast("¡Datos guardados!")
