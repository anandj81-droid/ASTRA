from sqlalchemy.orm import Session
from ..models import StatusEvent

VALID = {"initiated", "in_flight", "settled", "failed"}


def record_event(db: Session, payment_ref: str, status: str, detail: str | None = None):
    if status not in VALID:
        return {"error": f"Invalid status '{status}'. Valid: {sorted(VALID)}"}
    evt = StatusEvent(payment_ref=payment_ref, status=status, detail=detail)
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return {"payment_ref": payment_ref, "status": status, "detail": detail,
            "occurred_at": evt.occurred_at.isoformat()}


def get_events(db: Session, payment_ref: str):
    rows = (db.query(StatusEvent)
              .filter(StatusEvent.payment_ref == payment_ref)
              .order_by(StatusEvent.occurred_at.asc()).all())
    return {
        "payment_ref": payment_ref,
        "current_status": rows[-1].status if rows else None,
        "events": [
            {"status": r.status, "detail": r.detail, "occurred_at": r.occurred_at.isoformat()}
            for r in rows
        ],
    }