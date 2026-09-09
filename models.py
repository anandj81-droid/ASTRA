# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON, Enum, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base

# ──────────────────────────────────────────────────────────────
# 1. CURRENCY MANAGEMENT
# ──────────────────────────────────────────────────────────────

class Currency(Base):
    __tablename__ = "currencies"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(3), unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    symbol = Column(String(5), nullable=False)
    flag = Column(String(10))
    is_active = Column(Boolean, default=True)
    is_base = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    base_pairs = relationship("CurrencyPair", foreign_keys="CurrencyPair.base_currency_id", back_populates="base_currency")
    quote_pairs = relationship("CurrencyPair", foreign_keys="CurrencyPair.quote_currency_id", back_populates="quote_currency")


class CurrencyPair(Base):
    __tablename__ = "currency_pairs"
    
    id = Column(Integer, primary_key=True, index=True)
    base_currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)
    quote_currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    min_trade_amount = Column(DECIMAL(10, 2), default=1000.00)
    max_trade_amount = Column(DECIMAL(10, 2), default=1000000.00)
    historical_days = Column(Integer, default=30)
    prediction_model = Column(String(50), default="prophet")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    base_currency = relationship("Currency", foreign_keys=[base_currency_id], back_populates="base_pairs")
    quote_currency = relationship("Currency", foreign_keys=[quote_currency_id], back_populates="quote_pairs")
    rates = relationship("FXRate", back_populates="pair")
    predictions = relationship("Prediction", back_populates="pair")
    rules = relationship("AgentRule", back_populates="pair")


class FXRate(Base):
    __tablename__ = "fx_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    pair_id = Column(Integer, ForeignKey("currency_pairs.id"), nullable=False)
    rate = Column(DECIMAL(10, 6), nullable=False)
    bid = Column(DECIMAL(10, 6))
    ask = Column(DECIMAL(10, 6))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String(50), default="api")
    
    # Relationship
    pair = relationship("CurrencyPair", back_populates="rates")


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    pair_id = Column(Integer, ForeignKey("currency_pairs.id"), nullable=False)
    predicted_rate = Column(DECIMAL(10, 6), nullable=False)
    lower_bound = Column(DECIMAL(10, 6))
    upper_bound = Column(DECIMAL(10, 6))
    confidence = Column(Float, default=0.0)
    model_used = Column(String(50), default="prophet")
    horizon = Column(String(20), default="24h")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    pair = relationship("CurrencyPair", back_populates="predictions")


# ──────────────────────────────────────────────────────────────
# 2. USER MANAGEMENT
# ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    rules = relationship("AgentRule", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")


# ──────────────────────────────────────────────────────────────
# 3. AGENT RULES - MATCHING YOUR ACTUAL DATABASE
# ──────────────────────────────────────────────────────────────

class RuleStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRule(Base):
    __tablename__ = "agent_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pair_id = Column(Integer, ForeignKey("currency_pairs.id"), nullable=True)  # Made nullable for backward compatibility
    
    # Your actual database columns
    rule_type = Column(String(50), nullable=False)
    source_currency = Column(String(3), nullable=False)  # ✅ MATCHES YOUR DB
    target_currency = Column(String(3), nullable=False)  # ✅ MATCHES YOUR DB
    target_rate = Column(DECIMAL(10, 6), nullable=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)  # ✅ MATCHES YOUR DB
    
    # Additional columns (optional)
    currency_code = Column(String(3), nullable=True)  # For backward compatibility
    schedule_day = Column(Integer, nullable=True)
    schedule_time = Column(String(5), nullable=True)
    min_confidence = Column(Float, default=0.7)
    prediction_horizon = Column(String(20), default="24h")
    execution_count = Column(Integer, default=0)
    last_executed = Column(DateTime, nullable=True)
    next_execution = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    from_account = Column(String(50), nullable=True)
    to_account = Column(String(50), nullable=True)
    
    # Status as Enum
    status = Column(Enum(RuleStatus), default=RuleStatus.ACTIVE, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="rules")
    pair = relationship("CurrencyPair", back_populates="rules")
    transactions = relationship("Transaction", back_populates="rule", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("agent_rules.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Your actual database columns
    from_currency = Column(String(3), nullable=False)  # ✅ MATCHES YOUR DB
    to_currency = Column(String(3), nullable=False)    # ✅ MATCHES YOUR DB
    from_amount = Column(DECIMAL(10, 2), nullable=False)  # ✅ MATCHES YOUR DB
    to_amount = Column(DECIMAL(10, 2), nullable=False)    # ✅ MATCHES YOUR DB
    rate_used = Column(DECIMAL(10, 6), nullable=False)    # ✅ MATCHES YOUR DB
    
    # Additional columns
    currency_pair = Column(String(10), nullable=True)
    amount = Column(DECIMAL(10, 2), nullable=True)
    executed_rate = Column(DECIMAL(10, 6), nullable=True)
    
    execution_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="executed")
    error_message = Column(Text, nullable=True)
    
    # Bank integration fields
    bank_reference = Column(String(100), nullable=True)
    iso_message_path = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    rule = relationship("AgentRule", back_populates="transactions")
    user = relationship("User", back_populates="transactions")