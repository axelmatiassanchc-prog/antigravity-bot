# risk_manager.py
import config

def check_daily_pnl(start_balance, current_balance):
    """
    Calculates loss and activates kill switch if limit exceeded.
    
    Args:
        start_balance (float): Account balance at start of day
        current_balance (float): Current account balance
        
    Returns:
        bool: True if Kill Switch Activates, False otherwise.
    """
    try:
        loss = start_balance - current_balance
        max_loss_amount = start_balance * config.MAX_DAILY_LOSS_PCT
        
        if loss >= max_loss_amount:
            return True # ACTIVATE KILL SWITCH
        
        return False
    except Exception as e:
        print(f"Risk Manager Error: {e}")
        return True # Fail safe: Activate kill switch on error
