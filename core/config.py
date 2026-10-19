# core/config.py
import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import json
from datetime import timedelta

load_dotenv()

class Config:
    """Astra Platform Configuration - Phase 4 Ready"""
    
    # ============================
    # APPLICATION CONFIGURATION
    # ============================
    APP_NAME = os.getenv("APP_NAME", "Astra")
    APP_VERSION = os.getenv("APP_VERSION", "4.0.0")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # ============================
    # MODULE FLAGS (PHASE 4)
    # ============================
    MODULE_FX_TOOL: bool = os.getenv("MODULE_FX_TOOL", "True").lower() == "true"
    MODULE_COST_OPTIMIZER: bool = os.getenv("MODULE_COST_OPTIMIZER", "False").lower() == "true"
    MODULE_LAST_MILE: bool = os.getenv("MODULE_LAST_MILE", "False").lower() == "true"
    MODULE_COMPLIANCE: bool = os.getenv("MODULE_COMPLIANCE", "False").lower() == "true"
    MODULE_RECONCILIATION: bool = os.getenv("MODULE_RECONCILIATION", "False").lower() == "true"
    MODULE_ORCHESTRATOR: bool = os.getenv("MODULE_ORCHESTRATOR", "False").lower() == "true"
    
    # ============================
    # DATABASE CONFIGURATION
    # ============================
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./astra.db")
    DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "5"))
    DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
    DATABASE_POOL_TIMEOUT = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
    DATABASE_POOL_RECYCLE = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))
    DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"
    
    # ============================
    # REDIS & CELERY CONFIGURATION
    # ============================
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    
    CELERY_TASK_TRACK_STARTED = os.getenv("CELERY_TASK_TRACK_STARTED", "True").lower() == "true"
    CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "300"))
    CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "240"))
    CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", "2"))
    CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "100"))
    
    CELERY_BEAT_SCHEDULE = {
        'collect_fx_rates': {
            'schedule': 3600.0,
            'task': 'core.tasks.collect_fx_rates'
        },
        'check_agent_rules': {
            'schedule': 300.0,
            'task': 'core.tasks.check_agent_rules'
        },
        'train_prediction_models': {
            'schedule': 86400.0,
            'task': 'core.tasks.train_prediction_models'
        },
        'cleanup_old_logs': {
            'schedule': 604800.0,
            'task': 'core.tasks.cleanup_old_logs'
        }
    }
    
    # ============================
    # FX RATES API
    # ============================
    FX_API_URL = os.getenv("FX_API_URL", "https://api.exchangerate-api.com/v4/latest")
    FX_API_KEY = os.getenv("FX_API_KEY", "")
    FX_API_FALLBACK_1 = os.getenv("FX_API_FALLBACK_1", "https://api.frankfurter.app/latest")
    FX_API_FALLBACK_2 = os.getenv("FX_API_FALLBACK_2", "https://api.exchangeratesapi.io/latest")
    FX_API_TIMEOUT = int(os.getenv("FX_API_TIMEOUT", "10"))
    FX_RATE_CACHE_TTL = int(os.getenv("FX_RATE_CACHE_TTL", "3600"))
    DEV_MOCK_FX_RATES = os.getenv("DEV_MOCK_FX_RATES", "True").lower() == "true"
    
    # ============================
    # AGENT ENGINE CONFIGURATION
    # ============================
    AGENT_CHECK_INTERVAL = int(os.getenv("AGENT_CHECK_INTERVAL", "300"))
    AGENT_MAX_AMOUNT = int(os.getenv("AGENT_MAX_AMOUNT", "1000000"))
    AGENT_MIN_AMOUNT = int(os.getenv("AGENT_MIN_AMOUNT", "100"))
    AGENT_MAX_DAILY_TRANSACTIONS = int(os.getenv("AGENT_MAX_DAILY_TRANSACTIONS", "50"))
    AGENT_MAX_MONTHLY_VOLUME = int(os.getenv("AGENT_MAX_MONTHLY_VOLUME", "10000000"))
    
    RULE_EXECUTION_TIMEOUT = int(os.getenv("RULE_EXECUTION_TIMEOUT", "60"))
    RULE_EXECUTION_RETRY_ATTEMPTS = int(os.getenv("RULE_EXECUTION_RETRY_ATTEMPTS", "3"))
    RULE_EXECUTION_RETRY_DELAY = int(os.getenv("RULE_EXECUTION_RETRY_DELAY", "300"))
    
    # ============================
    # BANK INTEGRATION
    # ============================
    BANK_API_ENABLED = os.getenv("BANK_API_ENABLED", "True").lower() == "true"
    BANK_API_URL = os.getenv("BANK_API_URL", "http://localhost:8001")
    BANK_API_KEY = os.getenv("BANK_API_KEY", "test-api-key-change-in-production")
    BANK_API_TIMEOUT = int(os.getenv("BANK_API_TIMEOUT", "30"))
    BANK_API_RETRY_ATTEMPTS = int(os.getenv("BANK_API_RETRY_ATTEMPTS", "3"))
    
    BANK_SUPPORTED_BANKS = os.getenv("BANK_SUPPORTED_BANKS", "HDFC,ICICI,SBI,AXIS,HSBC,CITI,STANDARD_CHARTERED").split(",")
    BANK_DEFAULT = os.getenv("BANK_DEFAULT", "HDFC")
    
    ISO20022_SCHEMA_VALIDATION = os.getenv("ISO20022_SCHEMA_VALIDATION", "True").lower() == "true"
    ISO20022_SAVE_MESSAGES = os.getenv("ISO20022_SAVE_MESSAGES", "True").lower() == "true"
    ISO20022_MESSAGE_DIR = os.getenv("ISO20022_MESSAGE_DIR", "./iso_messages")
    
    WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "True").lower() == "true"
    WEBHOOK_RETRY_ATTEMPTS = int(os.getenv("WEBHOOK_RETRY_ATTEMPTS", "5"))
    WEBHOOK_RETRY_DELAY = int(os.getenv("WEBHOOK_RETRY_DELAY", "60"))
    WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "10"))
    
    # ============================
    # NOTIFICATION SERVICES
    # ============================
    SENDGRID_ENABLED = os.getenv("SENDGRID_ENABLED", "False").lower() == "true"
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@astra-platform.com")
    SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "Astra Platform")
    
    TWILIO_ENABLED = os.getenv("TWILIO_ENABLED", "False").lower() == "true"
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
    
    SLACK_ENABLED = os.getenv("SLACK_ENABLED", "False").lower() == "true"
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
    
    # ============================
    # AI & MACHINE LEARNING
    # ============================
    PROPHET_ENABLED = os.getenv("PROPHET_ENABLED", "False").lower() == "true"
    PROPHET_MODEL_PATH = os.getenv("PROPHET_MODEL_PATH", "./models/prophet")
    PROPHET_FORECAST_DAYS = int(os.getenv("PROPHET_FORECAST_DAYS", "30"))
    
    LSTM_ENABLED = os.getenv("LSTM_ENABLED", "False").lower() == "true"
    LSTM_MODEL_PATH = os.getenv("LSTM_MODEL_PATH", "./models/lstm")
    LSTM_SEQUENCE_LENGTH = int(os.getenv("LSTM_SEQUENCE_LENGTH", "60"))
    LSTM_HIDDEN_UNITS = int(os.getenv("LSTM_HIDDEN_UNITS", "50"))
    
    MODEL_RETRAIN_INTERVAL = int(os.getenv("MODEL_RETRAIN_INTERVAL", "604800"))
    MODEL_MIN_TRAINING_DATA = int(os.getenv("MODEL_MIN_TRAINING_DATA", "90"))
    MODEL_VALIDATION_SPLIT = float(os.getenv("MODEL_VALIDATION_SPLIT", "0.2"))
    
    PREDICTION_CONFIDENCE_THRESHOLD = float(os.getenv("PREDICTION_CONFIDENCE_THRESHOLD", "0.75"))
    PREDICTION_ACCURACY_THRESHOLD = float(os.getenv("PREDICTION_ACCURACY_THRESHOLD", "0.80"))
    
    # ============================
    # MONITORING & LOGGING
    # ============================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "./logs/astra.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "False").lower() == "true"
    PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
    GRAFANA_ENABLED = os.getenv("GRAFANA_ENABLED", "False").lower() == "true"
    GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
    
    SENTRY_ENABLED = os.getenv("SENTRY_ENABLED", "False").lower() == "true"
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")
    
    # ============================
    # SECURITY & AUTHENTICATION
    # ============================
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    PASSWORD_REQUIRE_UPPERCASE = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "True").lower() == "true"
    PASSWORD_REQUIRE_LOWERCASE = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "True").lower() == "true"
    PASSWORD_REQUIRE_NUMBER = os.getenv("PASSWORD_REQUIRE_NUMBER", "True").lower() == "true"
    PASSWORD_REQUIRE_SPECIAL = os.getenv("PASSWORD_REQUIRE_SPECIAL", "True").lower() == "true"
    
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    RATE_LIMIT_LOGIN_ATTEMPTS = int(os.getenv("RATE_LIMIT_LOGIN_ATTEMPTS", "5"))
    RATE_LIMIT_LOGIN_WINDOW = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW", "300"))
    
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "32-byte-key-for-dev-only-change-me")
    ENCRYPTION_ALGORITHM = os.getenv("ENCRYPTION_ALGORITHM", "AES-256-GCM")
    
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")
    ALLOWED_METHODS = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    ALLOWED_HEADERS = os.getenv("ALLOWED_HEADERS", "Content-Type,Authorization,X-Requested-With").split(",")
    
    # ============================
    # REGULATORY COMPLIANCE
    # ============================
    RBI_COMPLIANCE_ENABLED = os.getenv("RBI_COMPLIANCE_ENABLED", "True").lower() == "true"
    RBI_SANDBOX_MODE = os.getenv("RBI_SANDBOX_MODE", "True").lower() == "true"
    RBI_KYC_REQUIRED = os.getenv("RBI_KYC_REQUIRED", "True").lower() == "true"
    RBI_TRANSACTION_LIMIT = int(os.getenv("RBI_TRANSACTION_LIMIT", "250000"))
    RBI_DAILY_LIMIT = int(os.getenv("RBI_DAILY_LIMIT", "500000"))
    RBI_MONTHLY_LIMIT = int(os.getenv("RBI_MONTHLY_LIMIT", "5000000"))
    
    AML_ENABLED = os.getenv("AML_ENABLED", "True").lower() == "true"
    AML_TRANSACTION_THRESHOLD = int(os.getenv("AML_TRANSACTION_THRESHOLD", "100000"))
    AML_SUSPICIOUS_ACTIVITY_REPORTING = os.getenv("AML_SUSPICIOUS_ACTIVITY_REPORTING", "True").lower() == "true"
    AML_DAILY_REPORT = os.getenv("AML_DAILY_REPORT", "True").lower() == "true"
    
    FATF_COMPLIANCE_ENABLED = os.getenv("FATF_COMPLIANCE_ENABLED", "True").lower() == "true"
    FATF_HIGH_RISK_COUNTRIES = os.getenv("FATF_HIGH_RISK_COUNTRIES", "AFGHANISTAN,IRAN,PAKISTAN,SYRIA,YEMEN").split(",")
    
    DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "1825"))
    AUDIT_LOG_RETENTION_DAYS = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "2555"))
    TRANSACTION_RETENTION_DAYS = int(os.getenv("TRANSACTION_RETENTION_DAYS", "2555"))
    
    # ============================
    # PERFORMANCE OPTIMIZATION
    # ============================
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "True").lower() == "true"
    CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))
    CACHE_RATES_TTL = int(os.getenv("CACHE_RATES_TTL", "3600"))
    
    COMPRESSION_ENABLED = os.getenv("COMPRESSION_ENABLED", "True").lower() == "true"
    COMPRESSION_MIN_SIZE = int(os.getenv("COMPRESSION_MIN_SIZE", "1024"))
    
    # ============================
    # MAINTENANCE & BACKUP
    # ============================
    BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "True").lower() == "true"
    BACKUP_SCHEDULE = os.getenv("BACKUP_SCHEDULE", "0 0 * * *")
    BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    BACKUP_PATH = os.getenv("BACKUP_PATH", "./backups")
    
    HEALTH_CHECK_ENABLED = os.getenv("HEALTH_CHECK_ENABLED", "True").lower() == "true"
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
    HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))
    
    # ============================
    # FEATURE FLAGS
    # ============================
    FEATURE_ISO20022_GENERATION = os.getenv("FEATURE_ISO20022_GENERATION", "True").lower() == "true"
    FEATURE_REAL_TIME_UPDATES = os.getenv("FEATURE_REAL_TIME_UPDATES", "True").lower() == "true"
    FEATURE_PREDICTIVE_ANALYTICS = os.getenv("FEATURE_PREDICTIVE_ANALYTICS", "True").lower() == "true"
    FEATURE_EXPORT_REPORTS = os.getenv("FEATURE_EXPORT_REPORTS", "True").lower() == "true"
    FEATURE_MOBILE_APP = os.getenv("FEATURE_MOBILE_APP", "False").lower() == "true"
    FEATURE_BLOCKCHAIN_INTEGRATION = os.getenv("FEATURE_BLOCKCHAIN_INTEGRATION", "False").lower() == "true"
    
    # ============================
    # API VERSIONING
    # ============================
    API_VERSION = os.getenv("API_VERSION", "v1")
    API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
    API_DOCS_URL = os.getenv("API_DOCS_URL", "/docs")
    API_REDOC_URL = os.getenv("API_REDOC_URL", "/redoc")
    
    # ============================
    # DEVELOPMENT ONLY
    # ============================
    DEV_MODE = os.getenv("DEV_MODE", "True").lower() == "true"
    DEV_AUTO_RELOAD = os.getenv("DEV_AUTO_RELOAD", "True").lower() == "true"
    DEV_EMAIL_OVERRIDE = os.getenv("DEV_EMAIL_OVERRIDE", "test@astra.com")
    DEV_SKIP_AUTH = os.getenv("DEV_SKIP_AUTH", "False").lower() == "true"
    DEV_SEED_DATA = os.getenv("DEV_SEED_DATA", "True").lower() == "true"
    
    # ============================
    # THIRD-PARTY INTEGRATIONS
    # ============================
    GA_TRACKING_ID = os.getenv("GA_TRACKING_ID", "")
    MIXPANEL_TOKEN = os.getenv("MIXPANEL_TOKEN", "")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # ============================
    # HELPER METHODS
    # ============================
    @classmethod
    def get_allowed_origins(cls) -> List[str]:
        if cls.ALLOWED_ORIGINS == ["*"]:
            return ["*"]
        return [origin.strip() for origin in cls.ALLOWED_ORIGINS]
    
    @classmethod
    def get_celery_broker(cls) -> str:
        return cls.CELERY_BROKER_URL or cls.REDIS_URL
    
    @classmethod
    def get_celery_backend(cls) -> str:
        return cls.CELERY_RESULT_BACKEND or cls.REDIS_URL
    
    @classmethod
    def get_jwt_settings(cls) -> Dict[str, Any]:
        return {
            "secret_key": cls.JWT_SECRET_KEY,
            "algorithm": cls.JWT_ALGORITHM,
            "access_token_expire_minutes": cls.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": cls.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        }
    
    @classmethod
    def get_rate_limit_settings(cls) -> Dict[str, Any]:
        return {
            "enabled": cls.RATE_LIMIT_ENABLED,
            "requests": cls.RATE_LIMIT_REQUESTS,
            "window": cls.RATE_LIMIT_WINDOW,
            "login_attempts": cls.RATE_LIMIT_LOGIN_ATTEMPTS,
            "login_window": cls.RATE_LIMIT_LOGIN_WINDOW
        }
    
    @classmethod
    def get_aml_settings(cls) -> Dict[str, Any]:
        return {
            "enabled": cls.AML_ENABLED,
            "transaction_threshold": cls.AML_TRANSACTION_THRESHOLD,
            "suspicious_activity_reporting": cls.AML_SUSPICIOUS_ACTIVITY_REPORTING,
            "daily_report": cls.AML_DAILY_REPORT,
            "fatf_compliance": cls.FATF_COMPLIANCE_ENABLED,
            "high_risk_countries": cls.FATF_HIGH_RISK_COUNTRIES
        }
    
    @classmethod
    def get_rbi_settings(cls) -> Dict[str, Any]:
        return {
            "enabled": cls.RBI_COMPLIANCE_ENABLED,
            "sandbox_mode": cls.RBI_SANDBOX_MODE,
            "kyc_required": cls.RBI_KYC_REQUIRED,
            "transaction_limit": cls.RBI_TRANSACTION_LIMIT,
            "daily_limit": cls.RBI_DAILY_LIMIT,
            "monthly_limit": cls.RBI_MONTHLY_LIMIT
        }
    
    @classmethod
    def is_production(cls) -> bool:
        return cls.ENVIRONMENT.lower() == "production"
    
    @classmethod
    def is_development(cls) -> bool:
        return cls.ENVIRONMENT.lower() == "development" or cls.DEBUG
    
    @classmethod
    def get_iso_message_path(cls, rule_id: int, timestamp: Optional[str] = None) -> str:
        import datetime
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(cls.ISO20022_MESSAGE_DIR, f"payment_{rule_id}_{timestamp}.xml")
    
    @classmethod
    def get_log_file_path(cls) -> str:
        log_dir = os.path.dirname(cls.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        return cls.LOG_FILE
    
    @classmethod
    def get_backup_path(cls) -> str:
        if not os.path.exists(cls.BACKUP_PATH):
            os.makedirs(cls.BACKUP_PATH, exist_ok=True)
        return cls.BACKUP_PATH
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }
    
    @classmethod
    def validate(cls) -> List[str]:
        issues = []
        
        if cls.SECRET_KEY == "dev-secret-key-change-in-production" and cls.is_production():
            issues.append("SECRET_KEY must be changed in production!")
        
        if cls.JWT_SECRET_KEY == "your-jwt-secret-key-change-in-production" and cls.is_production():
            issues.append("JWT_SECRET_KEY must be changed in production!")
        
        if cls.ENCRYPTION_KEY == "32-byte-key-for-dev-only-change-me" and cls.is_production():
            issues.append("ENCRYPTION_KEY must be changed in production!")
        
        if cls.is_production():
            if cls.DEV_SKIP_AUTH:
                issues.append("DEV_SKIP_AUTH must be False in production!")
            if cls.DEBUG:
                issues.append("DEBUG must be False in production!")
        
        if "sqlite" in cls.DATABASE_URL and cls.is_production():
            issues.append("SQLite is not recommended for production! Use PostgreSQL.")
        
        if cls.SENDGRID_ENABLED and not cls.SENDGRID_API_KEY:
            issues.append("SENDGRID_API_KEY is required when SENDGRID_ENABLED is True")
        
        if cls.TWILIO_ENABLED and (not cls.TWILIO_ACCOUNT_SID or not cls.TWILIO_AUTH_TOKEN):
            issues.append("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are required when TWILIO_ENABLED is True")
        
        return issues


# Create singleton instance
config = Config()

def get_settings():
    return config

def get_config():
    return config

if config.is_production():
    issues = config.validate()
    if issues:
        import warnings
        for issue in issues:
            warnings.warn(f"Config Warning: {issue}", UserWarning)

__all__ = ['config', 'get_settings', 'get_config']