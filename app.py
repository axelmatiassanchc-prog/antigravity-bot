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
st.set_page_config(page_title="Antigravity Pro v3.0 - Copper Edition", layout="wide")
st_autorefresh(interval=30000, key="datarefresh")

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

# 2. CARGA DEL CEREBRO (Requiere re-entrenamiento con Cobre)
@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

model = load_brain()

# 3. OBTENCIÓN DE DATOS (TRIPLE CORRELACIÓN)
@st.cache_data(ttl=25)
def fetch_data():
    tickers = ["USDCLP=X", "GC=F", "HG=F"] # Añadimos Cobre
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

# --- INTERFAZ ---
st.title("🚀 Antigravity Pro v3.0")
st.caption("Integración: USD/CLP + ORO + COBRE | Monitoreo de Alta Fidelidad")

df_market = fetch_data()

if not df_market.empty:
    # MONITOR DE LATENCIA
    ultima_vel = df_market.index[-1].replace(tzinfo=pytz.utc).astimezone(tz_chile)
    retraso = (hora_chile - ultima_vel).total_seconds() / 60
    st.caption(f"📍 Macul | Último dato: {ultima_vel.strftime('%H:%M:%S')} | Latencia: {int(retraso)} min")

    # BUSCADOR ROBUSTO DE COLUMNAS
    cols = df_market.columns.tolist()
    usd_col = next((c for c in cols if "USDCLP" in str(c)), None)
    gold_col = next((c for c in cols if "GC=F" in str(c)), None)
    cop_col = next((c for c in cols if "HG=F" in str(c)), None)

    if usd_col and gold_col and cop_col:
        current_usd = df_market[usd_col].iloc[-1]
        current_gold = df_market[gold_col].iloc[-1]
        current_cop = df_market[cop_col].iloc[-1]

        # MÉTRICAS CUÁDRUPLES
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dólar", f"${current_usd:,.2f}")
        m2.metric("Oro", f"${current_gold:,.1f}")
        m3.metric("Cobre (Copper)", f"${current_cop:,.2f}")
        
        # 4. PREDICCIÓN CON COBRE
        tmp = df_market.tail(35).copy()
        tmp['Ret_USD'] = tmp[usd_col].pct_change()
        tmp['Ret_Gold'] = tmp[gold_col].pct_change()
        tmp['Ret_Cop'] = tmp[cop_col].pct_change() # Nueva característica
        tmp['Volat'] = tmp[usd_col].rolling(window=10).std()
        
        # Nota: El orden de features debe coincidir con tu nuevo entrenamiento
        features = tmp[['Ret_USD', 'Ret_Gold', 'Ret_Cop', 'Volat']].tail(1)
        
        confidence = 0.0
        if model and not features.isnull().values.any():
            try: confidence = model.predict_proba(features).max()
            except: st.sidebar.warning("⚠️ El modelo requiere re-entrenamiento para ver el Cobre.")

        m4.metric("Confianza IA", f"{confidence*100:.1f}%")

        # 5. GRÁFICO TRIPLE DE CORRELACIÓN
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot')), secondary_y=True)
        fig.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash')), secondary_y=True)
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

        # 6. DIAGNÓSTICO AVANZADO
        with st.expander("🔍 Análisis de Variables"):
            c1, c2 = st.columns(2)
            c1.write("**Impacto en el Dólar:**")
            if current_cop > df_market[cop_col].iloc[0]:
                st.write("🔴 **Cobre Subiendo:** Presión bajista para el dólar (Malo para compra).")
            else:
                st.write("🟢 **Cobre Bajando:** Camino libre para que el dólar suba (Bueno para compra).")
            
            c2.write("**Estado de Correlación:**")
            st.write(f"Oro: ${current_gold:,.1f} | Cobre: ${current_cop:,.2f}")

        # 7. PANEL DE ÓRDENES XTB
        st.divider()
        es_hora = 10 <= hora_chile.hour < 13
        
        if confidence > 0.65 and es_hora:
            st.success("🔥 SEÑAL VERDE: COMPRAR USD/CLP")
            audio_url = "https://www.soundjay.com/buttons/beep-07a.mp3"
            st.components.v1.html(f"""<audio autoplay><source src="{audio_url}" type="audio/mp3"></audio>""", height=0)
            
            tp, sl = current_usd + 2.5, current_usd - 1.5
            st.write(f"📦 Lote: **0.01** | 💰 Entrada: **${current_usd:,.2f}** | 🎯 TP: **${tp:,.2f}** | 🛡️ SL: **${sl:,.2f}**")
            st.warning(f"💵 Ganancia Estimada: **+$2.500 CLP**")
            st.balloons()
        else:
            st.warning("⏳ Analizando ciclo Dólar-Oro-Cobre. Esperando alineación de astros...")

# SIDEBAR
st.sidebar.title("Infraestructura v3.0")
if st.sidebar.button("Re-escanear"): st.rerun()
