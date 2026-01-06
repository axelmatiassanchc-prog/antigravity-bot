import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime

# 1. CONFIGURACIÓN Y CARGA DEL MODELO
st.set_page_config(page_title="Antigravity Pro - IA Trader", layout="wide")
MODEL_PATH = 'model.pkl'

@st.cache_resource
def load_brain():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

model = load_brain()

# 2. CONEXIÓN A DATOS (Yahoo Finance fallback con XTB Secrets)
def get_market_data():
    tickers = ["USDCLP=X", "GC=F"]
    # Intentamos obtener datos frescos para alimentar al modelo
    data = yf.download(tickers, period="1d", interval="1m", threads=False)
    if not data.empty:
        df = data['Close'].ffill()
        return df
    return pd.DataFrame()

# 3. LÓGICA DE PREDICCIÓN (MACHINE LEARNING)
def get_prediction(df):
    if model is None or len(df) < 10:
        return 0, 0.0
    
    # Preparamos las mismas variables que el entrenamiento
    last_prices = df.tail(20).copy()
    last_prices['Returns_USD'] = last_prices['USDCLP=X'].pct_change()
    last_prices['Returns_Gold'] = last_prices['GC=F'].pct_change()
    last_prices['Volatility'] = last_prices['USDCLP=X'].rolling(window=10).std()
    last_prices['SMA_10'] = last_prices['USDCLP=X'].rolling(window=10).mean()
    
    features = last_prices[['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']].tail(1)
    
    if features.isnull().values.any():
        return 0, 0.0
        
    pred = model.predict(features)[0]
    prob = model.predict_proba(features).max()
    return pred, prob

# 4. INTERFAZ DE USUARIO PARA TU PADRE
st.title("🚀 Antigravity Pro v2.0")
st.subheader(f"Analista TI: Axel Sánchez | Inversor: Papá")

df = get_market_data()

if not df.empty:
    current_usd = df['USDCLP=X'].iloc[-1]
    current_gold = df['GC=F'].iloc[-1]
    pred, confidence = get_prediction(df)
    
    # COLUMNAS DE PRECIO REAL
    col1, col2, col3 = st.columns(3)
    col1.metric("Dólar (USD/CLP)", f"${current_usd:.2f}")
    col2.metric("Oro (GOLD)", f"${current_gold:.2f}")
    col3.metric("Confianza IA", f"{confidence*100:.1f}%")

    # EL SEMÁFORO DE OPERACIÓN
    st.divider()
    
    # Condición de éxito: Modelo predice subida + Confianza > 65% + Horario ventana de oro
    is_gold_window = 10 <= datetime.now().hour < 13
    
    if pred == 1 and confidence > 0.65 and is_gold_window:
        st.success("🟢 SEÑAL VERDE: COMPRAR USD/CLP (Lotes: 0.01)")
        st.write(f"**TP Sugerido:** ${current_usd + 2.5:.2f} | **SL Sugerido:** ${current_usd - 1.5:.2f}")
    elif is_gold_window:
        st.warning("🟡 AMARILLO: MERCADO INESTABLE - ESPERAR")
    else:
        st.error("🔴 ROJO: FUERA DE HORARIO OPERATIVO")

# Barra lateral con estado de infraestructura
st.sidebar.header("Estado del Sistema")
if model:
    st.sidebar.success("🧠 Cerebro ML: Conectado")
else:
    st.sidebar.error("🧠 Cerebro ML: No encontrado")

st.sidebar.info(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
