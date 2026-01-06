import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime
import pytz
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CONFIGURACIÓN Y HORA DE CHILE
st.set_page_config(page_title="Antigravity Pro v2.0", layout="wide")
tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. CARGA DEL CEREBRO ML
@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        return joblib.load('model.pkl')
    return None

model = load_brain()

# 3. OBTENCIÓN DE DATOS ROBUSTA
@st.cache_data(ttl=30)
def fetch_data():
    tickers = ["USDCLP=X", "GC=F"]
    data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
    if data.empty: return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Close'].ffill()
    else:
        df = data.ffill()
    return df

# 4. INTELIGENCIA ARTIFICIAL
def get_ai_prediction(df):
    if model is None or len(df) < 15: return 0, 0.0
    tmp = df.tail(30).copy()
    tmp['Returns_USD'] = tmp['USDCLP=X'].pct_change()
    tmp['Returns_Gold'] = tmp['GC=F'].pct_change()
    tmp['Volatility'] = tmp['USDCLP=X'].rolling(window=10).std()
    tmp['SMA_10'] = tmp['USDCLP=X'].rolling(window=10).mean()
    features = tmp[['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']].tail(1)
    if features.isnull().values.any(): return 0, 0.0
    pred = model.predict(features)[0]
    prob = model.predict_proba(features).max()
    return pred, prob

# --- INTERFAZ ---
st.title("🚀 Antigravity Pro v2.0")
st.caption(f"Analista: Axel Sánchez | Hora Macul: {hora_chile.strftime('%H:%M:%S')}")

df_market = fetch_data()

if not df_market.empty:
    cols = df_market.columns.tolist()
    usd_col = next((c for c in cols if "USDCLP" in str(c)), None)
    gold_col = next((c for c in cols if "GC=F" in str(c)), None)

    if usd_col and gold_col:
        current_usd = df_market[usd_col].iloc[-1]
        current_gold = df_market[gold_col].iloc[-1]
        pred, confidence = get_ai_prediction(df_market)

        # MÉTRICAS PRINCIPALES
        m1, m2, m3 = st.columns(3)
        m1.metric("Dólar Actual", f"${current_usd:,.2f}")
        m2.metric("Oro Actual", f"${current_gold:,.2f}")
        m3.metric("Confianza IA", f"{confidence*100:.1f}%")

        # 5. GRÁFICO DUAL
        st.divider()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="USD/CLP", line=dict(color='#00ff00')), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="GOLD", line=dict(color='#ffbf00', dash='dot')), secondary_y=True)
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # 6. NUEVA SECCIÓN: PANEL DE OPERACIÓN XTB
        st.divider()
        st.subheader("📋 Parámetros de Orden para XTB")
        
        # Lógica de señales
        es_hora = 10 <= hora_chile.hour < 13
        
        if pred == 1 and confidence > 0.65 and es_hora:
            st.success("🔥 SEÑAL VERDE DETECTADA - COMPRAR AHORA")
            
            # Calculamos TP y SL automáticamente
            tp_valor = current_usd + 2.5
            sl_valor = current_usd - 1.5
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.info("📦 Volumen")
                st.code("0.01", language="text")
            with c2:
                st.info("💰 Precio Entrada")
                st.code(f"{current_usd:,.2f}", language="text")
            with c3:
                st.success("🎯 Take Profit")
                st.code(f"{tp_valor:,.2f}", language="text")
            with c4:
                st.error("🛡️ Stop Loss")
                st.code(f"{sl_valor:,.2f}", language="text")
                
            st.markdown("---")
            st.warning("⚠️ **Instrucción para Papá:** Abre xStation, pon el volumen en 0.01 y copia los valores de arriba antes de apretar el botón verde (BUY).")
            
        elif es_hora:
            st.warning("⏳ Analizando mercado... No hay señales claras todavía.")
        else:
            st.error(f"😴 Mercado Cerrado. Actual: {hora_chile.strftime('%H:%M')}. Abre a las 10:00 AM.")

# SIDEBAR
st.sidebar.title("Infraestructura")
st.sidebar.success("Cerebro ML: Conectado" if model else "Cerebro ML: No cargado")
if st.sidebar.button("Forzar Recarga"): st.rerun()
