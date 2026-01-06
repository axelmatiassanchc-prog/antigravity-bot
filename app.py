import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime
import plotly.graph_objects as go
import pytz # Librería para la hora de Chile

# 1. CONFIGURACIÓN DE PÁGINA Y ZONA HORARIA
st.set_page_config(page_title="Antigravity Pro v2.0", layout="wide")
tz_chile = pytz.timezone('America/Santiago')
hora_actual_chile = datetime.now(tz_chile)

# 2. CARGA DEL MODELO (CEREBRO ML)
MODEL_PATH = 'model.pkl'

@st.cache_resource
def load_trained_model():
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except:
            return None
    return None

model = load_trained_model()

# 3. OBTENCIÓN DE DATOS EN TIEMPO REAL
def fetch_market_data():
    tickers = ["USDCLP=X", "GC=F"]
    # Descargamos datos de 1 minuto para el gráfico interactivo
    data = yf.download(tickers, period="1d", interval="1m", threads=False)
    if not data.empty:
        df = data['Close'].ffill()
        return df
    return pd.DataFrame()

# 4. INTELIGENCIA ARTIFICIAL Y PREDICCIÓN
def analyze_market(df):
    if model is None or len(df) < 15:
        return 0, 0.0
    
    analysis_df = df.tail(30).copy()
    analysis_df['Returns_USD'] = analysis_df['USDCLP=X'].pct_change()
    analysis_df['Returns_Gold'] = analysis_df['GC=F'].pct_change()
    analysis_df['Volatility'] = analysis_df['USDCLP=X'].rolling(window=10).std()
    analysis_df['SMA_10'] = analysis_df['USDCLP=X'].rolling(window=10).mean()
    
    latest_features = analysis_df[['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']].tail(1)
    
    if latest_features.isnull().values.any():
        return 0, 0.0
        
    prediction = model.predict(latest_features)[0]
    probability = model.predict_proba(latest_features).max()
    return prediction, probability

# 5. DISEÑO DEL DASHBOARD
st.title("🚀 Antigravity Pro v2.0")
st.caption(f"Analista: Axel Sánchez | Hora Chile: {hora_actual_chile.strftime('%H:%M:%S')} | (UTC: {datetime.now().strftime('%H:%M')})")

df_data = fetch_market_data()

if not df_data.empty:
    current_usd = df_data['USDCLP=X'].iloc[-1]
    current_gold = df_data['GC=F'].iloc[-1]
    pred, confidence = analyze_market(df_data)
    
    # MÉTRICAS PRINCIPALES
    m1, m2, m3 = st.columns(3)
    m1.metric("Dólar (USD/CLP)", f"${current_usd:,.2f}", f"{(current_usd - df_data['USDCLP=X'].iloc[0]):.2f}")
    m2.metric("Oro (GOLD)", f"${current_gold:,.2f}")
    m3.metric("Confianza IA", f"{confidence*100:.1f}%")

    # GRÁFICO PROFESIONAL INTERACTIVO
    st.divider()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_data.index, y=df_data['USDCLP=X'], mode='lines', name='Dólar', line=dict(color='#00ff00')))
    fig.update_layout(template="plotly_dark", height=350, title="Tendencia USD/CLP (Hoy)")
    st.plotly_chart(fig, use_container_width=True)

    # SEMÁFORO DE SEÑALES
    st.divider()
    
    # Ventana operativa en Chile: 10:00 AM a 12:30 PM
    # Ahora usamos hora_actual_chile.hour para que coincida con tu reloj
    es_horario_valido = 10 <= hora_actual_chile.hour < 13
    
    if pred == 1 and confidence > 0.65 and es_horario_valido:
        st.success(f"🟢 SEÑAL VERDE: COMPRA DETECTADA (Confianza: {confidence*100:.0f}%)")
        st.info(f"👉 Sugerencia: Entrar en ${current_usd:,.2f} | TP: ${current_usd+2.5:.1f} | SL: ${current_usd-1.5:.1f}")
    elif es_horario_valido:
        st.warning("🟡 AMARILLO: ANALIZANDO MERCADO - ESPERAR SEÑAL FUERTE")
    else:
        st.error("🔴 ROJO: FUERA DE VENTANA OPERATIVA (10:00 - 12:30)")

# BARRA LATERAL
st.sidebar.header("Sistema")
st.sidebar.write(f"Estado Cerebro: {'✅ OK' if model else '❌ Sin model.pkl'}")
st.sidebar.write(f"Conectado como: {st.secrets.get('XTB_USER', 'Invitado')}")
if st.sidebar.button("Refrescar"):
    st.rerun()
