"""
Transparency - Detects hidden fees and rate markups.
"""
import logging
from typing import Dict, List
from sqlalchemy.orm import Session

from modules.cost_optimizer.models import ProviderConfig
from modules.cost_optimizer.services.cost_engine import CostEngine
from modules.cost_optimizer.services.provider_comparison import ProviderComparison

logger = logging.getLogger(__name__)


class TransparencyAnalyzer:
    """Detects hidden costs in provider pricing."""

    HIGH_MARKUP_PCT = 1.5
    HIGH_FIXED_FEE = 10.0
    SLOW_SETTLEMENT_DAYS = 3
    LOW_RELIABILITY = 0.7

    def __init__(self, db: Session):
        self.db = db

    def analyze_provider(
        self,
        provider_name: str,
        base: str,
        quote: str,
        amount: float = 1000.0,
    ) -> Dict:
        """Deep-dive analysis of a single provider."""
        provider = self.db.query(ProviderConfig).filter(
            ProviderConfig.name == provider_name,
            ProviderConfig.is_active == True,
        ).first()

        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found or inactive")

        comparison = ProviderComparison(self.db)
        mid_rate = comparison.get_mid_market_rate(base, quote)
        if not mid_rate:
            raise ValueError(f"Could not get FX rate for {base}/{quote}")

        engine = CostEngine(provider)
        breakdown = engine.calculate(base, quote, amount, mid_rate)

        flags = self._generate_flags(provider, breakdown, mid_rate)
        transparency_score = self._compute_transparency_score(provider, breakdown)

        return {
            "provider": provider.name,
            "display_name": provider.display_name,
            "sample_amount": amount,
            "mid_market_rate": breakdown["mid_market_rate"],
            "breakdown": breakdown,
            "flags": flags,
            "transparency_score": transparency_score,
            "verdict": self._verdict(transparency_score),
        }

    def compare_transparency(
        self,
        base: str,
        quote: str,
        amount: float = 1000.0,
    ) -> Dict:
        """Compare transparency across all providers."""
        comparison = ProviderComparison(self.db)
        providers = comparison.get_providers(active_only=True)

        analyses = []
        for p in providers:
            try:
                a = self.analyze_provider(p.name, base, quote, amount)
                analyses.append(a)
            except Exception as e:
                logger.error(f"Transparency analysis failed for {p.name}: {e}")

        analyses.sort(key=lambda a: a["transparency_score"], reverse=True)

        return {
            "input": {"base": base, "quote": quote, "amount": amount},
            "analyses": analyses,
            "most_transparent": analyses[0] if analyses else None,
            "least_transparent": analyses[-1] if analyses else None,
        }

    def _generate_flags(self, provider, breakdown, mid_rate) -> List[Dict]:
        flags = []

        if breakdown["rate_markup_pct"] > self.HIGH_MARKUP_PCT:
            flags.append({
                "level": "warning",
                "code": "high_rate_markup",
                "message": f"Rate markup of {breakdown['rate_markup_pct']}% is above {self.HIGH_MARKUP_PCT}% threshold",
                "impact": f"Costs {breakdown['rate_markup_cost']} in hidden markup",
            })

        if breakdown["fixed_fee"] > self.HIGH_FIXED_FEE:
            flags.append({
                "level": "info",
                "code": "high_fixed_fee",
                "message": f"Fixed fee of {breakdown['fixed_fee']} may not suit small transfers",
            })

        if provider.settlement_days > self.SLOW_SETTLEMENT_DAYS:
            flags.append({
                "level": "warning",
                "code": "slow_settlement",
                "message": f"Settlement in {provider.settlement_days} days is slow",
            })

        if provider.reliability_score < self.LOW_RELIABILITY:
            flags.append({
                "level": "warning",
                "code": "low_reliability",
                "message": f"Reliability score {provider.reliability_score} is below threshold",
            })

        if not flags:
            flags.append({
                "level": "ok",
                "code": "clean",
                "message": "No hidden fee concerns detected",
            })

        return flags

    def _compute_transparency_score(self, provider, breakdown) -> float:
        score = 1.0
        markup = breakdown["rate_markup_pct"]
        score -= min(markup / 5.0, 0.4)
        score -= min(provider.settlement_days / 25.0, 0.2)
        score -= max(0, (1.0 - provider.reliability_score) * 0.4)
        return round(max(0.0, min(1.0, score)), 3)

    def _verdict(self, score: float) -> str:
        if score >= 0.85:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "fair"
        else:
            return "poor"