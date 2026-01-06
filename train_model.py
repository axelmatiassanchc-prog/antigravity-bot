import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import time # Para añadir pausas entre reintentos

TICKERS = ["USDCLP=X", "GC=F"]
PERIODO = "6mo"
INTERVALO = "1h"

def prepare_data():
    # Intentamos la descarga hasta 3 veces para evitar fallos de red temporales
    for i in range(3):
        try:
            print(f"Intento {i+1}: Descargando datos para {TICKERS}...")
            # 'threads=False' evita el error 'database is locked' en servidores compartidos
            data = yf.download(TICKERS, period=PERIODO, interval=INTERVALO, threads=False)
            
            if not data.empty and 'Close' in data:
                df = data['Close'].dropna().copy()
                if len(df) > 50: # Aseguramos que haya datos suficientes
                    print(f"Descarga exitosa. Filas obtenidas: {len(df)}")
                    
                    # Ingeniería de variables
                    df['Returns_USD'] = df['USDCLP=X'].pct_change()
                    df['Returns_Gold'] = df['GC=F'].pct_change()
                    df['Volatility'] = df['USDCLP=X'].rolling(window=10).std()
                    df['SMA_10'] = df['USDCLP=X'].rolling(window=10).mean()
                    df['Target'] = (df['USDCLP=X'].shift(-3) - df['USDCLP=X'] > 2.5).astype(int)
                    
                    return df.dropna()
            
            print("Datos incompletos o vacíos, reintentando...")
            time.sleep(5) # Esperamos 5 segundos antes de reintentar
        except Exception as e:
            print(f"Error en el intento {i+1}: {e}")
            time.sleep(5)
            
    raise ValueError("No se pudieron obtener datos tras 3 intentos. Abortando entrenamiento.")

def train():
    try:
        df = prepare_data()
        features = ['Returns_USD', 'Returns_Gold', 'Volatility', 'SMA_10']
        X = df[features]
        y = df['Target']
        
        print("Entrenando modelo con datos actualizados...")
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X, y)
        
        joblib.dump(model, 'model.pkl')
        print("¡Modelo guardado con éxito!")
    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        exit(1) # Forzamos que GitHub Actions marque el error

if __name__ == "__main__":
    train()
