from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging
from decimal import Decimal
import random

from core.models import Currency, CurrencyPair, FXRate, Prediction
from core.fx_service import fx_service, get_exchange_rate

logger = logging.getLogger(__name__)

class CurrencyService:
    """Handles all currency management operations"""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def set_db(self, db: Session):
        """Set database session"""
        self.db = db
    
    def create_currency(self, code: str, name: str, symbol: str, 
                       flag: str = None, is_base: bool = False) -> Currency:
        """Create a new currency"""
        code = code.upper()
        
        existing = self.db.query(Currency).filter(Currency.code == code).first()
        if existing:
            raise ValueError(f"Currency {code} already exists")
        
        currency = Currency(
            code=code,
            name=name,
            symbol=symbol,
            flag=flag or "",
            is_base=is_base,
            is_active=True
        )
        self.db.add(currency)
        self.db.commit()
        self.db.refresh(currency)
        
        # Create pairs with existing currencies
        self._create_pairs_with_currency(currency)
        
        logger.info(f"Created currency: {code}")
        return currency
    
    def _create_pairs_with_currency(self, currency: Currency):
        """Create currency pairs with a currency"""
        other_currencies = self.db.query(Currency).filter(
            Currency.id != currency.id,
            Currency.is_active == True
        ).all()
        
        for other in other_currencies:
            try:
                if currency.is_base:
                    self.create_pair(currency.code, other.code)
                else:
                    if other.is_base:
                        self.create_pair(other.code, currency.code)
                    else:
                        usd = self.db.query(Currency).filter(Currency.code == "USD").first()
                        if usd and usd.id == other.id:
                            self.create_pair(other.code, currency.code)
                        elif usd and usd.id == currency.id:
                            self.create_pair(currency.code, other.code)
                        else:
                            self.create_pair(currency.code, other.code)
                logger.info(f"Created pair with {other.code}")
            except ValueError as e:
                logger.warning(f"Pair creation skipped: {e}")
    
    def create_pair(self, base_code: str, quote_code: str, 
                   historical_days: int = 30) -> CurrencyPair:
        """Create a new currency pair"""
        base = self.db.query(Currency).filter(Currency.code == base_code).first()
        quote = self.db.query(Currency).filter(Currency.code == quote_code).first()
        
        if not base or not quote:
            raise ValueError("Base or quote currency not found")
        
        if base_code == quote_code:
            raise ValueError("Base and quote cannot be same")
        
        existing = self.db.query(CurrencyPair).filter(
            CurrencyPair.base_currency_id == base.id,
            CurrencyPair.quote_currency_id == quote.id
        ).first()
        
        if existing:
            raise ValueError(f"Pair {base_code}/{quote_code} already exists")
        
        pair = CurrencyPair(
            base_currency_id=base.id,
            quote_currency_id=quote.id,
            historical_days=historical_days
        )
        self.db.add(pair)
        self.db.commit()
        self.db.refresh(pair)
        
        self._fetch_and_store_rate(pair)
        
        logger.info(f"Created pair: {base_code}/{quote_code}")
        return pair
    
    def get_all_pairs(self, active_only: bool = True) -> List[CurrencyPair]:
        """Get all currency pairs, optionally active only"""
        query = self.db.query(CurrencyPair)
        if active_only:
            query = query.filter(CurrencyPair.is_active == True)
        return query.all()
    
    def get_active_pairs(self) -> List[dict]:
        """Get all active currency pairs with details"""
        pairs = self.db.query(CurrencyPair).filter(
            CurrencyPair.is_active == True
        ).all()
        
        result = []
        for pair in pairs:
            # Get latest rate
            latest_rate = self.db.query(FXRate).filter(
                FXRate.pair_id == pair.id
            ).order_by(FXRate.timestamp.desc()).first()
            
            result.append({
                "id": pair.id,
                "pair": f"{pair.base_currency.code}/{pair.quote_currency.code}",
                "base_currency": pair.base_currency.code,
                "quote_currency": pair.quote_currency.code,
                "is_active": pair.is_active,
                "current_rate": float(latest_rate.rate) if latest_rate else None,
                "last_update": latest_rate.timestamp if latest_rate else None,
                "historical_days": pair.historical_days
            })
        
        return result
    
    def _fetch_and_store_rate(self, pair: CurrencyPair):
        """Fetch and store initial rate for a pair"""
        try:
            rate_data = get_exchange_rate(
                pair.base_currency.code,
                pair.quote_currency.code
            )
            
            if rate_data:
                rate = FXRate(
                    pair_id=pair.id,
                    rate=Decimal(str(rate_data['rate'])),
                    bid=Decimal(str(rate_data.get('bid', rate_data['rate']))),
                    ask=Decimal(str(rate_data.get('ask', rate_data['rate']))),
                    source='api'
                )
                self.db.add(rate)
                self.db.commit()
                logger.info(f"Stored initial rate for {pair.base_currency.code}/{pair.quote_currency.code}")
        except Exception as e:
            logger.error(f"Failed to fetch initial rate: {e}")
    
    def get_all_currencies(self, active_only: bool = True) -> List[Currency]:
        """Get all currencies, optionally active only"""
        query = self.db.query(Currency)
        if active_only:
            query = query.filter(Currency.is_active == True)
        return query.order_by(Currency.code).all()
    
    def toggle_currency(self, currency_id: int, active: bool) -> Currency:
        """Activate/deactivate a currency"""
        currency = self.db.query(Currency).filter(Currency.id == currency_id).first()
        if not currency:
            raise ValueError("Currency not found")
        
        currency.is_active = active
        self.db.commit()
        self.db.refresh(currency)
        return currency
    
    def ensure_historical_data(self, pair_id: int, days: int = 30):
        """Ensure we have historical data for a pair"""
        pair = self.db.query(CurrencyPair).filter(CurrencyPair.id == pair_id).first()
        if not pair:
            raise ValueError("Pair not found")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        existing = self.db.query(FXRate).filter(
            FXRate.pair_id == pair_id,
            FXRate.timestamp >= cutoff_date
        ).count()
        
        expected_count = days * 24
        if existing < expected_count * 0.7:
            logger.info(f"Backfilling historical data for pair {pair_id}")
            self._backfill_historical_data(pair, days)
    
    def _backfill_historical_data(self, pair: CurrencyPair, days: int):
        """Backfill historical rates - generates synthetic data for POC"""
        base = pair.base_currency
        quote = pair.quote_currency
        
        current_rate = self.db.query(FXRate).filter(
            FXRate.pair_id == pair.id
        ).order_by(FXRate.timestamp.desc()).first()
        
        if not current_rate:
            logger.warning(f"No current rate for {base.code}/{quote.code}")
            return
        
        base_rate = float(current_rate.rate)
        
        for i in range(min(days * 24, 720)):
            timestamp = datetime.utcnow() - timedelta(hours=i)
            volatility = 0.002
            change = random.uniform(-volatility, volatility)
            base_rate = base_rate * (1 + change)
            
            rate = FXRate(
                pair_id=pair.id,
                rate=Decimal(str(round(base_rate, 6))),
                timestamp=timestamp,
                source='synthetic'
            )
            self.db.add(rate)
        
        self.db.commit()
        logger.info(f"Backfilled historical rates for {base.code}/{quote.code}")