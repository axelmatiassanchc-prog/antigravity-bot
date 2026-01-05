# config.py
# Global Settings for Chilean Hedge Bot

# Assets
USD_PAIR = "CLP=X"
GOLD_PAIR = "GC=F"

# Financial Settings
INITIAL_CAPITAL = 500000  # CLP
LEVERAGE = 10  # 1:10 Conservative Leverage
MAX_DAILY_LOSS_PCT = 0.02  # 2% Kill Switch limit

# Blackout Dates (High Risk Events)
# NFP, CPI, and Central Bank meetings for Jan 2026
BLACKOUT_DATES = [
    "2026-01-09",
    "2026-01-13",
    "2026-01-27",
    "2026-01-28"
]
