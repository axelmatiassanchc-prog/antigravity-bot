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
    data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
    if data.empty: return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Close'].ffill()
    else:
        df = data.ffill()
    return df

# 4. INTELIGENCIA ARTIFICIAL (PREDICCIÓN)
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

df_market = fetch_data()

if not df_market.empty:
    # MONITOR DE LATENCIA
    ultima_vel = df_market.index[-1].replace(tzinfo=pytz.utc).astimezone(tz_chile)
    retraso = (hora_chile - ultima_vel).total_seconds() / 60
    
    st.caption(f"Último dato: {ultima_vel.strftime('%H:%M:%S')} | Retraso: {int(retraso)} min | " + 
               ("🟢 OK" if retraso < 5 else "🟡 Delay Yahoo" if retraso < 15 else "🔴 Desactualizado"))

    cols = df_market.columns.tolist()
    usd_col = next((c for c in cols if "USDCLP" in str(c)), None)
    gold_col = next((c for c in cols if "GC=F" in str(c)), None)

    if usd_col and gold_col:
        current_usd = df_market[usd_col].iloc[-1]
        current_gold = df_market[gold_col].iloc[-1]
        pred, confidence = get_ai_prediction(df_market)

        # MÉTRICAS
        m1, m2, m3 = st.columns(3)
        m1.metric("Dólar Actual", f"${current_usd:,.2f}")
        m2.metric("Oro Actual", f"${current_gold:,.2f}")
        m3.metric("Confianza IA", f"{confidence*100:.1f}%")

        # 5. GRÁFICO DUAL
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00')), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot')), secondary_y=True)
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # 6. PANEL DE OPERACIÓN CON ALERTA DE AUDIO
        st.divider()
        es_hora = 10 <= hora_chile.hour < 13
        
        if pred == 1 and confidence > 0.65 and es_hora:
            st.success("🔥 SEÑAL VERDE DETECTADA - COMPRAR EN XTB")
            
            # --- ALERTA DE AUDIO (Hack HTML) ---
            audio_url = "https://www.soundjay.com/buttons/beep-07a.mp3"
            st.components.v1.html(f"""<audio autoplay><source src="{audio_url}" type="audio/mp3"></audio>""", height=0)
            
            tp = current_usd + 2.5
            sl = current_usd - 1.5
            profit_clp = 2500 # Para 0.01 lotes
            
            c1, c2, c3, c4 = st.columns(4)
            c1.info(f"💰 Entrada\n\n**${current_usd:,.2f}**")
            c2.success(f"🎯 Take Profit\n\n**${tp:,.2f}**")
            c3.error(f"🛡️ Stop Loss\n\n**${sl:,.2f}**")
            c4.warning(f"💵 Ganancia Est.\n\n**+${profit_clp:,.0f} CLP**")
            
            st.balloons() # Animación visual extra
        elif es_hora:
            st.warning("⏳ Analizando mercado... Esperando señal fuerte (>65%).")
        else:
            st.error(f"🔴 Mercado Cerrado (10:00 - 12:30). Hora actual: {hora_chile.strftime('%H:%M')}")

# SIDEBAR
st.sidebar.title("Configuración TI")
st.sidebar.write(f"Cerebro: {'✅ OK' if model else '❌ No cargado'}")
if st.sidebar.button("Forzar Recarga"): st.rerun()
