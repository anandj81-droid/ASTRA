import csv
import io
from sqlalchemy.orm import Session

from modules.reconciliation.models import (
    ReconciliationRun, ReconciliationMatch, DiscrepancyRecord,
    LedgerEntry, StatementLine,
)


def export_run_csv(db: Session, run_id: int) -> str:
    run = db.query(ReconciliationRun).get(run_id)
    if not run:
        return ""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["run_id", run.id])
    w.writerow(["period_start", run.period_start.isoformat()])
    w.writerow(["period_end", run.period_end.isoformat()])
    w.writerow(["match_rate", run.match_rate])
    w.writerow([])
    w.writerow(["section", "ledger_external_id", "statement_ref",
                "amount_ledger", "amount_statement", "type", "status", "detail"])

    for m in db.query(ReconciliationMatch).filter_by(run_id=run_id).all():
        le = db.query(LedgerEntry).get(m.ledger_entry_id) if m.ledger_entry_id else None
        sl = db.query(StatementLine).get(m.statement_line_id) if m.statement_line_id else None
        w.writerow(["match",
                    getattr(le, "external_id", ""), getattr(sl, "txn_ref", ""),
                    getattr(le, "amount", ""), getattr(sl, "amount", ""),
                    m.match_method, "matched", ""])

    for d in db.query(DiscrepancyRecord).filter_by(run_id=run_id).all():
        le = db.query(LedgerEntry).get(d.ledger_entry_id) if d.ledger_entry_id else None
        sl = db.query(StatementLine).get(d.statement_line_id) if d.statement_line_id else None
        w.writerow(["discrepancy",
                    getattr(le, "external_id", ""), getattr(sl, "txn_ref", ""),
                    getattr(le, "amount", ""), getattr(sl, "amount", ""),
                    d.type, d.status, d.detail or ""])

    return buf.getvalue()