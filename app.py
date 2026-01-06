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

# 1. CONFIGURACIÓN E INFRAESTRUCTURA
st.set_page_config(page_title="Antigravity Pro v3.2.3", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") 

# --- CONFIGURACIÓN CALLMEBOT (Suspendido hasta el 10/01) ---
WA_PHONE = "569XXXXXXXX" # Reemplaza con tu número
WA_API_KEY = "XXXXXX"    # Reemplaza con tu clave
# ---------------------------------------------------------

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

def enviar_whatsapp(mensaje):
    # Revertido a la API de CallMeBot
    url = f"https://api.callmebot.com/whatsapp.php?phone={WA_PHONE}&text={mensaje}&apikey={WA_API_KEY}"
    try: requests.get(url, timeout=5)
    except: pass

@st.cache_data(ttl=25)
def fetch_data():
    tickers = ["USDCLP=X", "GC=F", "HG=F"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

# --- INTERFAZ ---
st.title("🚀 Antigravity Pro v3.2.3")
st.caption(f"📍 Macul, Chile | {hora_chile.strftime('%H:%M:%S')} | Triple Eje (Fix Plotly)")

model = load_brain()
df_market = fetch_data()

if not df_market.empty:
    cols = df_market.columns.tolist()
    usd_col = next((c for c in cols if "USDCLP" in str(c)), None)
    gold_col = next((c for c in cols if "GC=F" in str(c)), None)
    cop_col = next((c for c in cols if "HG=F" in str(c)), None)

    if usd_col and gold_col and cop_col:
        current_usd = df_market[usd_col].iloc[-1]
        current_gold = df_market[gold_col].iloc[-1]
        current_cop = df_market[cop_col].iloc[-1]

        # CÁLCULO DE PREDICCIÓN IA
        tmp = df_market.tail(35).copy()
        tmp['Ret_USD'] = tmp[usd_col].pct_change()
        tmp['Ret_Gold'] = tmp[gold_col].pct_change()
        tmp['Ret_Cop'] = tmp[cop_col].pct_change()
        tmp['Volat'] = tmp[usd_col].rolling(window=10).std()
        
        features = tmp[['Ret_USD', 'Ret_Gold', 'Ret_Cop', 'Volat']].tail(1)
        pred, confidence = 0, 0.0
        if model and not features.isnull().values.any():
            pred = model.predict(features)[0]
            confidence = model.predict_proba(features).max()

        # MÉTRICAS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("USD/CLP", f"${current_usd:,.2f}")
        m2.metric("ORO", f"${current_gold:,.1f}")
        m3.metric("COBRE", f"${current_cop:,.2f}")
        m4.metric("IA Confianza", f"{confidence*100:.1f}%")

        # --- GRÁFICO DE TRIPLE EJE (SOLUCIÓN AL VALUEERROR) ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))

        fig.update_layout(
            template="plotly_dark", height=450, margin=dict(l=50, r=160, t=30, b=20),
            xaxis=dict(domain=[0, 0.75]),
            yaxis=dict(
                title="Dólar ($)", 
                title_font=dict(color="#00ff00"), 
                tick_font=dict(color="#00ff00")
            ),
            yaxis2=dict(
                title="Oro ($)", 
                title_font=dict(color="#ffbf00"), 
                tick_font=dict(color="#ffbf00"), 
                anchor="free", overlaying="y", side="right", position=0.82
            ),
            yaxis3=dict(
                title="Cobre ($)", 
                title_font=dict(color="#ff4b4b"), 
                tick_font=dict(color="#ff4b4b"), 
                anchor="free", overlaying="y", side="right", position=0.92
            ),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- SEMÁFORO ---
        st.divider()
        es_hora = 10 <= hora_chile.hour < 13
        if pred == 1 and confidence > 0.65 and es_hora:
            st.success("🔥 SEÑAL VERDE: COMPRA")
            st.components.v1.html("""<audio autoplay><source src="https://www.soundjay.com/buttons/beep-07a.mp3" type="audio/mp3"></audio>""", height=0)
            
            # Alerta WA (Legacy CallMeBot)
            if 'last_wa' not in st.session_state or (datetime.now() - st.session_state.last_wa).seconds > 300:
                msg = f"🚀*ANTIGRAVITY*%0AVerde Detectado%0AEntrada: ${current_usd:,.2f}"
                enviar_whatsapp(msg)
                st.session_state.last_wa = datetime.now()
            st.balloons()
        elif es_hora:
            st.warning("🟡 AMARILLO: Analizando...")
        else:
            st.error("🔴 MERCADO CERRADO (Opera 10:00 - 13:00)")

# SIDEBAR
st.sidebar.title("Infraestructura")
st.sidebar.warning("WhatsApp: CallMeBot reabre el 10/01")
if st.sidebar.button("Re-entrenar Vista"): st.rerun()
