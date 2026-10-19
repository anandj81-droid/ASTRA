from modules.module_base import AstraModule
from .routes import router


class LastMileModule(AstraModule):
    name = "last_mile"
    version = "1.0.0"
    display_name = "Last Mile Expediter"   # ← ADD
    description = "Smart bank routing + real-time payment status tracking"
    dependencies = ["fx_tool", "cost_optimizer"]

    def get_api_prefix(self) -> str:
        return "/api/v1/lastmile"

    def register_routes(self, app):
        app.include_router(router, prefix=self.get_api_prefix(), tags=["Last Mile"])

    def on_startup(self):
       """Seed default banks on first run."""
       from .services.bank_performance import seed_default_banks
       seed_default_banks()