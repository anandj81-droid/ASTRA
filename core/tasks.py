# core/tasks.py
from core.celery_app import celery_app
from core.database import get_db_session
from core.models import CurrencyPair, FXRate, AgentRule, Transaction
from core.fx_service import fx_service
from core.config import config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# CORE TASKS
# ═══════════════════════════════════════════════════════════

@celery_app.task(name="core.tasks.collect_fx_rates")
def collect_fx_rates():
    """Collect FX rates for all active pairs"""
    logger.info("Starting FX rate collection...")
    db = get_db_session()
    try:
        pairs = db.query(CurrencyPair).filter(CurrencyPair.is_active == True).all()
        for pair in pairs:
            try:
                base = pair.base_currency.code
                quote = pair.quote_currency.code
                rate_data = fx_service.get_rate(base, quote)
                if rate_data:
                    from decimal import Decimal
                    new_rate = FXRate(
                        pair_id=pair.id,
                        rate=Decimal(str(rate_data['rate'])),
                        source=rate_data.get('source', 'api')
                    )
                    db.add(new_rate)
            except Exception as e:
                logger.error(f"Failed to collect rate for pair {pair.id}: {e}")
        db.commit()
        logger.info(f"✅ Collected rates for {len(pairs)} pairs")
    finally:
        db.close()


@celery_app.task(name="core.tasks.check_agent_rules")
def check_agent_rules():
    """Check and evaluate active agent rules"""
    logger.info("Checking agent rules...")
    # Your existing rule-check logic here
    # (import from modules.fx_tool.services.rule_engine if needed)
    pass


@celery_app.task(name="core.tasks.train_prediction_models")
def train_prediction_models():
    """Train prediction models for all pairs"""
    logger.info("Training prediction models...")
    db = get_db_session()
    try:
        from modules.fx_tool.services.predictor import PredictionService
        service = PredictionService(db)
        service.train_all_models()
    finally:
        db.close()


@celery_app.task(name="core.tasks.cleanup_old_logs")
def cleanup_old_logs():
    """Cleanup old logs and data"""
    logger.info("Cleaning up old logs...")
    pass


# ═══════════════════════════════════════════════════════════
# MODULE TASK REGISTRATION
# ═══════════════════════════════════════════════════════════
# Module-specific tasks are auto-discovered via Celery's include list
# defined in core/celery_app.py. No need to import manually here.