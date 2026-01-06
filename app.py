import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh # NUEVO: Auto-refresco

# 1. CONFIGURACIÓN Y AUTO-REFRESCO (Cada 30 segundos)
st.set_page_config(page_title="Antigravity Pro v2.0", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") # 30000ms = 30s

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. CARGA DEL CEREBRO ML
@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        return joblib.load('model.pkl')
    return None

model = load_brain()

# 3. OBTENCIÓN DE DATOS Y MONITOR DE LATENCIA
@st.cache_data(ttl=20)
def fetch_data():
    tickers = ["USDCLP=X", "GC=F"]
    data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
    if data.empty: return pd.DataFrame()
    df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
    return df

# --- INTERFAZ ---
st.title("🚀 Antigravity Pro v2.0")

df_market = fetch_data()

if not df_market.empty:
    # Monitor de Latencia: ¿Están frescos los datos?
    ultima_actualizacion = df_market.index[-1].replace(tzinfo=pytz.utc).astimezone(tz_chile)
    retraso = (hora_chile - ultima_actualizacion).total_seconds() / 60
    
    status_color = "🟢 Datos al día" if retraso < 5 else "🟡 Retraso en Yahoo" if retraso < 15 else "🔴 Datos Desactualizados"
    st.caption(f"Actualizado: {ultima_actualizacion.strftime('%H:%M:%S')} | Estado: {status_color} ({int(retraso)} min de delay)")

    cols = df_market.columns.tolist()
    usd_col = next((c for c in cols if "USDCLP" in str(c)), None)
    gold_col = next((c for c in cols if "GC=F" in str(c)), None)

    if usd_col and gold_col:
        current_usd = df_market[usd_col].iloc[-1]
        current_gold = df_market[gold_col].iloc[-1]

        # MÉTRICAS PRINCIPALES
        m1, m2, m3 = st.columns(3)
        m1.metric("Dólar Actual", f"${current_usd:,.2f}")
        m2.metric("Oro Actual", f"${current_gold:,.2f}")
        
        # 4. INTELIGENCIA ARTIFICIAL (PREDICCIÓN)
        tmp = df_market.tail(30).copy()
        tmp['Returns_USD'] = tmp['USDCLP=X'].pct_change()
        tmp['Returns_Gold'] = tmp['GC=F'].pct_change()
        tmp['Volatility'] = tmp['USDCLP=X'].rolling(window=10).std()
        tmp['SMA_10'] = tmp['USDCLP=X'].rolling(window=10).mean()
        features = tmp[['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']].tail(1)
        
        confidence = 0.0
        if not features.isnull().values.any() and model:
            confidence = model.predict_proba(features).max()
        
        m3.metric("Confianza IA", f"{confidence*100:.1f}%")

        # 5. GRÁFICO DUAL
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="USD/CLP", line=dict(color='#00ff00')), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="GOLD", line=dict(color='#ffbf00', dash='dot')), secondary_y=True)
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # 6. PANEL DE OPERACIÓN XTB CON CALCULADORA CLP
        st.divider()
        st.subheader("📋 Parámetros de Orden para XTB (0.01 Lotes)")
        
        es_hora = 10 <= hora_chile.hour < 13
        
        if confidence > 0.65 and es_hora:
            st.success("🔥 SEÑAL DE COMPRA DETECTADA")
            tp = current_usd + 2.5
            sl = current_usd - 1.5
            # Cálculo de pesos: 1 punto = $1.000 CLP en 0.01 lotes
            profit_clp = 2.5 * 1000 
            
            c1, c2, c3, c4 = st.columns(4)
            c1.info(f"💰 Entrada\n\n**${current_usd:,.2f}**")
            c2.success(f"🎯 Take Profit\n\n**${tp:,.2f}**")
            c3.error(f"🛡️ Stop Loss\n\n**${sl:,.2f}**")
            c4.warning(f"💵 Ganancia Est.\n\n**+${profit_clp:,.0f} CLP**")
        else:
            st.warning("⏳ Esperando confirmación de tendencia o apertura de mercado...")

# SIDEBAR
st.sidebar.title("Sistema")
st.sidebar.write(f"Cerebro: {'✅ OK' if model else '❌ Sin model.pkl'}")
st.sidebar.info("Modo: Simulación DEMO")
