# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import data_loader
import risk_manager
import news_filter
import config
from datetime import datetime

# Page Config
st.set_page_config(page_title="Antigravity Pro Dashboard", layout="wide", page_icon="🚀")

# --- STYLES ---
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .big-button {
        font-size: 20px !important;
        padding: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- STATE ---
if 'capital' not in st.session_state:
    st.session_state.capital = config.INITIAL_CAPITAL

# --- HELPER FUNCTIONS ---
def get_traffic_light(correlation, news_safe):
    if not news_safe:
        return "ROJO", "BLOQUEO DE SEGURIDAD (Noticias/Blackout)"
    
    if correlation > -0.4:
        return "ROJO", "BLOQUEO DE SEGURIDAD (Correlación Positiva/Baja)"
    elif -0.7 <= correlation <= -0.4:
        return "AMARILLO", "ESPERAR CONFIRMACIÓN (Rango Medio)"
    else: # correlation < -0.7
        return "VERDE", "EJECUTAR DISPARO (Correlación Ideal)"

def calculate_targets(entry_price):
    tp = entry_price + 2.5
    sl = entry_price - 1.5
    return tp, sl

# --- HEADER ---
st.title("🚀 Antigravity Pro Dashboard")
st.markdown("### Sistema de Cobertura USD/CLP + Gold")
st.markdown("---")

# --- DATA LOADING ---
with st.spinner('Conectando con el mercado (Live Data)...'):
    df = data_loader.fetch_market_data()

if df.empty:
    st.error("❌ Error de Conexión: No se pudieron obtener datos de Yahoo Finance.")
    st.stop()

current_usd = df['USD_Close'].iloc[-1]
current_gold = df['GOLD_Close'].iloc[-1]
correlation = df['USD_Close'].rolling(window=5).corr(df['GOLD_Close']).iloc[-1]
today = datetime.now().strftime("%Y-%m-%d")
news_status = news_filter.check_market_status(today)

# --- TRAFFIC LIGHT LOGIC ---
light_color, light_msg = get_traffic_light(correlation, news_status['safe'])

# --- DASHBOARD COLUMNS ---
col_charts, col_action = st.columns([2, 1])

with col_charts:
    st.subheader("📊 Análisis Técnico")
    
    # Chart 1: Normalize prices
    df_norm = df.copy()
    df_norm['USD_Norm'] = df_norm['USD_Close'] / df_norm['USD_Close'].iloc[0] * 100
    df_norm['GOLD_Norm'] = df_norm['GOLD_Close'] / df_norm['GOLD_Close'].iloc[0] * 100
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df_norm.index, y=df_norm['USD_Norm'], mode='lines', name='USD/CLP', line=dict(color='#00FF00', width=2)))
    fig1.add_trace(go.Scatter(x=df_norm.index, y=df_norm['GOLD_Norm'], mode='lines', name='Gold (GC=F)', line=dict(color='#FFD700', width=2)))
    fig1.update_layout(
        title="Divergencia USD vs Gold (Normalizado)",
        xaxis_title=None,
        yaxis_title="Índice Base 100",
        template="plotly_dark",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # Correlation Metric Display
    corr_color = "#00FF00" if correlation < -0.7 else "#FFFF00" if correlation <= -0.4 else "#FF0000"
    st.markdown(f"#### Correlación Actual (5h): <span style='color:{corr_color}; font-size:24px'>{correlation:.4f}</span>", unsafe_allow_html=True)

with col_action:
    # Traffic Light Display
    st.subheader("🚦 Semáforo de Trading")
    
    container_bg = "#1E1E1E"
    border_color = "#333333"
    
    if light_color == "VERDE":
        status_icon = "🟢"
        status_style = "background-color: rgba(0, 255, 0, 0.2); border: 2px solid #00FF00; color: #00FF00;"
    elif light_color == "AMARILLO":
        status_icon = "🟡"
        status_style = "background-color: rgba(255, 255, 0, 0.2); border: 2px solid #FFFF00; color: #FFFF00;"
    else:
        status_icon = "🔴"
        status_style = "background-color: rgba(255, 0, 0, 0.2); border: 2px solid #FF0000; color: #FF0000;"

    st.markdown(f"""
    <div style='padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; {status_style}'>
        <h2 style='margin:0'>{status_icon} {light_color}</h2>
        <p style='font-weight: bold; margin-top: 10px; font-size: 18px'>{light_msg}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Targets
    tp, sl = calculate_targets(current_usd)
    
    st.markdown("### 🎯 Objetivos")
    c1, c2, c3 = st.columns(3)
    c1.metric("Precio", f"${current_usd:.2f}")
    c2.metric("Take Profit", f"${tp:.2f}", delta="+2.5", delta_color="normal")
    c3.metric("Stop Loss", f"${sl:.2f}", delta="-1.5", delta_color="inverse")
    
    st.markdown("---")
    
    # Simulator
    st.subheader("🧮 Simulador Realista")
    
    spread_xtb = st.slider("Spread XTB (CLP)", min_value=0.0, max_value=2.0, value=0.5, step=0.1)
    volume = st.number_input("Volumen (Lotes/Contratos)", min_value=1, value=1000, step=100)
    
    if st.button("Simular Resultado (TP)", use_container_width=True):
        # Ganancia Neta = (Precio_Meta - Precio_Entrada) * Volumen - Spread_Cost
        # Caution: Spread usually applies to the opening and closing, effectively widening price.
        # Simple formula requested: (Meta - Entrada - Spread) * Volumen ? 
        # Or (Meta - Entrada) * Volume - Spread_Total_Cost?
        # User formula: (Price_Meta - Price_Entrada) * Volume - Spread
        # Interpreting "Spread" in the formula as 'Total Cost due to spread' or 'Spread per unit'?
        # Usually Spread XTB is per unit. So Net Move = Move - Spread.
        # Let's interpret user formula strictly but assume Spread is per unit cost sum.
        # Formula given: (Precio_Meta - Precio_Entrada) * Volumen - Spread
        # If Spread is the slider value (e.g. 0.5), it usually means 0.5 CLP per unit.
        # So total cost = Spread * Volume.
        # Let's assume the user meant: Result = ((TP - Entry) - Spread) * Volume
        
        gross_profit_per_unit = tp - current_usd # Should be 2.5
        net_profit_per_unit = gross_profit_per_unit - spread_xtb
        total_pnl = net_profit_per_unit * volume
        
        st.write(f"Movimiento Bruto: ${gross_profit_per_unit:.2f}")
        st.write(f"Costo Spread: -${spread_xtb:.2f}/u")
        
        if total_pnl > 0:
            st.success(f"💰 Ganancia Neta Proyectada: **${total_pnl:,.0f} CLP**")
        else:
            st.warning(f"📉 Pérdida Neta Proyectada: **${total_pnl:,.0f} CLP**")

# --- FOOTER ---
st.markdown("---")
st.caption(f"Antigravity Pro v2.0 | Capital: ${st.session_state.capital:,.0f} | Leverage: 1:{config.LEVERAGE}")
