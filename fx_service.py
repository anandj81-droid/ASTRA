# fx_service.py
import requests
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
import random

from config import config

logger = logging.getLogger(__name__)

# Supported currencies
SUPPORTED_CURRENCIES = {
    "USD": {"name": "US Dollar", "symbol": "$", "flag": "🇺🇸", "is_base": True},
    "EUR": {"name": "Euro", "symbol": "€", "flag": "🇪🇺", "is_base": True},
    "INR": {"name": "Indian Rupee", "symbol": "₹", "flag": "🇮🇳", "is_base": False},
    "GBP": {"name": "British Pound", "symbol": "£", "flag": "🇬🇧", "is_base": False},
    "JPY": {"name": "Japanese Yen", "symbol": "¥", "flag": "🇯🇵", "is_base": False},
    "SGD": {"name": "Singapore Dollar", "symbol": "S$", "flag": "🇸🇬", "is_base": False},
    "AED": {"name": "UAE Dirham", "symbol": "د.إ", "flag": "🇦🇪", "is_base": False},
    "SAR": {"name": "Saudi Riyal", "symbol": "﷼", "flag": "🇸🇦", "is_base": False},
    "AUD": {"name": "Australian Dollar", "symbol": "A$", "flag": "🇦🇺", "is_base": False},
    "CHF": {"name": "Swiss Franc", "symbol": "Fr", "flag": "🇨🇭", "is_base": False},
    "CAD": {"name": "Canadian Dollar", "symbol": "C$", "flag": "🇨🇦", "is_base": False},
    "MYR": {"name": "Malaysian Ringgit", "symbol": "RM", "flag": "🇲🇾", "is_base": False},
}

class FXService:
    """FX rate service with multi-currency support"""
    
    def __init__(self):
        self.base_url = config.FX_API_URL
        self.cache = {}
        self.cache_expiry = 3600  # 1 hour
    
    def get_rate(self, from_currency: str, to_currency: str) -> Dict:
        """Get rate between two currencies"""
        if from_currency == to_currency:
            return {"rate": 1.0, "bid": 1.0, "ask": 1.0}
        
        # Try to get real rate
        try:
            response = requests.get(f"{self.base_url}/{from_currency}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if to_currency in data.get('rates', {}):
                    rate = data['rates'][to_currency]
                    return {
                        "rate": round(rate, 6),
                        "bid": round(rate * 0.9998, 6),
                        "ask": round(rate * 1.0002, 6),
                        "from": from_currency,
                        "to": to_currency
                    }
        except Exception as e:
            logger.warning(f"API rate fetch failed, using mock: {e}")
        
        # Return mock rate for POC
        return self._get_mock_rate(from_currency, to_currency)
    
    def _get_mock_rate(self, from_curr: str, to_curr: str) -> Dict:
        """Generate mock rate for demo"""
        base_rates = {
            "USD": 1.0, "INR": 84.52, "EUR": 0.92, "GBP": 0.78,
            "JPY": 147.23, "SGD": 1.34, "AED": 3.67, "SAR": 3.75,
            "AUD": 1.52, "CHF": 0.88, "CAD": 1.37, "MYR": 4.68
        }
        
        if from_curr == "USD":
            rate = base_rates.get(to_curr, 1.0)
        elif to_curr == "USD":
            rate = 1 / base_rates.get(from_curr, 1.0)
        else:
            from_rate = base_rates.get(from_curr, 1.0)
            to_rate = base_rates.get(to_curr, 1.0)
            rate = to_rate / from_rate
        
        # Add small random variation for demo
        variation = random.uniform(-0.005, 0.005)
        rate = rate * (1 + variation)
        
        return {
            "rate": round(rate, 6),
            "bid": round(rate * 0.9998, 6),
            "ask": round(rate * 1.0002, 6),
            "from": from_curr,
            "to": to_curr
        }

# Singleton instance
fx_service = FXService()

# Helper function for backward compatibility
def get_exchange_rate(from_currency: str, to_currency: str) -> Dict:
    """Convenience function to get exchange rate"""
    return fx_service.get_rate(from_currency, to_currency)