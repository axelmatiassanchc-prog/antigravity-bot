import yfinance as yf
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import os

def train_antigravity_brain():
    print("🚀 Iniciando entrenamiento Versión 3.0 (Cobre Integrado)...")
    
    # 1. DEFINICIÓN DE ACTIVOS
    # USDCLP=X (Dólar Chile), GC=F (Oro), HG=F (Cobre)
    tickers = ["USDCLP=X", "GC=F", "HG=F"]
    
    # Descargamos datos de los últimos 60 días con intervalo de 5 minutos
    # Esto da una base de datos más amplia que el intervalo de 1 minuto
    print("📥 Descargando datos históricos de Yahoo Finance...")
    data = yf.download(tickers, period="60d", interval="5m", threads=True)
    
    if data.empty:
        print("❌ Error: No se pudieron obtener datos. Abortando.")
        return

    # 2. LIMPIEZA Y ALINEACIÓN
    df = data['Close'].ffill().dropna()
    
    # Renombramos para facilitar el manejo
    df.columns = ['Cobre', 'Oro', 'Dolar']
    
    print(f"✅ Datos alineados. Registros procesados: {len(df)}")

    # 3. FEATURE ENGINEERING (Ingeniería de Variables)
    print("🧠 Calculando indicadores técnicos...")
    
    # Retornos porcentuales (Lo que el bot "ve" para predecir)
    df['Ret_USD'] = df['Dolar'].pct_change()
    df['Ret_Gold'] = df['Oro'].pct_change()
    df['Ret_Cop'] = df['Cobre'].pct_change() # Nueva variable clave
    
    # Volatilidad y Tendencia
    df['Volat'] = df['Dolar'].rolling(window=10).std()
    df['SMA_10'] = df['Dolar'].rolling(window=10).mean()
    
    # 4. DEFINICIÓN DEL TARGET (Lo que queremos que aprenda)
    # Queremos predecir si en los próximos 15 minutos el precio subirá
    # 1 = Señal Verde (Compra), 0 = No hacer nada
    df['Target'] = np.where(df['Dolar'].shift(-3) > df['Dolar'], 1, 0)
    
    # Limpiamos valores nulos generados por los cálculos
    df = df.dropna()

    # 5. ENTRENAMIENTO DEL MODELO
    # Seleccionamos las columnas que usaremos en la APP
    features = ['Ret_USD', 'Ret_Gold', 'Ret_Cop', 'Volat']
    X = df[features]
    y = df['Target']

    # Dividimos datos: 80% entrenamiento, 20% prueba
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("🤖 Entrenando Random Forest (100 árboles)...")
    model = RandomForestClassifier(
        n_estimators=100, 
        max_depth=10, 
        random_state=42,
        class_weight='balanced' # Importante para no dar señales falsas
    )
    
    model.fit(X_train, y_train)

    # 6. VALIDACIÓN Y EXPORTACIÓN
    accuracy = model.score(X_test, y_test)
    print(f"📊 Precisión del modelo: {accuracy*100:.2f}%")

    # Guardamos el cerebro
    joblib.dump(model, 'model.pkl')
    print("💾 ¡Archivo model.pkl generado y guardado con éxito!")

if __name__ == "__main__":
    train_antigravity_brain()
