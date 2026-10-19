"""
Astra Platform - Module Base Class
All modules must inherit from AstraModule and implement required methods.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)


class AstraModule(ABC):
    """Base class for all Astra modules."""

    name: str = "base_module"
    version: str = "0.1.0"
    display_name: str = "Base Module"
    description: str = "Base module description"
    dependencies: List[str] = []

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._app: Optional[FastAPI] = None
        self._initialized = False

    def initialize(self, app: FastAPI) -> None:
        if not self.enabled:
            logger.info(f"⏭️  Module '{self.name}' is DISABLED, skipping")
            return
        if self._initialized:
            logger.warning(f"⚠️  Module '{self.name}' already initialized")
            return

        self._app = app
        logger.info(f"🔧 Initializing module: {self.display_name} (v{self.version})")

        try:
            self._check_dependencies()
            self.register_routes(app)
            self.on_startup()
            self._initialized = True
            logger.info(f"✅ Module '{self.name}' initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize module '{self.name}': {e}")
            raise

    def shutdown(self) -> None:
        if not self.enabled or not self._initialized:
            return
        logger.info(f"🛑 Shutting down module: {self.name}")
        self.on_shutdown()
        self._initialized = False

    @abstractmethod
    def register_routes(self, app: FastAPI) -> None:
        raise NotImplementedError

    def on_startup(self) -> None:
        pass

    def on_shutdown(self) -> None:
        pass

    def get_health(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "initialized": self._initialized,
            "status": "healthy" if self._initialized else "inactive",
        }

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "dependencies": self.dependencies,
            "enabled": self.enabled,
            "initialized": self._initialized,
            "api_prefix": self.get_api_prefix(),
        }

    def get_api_prefix(self) -> str:
        return f"/api/v1/{self.name}"

    def _check_dependencies(self) -> None:
        from modules.module_registry import registry
        for dep in self.dependencies:
            dep_module = registry.get(dep)
            if not dep_module:
                raise RuntimeError(
                    f"Module '{self.name}' requires '{dep}' but it's not registered"
                )
            if not dep_module.enabled:
                raise RuntimeError(
                    f"Module '{self.name}' requires '{dep}' but it's disabled"
                )