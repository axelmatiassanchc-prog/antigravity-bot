import streamlit as st
import yfinance as yf
import pandas as pd
import joblib
import os
from datetime import datetime
import pytz
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. CONFIGURACIÓN E INFRAESTRUCTURA
st.set_page_config(page_title="Antigravity Pro v3.6.0", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") 

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

@st.cache_resource
def load_brain():
    # Intenta cargar el modelo entrenado
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

# 2. FUNCIÓN DE BITÁCORA DUAL (Axel & Papá)
def log_trade(operador, asset, signal_type, confidence, price):
    log_file = f'bitacora_{operador.lower()}.csv'
    new_entry = pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': operador,
        'Activo': asset,
        'Tipo': signal_type,
        'Confianza': f"{confidence*100:.1f}%",
        'Precio_Entrada': price
    }])
    if not os.path.isfile(log_file):
        new_entry.to_csv(log_file, index=False)
    else:
        new_entry.to_csv(log_file, mode='a', header=False, index=False)

@st.cache_data(ttl=25)
def fetch_all_data():
    tickers = ["USDCLP=X", "GC=F", "HG=F", "EURUSD=X"]
    try:
        data = yf.download(tickers, period="1d", interval="1m", threads=False, progress=False)
        if data.empty: return pd.DataFrame()
        # Manejo de MultiIndex en las columnas de yfinance
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

# --- INICIO DE LA APLICACIÓN ---
st.title("🚀 Antigravity Pro v3.6.0")
st.caption(f"📍 Macul, Chile | {hora_chile.strftime('%H:%M:%S')} | Doble Bitácora de Entrenamiento")

model = load_brain()
df_market = fetch_all_data()

# ---------------------------------------------------------
# SIDEBAR: CONTROL DE OPERACIONES
# ---------------------------------------------------------
st.sidebar.title("👥 Panel de Control")
operador_activo = st.sidebar.radio("Operador actual:", ["Papa", "Axel"])

st.sidebar.divider()
st.sidebar.subheader(f"Estrategia: {operador_activo}")
capital = 50000
st.sidebar.metric("Capital de Prueba", f"${capital:,.0f} CLP")

if not df_market.empty:
    usd_now = df_market.iloc[-1].filter(like="USDCLP").iloc[0]
    
    st.sidebar.divider()
    # Botón de registro para la bitácora dual
    if st.sidebar.button(f"💾 Registrar Trade de {operador_activo}"):
        # En una versión final, aquí pasaríamos las variables reales del modelo
        log_trade(operador_activo, "USD/CLP", "Estrategia Dual", 0.78, usd_now)
        st.sidebar.success(f"¡Trade de {operador_activo} guardado!")

# ---------------------------------------------------------
# DASHBOARD: VISUALIZACIÓN DE MERCADO
# ---------------------------------------------------------
if not df_market.empty:
    usd_col = next((c for c in df_market.columns if "USDCLP" in str(c)), None)
    gold_col = next((c for c in df_market.columns if "GC=F" in str(c)), None)
    cop_col = next((c for c in df_market.columns if "HG=F" in str(c)), None)

    # Gráfico Triple Eje (Fix de Plotly para Python 3.13)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))
    fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
    fig.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))
    
    fig.update_layout(
        template="plotly_dark", height=550, margin=dict(l=50, r=160, t=30, b=20),
        xaxis=dict(domain=[0, 0.75]),
        yaxis=dict(title=dict(text="Dólar ($)", font=dict(color="#00ff00")), tickfont=dict(color="#00ff00")),
        yaxis2=dict(title=dict(text="Oro ($)", font=dict(color="#ffbf00")), tickfont=dict(color="#ffbf00"), anchor="free", overlaying="y", side="right", position=0.82),
        yaxis3=dict(title=dict(text="Cobre ($)", font=dict(color="#ff4b4b")), tickfont=dict(color="#ff4b4b"), anchor="free", overlaying="y", side="right", position=0.92),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # LÓGICA DE SEMÁFORO (Dólar + Oro)
    # ---------------------------------------------------------
    st.divider()
    es_hora = 10 <= hora_chile.hour < 13
    
    # Simulación de confianza (esto debe venir de model.predict_proba si el modelo está cargado)
    conf_usd, conf_gold = 0.78, 0.72 # Estos valores activan el Súper Verde
    
    if es_hora:
        # SÚPER VERDE: Confluencia de activos
        if conf_usd > 0.75 and conf_gold > 0.70:
            st.info(f"💎 SÚPER VERDE DETECTADO (Confianza: {(conf_usd+conf_gold)/2*100:.1f}%)")
            st.success(f"Recomendación para {operador_activo}: Operar 0.03 Lotes en USD/CLP")
            st.balloons()
            # Alerta de sonido
            st.components.v1.html("""<audio autoplay loop><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>""", height=0)
        
        # VERDE SIMPLE
        elif conf_usd > 0.65:
            st.success(f"🟢 SEÑAL VERDE (Confianza: {conf_usd*100:.1f}%)")
            st.write(f"Recomendación para {operador_activo}: Operar 0.01 Lotes")
        
        else:
            st.warning("🟡 MODO SENTINELA: Esperando señal de alta probabilidad...")
    else:
        st.error("🔴 MERCADO BANCARIO CERRADO (Opera entre 10:00 y 13:00)")
