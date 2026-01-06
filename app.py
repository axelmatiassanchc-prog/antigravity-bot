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
st.set_page_config(page_title="Antigravity Pro v3.2 - Sentinel", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") # Refresco cada 30s

# Configuración de WhatsApp (CallMeBot)
# Reemplaza con tus datos reales obtenidos del bot
WA_PHONE = "569XXXXXXXX" 
WA_API_KEY = "XXXXXX"

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. FUNCIONES DE APOYO
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
def fetch_data():
    tickers = ["USDCLP=X", "GC=F", "HG=F"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

# --- INTERFAZ DE USUARIO ---
st.title("🚀 Antigravity Pro v3.2")
st.caption(f"Nodo: Macul, Chile | {hora_chile.strftime('%d/%m/%Y %H:%M:%S')}")

model = load_brain()
df_market = fetch_data()

if not df_market.empty:
    # Identificación de Columnas
    cols = df_market.columns.tolist()
    usd_col = next((c for c in cols if "USDCLP" in str(c)), None)
    gold_col = next((c for c in cols if "GC=F" in str(c)), None)
    cop_col = next((c for c in cols if "HG=F" in str(c)), None)

    if usd_col and gold_col and cop_col:
        current_usd = df_market[usd_col].iloc[-1]
        current_gold = df_market[gold_col].iloc[-1]
        current_cop = df_market[cop_col].iloc[-1]

        # 3. MÉTRICAS PRINCIPALES
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dólar (USD/CLP)", f"${current_usd:,.2f}")
        m2.metric("Oro (Gold)", f"${current_gold:,.1f}")
        m3.metric("Cobre (Copper)", f"${current_cop:,.2f}")

        # Predicción IA
        tmp = df_market.tail(35).copy()
        tmp['Ret_USD'] = tmp[usd_col].pct_change()
        tmp['Ret_Gold'] = tmp[gold_col].pct_change()
        tmp['Ret_Cop'] = tmp[cop_col].pct_change()
        tmp['Volat'] = tmp[usd_col].rolling(window=10).std()
        
        features = tmp[['Ret_USD', 'Ret_Gold', 'Ret_Cop', 'Volat']].tail(1)
        pred, confidence = 0, 0.0
        
        if model and not features.isnull().values.any():
            pred = model.predict(features)[0]
            confidence = model.predict_proba(features).max()
        
        m4.metric("Confianza IA", f"{confidence*100:.1f}%")

        # 4. GRÁFICO DE TRIPLE EJE CORREGIDO
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))

        fig.update_layout(
            template="plotly_dark", height=450, margin=dict(l=50, r=150, t=20, b=20),
            xaxis=dict(domain=[0, 0.8]),
            yaxis=dict(title="Dólar ($)", titlefont=dict(color="#00ff00"), tickfont=dict(color="#00ff00")),
            yaxis2=dict(title="Oro ($)", titlefont=dict(color="#ffbf00"), tickfont=dict(color="#ffbf00"), anchor="free", overlaying="y", side="right", position=0.85),
            yaxis3=dict(title="Cobre ($)", titlefont=dict(color="#ff4b4b"), tickfont=dict(color="#ff4b4b"), anchor="free", overlaying="y", side="right", position=0.95),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

        # 5. DIAGNÓSTICO Y ALERTAS
        with st.expander("🔍 Diagnóstico del Cerebro IA"):
            motivos = []
            if confidence < 0.65: motivos.append(f"❌ Confianza baja ({confidence*100:.1f}%)")
            if features['Volat'].iloc[0] < 0.0002: motivos.append("❌ Mercado sin fuerza")
            if current_cop > df_market[cop_col].iloc[0]: motivos.append("⚠️ Cobre al alza frena al Dólar")
            
            for m in motivos: st.write(m)
            if not motivos: st.write("✅ Todo alineado para operar.")

        # 6. LÓGICA DE SEMÁFORO Y WHATSAPP
        st.divider()
        es_hora = 10 <= hora_chile.hour < 13
        
        if pred == 1 and confidence > 0.65 and es_hora:
            st.success("🔥 SEÑAL VERDE: COMPRA DETECTADA")
            
            # Audio Alerta
            st.components.v1.html("""<audio autoplay><source src="https://www.soundjay.com/buttons/beep-07a.mp3" type="audio/mp3"></audio>""", height=0)
            
            # WhatsApp (Evitar spam con session_state)
            msg = f"🚀 *ANTIGRAVITY VERDE*%0AEntrada: ${current_usd:,.2f}%0AConfianza: {confidence*100:.1f}%%0A🎯 TP: ${current_usd+2.5:,.2f}%0A🛡️ SL: ${current_usd-1.5:,.2f}"
            if 'last_wa' not in st.session_state or (datetime.now() - st.session_state.last_wa).seconds > 300:
                enviar_whatsapp(msg)
                st.session_state.last_wa = datetime.now()

            st.balloons()
            st.info(f"💰 Sugerencia: COMPRA 0.01 lotes | TP: {current_usd+2.5:.2f} | SL: {current_usd-1.5:.2f}")
        elif es_hora:
            st.warning("🟡 AMARILLO: Analizando... No operar aún.")
        else:
            st.error("🔴 MERCADO CERRADO (10:00 - 13:00 ventana ideal)")

# SIDEBAR
st.sidebar.title("Infraestructura")
st.sidebar.info(f"Cerebro: {'Activo' if model else 'Error'}")
if st.sidebar.button("Forzar Refresco"): st.rerun()
