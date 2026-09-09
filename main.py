# main.py
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, aliased
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from database import get_db, init_db
from models import User, AgentRule, RuleStatus, Transaction, Currency, CurrencyPair, FXRate
from auth import get_current_user, authenticate_user, create_access_token, get_password_hash
from agent import AgentEngine
from fx_service import fx_service
from predictor import PredictionService
from currency_service import CurrencyService
from config import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Astra Platform",
    description="AI-Powered Autonomous Treasury for Cross-Border Payments",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ──────────────────────────────────────────────────────────────
# ROOT & UI ROUTES
# ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "Astra Platform",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "login": "/login",
        "dashboard": "/dashboard"
    }

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve login page"""
    try:
        with open("static/login.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
            <html>
                <head><title>Login</title></head>
                <body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5;">
                    <div style="background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                        <h1>🚀 Astra Platform</h1>
                        <p>Demo credentials: test@astra.com / Test@123</p>
                        <button onclick="location.href='/dashboard'" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;">
                            Go to Dashboard
                        </button>
                    </div>
                </body>
            </html>
        """)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve dashboard page"""
    try:
        with open("static/dashboard.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
            <html>
                <head><title>Dashboard</title></head>
                <body style="font-family: sans-serif; padding: 40px; background: #f0f2f5;">
                    <h1>📊 Dashboard</h1>
                    <p>Please create static/dashboard.html</p>
                    <button onclick="location.href='/login'" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;">
                        Back to Login
                    </button>
                </body>
            </html>
        """)

@app.get("/ui", response_class=HTMLResponse)
async def ui_redirect():
    """Redirect to login page"""
    return RedirectResponse(url="/login")


@app.get("/testrules", response_class=HTMLResponse)
async def test_rules_page():
    """Serve rule testing page"""
    try:
        with open("static/testrules.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
            <html>
                <head><title>Test Rules</title></head>
                <body style="font-family: sans-serif; padding: 40px; background: #f0f2f5;">
                    <h1>🧪 Rule Testing</h1>
                    <p>Please create static/testrules.html</p>
                    <button onclick="location.href='/dashboard'" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;">
                        Back to Dashboard
                    </button>
                </body>
            </html>
        """)

# ──────────────────────────────────────────────────────────────
# AUTH ROUTES
# ──────────────────────────────────────────────────────────────

from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint"""
    try:
        user = authenticate_user(db, request.email, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name
            }
        }
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )





# ──────────────────────────────────────────────────────────────
# CURRENCY ROUTES
# ──────────────────────────────────────────────────────────────

