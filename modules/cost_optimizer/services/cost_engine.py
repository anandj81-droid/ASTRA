"""
Cost Engine - Core cost calculation logic.
Given base rate + provider config, computes total landed cost.
"""
import logging
from typing import Dict
from decimal import Decimal, ROUND_HALF_UP

from modules.cost_optimizer.models import ProviderConfig

logger = logging.getLogger(__name__)


def _round2(x: float) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class CostEngine:
    """Computes cost breakdown for a single provider."""

    def __init__(self, provider: ProviderConfig):
        self.provider = provider

    def _get_corridor_config(self, base: str, quote: str) -> Dict:
        """Return provider config, applying corridor override if present."""
        base_cfg = {
            "rate_markup_pct": self.provider.rate_markup_pct or 0.0,
            "fixed_fee": self.provider.fixed_fee or 0.0,
            "variable_fee_pct": self.provider.variable_fee_pct or 0.0,
            "min_fee": self.provider.min_fee or 0.0,
            "max_fee": self.provider.max_fee,
        }
        overrides = self.provider.corridor_overrides or {}
        corridor_key = f"{base.upper()}-{quote.upper()}"
        if corridor_key in overrides:
            base_cfg.update(overrides[corridor_key])
        return base_cfg

    def calculate(
        self,
        base: str,
        quote: str,
        amount: float,
        mid_market_rate: float,
    ) -> Dict:
        """Compute full cost breakdown for this provider."""
        cfg = self._get_corridor_config(base, quote)

        # 1. Offered rate = mid-market rate reduced by markup
        markup_factor = 1.0 - (cfg["rate_markup_pct"] / 100.0)
        offered_rate = mid_market_rate * markup_factor

        # 2. Cost components
        ideal_quote_amount = amount * mid_market_rate
        actual_quote_amount = amount * offered_rate
        rate_markup_cost = (ideal_quote_amount - actual_quote_amount) / mid_market_rate

        fixed_fee = cfg["fixed_fee"]
        variable_fee = amount * (cfg["variable_fee_pct"] / 100.0)
        total_fee = fixed_fee + variable_fee

        if total_fee < cfg["min_fee"]:
            total_fee = cfg["min_fee"]
        if cfg["max_fee"] is not None and total_fee > cfg["max_fee"]:
            total_fee = cfg["max_fee"]

        # 3. Net amount sent (after fee)
        net_amount = amount - total_fee
        if net_amount <= 0:
            return {
                "provider": self.provider.name,
                "provider_display_name": self.provider.display_name,
                "mid_market_rate": round(mid_market_rate, 6),
                "offered_rate": round(offered_rate, 6),
                "rate_markup_pct": round(cfg["rate_markup_pct"], 4),
                "rate_markup_cost": None,
                "fixed_fee": _round2(fixed_fee),
                "variable_fee": _round2(variable_fee),
                "total_fee": _round2(total_fee),
                "total_cost": None,
                "recipient_gets": 0.0,
                "settlement_days": self.provider.settlement_days,
                "reliability_score": self.provider.reliability_score,
                "error": "fee_exceeds_amount",
            }

        recipient_gets = net_amount * offered_rate
        total_cost = rate_markup_cost + total_fee

        def _fmt_rate(x: float) -> float:
            return round(x, 6) if x < 100 else round(x, 4)

        return {
            "provider": self.provider.name,
            "provider_display_name": self.provider.display_name,
            "mid_market_rate": _fmt_rate(mid_market_rate),
            "offered_rate": _fmt_rate(offered_rate),
            "rate_markup_pct": round(cfg["rate_markup_pct"], 4),
            "rate_markup_cost": _round2(rate_markup_cost),
            "fixed_fee": _round2(fixed_fee),
            "variable_fee": _round2(variable_fee),
            "total_fee": _round2(total_fee),
            "total_cost": _round2(total_cost),
            "recipient_gets": _round2(recipient_gets),
            "settlement_days": self.provider.settlement_days,
            "reliability_score": self.provider.reliability_score,
        }