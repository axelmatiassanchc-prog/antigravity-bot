# strategy_engine.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import config

def prepare_features(df):
    """
    Calculates rolling correlation and prepares features for ML.
    """
    data = df.copy()
    
    # Feature 1: Rolling Correlation (Window=5)
    data['Correlation'] = data['USD_Close'].rolling(window=5).corr(data['GOLD_Close'])
    
    # Feature 2: Returns
    data['USD_Ret'] = data['USD_Close'].pct_change()
    data['GOLD_Ret'] = data['GOLD_Close'].pct_change()
    
    # Feature 3: Lagged Returns (for prediction)
    data['USD_Ret_Lag1'] = data['USD_Ret'].shift(1)
    data['GOLD_Ret_Lag1'] = data['GOLD_Ret'].shift(1)
    
    # Target: Next Hour USD Close
    data['Target'] = data['USD_Close'].shift(-1)
    
    return data

def train_and_predict(df):
    """
    Trains a lightweight Random Forest to predict next USD Close.
    Returns the prediction for the next hour (based on the last available row).
    """
    data = prepare_features(df)
    
    # Drop NaN values created by lags and rolling window
    # We keep the last row separate for prediction as it has no Target
    train_data = data.dropna()
    
    if len(train_data) < 50:
        return None, 0.0 # Not enough data
    
    # Features for training
    features = ['USD_Close', 'GOLD_Close', 'Correlation', 'USD_Ret_Lag1', 'GOLD_Ret_Lag1']
    X = train_data[features]
    y = train_data['Target']
    
    # Train lightweight model
    model = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42, n_jobs=-1)
    model.fit(X, y)
    
    # Prediction for the "Next" step (using the very last row of available data)
    # The last row in 'data' has NaN Target, but valid current features for next step prediction
    last_row = data.iloc[[-1]][features]
    
    # If last row has NaNs (e.g. not enough data points for lags), validation needed
    if last_row.isnull().values.any():
        # Fallback: try previous row or return current close
        prediction = data.iloc[-1]['USD_Close']
    else:
        prediction = model.predict(last_row)[0]
        
    return model, prediction

def get_trade_signal(df, news_safe):
    """
    Generates trading signal based on Logic.
    
    Returns:
        dict: {
            'action': 'BUY_HEDGE' or 'NEUTRAL',
            'correlation': float,
            'predicted_price': float,
            'prediction_direction': 'UP' or 'DOWN',
            'reason': str
        }
    """
    if df.empty:
         return {'action': 'NEUTRAL', 'reason': 'No Data'}
         
    # 1. Feature Engineering & ML
    model, predicted_price = train_and_predict(df)
    
    current_price = df.iloc[-1]['USD_Close']
    current_corr = df['USD_Close'].rolling(window=5).corr(df['GOLD_Close']).iloc[-1]
    
    # Determine Prediction Direction
    prediction_direction = "UP" if predicted_price > current_price else "DOWN"
    
    # 2. News Filter Check
    if not news_safe:
        return {
            'action': 'NEUTRAL',
            'correlation': current_corr,
            'predicted_price': predicted_price,
            'prediction_direction': prediction_direction,
            'reason': 'News/Event Risk (Blackout)'
        }
        
    # 3. Strategy Logic
    # BUY_HEDGE: IF (Correlation < -0.5) AND (ML_Prediction == UP)
    # Explanation: Gold is acting as a hedge against USD.
    
    if (current_corr < -0.5) and (prediction_direction == "UP"):
        return {
            'action': 'BUY_HEDGE',
            'correlation': current_corr,
            'predicted_price': predicted_price,
            'prediction_direction': prediction_direction,
            'reason': 'Correlation Negativa + Predicción Alcista'
        }
        
    # NEUTRAL: IF (Correlation > 0.0) 
    if current_corr > 0.0:
        return {
            'action': 'NEUTRAL',
            'correlation': current_corr,
            'predicted_price': predicted_price,
            'prediction_direction': prediction_direction,
            'reason': 'Correlación Positiva (Riesgo Alto)'
        }
        
    # Default Neutral for in-between states
    return {
        'action': 'NEUTRAL',
        'correlation': current_corr,
        'predicted_price': predicted_price,
        'prediction_direction': prediction_direction,
        'reason': 'Condiciones no ideales'
    }
