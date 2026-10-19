from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from core.database import Base


class LedgerEntry(Base):
    """Internal ledger entry, owned by this module (Option B)."""
    __tablename__ = "recon_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(120), nullable=False, index=True)
    entry_date = Column(DateTime, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False, default="INR")
    party = Column(String(255), nullable=True)
    reference = Column(String(255), nullable=True, index=True)
    direction = Column(String(8), nullable=False, default="debit")  # debit|credit
    source = Column(String(32), nullable=False, default="manual")   # manual|fx_bridge|import
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_recon_ledger_ext", "external_id", "currency"),
    )


class StatementImport(Base):
    __tablename__ = "recon_statement_imports"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=True)
    format = Column(String(16), nullable=False, default="csv")  # csv|json
    line_count = Column(Integer, nullable=False, default=0)
    imported_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship("StatementLine", back_populates="import_row",
                         cascade="all, delete-orphan")


class StatementLine(Base):
    __tablename__ = "recon_statement_lines"

    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("recon_statement_imports.id"), nullable=False)
    txn_ref = Column(String(120), nullable=False, index=True)
    value_date = Column(DateTime, nullable=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False, default="INR")
    counterparty = Column(String(255), nullable=True)
    narration = Column(String(512), nullable=True)
    status = Column(String(32), nullable=True)

    import_row = relationship("StatementImport", back_populates="lines")


class ReconciliationRun(Base):
    __tablename__ = "recon_runs"

    id = Column(Integer, primary_key=True, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    status = Column(String(16), nullable=False, default="completed")
    total_ledger = Column(Integer, default=0)
    total_statement = Column(Integer, default=0)
    matched = Column(Integer, default=0)
    discrepancies = Column(Integer, default=0)
    match_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    matches = relationship("ReconciliationMatch", back_populates="run",
                           cascade="all, delete-orphan")
    discrepancies_rel = relationship("DiscrepancyRecord", back_populates="run",
                                     cascade="all, delete-orphan")


class ReconciliationMatch(Base):
    __tablename__ = "recon_matches"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("recon_runs.id"), nullable=False)
    ledger_entry_id = Column(Integer, ForeignKey("recon_ledger_entries.id"), nullable=True)
    statement_line_id = Column(Integer, ForeignKey("recon_statement_lines.id"), nullable=True)
    match_method = Column(String(32), nullable=False)  # exact_ref|amount_date_party|amount_date
    confidence = Column(Float, nullable=False, default=1.0)

    run = relationship("ReconciliationRun", back_populates="matches")


class DiscrepancyRecord(Base):
    __tablename__ = "recon_discrepancies"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("recon_runs.id"), nullable=False)
    type = Column(String(32), nullable=False, index=True)
    # missing_in_statement | missing_in_ledger | amount_mismatch |
    # date_mismatch | duplicate
    ledger_entry_id = Column(Integer, ForeignKey("recon_ledger_entries.id"), nullable=True)
    statement_line_id = Column(Integer, ForeignKey("recon_statement_lines.id"), nullable=True)
    detail = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="open")  # open|resolved|ignored
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(String(512), nullable=True)

    run = relationship("ReconciliationRun", back_populates="discrepancies_rel")