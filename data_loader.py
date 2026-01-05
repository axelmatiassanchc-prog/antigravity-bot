# data_loader.py
import yfinance as yf
import pandas as pd
import config

def fetch_market_data():
    """
    Downloads the last 60 days of data (interval="1h") for USD and GOLD.
    Merges dataframes on the index (Datetime) to ensure alignment.
    Handles missing values using ffill().
    
    Returns:
        pd.DataFrame: Clean DataFrame with columns like USD_Close, GOLD_Close.
    """
    try:
        # Download data for USD/CLP
        usd_data = yf.download(config.USD_PAIR, period="60d", interval="1h", progress=False)
        
        # Download data for Gold
        gold_data = yf.download(config.GOLD_PAIR, period="60d", interval="1h", progress=False)
        
        # Ensure we are using the 'Close' price and rename columns
        # yfinance might return multi-index columns, so we handle that
        if isinstance(usd_data.columns, pd.MultiIndex):
             usd_close = usd_data['Close']
        else:
             usd_close = usd_data[['Close']]
             
        if isinstance(gold_data.columns, pd.MultiIndex):
             gold_close = gold_data['Close']
        else:
             gold_close = gold_data[['Close']]

        usd_close = usd_close.rename(columns={config.USD_PAIR: 'USD_Close', 'Close': 'USD_Close'})
        gold_close = gold_close.rename(columns={config.GOLD_PAIR: 'GOLD_Close', 'Close': 'GOLD_Close'})
        
        # Handle cases where column renaming might rely on the specific yfinance version structure
        # Simplified approach: Extract series if possible or force rename
        if 'USD_Close' not in usd_close.columns:
            usd_close.columns = ['USD_Close']
        if 'GOLD_Close' not in gold_close.columns:
            gold_close.columns = ['GOLD_Close']

        # Merge on Datetime index
        merged_data = pd.merge(usd_close, gold_close, left_index=True, right_index=True, how='inner')
        
        # Handle missing values
        merged_data = merged_data.ffill()
        
        return merged_data

    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame() # Return empty on error
