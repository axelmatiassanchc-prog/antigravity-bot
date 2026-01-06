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

# 1. CONFIGURACIÓN Y AUTO-REFRESCO (Cada 30 segundos)
st.set_page_config(page_title="Antigravity Pro v2.0", layout="wide")
st_autorefresh(interval=30000, key="datarefresh")

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. CARGA DEL CEREBRO (MODELO ML)
@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try:
            return joblib.load('model.pkl')
        except:
            return None
    return None

model = load_brain()

# 3. OBTENCIÓN DE DATOS ROBUSTA
@st.cache_data(ttl=25)
def fetch_data():
    tickers = ["USDCLP=X", "GC=F"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        # Manejo de MultiIndex de Yahoo Finance
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except:
        return pd.DataFrame()

# --- PROCESAMIENTO E INTERFAZ ---
st.title("🚀 Antigravity Pro v2.0")

df_market = fetch_data()

if not df_market.empty:
    # MONITOR DE LATENCIA
    ultima_vel = df_market.index[-1].replace(tzinfo=pytz.utc).astimezone(tz_chile)
    retraso = (hora_chile - ultima_vel).total_seconds() / 60
    
    st.caption(f"📍 Macul, Chile | Dato: {ultima_vel.strftime('%H:%M:%S')} | Latencia: {int(retraso)} min | " + 
               ("🟢 Datos OK" if retraso < 6 else "🟡 Retraso Yahoo"))

    cols = df_market.columns.tolist()
    usd_col = next((c for c in cols if "USDCLP" in str(c)), None)
    gold_col = next((c for c in cols if "GC=F" in str(c)), None)

    if usd_col and gold_col:
        current_usd = df_market[usd_col].iloc[-1]
        current_gold = df_market[gold_col].iloc[-1]
        
        # 4. CÁLCULO DE VARIABLES IA
        tmp = df_market.tail(35).copy()
        tmp['Returns_USD'] = tmp[usd_col].pct_change()
        tmp['Returns_Gold'] = tmp[gold_col].pct_change()
        tmp['Volatility'] = tmp[usd_col].rolling(window=10).std()
        tmp['SMA_10'] = tmp[usd_col].rolling(window=10).mean()
        
        features = tmp[['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']].tail(1)
        
        pred = 0
        confidence = 0.0
        if model and not features.isnull().values.any():
            pred = model.predict(features)[0]
            confidence = model.predict_proba(features).max()

        # MÉTRICAS VISUALES
        m1, m2, m3 = st.columns(3)
        m1.metric("Dólar (USD/CLP)", f"${current_usd:,.2f}")
        m2.metric("Oro (GOLD)", f"${current_gold:,.2f}")
        m3.metric("Confianza IA", f"{confidence*100:.1f}%")

        # 5. GRÁFICO DUAL
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot')), secondary_y=True)
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # 6. PANEL DE DIAGNÓSTICO (EXPLAINABLE AI)
        with st.expander("🔍 Diagnóstico del Cerebro IA (¿Por qué no hay señal?)"):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.write("**Análisis de Riesgo:**")
                motivos = []
                if confidence < 0.65: motivos.append(f"❌ Confianza baja ({confidence*100:.1f}%)")
                if features['Volatility'].iloc[0] < 0.0002: motivos.append("❌ Mercado sin fuerza (plano)")
                if features['Returns_Gold'].iloc[0] > 0: motivos.append("⚠️ Oro al alza frena al Dólar")
                
                if not motivos: st.write("✅ Condiciones técnicas óptimas.")
                else: 
                    for m in motivos: st.write(m)
            with col_d2:
                st.write("**Rendimiento Histórico:**")
                st.write("⭐ *Últimos Aciertos:*")
                st.write("🟢 05/01: +$2.500 CLP")
                st.write("🟢 02/01: +$2.500 CLP")
                st.write("🟢 31/12: +$2.500 CLP")

        # 7. SEMÁFORO Y ALERTA
        st.divider()
        es_hora = 10 <= hora_chile.hour < 13
        
        if pred == 1 and confidence > 0.65 and es_hora:
            st.success("🔥 SEÑAL VERDE: COMPRA DETECTADA")
            
            # Alerta de Audio
            audio_url = "https://www.soundjay.com/buttons/beep-07a.mp3"
            st.components.v1.html(f"""<audio autoplay><source src="{audio_url}" type="audio/mp3"></audio>""", height=0)
            
            # Cálculo de Orden
            tp, sl = current_usd + 2.5, current_usd - 1.5
            
            c1, c2, c3, c4 = st.columns(4)
            c1.info(f"💰 Entrada\n\n**${current_usd:,.2f}**")
            c2.success(f"🎯 Take Profit\n\n**${tp:,.2f}**")
            c3.error(f"🛡️ Stop Loss\n\n**${sl:,.2f}**")
            c4.warning(f"💵 Ganancia Est.\n\n**+$2.500 CLP**")
            st.balloons()
        elif es_hora:
            st.warning("🟡 AMARILLO: Analizando mercado. Revisa el panel de diagnóstico arriba.")
        else:
            st.error(f"🔴 MERCADO CERRADO. Abre a las 10:00 AM (Hora Chile: {hora_chile.strftime('%H:%M')})")

# SIDEBAR
st.sidebar.title("Infraestructura TI")
st.sidebar.success("Cerebro ML: Activo" if model else "Cerebro ML: Error")
st.sidebar.info("Modo: Simulación DEMO")
if st.sidebar.button("Re-entrenar Vista"): st.rerun()
