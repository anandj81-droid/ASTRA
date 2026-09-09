# init_db.py
from database import init_db, get_db
from models import User, Currency, CurrencyPair
from currency_service import CurrencyService
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simple_hash(password: str) -> str:
    """Simple SHA256 hash for POC"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_test_user(db):
    """Create test user if it doesn't exist"""
    try:
        # Check if test user exists
        user = db.query(User).filter(User.email == "test@astra.com").first()
        if not user:
            user = User(
                email="test@astra.com",
                full_name="Test User",
                hashed_password=simple_hash("Test@123"),
                is_active=True,
                is_admin=True
            )
            db.add(user)
            db.commit()
            logger.info("✅ Created test user: test@astra.com / Test@123")
        else:
            logger.info("✅ Test user already exists")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create test user: {e}")
        return False

def create_missing_currencies(db):
    """Create missing currencies"""
    service = CurrencyService(db)
    
    # List of all currencies we want
    all_currencies = {
        "USD": {"name": "US Dollar", "symbol": "$", "flag": "🇺🇸", "is_base": True},
        "EUR": {"name": "Euro", "symbol": "€", "flag": "🇪🇺", "is_base": False},
        "GBP": {"name": "British Pound", "symbol": "£", "flag": "🇬🇧", "is_base": False},
        "JPY": {"name": "Japanese Yen", "symbol": "¥", "flag": "🇯🇵", "is_base": False},
        "INR": {"name": "Indian Rupee", "symbol": "₹", "flag": "🇮🇳", "is_base": False},
        "SGD": {"name": "Singapore Dollar", "symbol": "S$", "flag": "🇸🇬", "is_base": False},
        "AED": {"name": "UAE Dirham", "symbol": "د.إ", "flag": "🇦🇪", "is_base": False},
        "SAR": {"name": "Saudi Riyal", "symbol": "﷼", "flag": "🇸🇦", "is_base": False},
        "AUD": {"name": "Australian Dollar", "symbol": "A$", "flag": "🇦🇺", "is_base": False},
        "CHF": {"name": "Swiss Franc", "symbol": "Fr", "flag": "🇨🇭", "is_base": False},
        "CAD": {"name": "Canadian Dollar", "symbol": "C$", "flag": "🇨🇦", "is_base": False},
        "MYR": {"name": "Malaysian Ringgit", "symbol": "RM", "flag": "🇲🇾", "is_base": False},
        "BRL": {"name": "Brazilian Real", "symbol": "R$", "flag": "🇧🇷", "is_base": False},
    }
    
    created = 0
    for code, data in all_currencies.items():
        try:
            # Check if currency exists
            existing = db.query(Currency).filter(Currency.code == code).first()
            if not existing:
                service.create_currency(
                    code=code,
                    name=data["name"],
                    symbol=data["symbol"],
                    flag=data["flag"],
                    is_base=data["is_base"]
                )
                logger.info(f"✅ Created missing currency: {code}")
                created += 1
        except Exception as e:
            logger.warning(f"⚠️ Could not create {code}: {e}")
    
    if created == 0:
        logger.info("✅ All currencies already exist")
    else:
        logger.info(f"✅ Created {created} missing currencies")
    
    return True

def create_missing_pairs(db):
    """Create missing currency pairs"""
    service = CurrencyService(db)
    
    # Get all active currencies
    currencies = db.query(Currency).filter(Currency.is_active == True).all()
    currency_codes = [c.code for c in currencies]
    
    logger.info(f"📊 Found {len(currency_codes)} currencies: {', '.join(currency_codes)}")
    
    # Check if USD exists (needed for pairs)
    if "USD" not in currency_codes:
        logger.error("❌ USD not found! Please add USD as base currency first.")
        return False
    
    # Define pairs to create
    pairs_to_create = [
        # USD pairs
        ("USD", "EUR"),
        ("USD", "GBP"),
        ("USD", "JPY"),
        ("USD", "INR"),
        ("USD", "SGD"),
        ("USD", "AED"),
        ("USD", "SAR"),
        ("USD", "AUD"),
        ("USD", "CHF"),
        ("USD", "CAD"),
        ("USD", "MYR"),
        ("USD", "BRL"),
        # Cross pairs
        ("EUR", "USD"),
        ("EUR", "GBP"),
        ("GBP", "USD"),
        ("GBP", "EUR"),
        ("JPY", "USD"),
        ("INR", "USD"),
    ]
    
    created = 0
    skipped = 0
    
    for base, quote in pairs_to_create:
        # Check if both currencies exist
        if base not in currency_codes or quote not in currency_codes:
            logger.debug(f"⚠️ Skipping {base}/{quote} - missing currency")
            skipped += 1
            continue
        
        try:
            # Check if pair already exists
            existing = db.query(CurrencyPair).join(
                Currency, Currency.id == CurrencyPair.base_currency_id
            ).filter(
                Currency.code == base
            ).first()
            
            if existing:
                logger.debug(f"⏭️ Pair {base}/{quote} already exists")
                skipped += 1
                continue
            
            # Create the pair
            service.create_pair(base, quote)
            logger.info(f"✅ Created pair: {base}/{quote}")
            created += 1
        except Exception as e:
            logger.warning(f"⚠️ Could not create pair {base}/{quote}: {e}")
            skipped += 1
    
    logger.info(f"✅ Created {created} new pairs, {skipped} existing/skipped")
    return True

def init_database():
    """Initialize database with tables, test user, currencies, and pairs"""
    logger.info("🚀 Initializing database...")
    
    # Create tables
    init_db()
    
    # Get database session
    db = next(get_db())
    
    try:
        # 1. Create test user
        create_test_user(db)
        
        # 2. Create missing currencies
        create_missing_currencies(db)
        
        # 3. Create missing pairs
        create_missing_pairs(db)
        
        # Commit any pending changes
        db.commit()
        logger.info("✅ Database initialization complete!")
        
        # Show summary
        currency_count = db.query(Currency).count()
        pair_count = db.query(CurrencyPair).count()
        logger.info(f"📊 Summary: {currency_count} currencies, {pair_count} currency pairs")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()