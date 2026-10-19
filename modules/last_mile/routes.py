from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import get_db
from .services import router as routing_svc
from .services import bank_performance as perf_svc
from .services import status_tracker as status_svc

router = APIRouter()


class RouteRequest(BaseModel):
    source_currency: str
    target_currency: str
    amount: float
    strategy: str = "balanced"     # fastest | cheapest | balanced


class StatusEventRequest(BaseModel):
    status: str
    detail: str | None = None


@router.post("/route")
def create_route(req: RouteRequest, db: Session = Depends(get_db)):
    """Pick the best bank for this corridor + amount."""
    return routing_svc.pick_bank(
        db, req.source_currency, req.target_currency, req.amount, req.strategy
    )


@router.get("/banks")
def list_banks(db: Session = Depends(get_db)):
    return perf_svc.list_banks_with_stats(db)


@router.get("/banks/{bank_code}/performance")
def bank_performance(bank_code: str, db: Session = Depends(get_db)):
    result = perf_svc.get_performance(db, bank_code)
    if not result:
        raise HTTPException(404, f"Bank '{bank_code}' not found")
    return result


@router.get("/status/{payment_ref}")
def get_status(payment_ref: str, db: Session = Depends(get_db)):
    return status_svc.get_events(db, payment_ref)


@router.post("/status/{payment_ref}/event")
def push_event(payment_ref: str, req: StatusEventRequest, db: Session = Depends(get_db)):
    return status_svc.record_event(db, payment_ref, req.status, req.detail)