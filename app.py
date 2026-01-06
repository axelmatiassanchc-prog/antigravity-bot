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
st.set_page_config(page_title="Antigravity Pro v3.3.1", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") 

# --- CONFIGURACIÓN CALLMEBOT (Activo 10/01) ---
WA_PHONE = "569XXXXXXXX" 
WA_API_KEY = "XXXXXX"

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
    tickers = ["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

# --- NÚCLEO DE LA APP ---
st.title("🚀 Antigravity Pro v3.3.1")
st.caption(f"📍 Macul, Chile | {hora_chile.strftime('%H:%M:%S')} | Multi-Asset & Margin Control")

model = load_brain()
df_market = fetch_all_data()

# ---------------------------------------------------------
# SIDEBAR: CALCULADORA DE MARGEN TI
# ---------------------------------------------------------
st.sidebar.title("💳 Control de Capital")
capital_total = 50000 # El capital de tu padre
st.sidebar.metric("Balance Estimado", f"${capital_total:,.0f} CLP")

st.sidebar.divider()
asset_select = st.sidebar.selectbox("Simular Activo", ["USD/CLP", "EUR/USD", "ORO"])
lotes = st.sidebar.number_input("Volumen (Lotes)", min_value=0.01, max_value=1.0, value=0.01, step=0.01)

# Lógica de Margen (Apalancamiento 1:100 estándar en Chile)
if not df_market.empty:
    usd_val = df_market.iloc[-1].filter(like="USDCLP").iloc[0]
    if asset_select == "USD/CLP":
        # Margen = (Lotes * 100.000 USD) / Apalancamiento
        margen_clp = (lotes * 100000 * 1) / 100 * usd_val / usd_val # Simplificado a USD 1000 * Lote
        margen_req = lotes * 1000 * usd_val / 100
    elif asset_select == "EUR/USD":
        eur_val = df_market.iloc[-1].filter(like="EURUSD").iloc[0]
        margen_req = (lotes * 100000 * eur_val) / 100 * usd_val
    else: # ORO
        gold_val = df_market.iloc[-1].filter(like="GC=F").iloc[0]
        margen_req = (lotes * 100 * gold_val) / 100 * usd_val / 20 # El oro suele pedir menos margen

    st.sidebar.warning(f"Margen a Retener: ${margen_req:,.0f} CLP")
    st.sidebar.info(f"Oxígeno Restante: ${capital_total - margen_req:,.0f} CLP")

# ---------------------------------------------------------
# DASHBOARD PRINCIPAL
# ---------------------------------------------------------
if not df_market.empty:
    tab1, tab2 = st.tabs(["💵 USD/CLP & Commodities", "🇪🇺 EUR/USD Trading"])

    with tab1:
        usd_col = next((c for c in df_market.columns if "USDCLP" in str(c)), None)
        gold_col = next((c for c in df_market.columns if "GC=F" in str(c)), None)
        cop_col = next((c for c in df_market.columns if "HG=F" in str(c)), None)

        if usd_col:
            # Gráfico con Parche Plotly v3.3.1
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))
            if gold_col: fig1.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
            if cop_col: fig1.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))

            fig1.update_layout(
                template="plotly_dark", height=450, margin=dict(l=50, r=160, t=30, b=20),
                xaxis=dict(domain=[0, 0.75]),
                yaxis=dict(title=dict(text="Dólar ($)", font=dict(color="#00ff00")), tickfont=dict(color="#00ff00")),
                yaxis2=dict(title=dict(text="Oro ($)", font=dict(color="#ffbf00")), tickfont=dict(color="#ffbf00"), anchor="free", overlaying="y", side="right", position=0.82),
                yaxis3=dict(title=dict(text="Cobre ($)", font=dict(color="#ff4b4b")), tickfont=dict(color="#ff4b4b"), anchor="free", overlaying="y", side="right", position=0.92),
                showlegend=True
            )
            st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        eur_col = next((c for c in df_market.columns if "EURUSD" in str(c)), None)
        if eur_col:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_market.index, y=df_market[eur_col], name="EUR/USD", line=dict(color='#3399ff', width=3)))
            fig2.update_layout(
                template="plotly_dark", height=450,
                yaxis=dict(title=dict(text="Euro ($)", font=dict(color="#3399ff")), tickfont=dict(color="#3399ff")),
                showlegend=True
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.metric("EUR/USD", f"{df_market[eur_col].iloc[-1]:,.4f}")

    # SEMÁFORO GLOBAL
    st.divider()
    if 10 <= hora_chile.hour < 13:
        st.success("📡 Vigilante Online: Escaneando oportunidades de 0.01 lotes...")
    else:
        st.error("💤 Modo Hibernación: Mercado sin liquidez para scalping.")