@app.get("/currencies")
async def get_currencies(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    service = CurrencyService(db)
    currencies = service.get_all_currencies()
    
    return {
        "currencies": [
            {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "symbol": c.symbol,
                "flag": c.flag,
                "is_base": c.is_base,
                "is_active": c.is_active
            }
            for c in currencies
        ]
    }

@app.post("/currencies")
async def add_currency(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a new currency - accepts JSON body"""
    try:
        data = await request.json()
        logger.info(f"Adding currency with data: {data}")
        
        code = data.get('code', '').strip().upper()
        name = data.get('name', '').strip()
        symbol = data.get('symbol', '').strip()
        flag = data.get('flag', '').strip()
        is_base = data.get('is_base', False)
        
        if not code:
            raise HTTPException(status_code=400, detail="Currency code is required")
        if not name:
            raise HTTPException(status_code=400, detail="Currency name is required")
        if not symbol:
            raise HTTPException(status_code=400, detail="Currency symbol is required")
        if len(code) != 3:
            raise HTTPException(status_code=400, detail="Currency code must be 3 characters")
        
        service = CurrencyService(db)
        currency = service.create_currency(
            code=code,
            name=name,
            symbol=symbol,
            flag=flag,
            is_base=is_base
        )
        
        return {
            "success": True,
            "currency": {
                "id": currency.id,
                "code": currency.code,
                "name": currency.name,
                "symbol": currency.symbol,
                "flag": currency.flag,
                "is_base": currency.is_base,
                "is_active": currency.is_active
            },
            "message": f"Currency {code} added successfully"
        }
    except ValueError as e:
        logger.error(f"ValueError adding currency: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding currency: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/currency-pairs")
async def get_currency_pairs(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all currency pairs"""
    try:
        service = CurrencyService(db)
        pairs = service.get_active_pairs()
        
        # If no pairs exist, create default ones
        if not pairs:
            logger.info("No pairs found, creating default pairs...")
            await create_default_pairs(db)
            pairs = service.get_active_pairs()
        
        return {"pairs": pairs}
    except Exception as e:
        logger.error(f"Error fetching currency pairs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def create_default_pairs(db: Session):
    """Create default currency pairs if none exist"""
    service = CurrencyService(db)
    
    default_pairs = [
        ("USD", "INR"),
        ("USD", "EUR"),
        ("EUR", "USD"),
        ("USD", "GBP"),
        ("USD", "JPY"),
        ("USD", "SGD"),
        ("USD", "AED"),
        ("USD", "SAR"),
        ("USD", "AUD"),
        ("USD", "CHF"),
        ("USD", "CAD"),
        ("USD", "MYR"),
        ("USD", "BRL"),
    ]
    
    for base, quote in default_pairs:
        try:
            service.create_pair(base, quote)
            logger.info(f"Created default pair: {base}/{quote}")
        except Exception as e:
            logger.warning(f"Could not create pair {base}/{quote}: {e}")

@app.get("/fx/rate/{base}/{quote}")
async def get_rate(
    base: str,
    quote: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    rate_data = fx_service.get_rate(base.upper(), quote.upper())
    if not rate_data:
        raise HTTPException(status_code=404, detail="Rate not found")
    
    return rate_data

# ──────────────────────────────────────────────────────────────
# RULE ROUTES - UPDATED FOR YOUR DATABASE SCHEMA
# ──────────────────────────────────────────────────────────────

class RuleCreateRequest(BaseModel):
    pair_code: str
    rule_type: str
    amount: float
    target_rate: Optional[float] = None
    schedule_day: Optional[int] = None
    schedule_time: Optional[str] = None
    min_confidence: Optional[float] = 0.7
    prediction_horizon: Optional[str] = "24h"

@app.post("/rules")
async def create_rule(
    request: RuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Parse pair_code correctly
        pair_code = request.pair_code.strip()
        logger.info(f"Creating rule for pair: {pair_code}")
        
        # Handle both "USD/INR" and "USD-INR" formats
        if "/" in pair_code:
            base, quote = pair_code.split("/")
        elif "-" in pair_code:
            base, quote = pair_code.split("-")
        else:
            raise HTTPException(status_code=400, detail="Invalid pair format. Use USD/INR")
        
        base = base.strip().upper()
        quote = quote.strip().upper()
        
        logger.info(f"Looking for pair: {base}/{quote}")
        
        # Get currency IDs
        base_currency = db.query(Currency).filter(Currency.code == base).first()
        quote_currency = db.query(Currency).filter(Currency.code == quote).first()
        
        if not base_currency:
            raise HTTPException(status_code=404, detail=f"Base currency {base} not found")
        if not quote_currency:
            raise HTTPException(status_code=404, detail=f"Quote currency {quote} not found")
        
        # Find the pair
        pair = db.query(CurrencyPair).filter(
            CurrencyPair.base_currency_id == base_currency.id,
            CurrencyPair.quote_currency_id == quote_currency.id
        ).first()
        
        if not pair:
            # Try to create the pair
            logger.info(f"Pair {base}/{quote} not found, attempting to create...")
            currency_service = CurrencyService(db)
            try:
                pair = currency_service.create_pair(base, quote)
                logger.info(f"✅ Created new pair: {base}/{quote}")
            except Exception as e:
                logger.error(f"Could not create pair: {e}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Pair {base}/{quote} not found and could not be created: {str(e)}"
                )
        
        # Create the rule
        engine = AgentEngine(db)
        rule = engine.create_rule(
            user_id=current_user['id'],
            pair_id=pair.id,
            rule_type=request.rule_type,
            amount=request.amount,
            target_rate=request.target_rate,
            schedule_day=request.schedule_day,
            schedule_time=request.schedule_time,
            min_confidence=request.min_confidence,
            prediction_horizon=request.prediction_horizon
        )
        
        logger.info(f"✅ Rule created: ID={rule.id}, Pair={base}/{quote}, Type={request.rule_type}")
        
        return {
            "id": rule.id,
            "message": f"Rule created successfully for {base}/{quote}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/rules")
async def get_rules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    engine = AgentEngine(db)
    rules = engine.get_user_rules(current_user['id'])
    
    return {
        "rules": [
            {
                "id": r.id,
                "pair": f"{r.source_currency}/{r.target_currency}",  # ✅ Use source/target
                "rule_type": r.rule_type,
                "amount": float(r.amount),
                "target_rate": float(r.target_rate) if r.target_rate else None,
                "schedule_day": r.schedule_day,
                "schedule_time": r.schedule_time,
                "status": "active" if r.is_active else "inactive",  # ✅ Use is_active
                "execution_count": r.execution_count,
                "last_executed": r.last_executed,
                "created_at": r.created_at
            }
            for r in rules
        ]
    }

@app.patch("/rules/{rule_id}")
async def update_rule_status(
    rule_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    engine = AgentEngine(db)
    try:
        rule = engine.update_rule_status(rule_id, status)
        return {
            "id": rule.id,
            "status": "active" if rule.is_active else "inactive",
            "message": f"Rule updated to {status}"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    engine = AgentEngine(db)
    try:
        engine.delete_rule(rule_id)
        return {"message": f"Rule {rule_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ──────────────────────────────────────────────────────────────
# TRANSACTION ROUTES
# ──────────────────────────────────────────────────────────────

@app.get("/transactions")
async def get_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get transaction history"""
    try:
        transactions = db.query(Transaction).filter(
            Transaction.user_id == current_user['id']
        ).order_by(
            Transaction.execution_time.desc()
        ).offset(offset).limit(limit).all()
        
        total = db.query(Transaction).filter(
            Transaction.user_id == current_user['id']
        ).count()
        
        return {
            "transactions": [
                {
                    "id": t.id,
                    "rule_id": t.rule_id,
                    "from_currency": t.from_currency,
                    "to_currency": t.to_currency,
                    "from_amount": float(t.from_amount),
                    "to_amount": float(t.to_amount),
                    "rate_used": float(t.rate_used),
                    "status": t.status,
                    "execution_time": t.execution_time,
                    "bank_reference": t.bank_reference
                }
                for t in transactions
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/createrule", response_class=HTMLResponse)
async def create_rule_page():
    """Serve create rule page"""
    try:
        with open("static/createrule.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
            <html>
                <head><title>Create Rule</title></head>
                <body style="font-family: sans-serif; padding: 40px; background: #f0f2f5;">
                    <h1>➕ Create Rule</h1>
                    <p>Please create static/createrule.html</p>
                    <button onclick="location.href='/dashboard'" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer;">
                        Back to Dashboard
                    </button>
                </body>
            </html>
        """)
        
        
# Add this to main.py after the existing rule endpoints

@app.post("/rules/{rule_id}/trigger")
async def trigger_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger a rule for testing"""
    try:
        engine = AgentEngine(db)
        rule = engine.get_rule(rule_id, current_user['id'])
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # Get current rate
        rate_data = fx_service.get_rate(rule.source_currency, rule.target_currency)
        current_rate = float(rate_data['rate']) if rate_data else 85.0
        
        # Execute the rule
        from datetime import datetime
        import os
        
        # Generate ISO 20022 message
        from iso20022_messages import ISO20022MessageGenerator
        iso_gen = ISO20022MessageGenerator(
            sender_bic="ASTRAINBBXXX",
            receiver_bic="HDFCINBBXXX",
            sender_account="ASTRA123456789"
        )
        
        # 🔧 FIX: Convert amount to float explicitly
        amount = float(rule.amount) if rule.amount else 0.0
        
        transaction_data = {
            'amount': amount,
            'currency': rule.source_currency,
            'beneficiary_name': 'Test Beneficiary',
            'beneficiary_account': 'TEST123456789',
            'beneficiary_bic': 'TESTBICXXX',
            'reference': f"TEST_{rule.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'purpose': f'Test execution - Rule {rule.id}'
        }
        
        # Generate XML
        xml_message = iso_gen.generate_pain_001(transaction_data)
        
        # Save XML
        os.makedirs("iso_messages", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        xml_path = f"iso_messages/test_rule_{rule.id}_{timestamp}.xml"
        with open(xml_path, 'w') as f:
            f.write(xml_message)
        
        # Call Bank API (mock)
        from bank_integration import BankIntegration
        bank_api = BankIntegration()
        payment_response = bank_api.submit_payment(xml_message, rule.id)
        
        # 🔧 FIX: Convert all numeric values to float
        rate_used = float(current_rate)
        from_amount = float(amount)
        to_amount = float(amount * rate_used)
        
        # Create transaction record
        transaction = Transaction(
            user_id=rule.user_id,
            rule_id=rule.id,
            from_currency=rule.source_currency,
            to_currency=rule.target_currency,
            from_amount=from_amount,
            to_amount=to_amount,
            rate_used=rate_used,
            currency_pair=f"{rule.source_currency}/{rule.target_currency}",
            amount=from_amount,
            executed_rate=rate_used,
            status=payment_response.get('status', 'executed'),
            bank_reference=payment_response.get('reference'),
            iso_message_path=xml_path,
            execution_time=datetime.now()
        )
        
        db.add(transaction)
        rule.execution_count += 1
        rule.last_executed = datetime.now()
        db.commit()
        db.refresh(transaction)
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "bank_reference": payment_response.get('reference'),
            "iso_message_path": xml_path,
            "bank_api_called": True,
            "status": payment_response.get('status', 'executed'),
            "xml_preview": xml_message[:500] + "..." if len(xml_message) > 500 else xml_message,
            "message": f"Rule {rule_id} triggered successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error triggering rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ──────────────────────────────────────────────────────────────
# PREDICTION ROUTES
# ──────────────────────────────────────────────────────────────

@app.get("/predictions")
async def get_predictions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    pairs = db.query(CurrencyPair).filter(
        CurrencyPair.is_active == True
    ).all()
    
    prediction_service = PredictionService(db)
    results = []
    
    for pair in pairs:
        try:
            pred = prediction_service.predict(pair.id, "24h")
            results.append({
                "pair": f"{pair.base_currency.code}/{pair.quote_currency.code}",
                "predicted_rate": pred['rate'],
                "confidence": pred.get('confidence', 0.0),
                "model": pred.get('model_used', 'moving_average')
            })
        except Exception as e:
            logger.error(f"Prediction failed for pair {pair.id}: {e}")
    
    return {"predictions": results}

# ──────────────────────────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Astra Platform...")
    init_db()
    
    # Create default pairs on startup
    try:
        db = next(get_db())
        await create_default_pairs(db)
        db.close()
    except Exception as e:
        logger.error(f"Error creating default pairs: {e}")
    
    logger.info("Astra Platform is ready!")

# ──────────────────────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)