# core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from core.config import config
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = config.DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=config.DATABASE_POOL_SIZE,
        max_overflow=config.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Session:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables (core + all module models)."""
    try:
        # ── Core models (always) ──
        from core import models  # noqa

        # ── Module models (import so tables get created) ──
        # Each module that defines its own tables must be imported here.
        # If a module is disabled, the tables just won't be created.

        try:
            from modules.fx_tool import models as fx_models  # noqa
        except Exception as e:
            logger.debug(f"fx_tool models not loaded: {e}")

        try:
            from modules.cost_optimizer import models as cost_models  # noqa
        except Exception as e:
            logger.debug(f"cost_optimizer models not loaded: {e}")

        try:
            from modules.last_mile import models as lm_models  # noqa
        except Exception as e:
            logger.debug(f"last_mile models not loaded: {e}")
        
        # try:
        #     from modules.compliance import models as compliance_models  # noqa
        # except Exception as e:
        #     logger.debug(f"compliance models not loaded: {e}")
        #
        try:
            from modules.reconciliation import models as recon_models  # noqa
        except Exception as e:
            logger.debug(f"reconciliation models not loaded: {e}")

        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False


def get_db_session() -> Session:
    """Get a database session (for background tasks)"""
    return SessionLocal()