import logging
from modules.module_base import AstraModule

logger = logging.getLogger(__name__)


class ReconciliationModule(AstraModule):
    name = "reconciliation"
    version = "1.0.0"
    display_name = "Reconciliation"
    description = "Statement reconciliation, matching, and discrepancy reporting"
    dependencies = []  # soft/optional dependency on fx_tool via import-from-fx endpoint

    def get_api_prefix(self) -> str:
        return "/api/v1/reconciliation"

    def register_routes(self, app):
        from modules.reconciliation.routes import router
        app.include_router(router, prefix=self.get_api_prefix(), tags=["reconciliation"])

    def on_startup(self):
        # Seed nothing by default; ledger is populated via import endpoints.
        logger.info("✅ Reconciliation module ready (ledger import + statement matching)")