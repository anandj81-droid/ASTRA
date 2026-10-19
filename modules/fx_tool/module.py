"""FX Tool Module Definition"""
from fastapi import FastAPI

from modules.module_base import AstraModule
from modules.fx_tool.routes import router as fx_router


class FxToolModule(AstraModule):
    name = "fx_tool"
    version = "1.0.0"
    display_name = "FX Tool"
    description = "AI-powered FX rate prediction, rule engine, and automated trading"
    dependencies = []

    def register_routes(self, app: FastAPI) -> None:
        app.include_router(fx_router, prefix="/api/v1/fx", tags=["FX Tool"])
    
    def get_api_prefix(self) -> str:
        return "/api/v1/fx"
    