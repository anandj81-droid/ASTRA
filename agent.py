# agent.py
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from models import AgentRule, Transaction, CurrencyPair
from iso20022_messages import ISO20022MessageGenerator
from bank_integration import BankIntegration
from config import config

logger = logging.getLogger(__name__)

class AgentEngine:
    """Agent engine for executing trading rules"""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # Initialize ISO20022 with default values
        self.iso_generator = ISO20022MessageGenerator(
            sender_bic="ASTRAINBBXXX",
            receiver_bic="HDFCINBBXXX",
            sender_account="ASTRA123456789"
        )
        
        # Initialize BankIntegration with default values
        self.bank_api = BankIntegration(
            api_url=config.BANK_API_URL,
            api_key=config.BANK_API_KEY,
            bank_code=config.BANK_DEFAULT
        )
    
    def create_rule(self, user_id: int, pair_id: int, rule_type: str, 
                    amount: float, target_rate: Optional[float] = None,
                    schedule_day: Optional[int] = None, 
                    schedule_time: Optional[str] = None,
                    min_confidence: float = 0.7,
                    prediction_horizon: str = "24h") -> AgentRule:
        """Create a new agent rule matching your database schema"""
        # Get the currency pair to get currency codes
        pair = self.db.query(CurrencyPair).filter(
            CurrencyPair.id == pair_id
        ).first()
        
        if not pair:
            raise ValueError(f"Currency pair with id {pair_id} not found")
        
        # Ensure numeric values are floats
        amount = float(amount) if amount else 0.0
        target_rate = float(target_rate) if target_rate else None
        min_confidence = float(min_confidence) if min_confidence else 0.7
        
        # Create rule with your actual database columns
        rule = AgentRule(
            user_id=user_id,
            pair_id=pair_id,
            rule_type=rule_type,
            source_currency=pair.base_currency.code,
            target_currency=pair.quote_currency.code,
            target_rate=target_rate,
            amount=amount,
            is_active=True,
            currency_code=pair.base_currency.code,
            schedule_day=schedule_day,
            schedule_time=schedule_time,
            min_confidence=min_confidence,
            prediction_horizon=prediction_horizon,
            execution_count=0
        )
        
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        self.logger.info(f"Rule created: ID={rule.id}, Type={rule_type}, {rule.source_currency}/{rule.target_currency}")
        return rule
    
    def get_user_rules(self, user_id: int) -> list:
        """Get all rules for a user"""
        return self.db.query(AgentRule).filter(
            AgentRule.user_id == user_id
        ).all()
    
    def get_rule(self, rule_id: int, user_id: int) -> Optional[AgentRule]:
        """Get a specific rule"""
        rule = self.db.query(AgentRule).filter(
            AgentRule.id == rule_id,
            AgentRule.user_id == user_id
        ).first()
        
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")
        
        return rule
    
    def update_rule_status(self, rule_id: int, status: str) -> AgentRule:
        """Update rule status"""
        rule = self.db.query(AgentRule).filter(
            AgentRule.id == rule_id
        ).first()
        
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")
        
        # Use is_active (boolean)
        rule.is_active = (status.lower() == 'active')
        
        self.db.commit()
        self.db.refresh(rule)
        
        return rule
    
    def delete_rule(self, rule_id: int):
        """Delete a rule"""
        try:
            # First, check if there are transactions for this rule
            transactions = self.db.query(Transaction).filter(
                Transaction.rule_id == rule_id
            ).all()
            
            # Delete associated transactions first (if any)
            if transactions:
                self.logger.info(f"Deleting {len(transactions)} transactions for rule {rule_id}")
                for tx in transactions:
                    self.db.delete(tx)
                self.db.commit()
            
            # Now delete the rule
            rule = self.db.query(AgentRule).filter(
                AgentRule.id == rule_id
            ).first()
            
            if not rule:
                raise ValueError(f"Rule {rule_id} not found")
            
            self.db.delete(rule)
            self.db.commit()
            
            self.logger.info(f"Rule {rule_id} deleted successfully")
            
        except Exception as e:
            self.logger.error(f"Error deleting rule {rule_id}: {e}")
            self.db.rollback()
            raise
    
    async def execute_rule(self, rule: AgentRule, execution_details: dict) -> Transaction:
        """Execute a rule with full integration"""
        try:
            # Use source_currency and target_currency from rule
            source_curr = rule.source_currency
            target_curr = rule.target_currency
            
            # Prepare transaction data for ISO 20022
            transaction_data = {
                'amount': float(rule.amount),
                'currency': source_curr,
                'beneficiary_name': 'Recipient Name',
                'beneficiary_account': 'RECIPIENT123456789',
                'beneficiary_bic': 'RECIPIENTBICXXX',
                'reference': f"PAY{rule.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'purpose': f'Astra Platform payment - Rule {rule.id}'
            }
            
            # 1. Generate ISO 20022 message
            xml_message = self.iso_generator.generate_pain_001(transaction_data)
            
            # 2. Save XML for audit
            xml_path = self.save_xml_message(rule.id, xml_message)
            
            # 3. Call Bank API
            payment_response = self.bank_api.submit_payment(
                iso20022_xml=xml_message,
                transaction_id=rule.id
            )
            
            # 4. Create transaction record matching your database
            transaction = Transaction(
                user_id=rule.user_id,
                rule_id=rule.id,
                from_currency=source_curr,
                to_currency=target_curr,
                from_amount=float(rule.amount),
                to_amount=float(rule.amount) * float(execution_details.get('rate', 1.0)),
                rate_used=execution_details.get('rate', 1.0),
                currency_pair=f"{source_curr}/{target_curr}",
                amount=float(rule.amount),
                executed_rate=execution_details.get('rate'),
                status=payment_response.get('status', 'pending'),
                bank_reference=payment_response.get('reference'),
                iso_message_path=xml_path,
                execution_time=datetime.now()
            )
            
            self.db.add(transaction)
            
            # 5. Update rule execution count
            rule.execution_count += 1
            rule.last_executed = datetime.now()
            
            self.db.commit()
            self.logger.info(f"Rule {rule.id} executed successfully")
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error executing rule {rule.id}: {str(e)}")
            # Handle failure
            rule.is_active = False
            rule.error_message = str(e)
            self.db.commit()
            raise
    
    def save_xml_message(self, rule_id: int, xml_content: str) -> str:
        """Save XML message for audit"""
        import os
        from config import config
        
        # Create directory if it doesn't exist
        os.makedirs(config.ISO20022_MESSAGE_DIR, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"payment_{rule_id}_{timestamp}.xml"
        filepath = os.path.join(config.ISO20022_MESSAGE_DIR, filename)
        
        # Save file
        with open(filepath, 'w') as f:
            f.write(xml_content)
        
        self.logger.info(f"ISO 20022 message saved: {filepath}")
        return filepath