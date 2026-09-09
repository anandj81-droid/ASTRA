# tasks.py
import logging
from datetime import datetime, timedelta
from celery_app import celery_app
from database import SessionLocal
from models import CurrencyPair, FXRate, AgentRule, Transaction
from fx_service import fx_service
from agent import AgentEngine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

@celery_app.task(name="collect_fx_rates")
def collect_fx_rates():
    """Collect FX rates for all active currency pairs"""
    logger.info("Starting FX rate collection...")
    
    db = SessionLocal()
    try:
        pairs = db.query(CurrencyPair).filter(CurrencyPair.is_active == True).all()
        rates_collected = 0
        errors = 0
        
        for pair in pairs:
            try:
                base = pair.base_currency.code
                quote = pair.quote_currency.code
                
                rate_data = fx_service.get_rate(base, quote)
                if rate_data:
                    # Save to database
                    fx_rate = FXRate(
                        pair_id=pair.id,
                        rate=rate_data['rate'],
                        bid=rate_data.get('bid'),
                        ask=rate_data.get('ask'),
                        source=rate_data.get('source', 'api'),
                        timestamp=datetime.utcnow()
                    )
                    db.add(fx_rate)
                    rates_collected += 1
                    logger.debug(f"✅ Collected rate for {base}/{quote}: {rate_data['rate']}")
                else:
                    errors += 1
                    logger.warning(f"❌ Failed to get rate for {base}/{quote}")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error collecting rate for pair {pair.id}: {e}")
        
        db.commit()
        logger.info(f"FX rate collection completed: {rates_collected} rates collected, {errors} errors")
        return {
            "status": "completed",
            "pairs_processed": len(pairs),
            "rates_collected": rates_collected,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"FX rate collection failed: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="check_agent_rules")
def check_agent_rules():
    """Check and execute agent rules"""
    logger.info("Checking agent rules...")
    
    db = SessionLocal()
    try:
        # Get all active rules
        rules = db.query(AgentRule).filter(AgentRule.is_active == True).all()
        executed = 0
        errors = 0
        
        for rule in rules:
            try:
                # Get current rate
                pair = db.query(CurrencyPair).filter(CurrencyPair.id == rule.pair_id).first()
                if not pair:
                    continue
                
                rate_data = fx_service.get_rate(rule.source_currency, rule.target_currency)
                if not rate_data:
                    continue
                
                current_rate = rate_data['rate']
                
                # Check if rule should execute
                should_execute = False
                execution_details = {}
                
                if rule.rule_type == "target_rate" and rule.target_rate:
                    if current_rate >= rule.target_rate:
                        should_execute = True
                        execution_details['rate'] = current_rate
                        execution_details['reason'] = f"Target rate {rule.target_rate} reached"
                
                elif rule.rule_type == "predictive":
                    # Simple predictive logic
                    if current_rate > rule.target_rate * 1.01:  # 1% above target
                        should_execute = True
                        execution_details['rate'] = current_rate
                        execution_details['reason'] = "Predictive trigger"
                
                elif rule.rule_type == "schedule":
                    # Check if scheduled day/time matches
                    now = datetime.now()
                    if rule.schedule_day and rule.schedule_day == now.day:
                        if rule.schedule_time and rule.schedule_time == now.strftime("%H:%M"):
                            should_execute = True
                            execution_details['rate'] = current_rate
                            execution_details['reason'] = "Scheduled trigger"
                
                if should_execute:
                    # Execute the rule
                    engine = AgentEngine(db)
                    # Use sync version (not async for Celery)
                    transaction = Transaction(
                        user_id=rule.user_id,
                        rule_id=rule.id,
                        from_currency=rule.source_currency,
                        to_currency=rule.target_currency,
                        from_amount=float(rule.amount),
                        to_amount=float(rule.amount) * float(current_rate),
                        rate_used=current_rate,
                        currency_pair=f"{rule.source_currency}/{rule.target_currency}",
                        amount=float(rule.amount),
                        executed_rate=current_rate,
                        status="executed",
                        execution_time=datetime.now()
                    )
                    db.add(transaction)
                    
                    rule.execution_count += 1
                    rule.last_executed = datetime.now()
                    
                    executed += 1
                    logger.info(f"✅ Rule {rule.id} executed: {rule.source_currency}/{rule.target_currency} at {current_rate}")
                
            except Exception as e:
                errors += 1
                logger.error(f"Error executing rule {rule.id}: {e}")
                rule.error_message = str(e)
        
        db.commit()
        logger.info(f"Rule check completed: {executed} executed, {errors} errors")
        return {
            "status": "completed",
            "rules_checked": len(rules),
            "executed": executed,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Rule check failed: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="train_prediction_models")
def train_prediction_models():
    """Train prediction models"""
    logger.info("Starting model training...")
    
    db = SessionLocal()
    try:
        # Simple placeholder - just log
        logger.info("Model training would run here")
        return {"status": "completed", "message": "Model training placeholder"}
    except Exception as e:
        logger.error(f"Model training failed: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="cleanup_old_logs")
def cleanup_old_logs():
    """Cleanup old log files"""
    logger.info("Cleaning up old logs...")
    return {"status": "completed", "message": "Log cleanup placeholder"}


@celery_app.task(name="health_check")
def health_check():
    """Health check task"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}