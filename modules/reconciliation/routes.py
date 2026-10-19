import csv
import io
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.database import get_db
from modules.reconciliation.models import (
    LedgerEntry, StatementImport, StatementLine,
    ReconciliationRun, ReconciliationMatch, DiscrepancyRecord,
)
from modules.reconciliation.services.statement_parser import parse_statement
from modules.reconciliation.services.matcher import run_reconciliation
from modules.reconciliation.services.discrepancy import classify_run
from modules.reconciliation.services.reports import export_run_csv

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------- Schemas ----------

class LedgerEntryIn(BaseModel):
    external_id: str
    date: datetime
    amount: float
    currency: str = "INR"
    party: Optional[str] = None
    reference: Optional[str] = None
    direction: str = Field(default="debit", pattern="^(debit|credit)$")


class LedgerImportRequest(BaseModel):
    entries: List[LedgerEntryIn]
    source: str = "import"


class RunRequest(BaseModel):
    period_start: datetime
    period_end: datetime
    import_id: Optional[int] = None  # if omitted, use all statement lines in period


class DiscrepancyResolve(BaseModel):
    status: str = Field(pattern="^(open|resolved|ignored)$")
    note: Optional[str] = None


# ---------- Ledger ----------

@router.post("/ledger/import")
def import_ledger(payload: LedgerImportRequest, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    created = 0
    for e in payload.entries:
        db.add(LedgerEntry(
            external_id=e.external_id, entry_date=e.date, amount=e.amount,
            currency=e.currency, party=e.party, reference=e.reference,
            direction=e.direction, source=payload.source,
        ))
        created += 1
    db.commit()
    return {"imported": created}


@router.post("/ledger/import-from-fx")
def import_ledger_from_fx(limit: int = Query(default=200, le=2000),
                          db: Session = Depends(get_db),
                          user=Depends(get_current_user)):
    """Optional bridge: pull core Transaction rows into the recon ledger."""
    try:
        from core.models import Transaction
    except Exception:
        raise HTTPException(400, "Core Transaction model not available")
    rows = db.query(Transaction).order_by(Transaction.id.desc()).limit(limit).all()
    created = 0
    for t in rows:
        ext = f"FX-{t.id}"
        if db.query(LedgerEntry).filter_by(external_id=ext).first():
            continue
        amt = float(getattr(t, "amount", 0) or 0)
        db.add(LedgerEntry(
            external_id=ext,
            entry_date=getattr(t, "created_at", None) or datetime.utcnow(),
            amount=amt,
            currency=getattr(t, "from_currency", None) or "INR",
            party=getattr(t, "recipient_name", None),
            reference=getattr(t, "reference", None) or ext,
            direction="debit",
            source="fx_bridge",
        ))
        created += 1
    db.commit()
    return {"imported_from_fx": created}


@router.get("/ledger")
def list_ledger(limit: int = Query(default=50, le=500), offset: int = 0,
                db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(LedgerEntry).order_by(LedgerEntry.id.desc())
    total = q.count()
    rows = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {"id": r.id, "external_id": r.external_id,
             "date": r.entry_date.isoformat() if r.entry_date else None,
             "amount": r.amount, "currency": r.currency, "party": r.party,
             "reference": r.reference, "direction": r.direction, "source": r.source}
            for r in rows
        ],
    }


# ---------- Statements ----------

