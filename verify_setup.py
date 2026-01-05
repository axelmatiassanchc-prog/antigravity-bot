
import sys
import os

# Add the directory to path so imports work if not already there (standard for scripts in same dir)
sys.path.append(os.getcwd())

try:
    print("Testing imports...")
    import config
    import data_loader
    import news_filter
    import risk_manager
    import strategy_engine
    import app 
    # Note: importing app might run top level code, but since it's streamlit it usually needs 'streamlit run'. 
    # However, app.py code is mostly inside if blocks or function calls, except for the top level setup.
    # Actually, streamlit script execution model runs top to bottom. Importing it might fail if streamlit is not active context, 
    # but we just want to check syntax and standard imports.
    # Let's Skip importing app to avoid streamlit warnings/errors in console.
    print("Imports successful (excluding app.py).")

    print("Testing Data Loader...")
    df = data_loader.fetch_market_data()
    if df.empty:
        print("Data Loader returned empty DataFrame (Possible connection issue or no data).")
    else:
        print(f"Data Loader success. Shape: {df.shape}")
        print("Columns:", df.columns.tolist())

    print("Testing News Filter...")
    status = news_filter.check_market_status("2026-01-09")
    print(f"Blackout date check (2026-01-09): {status}")
    
    print("Testing Risk Manager...")
    is_kill = risk_manager.check_daily_pnl(500000, 480000) # 20k loss = 4% > 2%
    print(f"Risk Manager Test (should be True): {is_kill}")

    print("Verification Script Completed.")

except Exception as e:
    print(f"Verification Failed: {e}")
    import traceback
    traceback.print_exc()
