# core/main.py
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import os

from core.database import get_db, init_db, SessionLocal
from core.models import User, AgentRule, RuleStatus, Transaction, Currency, CurrencyPair, FXRate
from core.auth import get_current_user, authenticate_user, create_access_token, get_password_hash
from core.fx_service import fx_service
from core.currency_service import CurrencyService
from core.config import config

# Module system
from modules.module_registry import registry
from modules.module_base import AstraModule

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# CREATE APP
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="Astra Platform",
    description="AI-Powered Autonomous Treasury for Cross-Border Payments",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/module-data", StaticFiles(directory="modules"), name="module_data")


# ═══════════════════════════════════════════════════════════
# MODULE REGISTRATION
# ═══════════════════════════════════════════════════════════

def register_all_modules() -> None:
    """Register all available modules (enabled/disabled per config flags)."""
    from modules.fx_tool.module import FxToolModule
    
    # FX Tool (Phase 4.1 — enabled by default)
    registry.register_class(FxToolModule, enabled=config.MODULE_FX_TOOL)
    
    # ⏭️ Future modules — register here as you build them:
    from modules.cost_optimizer.module import CostOptimizerModule
    registry.register_class(CostOptimizerModule, enabled=config.MODULE_COST_OPTIMIZER)
    #
    from modules.last_mile.module import LastMileModule
    registry.register_class(LastMileModule, enabled=config.MODULE_LAST_MILE)
    #
    # from modules.compliance.module import ComplianceModule
    # registry.register_class(ComplianceModule, enabled=config.MODULE_COMPLIANCE)
    #
    from modules.reconciliation.module import ReconciliationModule
    registry.register_class(ReconciliationModule, enabled=config.MODULE_RECONCILIATION)

register_all_modules()

# ═══════════════════════════════════════════════════════════
# ROOT & UI ROUTES
# ═══════════════════════════════════════════════════════════

@app.get("/testfx", include_in_schema=False)
async def testfx_alias():
    return RedirectResponse(url="/testrules")

@app.get("/testcost", include_in_schema=False)
async def testcost_alias():
    return RedirectResponse(url="/api/v1/cost/test")

@app.get("/")
async def root():
    return {
        "name": "Astra Platform",
        "version": "4.0.0",
        "status": "running",
        "docs": "/docs",
        "login": "/login",
        "dashboard": "/dashboard",
        "modules": "/modules"
    }


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    try:
        with open("static/login.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Login page not found</h1>")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    try:
        # Try module dashboard first, fall back to shared
        paths = [
            "modules/fx_tool/static/fx_dashboard.html",
            "static/dashboard.html",
        ]
        for p in paths:
            if os.path.exists(p):
                with open(p, "r") as f:
                    return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>Dashboard not found</h1>")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>")


@app.get("/ui", response_class=HTMLResponse)
async def ui_redirect():
    return RedirectResponse(url="/login")


@app.get("/testrules", response_class=HTMLResponse)
async def test_rules_page():
    try:
        paths = [
            "modules/fx_tool/static/test_fx.html"
                ]
        for p in paths:
            if os.path.exists(p):
                with open(p, "r") as f:
                    return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>Test rules page not found</h1>")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>")


@app.get("/createrule", response_class=HTMLResponse)
async def create_rule_page():
    try:
        paths = [
            "modules/fx_tool/static/createrule.html"
        ]
        for p in paths:
            if os.path.exists(p):
                with open(p, "r") as f:
                    return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>Create rule page not found</h1>")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>")


# ═══════════════════════════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════════════════════════

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


# ═══════════════════════════════════════════════════════════
# CORE CURRENCY ROUTES (shared by all modules)
# ═══════════════════════════════════════════════════════════



@app.get("/lastmile", response_class=HTMLResponse, include_in_schema=False)
async def lastmile_dashboard_page():
    try:
        paths = [
            "modules/last_mile/static/lastmile_dashboard.html",
        ]
        for p in paths:
            if os.path.exists(p):
                with open(p, "r") as f:
                    return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>Last Mile dashboard not found</h1>")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {e}</h1>")


@app.get("/testlastmile", response_class=HTMLResponse, include_in_schema=False)
async def test_lastmile_page():
    import os
    for p in ("modules/last_mile/static/test_lastmile.html",):
        if os.path.exists(p):
            with open(p, "r") as f:
                return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Last Mile test page not found</h1>")

@app.get("/testdashboard", response_class=HTMLResponse, include_in_schema=False)
async def test_dashboard_page():
    from fastapi.responses import FileResponse
    return FileResponse("static/test_dashboard.html")

@app.get("/testreconciliation", response_class=HTMLResponse)
async def test_reconciliation_page():
    from fastapi.responses import FileResponse
    return FileResponse("modules/reconciliation/static/test_reconciliation.html")

@app.get("/reconciliation", response_class=HTMLResponse)
async def reconciliation_dashboard_page():
    from fastapi.responses import FileResponse
    return FileResponse("modules/reconciliation/static/reconciliation_dashboard.html")

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
                "id": c.id, "code": c.code, "name": c.name, "symbol": c.symbol,
                "flag": c.flag, "is_base": c.is_base, "is_active": c.is_active
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
    try:
        data = await request.json()
        code = data.get('code', '').strip().upper()
        name = data.get('name', '').strip()
        symbol = data.get('symbol', '').strip()
        flag = data.get('flag', '').strip()
        is_base = data.get('is_base', False)
        
        if not code or len(code) != 3:
            raise HTTPException(status_code=400, detail="Currency code must be 3 characters")
        if not name:
            raise HTTPException(status_code=400, detail="Currency name is required")
        if not symbol:
            raise HTTPException(status_code=400, detail="Currency symbol is required")
        
        service = CurrencyService(db)
        currency = service.create_currency(code=code, name=name, symbol=symbol, flag=flag, is_base=is_base)
        
        return {
            "success": True,
            "currency": {
                "id": currency.id, "code": currency.code, "name": currency.name,
                "symbol": currency.symbol, "flag": currency.flag,
                "is_base": currency.is_base, "is_active": currency.is_active
            },
            "message": f"Currency {code} added successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding currency: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ═══════════════════════════════════════════════════════════
# HEALTH & MODULE INFO
# ═══════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "4.0.0",
        "modules": len(registry.all()),
        "enabled_modules": len(registry.enabled_modules()),
    }


@app.get("/modules")
async def list_modules():
    """List all registered modules and their status."""
    return {
        "modules": registry.get_metadata_all(),
        "count": len(registry.all()),
        "enabled_count": len(registry.enabled_modules()),
    }


@app.get("/modules/{module_name}")
async def get_module_info(module_name: str):
    """Get info about a specific module."""
    module = registry.get(module_name)
    if not module:
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")
    return module.get_metadata()


# ═══════════════════════════════════════════════════════════
# STARTUP / SHUTDOWN
# ═══════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting Astra Platform...")
    
    # 1. Initialize DB
    init_db()
    
    # 2. Register modules
    register_all_modules()
    
    # 3. Initialize all enabled modules (this registers their routes)
    registry.initialize_all(app)
    
    # 4. Seed default currency pairs
    try:
        db = SessionLocal()
        from modules.fx_tool.routes import _create_default_pairs
        await _create_default_pairs(db)
        db.close()
    except Exception as e:
        logger.error(f"Error creating default pairs: {e}")
    
    logger.info("✅ Astra Platform is ready!")
    logger.info(f"📦 Modules: {[m.name for m in registry.enabled_modules()]}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Shutting down Astra Platform...")
    registry.shutdown_all()
    logger.info("✅ Shutdown complete")


# ═══════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)