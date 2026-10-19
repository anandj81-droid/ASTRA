from sqlalchemy.orm import Session
from core.database import SessionLocal
from ..models import Bank, BankPerformance

_DEFAULT_BANKS = [
    ("hdfc",  "HDFC Bank",   "IN", ["USD-INR", "EUR-INR", "GBP-INR"], 0.94, 7200,  12.0),
    ("icici", "ICICI Bank",  "IN", ["USD-INR", "EUR-INR"],            0.91, 5400,  14.5),
    ("sbi",   "State Bank",  "IN", ["USD-INR", "GBP-INR"],            0.88, 10800,  9.0),
    ("axis",  "Axis Bank",   "IN", ["USD-INR", "AED-INR"],            0.90, 6300,  13.0),
    ("kotak", "Kotak Bank",  "IN", ["USD-INR", "SGD-INR"],            0.89, 8100,  11.5),
]


def seed_default_banks():
    db: Session = SessionLocal()
    try:
        if db.query(Bank).count() > 0:
            return
        for code, name, country, corridors, success, settle_s, cost in _DEFAULT_BANKS:
            bank = Bank(code=code, name=name, country=country, corridors=corridors)
            db.add(bank)
            db.flush()
            total = 100
            for corridor in corridors:
                db.add(BankPerformance(
                    bank_id=bank.id,
                    corridor=corridor,
                    total_payments=total,
                    successful_payments=int(total * success),
                    failed_payments=total - int(total * success),
                    avg_settlement_seconds=settle_s,
                ))
        db.commit()
    finally:
        db.close()


def get_corridor_stats(db: Session, corridor: str):
    rows = (
        db.query(BankPerformance, Bank)
        .join(Bank, Bank.id == BankPerformance.bank_id)
        .filter(BankPerformance.corridor == corridor, Bank.is_active == 1)
        .all()
    )
    out = []
    for perf, bank in rows:
        total = max(perf.total_payments, 1)
        out.append({
            "bank_code": bank.code,
            "bank_name": bank.name,
            "success_rate": perf.successful_payments / total,
            "avg_settlement_seconds": perf.avg_settlement_seconds,
            "avg_cost_usd": 10.0,   # placeholder — will pull from cost_optimizer later
        })
    return out


def list_banks_with_stats(db: Session):
    banks = db.query(Bank).all()
    return [
        {
            "code": b.code, "name": b.name, "country": b.country,
            "corridors": b.corridors, "is_active": bool(b.is_active),
        }
        for b in banks
    ]


def get_performance(db: Session, bank_code: str):
    bank = db.query(Bank).filter(Bank.code == bank_code).first()
    if not bank:
        return None
    rows = db.query(BankPerformance).filter(BankPerformance.bank_id == bank.id).all()
    return {
        "bank_code": bank.code,
        "bank_name": bank.name,
        "corridors": [
            {
                "corridor": r.corridor,
                "total": r.total_payments,
                "successful": r.successful_payments,
                "failed": r.failed_payments,
                "success_rate": round(r.successful_payments / max(r.total_payments, 1), 3),
                "avg_settlement_seconds": r.avg_settlement_seconds,
            }
            for r in rows
        ],
    }