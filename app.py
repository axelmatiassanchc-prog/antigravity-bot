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
st.set_page_config(page_title="Antigravity Pro v3.6.1", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") 

tz_chile = pytz.timezone('America/Santiago')
hora_chile = datetime.now(tz_chile)

@st.cache_resource
def load_brain():
    if os.path.exists('model.pkl'):
        try: return joblib.load('model.pkl')
        except: return None
    return None

# 2. FUNCIÓN DE BITÁCORA DUAL (Axel & Papá)
def log_trade(operador, asset, signal_type, confidence, price, tp, sl):
    log_file = f'bitacora_{operador.lower()}.csv'
    new_entry = pd.DataFrame([{
        'Fecha': datetime.now(tz_chile).strftime("%Y-%m-%d %H:%M:%S"),
        'Operador': operador,
        'Activo': asset,
        'Tipo': signal_type,
        'Confianza': f"{confidence*100:.1f}%",
        'Precio_Entrada': price,
        'TP': tp,
        'SL': sl
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
        df = data['Close'].ffill() if isinstance(data.columns, pd.MultiIndex) else data.ffill()
        return df
    except: return pd.DataFrame()

# --- PROCESAMIENTO ---
st.title("🚀 Antigravity Pro v3.6.1")
st.caption(f"📍 Macul, Chile | {hora_chile.strftime('%H:%M:%S')} | Doble Bitácora + TP/SL Automático")

model = load_brain()
df_market = fetch_all_data()

# ---------------------------------------------------------
# SIDEBAR: PANEL DE CONTROL Y REGISTRO
# ---------------------------------------------------------
st.sidebar.title("👥 Control de Operadores")
operador_activo = st.sidebar.radio("Operador actual:", ["Papa", "Axel"])

st.sidebar.divider()
st.sidebar.subheader(f"Estrategia: {operador_activo}")
capital = 50000
st.sidebar.metric("Capital de Prueba", f"${capital:,.0f} CLP")

# ---------------------------------------------------------
# DASHBOARD PRINCIPAL
# ---------------------------------------------------------
if not df_market.empty:
    usd_col = next((c for c in df_market.columns if "USDCLP" in str(c)), None)
    gold_col = next((c for c in df_market.columns if "GC=F" in str(c)), None)
    cop_col = next((c for c in df_market.columns if "HG=F" in str(c)), None)
    usd_actual = df_market[usd_col].iloc[-1]

    # Gráfico Triple Eje
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_market.index, y=df_market[usd_col], name="Dólar", line=dict(color='#00ff00', width=3)))
    fig.add_trace(go.Scatter(x=df_market.index, y=df_market[gold_col], name="Oro", line=dict(color='#ffbf00', dash='dot'), yaxis="y2"))
    fig.add_trace(go.Scatter(x=df_market.index, y=df_market[cop_col], name="Cobre", line=dict(color='#ff4b4b', dash='dash'), yaxis="y3"))
    
    fig.update_layout(
        template="plotly_dark", height=500, margin=dict(l=50, r=160, t=30, b=20),
        xaxis=dict(domain=[0, 0.75]),
        yaxis=dict(title=dict(text="Dólar ($)", font=dict(color="#00ff00")), tickfont=dict(color="#00ff00")),
        yaxis2=dict(title=dict(text="Oro ($)", font=dict(color="#ffbf00")), tickfont=dict(color="#ffbf00"), anchor="free", overlaying="y", side="right", position=0.82),
        yaxis3=dict(title=dict(text="Cobre ($)", font=dict(color="#ff4b4b")), tickfont=dict(color="#ff4b4b"), anchor="free", overlaying="y", side="right", position=0.92),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # LÓGICA DE SEMÁFORO CON TP/SL DINÁMICO
    # ---------------------------------------------------------
    st.divider()
    es_hora = 10 <= hora_chile.hour < 13
    
    # Probabilidades de simulación (ajustar a model.predict_proba si se desea)
    conf_usd, conf_gold = 0.78, 0.72 
    
    current_tp, current_sl, current_type = 0, 0, "Ninguna"

    if es_hora:
        # 💎 ESCENARIO SÚPER VERDE
        if conf_usd > 0.75 and conf_gold > 0.70:
            current_type = "Súper Verde"
            current_tp = usd_actual + 3.50
            current_sl = usd_actual - 2.00
            
            st.info(f"💎 SÚPER VERDE DETECTADO: **0.03 Lotes**")
            c1, c2 = st.columns(2)
            c1.success(f"📈 TAKE PROFIT (Meta): **{current_tp:,.2f}**")
            c2.error(f"🛡️ STOP LOSS (Seguridad): **{current_sl:,.2f}**")
            st.balloons()
            st.components.v1.html("""<audio autoplay loop><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mp3"></audio>""", height=0)
        
        # 🟢 ESCENARIO VERDE SIMPLE
        elif conf_usd > 0.65:
            current_type = "Verde"
            current_tp = usd_actual + 2.50
            current_sl = usd_actual - 1.50
            
            st.success(f"🟢 SEÑAL VERDE: **0.01 Lotes**")
            c1, c2 = st.columns(2)
            c1.success(f"📈 TAKE PROFIT: **{current_tp:,.2f}**")
            c2.warning(f"🛡️ STOP LOSS: **{current_sl:,.2f}**")
        
        else:
            st.warning("🟡 MODO SENTINELA: Esperando señal confirmada...")

        # Botón de registro en el Sidebar usando los valores calculados
        st.sidebar.divider()
        if st.sidebar.button(f"💾 Registrar Entrada de {operador_activo}"):
            log_trade(operador_activo, "USD/CLP", current_type, conf_usd, usd_actual, current_tp, current_sl)
            st.sidebar.success(f"Trade guardado en bitacora_{operador_activo.lower()}.csv")
            
    else:
        st.error("🔴 MERCADO CERRADO (Opera entre 10:00 y 13:00)")
