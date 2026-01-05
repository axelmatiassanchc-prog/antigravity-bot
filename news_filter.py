# news_filter.py
import config

def check_market_status(current_date):
    """
    Checks if current_date exists in config.BLACKOUT_DATES.
    
    Args:
        current_date (str): Date string in format "YYYY-MM-DD"
        
    Returns:
        dict: {'safe': Bool, 'message': String}
    """
    try:
        # Ensure input is string and matches format if it comes from datetime object
        date_str = str(current_date).split(' ')[0]
        
        if date_str in config.BLACKOUT_DATES:
            return {
                'safe': False,
                'message': "⚠️ MERCADO CERRADO: Evento Económico de Alto Impacto"
            }
        
        return {
            'safe': True,
            'message': "✅ Mercado Seguro"
        }
    except Exception as e:
        # Fail safe
        return {
            'safe': False, 
            'message': f"⚠️ Error en filtro de noticias: {str(e)}"
        }