@router.post("/statements/import")
async def import_statement(
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Accepts multipart file upload (.csv or .json). Detects format by extension/content."""
    if file is None:
        raise HTTPException(400, "No file uploaded")
    raw = (await file.read()).decode("utf-8", errors="replace")
    fmt = "json" if file.filename.lower().endswith(".json") else "csv"
    try:
        lines = parse_statement(raw, fmt)
    except Exception as e:
        raise HTTPException(400, f"Parse error: {e}")

    imp = StatementImport(filename=file.filename, format=fmt, line_count=len(lines))
    db.add(imp)
    db.flush()
    for ln in lines:
        db.add(StatementLine(import_id=imp.id, **ln))
    db.commit()
    return {"import_id": imp.id, "format": fmt, "lines": len(lines)}


@router.get("/statements")
def list_statements(limit: int = Query(default=25, le=200),
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (db.query(StatementImport)
              .order_by(StatementImport.id.desc()).limit(limit).all())
    return {"items": [
        {"id": r.id, "filename": r.filename, "format": r.format,
         "line_count": r.line_count,
         "imported_at": r.imported_at.isoformat() if r.imported_at else None}
        for r in rows
    ]}


# ---------- Runs ----------

@router.post("/runs")
def create_run(payload: RunRequest, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    if payload.period_end < payload.period_start:
        raise HTTPException(400, "period_end must be >= period_start")

    ledger_q = (db.query(LedgerEntry)
                  .filter(LedgerEntry.entry_date >= payload.period_start,
                          LedgerEntry.entry_date <= payload.period_end))
    ledger = ledger_q.all()

    stmt_q = (db.query(StatementLine)
                .filter(StatementLine.value_date >= payload.period_start,
                        StatementLine.value_date <= payload.period_end))
    if payload.import_id:
        stmt_q = stmt_q.filter(StatementLine.import_id == payload.import_id)
    statement = stmt_q.all()

    run = ReconciliationRun(
        period_start=payload.period_start,
        period_end=payload.period_end,
        status="running",
        total_ledger=len(ledger),
        total_statement=len(statement),
    )
    db.add(run)
    db.flush()

    pairs, unmatched_ledger, unmatched_stmt = run_reconciliation(ledger, statement)

    for p in pairs:
        db.add(ReconciliationMatch(
            run_id=run.id,
            ledger_entry_id=p["ledger_entry_id"],
            statement_line_id=p["statement_line_id"],
            match_method=p["match_method"],
            confidence=p["confidence"],
        ))
    db.flush()

    disc = classify_run(run.id, unmatched_ledger, unmatched_stmt, pairs)
    for d in disc:
        db.add(DiscrepancyRecord(**d))

    run.matched = len(pairs)
    run.discrepancies = len(disc)
    denom = max(len(ledger), 1)
    run.match_rate = round(len(pairs) / denom, 4)
    run.status = "completed"
    db.commit()

    return {
        "run_id": run.id,
        "total_ledger": run.total_ledger,
        "total_statement": run.total_statement,
        "matched": run.matched,
        "discrepancies": run.discrepancies,
        "match_rate": run.match_rate,
    }


@router.get("/runs")
def list_runs(limit: int = Query(default=25, le=200),
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(ReconciliationRun).order_by(ReconciliationRun.id.desc()).limit(limit).all()
    return {"items": [
        {"id": r.id, "period_start": r.period_start.isoformat(),
         "period_end": r.period_end.isoformat(), "status": r.status,
         "total_ledger": r.total_ledger, "total_statement": r.total_statement,
         "matched": r.matched, "discrepancies": r.discrepancies,
         "match_rate": r.match_rate}
        for r in rows
    ]}


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    r = db.query(ReconciliationRun).get(run_id)
    if not r:
        raise HTTPException(404, "Run not found")
    return {
        "id": r.id, "period_start": r.period_start.isoformat(),
        "period_end": r.period_end.isoformat(), "status": r.status,
        "total_ledger": r.total_ledger, "total_statement": r.total_statement,
        "matched": r.matched, "discrepancies": r.discrepancies,
        "match_rate": r.match_rate,
    }


@router.get("/runs/{run_id}/matches")
def get_matches(run_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(ReconciliationMatch).filter_by(run_id=run_id).all()
    return {"items": [
        {"id": m.id, "ledger_entry_id": m.ledger_entry_id,
         "statement_line_id": m.statement_line_id,
         "match_method": m.match_method, "confidence": m.confidence}
        for m in rows
    ]}


@router.get("/runs/{run_id}/discrepancies")
def get_discrepancies(run_id: int, type: Optional[str] = None,
                      db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DiscrepancyRecord).filter_by(run_id=run_id)
    if type:
        q = q.filter_by(type=type)
    rows = q.all()
    return {"items": [
        {"id": d.id, "type": d.type, "ledger_entry_id": d.ledger_entry_id,
         "statement_line_id": d.statement_line_id, "detail": d.detail,
         "status": d.status, "resolution_note": d.resolution_note}
        for d in rows
    ]}


@router.patch("/discrepancies/{disc_id}")
def resolve_discrepancy(disc_id: int, payload: DiscrepancyResolve,
                        db: Session = Depends(get_db), user=Depends(get_current_user)):
    d = db.query(DiscrepancyRecord).get(disc_id)
    if not d:
        raise HTTPException(404, "Discrepancy not found")
    d.status = payload.status
    d.resolution_note = payload.note
    if payload.status in ("resolved", "ignored"):
        d.resolved_at = datetime.utcnow()
    db.commit()
    return {"id": d.id, "status": d.status}


@router.get("/runs/{run_id}/export", response_class=PlainTextResponse)
def export_run(run_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    r = db.query(ReconciliationRun).get(run_id)
    if not r:
        raise HTTPException(404, "Run not found")
    csv_text = export_run_csv(db, run_id)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="recon_run_{run_id}.csv"'},
    )