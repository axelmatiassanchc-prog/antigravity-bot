import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime
import pytz
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. CONFIGURACIÓN DE PÁGINA Y HORA DE CHILE
st.set_page_config(page_title="Antigravity Pro v2.0", layout="wide")
tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. CARGA DEL MODELO (CEREBRO ML)
MODEL_PATH = 'model.pkl'

@st.cache_resource
def load_brain():
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            st.error(f"Error cargando el modelo: {e}")
            return None
    return None

model = load_brain()

# 3. OBTENCIÓN DE DATOS (DÓLAR Y ORO)
@st.cache_data(ttl=60)
def fetch_data():
    tickers = ["USDCLP=X", "GC=F"]
    # Descargamos 1 día con intervalo de 1 minuto para el gráfico
    data = yf.download(tickers, period="1d", interval="1m", threads=False)
    if not data.empty and 'Close' in data:
        return data['Close'].ffill()
    return pd.DataFrame()

# 4. INTELIGENCIA ARTIFICIAL (PREDICCIÓN)
def get_ai_prediction(df):
    if model is None or len(df) < 15:
        return 0, 0.0
    
    # Preparamos las variables exactamente como en el entrenamiento
    tmp = df.tail(30).copy()
    tmp['Returns_USD'] = tmp['USDCLP=X'].pct_change()
    tmp['Returns_Gold'] = tmp['GC=F'].pct_change()
    tmp['Volatility'] = tmp['USDCLP=X'].rolling(window=10).std()
    tmp['SMA_10'] = tmp['USDCLP=X'].rolling(window=10).mean()
    
    features = tmp[['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']].tail(1)
    
    if features.isnull().values.any():
        return 0, 0.0
        
    pred = model.predict(features)[0]
    prob = model.predict_proba(features).max()
    return pred, prob

# 5. INTERFAZ DEL DASHBOARD
st.title("🚀 Antigravity Pro v2.0")
st.caption(f"Analista: Axel Sánchez | Hora Chile: {hora_chile.strftime('%H:%M:%S')} | UTC: {datetime.now().strftime('%H:%M')}")

df_market = fetch_data()

if not df_market.empty:
    current_usd = df_market['USDCLP=X'].iloc[-1]
    current_gold = df_market['GC=F'].iloc[-1]
    pred, confidence = get_ai_prediction(df_market)

    # MÉTRICAS CLAVE
    m1, m2, m3 = st.columns(3)
    m1.metric("Dólar (USD/CLP)", f"${current_usd:,.2f}", f"{(current_usd - df_market['USDCLP=X'].iloc[0]):.2f}")
    m2.metric("Oro (GOLD)", f"${current_gold:,.2f}")
    m3.metric("Confianza IA", f"{confidence*100:.1f}%")

    # 6. GRÁFICO DUAL (DÓLAR VS ORO)
    st.divider()
    st.subheader("📊 Correlación Estratégica")
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Línea Dólar (Eje Principal)
    fig.add_trace(
        go.Scatter(x=df_market.index, y=df_market['USDCLP=X'], name="Dólar (Verde)", line=dict(color='#00ff00', width=3)),
        secondary_y=False,
    )
    
    # Línea Oro (Eje Secundario)
    fig.add_trace(
        go.Scatter(x=df_market.index, y=df_market['GC=F'], name="Oro (Amarillo)", line=dict(color='#ffbf00', width=2, dash='dot')),
        secondary_y=True,
    )
    
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # 7. SEMÁFORO DE OPERACIÓN
    st.divider()
    
    # Ventana de Oro en Chile: 10:00 AM a 12:30 PM
    es_horario_operativo = 10 <= hora_chile.hour < 13 and not (hora_chile.hour == 12 and hora_chile.minute > 30)
    
    if pred == 1 and confidence > 0.65 and es_horario_operativo:
        st.success(f"🟢 SEÑAL VERDE: COMPRA DETECTADA")
        st.write(f"### 👉 Sugerencia Papá: Entrar en ${current_usd:,.2f} | TP: ${current_usd+2.5:.1f} | SL: ${current_usd-1.5:.1f}")
    elif es_horario_operativo:
        st.warning("🟡 AMARILLO: ANALIZANDO TENDENCIAS - ESPERAR")
    else:
        st.error(f"🔴 ROJO: FUERA DE VENTANA OPERATIVA (Cierre 12:30)")

# BARRA LATERAL DE INFRAESTRUCTURA
st.sidebar.header("Estado TI")
st.sidebar.write(f"Cerebro ML: {'✅ Conectado' if model else '❌ Desconectado'}")
st.sidebar.write(f"XTB User: {st.secrets.get('XTB_USER', 'No detectado')}")
if st.sidebar.button("Forzar Recarga"):
    st.rerun()
