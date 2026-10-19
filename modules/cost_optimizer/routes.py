"""
Cost Optimizer Module - API Routes
Mounted at: /api/v1/cost/*
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
import logging
import os

from core.database import get_db
from core.auth import get_current_user
from modules.cost_optimizer.models import ProviderConfig, CostComparison
from modules.cost_optimizer.services.provider_comparison import ProviderComparison
from modules.cost_optimizer.services.transparency import TransparencyAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════

class CompareRequest(BaseModel):
    base: str = Field(..., min_length=3, max_length=3, description="Source currency, e.g. USD")
    quote: str = Field(..., min_length=3, max_length=3, description="Destination currency, e.g. INR")
    amount: float = Field(..., gt=0, description="Amount to send in base currency")


class ProviderConfigRequest(BaseModel):
    name: str
    display_name: str
    rate_markup_pct: float = 0.0
    fixed_fee: float = 0.0
    variable_fee_pct: float = 0.0
    min_fee: float = 0.0
    max_fee: Optional[float] = None
    settlement_days: int = 1
    reliability_score: float = 1.0
    corridor_overrides: Optional[dict] = None


# ═══════════════════════════════════════════════════════════
# COMPARE ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.post("/compare")
async def compare_providers(
    req: CompareRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Compare all active providers for a transfer. Returns ranked list."""
    try:
        comparison = ProviderComparison(db)
        return comparison.compare(
            base=req.base,
            quote=req.quote,
            amount=req.amount,
            user_id=current_user["id"],
            persist=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Compare failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_providers_get(
    base: str = Query(..., min_length=3, max_length=3),
    quote: str = Query(..., min_length=3, max_length=3),
    amount: float = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """GET version of /compare — convenient for browser testing."""
    try:
        comparison = ProviderComparison(db)
        return comparison.compare(
            base=base, quote=quote, amount=amount,
            user_id=current_user["id"], persist=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history")
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Recent cost comparisons for this user."""
    records = db.query(CostComparison).filter(
        CostComparison.user_id == current_user["id"]
    ).order_by(CostComparison.created_at.desc()).limit(limit).all()

    return {
        "comparisons": [
            {
                "id": r.id,
                "base": r.base_currency,
                "quote": r.quote_currency,
                "amount": r.amount,
                "best_provider": r.best_provider,
                "best_total_cost": r.best_total_cost,
                "worst_provider": r.worst_provider,
                "worst_total_cost": r.worst_total_cost,
                "max_savings": r.max_savings,
                "created_at": r.created_at,
            }
            for r in records
        ]
    }


# ═══════════════════════════════════════════════════════════
# TRANSPARENCY ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.get("/transparency/{provider_name}")
async def analyze_provider_transparency(
    provider_name: str,
    base: str = Query("USD", min_length=3, max_length=3),
    quote: str = Query("INR", min_length=3, max_length=3),
    amount: float = Query(1000.0, gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Deep analysis of a provider's pricing transparency."""
    try:
        analyzer = TransparencyAnalyzer(db)
        return analyzer.analyze_provider(provider_name, base, quote, amount)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Transparency failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transparency")
async def compare_all_transparency(
    base: str = Query("USD", min_length=3, max_length=3),
    quote: str = Query("INR", min_length=3, max_length=3),
    amount: float = Query(1000.0, gt=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Compare transparency across all providers."""
    try:
        analyzer = TransparencyAnalyzer(db)
        return analyzer.compare_transparency(base, quote, amount)
    except Exception as e:
        logger.error(f"Transparency compare failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# PROVIDER MANAGEMENT
# ═══════════════════════════════════════════════════════════

@router.get("/providers")
async def list_providers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all configured providers."""
    providers = db.query(ProviderConfig).all()
    return {
        "providers": [
            {
                "id": p.id,
                "name": p.name,
                "display_name": p.display_name,
                "rate_markup_pct": p.rate_markup_pct,
                "fixed_fee": p.fixed_fee,
                "variable_fee_pct": p.variable_fee_pct,
                "min_fee": p.min_fee,
                "max_fee": p.max_fee,
                "settlement_days": p.settlement_days,
                "reliability_score": p.reliability_score,
                "is_active": p.is_active,
                "corridor_overrides": p.corridor_overrides,
            }
            for p in providers
        ],
        "count": len(providers),
    }


@router.post("/providers")
async def create_provider(
    req: ProviderConfigRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new provider config."""
    existing = db.query(ProviderConfig).filter(ProviderConfig.name == req.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Provider '{req.name}' already exists")

    p = ProviderConfig(
        name=req.name,
        display_name=req.display_name,
        rate_markup_pct=req.rate_markup_pct,
        fixed_fee=req.fixed_fee,
        variable_fee_pct=req.variable_fee_pct,
        min_fee=req.min_fee,
        max_fee=req.max_fee,
        settlement_days=req.settlement_days,
        reliability_score=req.reliability_score,
        corridor_overrides=req.corridor_overrides,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    return {"id": p.id, "name": p.name, "message": f"Provider '{p.name}' created"}


@router.patch("/providers/{provider_name}/toggle")
async def toggle_provider(
    provider_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Enable or disable a provider."""
    p = db.query(ProviderConfig).filter(ProviderConfig.name == provider_name).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")
    p.is_active = not p.is_active
    db.commit()
    return {"name": p.name, "is_active": p.is_active}


# ═══════════════════════════════════════════════════════════
# UI PAGES
# ═══════════════════════════════════════════════════════════

@router.get("/test", response_class=HTMLResponse)
async def test_cost_page():
    """Serve the Cost Optimizer test page."""
    try:
        with open("modules/cost_optimizer/static/test_cost.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
            <html>
                <head><title>Cost Optimizer Test</title></head>
                <body style="font-family: sans-serif; padding: 40px; background: #f0f2f5;">
                    <h1>💰 Cost Optimizer</h1>
                    <p>test_cost.html not found. Please create it.</p>
                </body>
            </html>
        """)