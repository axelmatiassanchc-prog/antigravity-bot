import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

# 1. CONFIGURACIÓN DE PARÁMETROS TÉCNICOS
# Usamos USD/CLP y Oro (GC=F) por la correlación inversa que utiliza el bot
TICKERS = ["USDCLP=X", "GC=F"]
PERIODO = "6mo"  # Entrenamos con los últimos 6 meses de historia
INTERVALO = "1h" # Datos por hora para coincidir con la visualización H1 de XTB

def prepare_data():
    print(f"Descargando datos históricos para {TICKERS}...")
    data = yf.download(TICKERS, period=PERIODO, interval=INTERVALO)['Close']
    
    # Limpieza: eliminamos valores nulos
    df = data.dropna().copy()
    
    # 2. INGENIERÍA DE VARIABLES (FEATURES)
    # Calculamos indicadores para que el bot aprenda a leer el mercado
    df['Returns_USD'] = df['USDCLP=X'].pct_change()
    df['Returns_Gold'] = df['GC=F'].pct_change()
    
    # Volatilidad móvil y medias (indicadores clave para el modelo)
    df['Volatility'] = df['USDCLP=X'].rolling(window=10).std()
    df['SMA_10'] = df['USDCLP=X'].rolling(window=10).mean()
    
    # 3. DEFINICIÓN DEL OBJETIVO (TARGET)
    # El bot debe aprender a predecir si el precio subirá +2.5 CLP en las próximas 3 horas
    # Usamos .shift(-3) para mirar hacia el futuro durante el entrenamiento
    df['Target'] = (df['USDCLP=X'].shift(-3) - df['USDCLP=X'] > 2.5).astype(int)
    
    return df.dropna()

def train():
    df = prepare_data()
    
    # Definimos las variables que el modelo analizará
    features = ['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']
    X = df[features]
    y = df['Target']
    
    # 4. ENTRENAMIENTO DEL MODELO (RANDOM FOREST)
    print("Iniciando entrenamiento del modelo Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100, 
        max_depth=10, 
        random_state=42
    )
    model.fit(X, y)
    
    # 5. EXPORTACIÓN DEL CEREBRO
    # Guardamos el modelo para que 'app.py' pueda cargarlo instantáneamente
    joblib.dump(model, 'model.pkl')
    print("¡Modelo optimizado y guardado como 'model.pkl'!")

if __name__ == "__main__":
    train()