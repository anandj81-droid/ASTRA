"""
FX Tool Module - API Routes
Mounted at: /api/v1/fx/*
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import logging
import os

from core.database import get_db
from core.models import User, AgentRule, Transaction, Currency, CurrencyPair, FXRate
from core.auth import get_current_user
from core.fx_service import fx_service
from core.currency_service import CurrencyService
from core.iso20022_messages import ISO20022MessageGenerator
from modules.fx_tool.services.predictor import PredictionService
from modules.fx_tool.services.rule_engine import AgentEngine
from modules.last_mile.services.bank_integration import BankIntegration

logger = logging.getLogger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════

class RuleCreateRequest(BaseModel):
    pair_code: str
    rule_type: str
    amount: float
    target_rate: Optional[float] = None
    schedule_day: Optional[int] = None
    schedule_time: Optional[str] = None
    min_confidence: Optional[float] = 0.7
    prediction_horizon: Optional[str] = "24h"


# ═══════════════════════════════════════════════════════════
# CURRENCY PAIRS
# ═══════════════════════════════════════════════════════════

@router.get("/currency-pairs")
async def get_currency_pairs(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        service = CurrencyService(db)
        pairs = service.get_active_pairs()
        if not pairs:
            await _create_default_pairs(db)
            pairs = service.get_active_pairs()
        return {"pairs": pairs}
    except Exception as e:
        logger.error(f"Error fetching currency pairs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _create_default_pairs(db: Session):
    """Create default currency pairs if they don't exist (idempotent)."""
    service = CurrencyService(db)
    default_pairs = [
        ("USD", "INR"), ("USD", "EUR"), ("EUR", "USD"), ("USD", "GBP"),
        ("USD", "JPY"), ("USD", "SGD"), ("USD", "AED"), ("USD", "SAR"),
        ("USD", "AUD"), ("USD", "CHF"), ("USD", "CAD"), ("USD", "MYR"),
        ("USD", "BRL"),
    ]
    created = 0
    for base, quote in default_pairs:
        try:
            base_curr = db.query(Currency).filter(Currency.code == base).first()
            quote_curr = db.query(Currency).filter(Currency.code == quote).first()
            if not base_curr or not quote_curr:
                continue
            existing = db.query(CurrencyPair).filter(
                CurrencyPair.base_currency_id == base_curr.id,
                CurrencyPair.quote_currency_id == quote_curr.id
            ).first()
            if existing:
                continue
            service.create_pair(base, quote)
            created += 1
        except Exception as e:
            logger.debug(f"Skipped {base}/{quote}: {e}")
    if created:
        logger.info(f"✅ Created {created} default currency pair(s)")

# ═══════════════════════════════════════════════════════════
# FX RATES
# ═══════════════════════════════════════════════════════════

