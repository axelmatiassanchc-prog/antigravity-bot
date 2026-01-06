import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime
import pytz
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURACIÓN Y AUTO-REFRESCO
st.set_page_config(page_title="Antigravity Pro v3.1", layout="wide")
st_autorefresh(interval=30000, key="datarefresh")

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

model = load_brain()

@st.cache_data(ttl=25)
def fetch_data():
    tickers = ["USDCLP=X", "GC=F", "HG=F"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

st.title("🚀 Antigravity Pro v3.1 - Copper Edition")

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

        # --- GRÁFICO PROFESIONAL DE 3 EJES ---
        fig = go.Figure()

        # Eje 1: Dólar (Principal)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))

        # Eje 2: Oro (Derecha)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))

        # Eje 3: Cobre (Derecha Extrema)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))

        fig.update_layout(
            template="plotly_dark",
            height=400,
            margin=dict(l=50, r=100, t=20, b=20),
            xaxis=dict(domain=[0, 0.85]), # Espacio para el tercer eje
            yaxis=dict(title="Dólar ($)", titlefont=dict(color="#00ff00"), tickfont=dict(color="#00ff00")),
            yaxis2=dict(title="Oro ($)", titlefont=dict(color="#ffbf00"), tickfont=dict(color="#ffbf00"), anchor="free", overlaying="y", side="right", position=0.85),
            yaxis3=dict(title="Cobre ($)", titlefont=dict(color="#ff4b4b"), tickfont=dict(color="#ff4b4b"), anchor="free", overlaying="y", side="right", position=0.95),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

        # MÉTRICAS Y SEMÁFORO (Igual al anterior)
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("USD/CLP", f"${current_usd:,.2f}")
        m2.metric("GOLD", f"${current_gold:,.1f}")
        m3.metric("COPPER", f"${current_cop:,.2f}")

        # ... (Mantén el resto del código de diagnóstico y órdenes de la v3.0)
