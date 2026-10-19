from sqlalchemy.orm import Session
from .bank_performance import get_corridor_stats, seed_default_banks


def pick_bank(db: Session, src: str, tgt: str, amount: float, strategy: str = "balanced"):
    seed_default_banks()
    corridor = f"{src}-{tgt}"
    candidates = get_corridor_stats(db, corridor)

    if not candidates:
        return {"corridor": corridor, "amount": amount, "recommended": None,
                "reason": "No banks serve this corridor yet."}

    def score(c):
        success = c["success_rate"]                       # 0..1
        speed = 1.0 / (1.0 + c["avg_settlement_seconds"] / 3600.0)  # faster = higher
        cost = 1.0 / (1.0 + c["avg_cost_usd"])            # cheaper = higher
        if strategy == "fastest":
            return 0.7 * speed + 0.3 * success
        if strategy == "cheapest":
            return 0.7 * cost + 0.3 * success
        return 0.45 * success + 0.35 * speed + 0.20 * cost

    ranked = sorted(candidates, key=score, reverse=True)
    best = ranked[0]

    return {
        "corridor": corridor,
        "amount": amount,
        "strategy": strategy,
        "recommended": {
            "bank_code": best["bank_code"],
            "bank_name": best["bank_name"],
            "score": round(score(best), 4),
            "success_rate": round(best["success_rate"], 3),
            "avg_settlement_seconds": best["avg_settlement_seconds"],
            "avg_cost_usd": round(best["avg_cost_usd"], 2),
        },
        "alternatives": [
            {"bank_code": c["bank_code"], "score": round(score(c), 4)}
            for c in ranked[1:4]
        ],
    }