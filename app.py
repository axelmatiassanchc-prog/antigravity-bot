import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(page_title="Antigravity Pro v2.0 - IA Trader", layout="wide")
st.markdown("""<style> .main { background-color: #0e1117; } </style>""", unsafe_allow_html=True)

# 2. CARGA DEL CEREBRO (MODELO ENTRENADO)
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

# 3. OBTENCIÓN DE DATOS (YAHOO FINANCE + XTB SECRETS)
def fetch_market_data():
    tickers = ["USDCLP=X", "GC=F"]
    # Descargamos datos de 1 minuto para máxima precisión en el gráfico
    data = yf.download(tickers, period="1d", interval="1m", threads=False)
    if not data.empty:
        df = data['Close'].ffill()
        return df
    return pd.DataFrame()

# 4. PROCESAMIENTO E INTELIGENCIA ARTIFICIAL
def analyze_market(df):
    if model is None or len(df) < 15:
        return 0, 0.0
    
    # Creamos las mismas columnas con las que se entrenó el modelo
    analysis_df = df.tail(30).copy()
    analysis_df['Returns_USD'] = analysis_df['USDCLP=X'].pct_change()
    analysis_df['Returns_Gold'] = analysis_df['GC=F'].pct_change()
    analysis_df['Volatility'] = analysis_df['USDCLP=X'].rolling(window=10).std()
    analysis_df['SMA_10'] = analysis_df['USDCLP=X'].rolling(window=10).mean()
    
    # Tomamos la última fila para la predicción
    latest_features = analysis_df[['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']].tail(1)
    
    if latest_features.isnull().values.any():
        return 0, 0.0
        
    prediction = model.predict(latest_features)[0]
    # Calculamos la probabilidad de éxito de la señal
    probability = model.predict_proba(latest_features).max()
    return prediction, probability

# 5. INTERFAZ GRÁFICA DEL DASHBOARD
st.title("🚀 Antigravity Pro v2.0")
st.caption(f"Terminal de Operaciones de Axel Sánchez | Hoy: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

df_data = fetch_market_data()

if not df_data.empty:
    current_usd = df_data['USDCLP=X'].iloc[-1]
    current_gold = df_data['GC=F'].iloc[-1]
    pred, confidence = analyze_market(df_data)
    
    # MÉTRICAS EN TIEMPO REAL
    m1, m2, m3 = st.columns(3)
    m1.metric("Dólar (USD/CLP)", f"${current_usd:,.2f}", f"{(current_usd - df_data['USDCLP=X'].iloc[0]):.2f}")
    m2.metric("Oro (GOLD)", f"${current_gold:,.2f}")
    m3.metric("Confianza de la IA", f"{confidence*100:.1f}%")

    # GRÁFICO PROFESIONAL
    st.divider()
    st.subheader("📊 Gráfico de Tendencia (1 Minuto)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_data.index, y=df_data['USDCLP=X'], mode='lines', name='USD/CLP', line=dict(color='#00ff00', width=2)))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # SEMÁFORO DE DECISIÓN
    st.divider()
    
    # Regla: 10:00 AM a 12:30 PM (Ventana de Oro Chile)
    hora_actual = datetime.now().hour
    minuto_actual = datetime.now().minute
    momento_operativo = 10 <= hora_actual < 13
    
    if pred == 1 and confidence > 0.65 and momento_operativo:
        st.success("🟢 SEÑAL VERDE: OPORTUNIDAD DE COMPRA DETECTADA")
        st.write(f"### 👉 Abrir en XTB: Lotes 0.01 | TP: ${current_usd + 2.5:.2f} | SL: ${current_usd - 1.5:.2f}")
    elif momento_operativo:
        st.warning("🟡 AMARILLO: ESPERAR CONFIRMACIÓN DEL MODELO")
    else:
        st.error("🔴 ROJO: MERCADO CERRADO O BAJA LIQUIDEZ")

# BARRA LATERAL
st.sidebar.title("Configuración")
st.sidebar.success("✅ Conectado a model.pkl" if model else "❌ model.pkl no encontrado")
st.sidebar.info(f"Usuario: {st.secrets.get('XTB_USER', 'No verificado')}")
if st.sidebar.button("Forzar Actualización"):
    st.rerun()