@router.get("/rate/{base}/{quote}")
async def get_rate(
    base: str,
    quote: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    rate_data = fx_service.get_rate(base.upper(), quote.upper())
    if not rate_data:
        raise HTTPException(status_code=404, detail="Rate not found")
    return rate_data


# ═══════════════════════════════════════════════════════════
# RULES
# ═══════════════════════════════════════════════════════════

@router.post("/rules")
async def create_rule(
    request: RuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        pair_code = request.pair_code.strip()
        if "/" in pair_code:
            base, quote = pair_code.split("/")
        elif "-" in pair_code:
            base, quote = pair_code.split("-")
        else:
            raise HTTPException(status_code=400, detail="Invalid pair format. Use USD/INR")
        
        base = base.strip().upper()
        quote = quote.strip().upper()
        
        base_currency = db.query(Currency).filter(Currency.code == base).first()
        quote_currency = db.query(Currency).filter(Currency.code == quote).first()
        
        if not base_currency:
            raise HTTPException(status_code=404, detail=f"Base currency {base} not found")
        if not quote_currency:
            raise HTTPException(status_code=404, detail=f"Quote currency {quote} not found")
        
        pair = db.query(CurrencyPair).filter(
            CurrencyPair.base_currency_id == base_currency.id,
            CurrencyPair.quote_currency_id == quote_currency.id
        ).first()
        
        if not pair:
            currency_service = CurrencyService(db)
            try:
                pair = currency_service.create_pair(base, quote)
            except Exception as e:
                raise HTTPException(
                    status_code=404,
                    detail=f"Pair {base}/{quote} not found and could not be created: {str(e)}"
                )
        
        engine = AgentEngine(db)
        rule = engine.create_rule(
            user_id=current_user['id'],
            pair_id=pair.id,
            rule_type=request.rule_type,
            amount=request.amount,
            target_rate=request.target_rate,
            schedule_day=request.schedule_day,
            schedule_time=request.schedule_time,
            min_confidence=request.min_confidence,
            prediction_horizon=request.prediction_horizon
        )
        
        return {"id": rule.id, "message": f"Rule created successfully for {base}/{quote}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rules")
async def get_rules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    engine = AgentEngine(db)
    rules = engine.get_user_rules(current_user['id'])
    return {
        "rules": [
            {
                "id": r.id,
                "pair": f"{r.source_currency}/{r.target_currency}",
                "rule_type": r.rule_type,
                "amount": float(r.amount),
                "target_rate": float(r.target_rate) if r.target_rate else None,
                "schedule_day": r.schedule_day,
                "schedule_time": r.schedule_time,
                "status": "active" if r.is_active else "inactive",
                "execution_count": r.execution_count,
                "last_executed": r.last_executed,
                "created_at": r.created_at
            }
            for r in rules
        ]
    }


@router.patch("/rules/{rule_id}")
async def update_rule_status(
    rule_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    engine = AgentEngine(db)
    try:
        rule = engine.update_rule_status(rule_id, status)
        return {
            "id": rule.id,
            "status": "active" if rule.is_active else "inactive",
            "message": f"Rule updated to {status}"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    engine = AgentEngine(db)
    try:
        engine.delete_rule(rule_id)
        return {"message": f"Rule {rule_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/rules/{rule_id}/trigger")
async def trigger_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        engine = AgentEngine(db)
        rule = engine.get_rule(rule_id, current_user['id'])
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        rate_data = fx_service.get_rate(rule.source_currency, rule.target_currency)
        current_rate = float(rate_data['rate']) if rate_data else 85.0
        
        iso_gen = ISO20022MessageGenerator(
            sender_bic="ASTRAINBBXXX",
            receiver_bic="HDFCINBBXXX",
            sender_account="ASTRA123456789"
        )
        
        amount = float(rule.amount) if rule.amount else 0.0
        
        transaction_data = {
            'amount': amount,
            'currency': rule.source_currency,
            'beneficiary_name': 'Test Beneficiary',
            'beneficiary_account': 'TEST123456789',
            'beneficiary_bic': 'TESTBICXXX',
            'reference': f"TEST_{rule.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'purpose': f'Test execution - Rule {rule.id}'
        }
        
        xml_message = iso_gen.generate_pain_001(transaction_data)
        
        os.makedirs("iso_messages", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        xml_path = f"iso_messages/test_rule_{rule.id}_{timestamp}.xml"
        with open(xml_path, 'w') as f:
            f.write(xml_message)
        
        bank_api = BankIntegration()
        payment_response = bank_api.submit_payment(xml_message, rule.id)
        
        rate_used = float(current_rate)
        from_amount = float(amount)
        to_amount = float(amount * rate_used)
        
        transaction = Transaction(
            user_id=rule.user_id,
            rule_id=rule.id,
            from_currency=rule.source_currency,
            to_currency=rule.target_currency,
            from_amount=from_amount,
            to_amount=to_amount,
            rate_used=rate_used,
            currency_pair=f"{rule.source_currency}/{rule.target_currency}",
            amount=from_amount,
            executed_rate=rate_used,
            status=payment_response.get('status', 'executed'),
            bank_reference=payment_response.get('reference'),
            iso_message_path=xml_path,
            execution_time=datetime.now()
        )
        
        db.add(transaction)
        rule.execution_count += 1
        rule.last_executed = datetime.now()
        db.commit()
        db.refresh(transaction)
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "bank_reference": payment_response.get('reference'),
            "iso_message_path": xml_path,
            "bank_api_called": True,
            "status": payment_response.get('status', 'executed'),
            "xml_preview": xml_message[:500] + "..." if len(xml_message) > 500 else xml_message,
            "message": f"Rule {rule_id} triggered successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# TRANSACTIONS
# ═══════════════════════════════════════════════════════════

@router.get("/transactions")
async def get_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        transactions = db.query(Transaction).filter(
            Transaction.user_id == current_user['id']
        ).order_by(Transaction.execution_time.desc()).offset(offset).limit(limit).all()
        
        total = db.query(Transaction).filter(
            Transaction.user_id == current_user['id']
        ).count()
        
        return {
            "transactions": [
                {
                    "id": t.id,
                    "rule_id": t.rule_id,
                    "from_currency": t.from_currency,
                    "to_currency": t.to_currency,
                    "from_amount": float(t.from_amount),
                    "to_amount": float(t.to_amount),
                    "rate_used": float(t.rate_used),
                    "status": t.status,
                    "execution_time": t.execution_time,
                    "bank_reference": t.bank_reference
                }
                for t in transactions
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# PREDICTIONS
# ═══════════════════════════════════════════════════════════

@router.get("/predictions")
async def get_predictions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    pairs = db.query(CurrencyPair).filter(CurrencyPair.is_active == True).all()
    prediction_service = PredictionService(db)
    results = []
    
    for pair in pairs:
        try:
            pred = prediction_service.predict(pair.id, "24h")
            results.append({
                "pair": f"{pair.base_currency.code}/{pair.quote_currency.code}",
                "predicted_rate": pred['rate'],
                "confidence": pred.get('confidence', 0.0),
                "model": pred.get('model_used', 'moving_average')
            })
        except Exception as e:
            logger.error(f"Prediction failed for pair {pair.id}: {e}")
    
    return {"predictions": results}