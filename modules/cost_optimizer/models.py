"""
Cost Optimizer Module - Database Models
Tracks provider configurations, cost comparisons, and audit trail.
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime

from core.database import Base


class ProviderConfig(Base):
    """Configuration for a payment provider (rate markups, fees, corridors)."""
    __tablename__ = "cost_provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)

    # Rate markup: percentage above interbank rate (e.g., 0.5 = 0.5% markup)
    rate_markup_pct = Column(Float, default=0.0)

    # Fixed fee in source currency (e.g., 5.0 = $5 flat fee)
    fixed_fee = Column(Float, default=0.0)

    # Variable fee as % of amount (e.g., 0.3 = 0.3%)
    variable_fee_pct = Column(Float, default=0.0)

    # Minimum/maximum fees
    min_fee = Column(Float, default=0.0)
    max_fee = Column(Float, nullable=True)

    # Optional corridor-specific configs as JSON
    # e.g., {"USD-INR": {"rate_markup_pct": 0.4, "fixed_fee": 0.0}}
    corridor_overrides = Column(JSON, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True)
    settlement_days = Column(Integer, default=1)
    reliability_score = Column(Float, default=1.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CostComparison(Base):
    """Historical record of a cost comparison (audit + analytics)."""
    __tablename__ = "cost_comparisons"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    base_currency = Column(String(3), nullable=False)
    quote_currency = Column(String(3), nullable=False)
    amount = Column(Float, nullable=False)

    # Full ranking list as JSON
    results_json = Column(JSON, nullable=False)

    best_provider = Column(String(50), nullable=True)
    best_total_cost = Column(Float, nullable=True)
    worst_provider = Column(String(50), nullable=True)
    worst_total_cost = Column(Float, nullable=True)
    max_savings = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", backref="cost_comparisons")