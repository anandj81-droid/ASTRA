# tests/test_rule_execution.py

import pytest
from datetime import datetime, timedelta
from agent import AgentEngine
from models import Rule, RuleType, RuleStatus, Transaction
from database import SessionLocal

class TestRuleExecution:
    
    def setup_method(self):
        """Setup test data before each test"""
        self.db = SessionLocal()
        self.agent = AgentEngine()
        
    def teardown_method(self):
        """Cleanup after each test"""
        self.db.close()
        
    def test_target_rate_execution(self):
        """Test target rate rule triggers correctly"""
        # Create target rate rule
        rule = Rule(
            name="USD/INR Target 85",
            rule_type=RuleType.TARGET_RATE,
            currency_pair="USD/INR",
            target_rate=85.00,
            amount=1000,
            status=RuleStatus.ACTIVE
        )
        self.db.add(rule)
        self.db.commit()
        
        # Simulate rate reaching target
        fx_rate = 85.05
        
        # Check rule should trigger
        assert self.agent.check_target_rate(rule, fx_rate) == True
        
    def test_predictive_rule_execution(self):
        """Test predictive rule triggers with confidence"""
        rule = Rule(
            name="USD/INR Predictive",
            rule_type=RuleType.PREDICTIVE,
            currency_pair="USD/INR",
            confidence_threshold=75.0,
            amount=1000,
            status=RuleStatus.ACTIVE
        )
        self.db.add(rule)
        self.db.commit()
        
        # Mock prediction with high confidence
        prediction = {
            'predicted_rate': 84.75,
            'confidence': 82.5,
            'direction': 'up'
        }
        
        # Should trigger
        assert self.agent.check_predictive(rule, prediction) == True
        
    def test_schedule_rule_execution(self):
        """Test scheduled rule triggers at correct time"""
        # Create rule for tomorrow at 10:00
        tomorrow = datetime.now() + timedelta(days=1)
        rule = Rule(
            name="Monthly Transfer",
            rule_type=RuleType.SCHEDULE,
            currency_pair="USD/INR",
            schedule_day=tomorrow.day,
            schedule_time="10:00",
            amount=1500,
            status=RuleStatus.ACTIVE
        )
        self.db.add(rule)
        self.db.commit()
        
        # Check if should execute now
        now = datetime.now()
        assert self.agent.check_schedule(rule, now) == False
        
        # Simulate at scheduled time
        scheduled_time = datetime(
            now.year, now.month, 
            rule.schedule_day, 10, 0
        )
        assert self.agent.check_schedule(rule, scheduled_time) == True