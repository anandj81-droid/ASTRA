"""Cost Optimizer Module Definition"""
from fastapi import FastAPI

from modules.module_base import AstraModule
from modules.cost_optimizer.routes import router as cost_router
from modules.cost_optimizer.models import ProviderConfig   # ⚠️ ADDED — was missing


class CostOptimizerModule(AstraModule):
    name = "cost_optimizer"
    version = "1.0.0"
    display_name = "Cost Optimizer"
    description = "Compare payment providers, detect hidden fees, optimize transfer costs"
    dependencies = ["fx_tool"]

    def register_routes(self, app: FastAPI) -> None:
        app.include_router(cost_router, prefix="/api/v1/cost", tags=["Cost Optimizer"])

    def get_api_prefix(self) -> str:
        return "/api/v1/cost"

    def on_startup(self) -> None:
        """Seed default provider configs if none exist."""
        from core.database import SessionLocal
        db = SessionLocal()
        try:
            count = db.query(ProviderConfig).count()
            if count == 0:
                self._seed_default_providers(db)
        finally:
            db.close()

    def _seed_default_providers(self, db) -> None:
        """Seed realistic provider configs for demo."""
        import logging
        logger = logging.getLogger(__name__)

        providers = [
            ProviderConfig(
                name="bank_wire",
                display_name="Bank Wire (SWIFT)",
                rate_markup_pct=2.0,
                fixed_fee=25.0,
                variable_fee_pct=0.1,
                min_fee=25.0,
                settlement_days=3,
                reliability_score=0.95,
                corridor_overrides={
                    "USD-INR": {"rate_markup_pct": 2.5, "fixed_fee": 25.0},
                    "USD-EUR": {"rate_markup_pct": 1.5, "fixed_fee": 15.0},
                },
            ),
            ProviderConfig(
                name="wise",
                display_name="Wise",
                rate_markup_pct=0.4,
                fixed_fee=0.0,
                variable_fee_pct=0.6,
                min_fee=2.0,
                settlement_days=1,
                reliability_score=0.92,
                corridor_overrides={
                    "USD-INR": {"rate_markup_pct": 0.35, "variable_fee_pct": 0.55},
                },
            ),
            ProviderConfig(
                name="remitly",
                display_name="Remitly",
                rate_markup_pct=0.7,
                fixed_fee=0.0,
                variable_fee_pct=0.5,
                min_fee=1.99,
                settlement_days=0,
                reliability_score=0.88,
            ),
            ProviderConfig(
                name="revolut",
                display_name="Revolut",
                rate_markup_pct=0.0,
                fixed_fee=0.0,
                variable_fee_pct=0.5,
                min_fee=0.0,
                settlement_days=0,
                reliability_score=0.85,
                corridor_overrides={
                    "USD-INR": {"rate_markup_pct": 0.6, "variable_fee_pct": 0.5},
                },
            ),
            ProviderConfig(
                name="western_union",
                display_name="Western Union",
                rate_markup_pct=1.8,
                fixed_fee=5.0,
                variable_fee_pct=1.0,
                min_fee=5.0,
                settlement_days=0,
                reliability_score=0.90,
            ),
        ]

        for p in providers:
            db.add(p)
        db.commit()
        logger.info(f"✅ Seeded {len(providers)} default cost providers")