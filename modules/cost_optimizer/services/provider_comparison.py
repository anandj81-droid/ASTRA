"""
Provider Comparison - Ranks all providers for a given transfer.
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from core.models import Currency
from core.fx_service import fx_service
from modules.cost_optimizer.models import ProviderConfig, CostComparison
from modules.cost_optimizer.services.cost_engine import CostEngine

logger = logging.getLogger(__name__)


class ProviderComparison:
    """Compare costs across all active providers."""

    def __init__(self, db: Session):
        self.db = db

    def get_providers(self, active_only: bool = True) -> List[ProviderConfig]:
        q = self.db.query(ProviderConfig)
        if active_only:
            q = q.filter(ProviderConfig.is_active == True)
        return q.all()

    def get_mid_market_rate(self, base: str, quote: str) -> Optional[float]:
        """Get mid-market rate from FX service."""
        try:
            rate_data = fx_service.get_rate(base.upper(), quote.upper())
            if rate_data and "rate" in rate_data:
                return float(rate_data["rate"])
        except Exception as e:
            logger.error(f"Failed to get rate for {base}/{quote}: {e}")
        return None

    def compare(
        self,
        base: str,
        quote: str,
        amount: float,
        user_id: Optional[int] = None,
        persist: bool = True,
    ) -> Dict:
        """Compare all active providers for a transfer."""
        base = base.upper()
        quote = quote.upper()

        if amount <= 0:
            raise ValueError("amount must be positive")

        for code in (base, quote):
            if not self.db.query(Currency).filter(Currency.code == code).first():
                raise ValueError(f"Currency {code} not found")

        mid_market_rate = self.get_mid_market_rate(base, quote)
        if not mid_market_rate:
            raise ValueError(f"Could not get FX rate for {base}/{quote}")

        providers = self.get_providers(active_only=True)
        if not providers:
            raise ValueError("No active providers configured")

        results = []
        for provider in providers:
            try:
                engine = CostEngine(provider)
                r = engine.calculate(base, quote, amount, mid_market_rate)
                if r.get("total_cost") is not None and "error" not in r:
                    results.append(r)
            except Exception as e:
                logger.error(f"Provider {provider.name} failed: {e}")

        if not results:
            raise ValueError("No provider could quote this transfer")

        results.sort(key=lambda r: r["total_cost"])

        best = results[0]
        worst = results[-1]
        max_savings = round(worst["total_cost"] - best["total_cost"], 2)

        response = {
            "input": {"base": base, "quote": quote, "amount": amount},
            "mid_market_rate": results[0]["mid_market_rate"],
            "results": results,
            "best": best,
            "worst": worst,
            "max_savings": max_savings,
            "provider_count": len(results),
        }

        if persist:
            try:
                record = CostComparison(
                    user_id=user_id,
                    base_currency=base,
                    quote_currency=quote,
                    amount=amount,
                    results_json=results,
                    best_provider=best["provider"],
                    best_total_cost=best["total_cost"],
                    worst_provider=worst["provider"],
                    worst_total_cost=worst["total_cost"],
                    max_savings=max_savings,
                )
                self.db.add(record)
                self.db.commit()
            except Exception as e:
                logger.error(f"Failed to persist comparison: {e}")
                self.db.rollback()

        return response