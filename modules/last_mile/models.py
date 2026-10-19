from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Bank(Base):
    __tablename__ = "lastmile_banks"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)      # e.g. "hdfc", "icici", "sbi"
    name = Column(String(128), nullable=False)
    country = Column(String(2), nullable=False)                 # ISO-2
    corridors = Column(JSON, default=list)                      # ["USD-INR", "EUR-INR"]
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    performances = relationship("BankPerformance", back_populates="bank",
                                cascade="all, delete-orphan")


class BankPerformance(Base):
    __tablename__ = "lastmile_bank_performance"

    id = Column(Integer, primary_key=True)
    bank_id = Column(Integer, ForeignKey("lastmile_banks.id"), nullable=False)
    corridor = Column(String(16), nullable=False)               # "USD-INR"
    total_payments = Column(Integer, default=0)
    successful_payments = Column(Integer, default=0)
    failed_payments = Column(Integer, default=0)
    avg_settlement_seconds = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bank = relationship("Bank", back_populates="performances")


class PaymentRoute(Base):
    __tablename__ = "lastmile_payment_routes"

    id = Column(Integer, primary_key=True)
    payment_ref = Column(String(64), unique=True, nullable=False)
    source_currency = Column(String(3), nullable=False)
    target_currency = Column(String(3), nullable=False)
    amount = Column(Float, nullable=False)
    bank_code = Column(String(32), nullable=False)
    score = Column(Float, default=0.0)                          # routing score
    reason = Column(String(256))
    created_at = Column(DateTime, default=datetime.utcnow)


class StatusEvent(Base):
    __tablename__ = "lastmile_status_events"

    id = Column(Integer, primary_key=True)
    payment_ref = Column(String(64), index=True, nullable=False)
    status = Column(String(32), nullable=False)                 # initiated | in_flight | settled | failed
    detail = Column(String(256))
    occurred_at = Column(DateTime, default=datetime.utcnow)