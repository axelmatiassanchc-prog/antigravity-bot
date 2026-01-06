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
st.set_page_config(page_title="Antigravity Pro v3.3.0", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") 

# --- CONFIGURACIÓN CALLMEBOT (Activo desde el 10/01) ---
WA_PHONE = "569XXXXXXXX" # Reemplaza con tu número
WA_API_KEY = "XXXXXX"    # Reemplaza con tu clave

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

def enviar_whatsapp(mensaje):
    url = f"https://api.callmebot.com/whatsapp.php?phone={WA_PHONE}&text={mensaje}&apikey={WA_API_KEY}"
    try: requests.get(url, timeout=5)
    except: pass

@st.cache_data(ttl=25)
def fetch_all_data():
    # Descargamos todo de una vez para optimizar latencia
    tickers = ["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

# --- NÚCLEO DE LA APP ---
st.title("🚀 Antigravity Pro v3.3.0")
st.caption(f"📍 Macul, Chile | {hora_chile.strftime('%H:%M:%S')} | Multi-Asset System")

model = load_brain()
df_market = fetch_all_data()

if not df_market.empty:
    # Definición de pestañas
    tab1, tab2 = st.tabs(["💵 USD/CLP & Commodities", "🇪🇺 EUR/USD Trading"])

    # ---------------------------------------------------------
    # PESTAÑA 1: USD/CLP, ORO Y COBRE
    # ---------------------------------------------------------
    with tab1:
        usd_col = next((c for c in df_market.columns if "USDCLP" in str(c)), None)
        gold_col = next((c for c in df_market.columns if "GC=F" in str(c)), None)
        cop_col = next((c for c in df_market.columns if "HG=F" in str(c)), None)

        if usd_col and gold_col and cop_col:
            current_usd = df_market[usd_col].iloc[-1]
            
            # Gráfico de Triple Eje (Fix Plotly)
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))
            fig1.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
            fig1.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))

            fig1.update_layout(
                template="plotly_dark", height=450, margin=dict(l=50, r=160, t=30, b=20),
                xaxis=dict(domain=[0, 0.75]),
                yaxis=dict(title=dict(text="Dólar ($)", font=dict(color="#00ff00")), tickfont=dict(color="#00ff00")),
                yaxis2=dict(title=dict(text="Oro ($)", font=dict(color="#ffbf00")), tickfont=dict(color="#ffbf00"), anchor="free", overlaying="y", side="right", position=0.82),
                yaxis3=dict(title=dict(text="Cobre ($)", font=dict(color="#ff4b4b")), tickfont=dict(color="#ff4b4b"), anchor="free", overlaying="y", side="right", position=0.92),
                showlegend=True
            )
            st.plotly_chart(fig1, use_container_width=True)
            st.metric("Estatus USD/CLP", f"${current_usd:,.2f}")

    # ---------------------------------------------------------
    # PESTAÑA 2: EUR/USD (EURO)
    # ---------------------------------------------------------
    with tab2:
        eur_col = next((c for c in df_market.columns if "EURUSD" in str(c)), None)
        if eur_col:
            current_eur = df_market[eur_col].iloc[-1]
            
            # Gráfico Euro (Simple para no confundir)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_market.index, y=df_market[eur_col], name="EUR/USD", line=dict(color='#3399ff', width=3)))
            fig2.update_layout(
                template="plotly_dark", height=450,
                yaxis=dict(title=dict(text="Euro ($)", font=dict(color="#3399ff")), tickfont=dict(color="#3399ff")),
                showlegend=True
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            st.metric("Estatus EUR/USD", f"{current_eur:,.4f}")
            st.info("💡 El Euro tiene un spread más bajo en XTB. Ideal para scalping rápido.")

    # --- LÓGICA GLOBAL DE SEMÁFORO (CORRE SIEMPRE) ---
    st.divider()
    es_hora = 10 <= hora_chile.hour < 13
    
    # Aquí puedes añadir la lógica de predicción para el Euro también
    if es_hora:
        st.success("✅ Sistema Vigilante Activo: Buscando señales en Dólar y Euro...")
    else:
        st.error("🔴 Fuera de horario: Mercado sin volumen.")

# SIDEBAR
st.sidebar.title("Configuración TI")
st.sidebar.warning("WhatsApp: CallMeBot reabre 10/01")
if st.sidebar.button("Test Sonido Alerta"):
    st.components.v1.html("""<audio autoplay><source src="https://www.soundjay.com/buttons/beep-07a.mp3" type="audio/mp3"></audio>""", height=0)
