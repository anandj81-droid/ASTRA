"""
Astra Platform - Module Registry
"""
from typing import Dict, List, Optional, Type
import logging

from modules.module_base import AstraModule

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """Singleton registry for all Astra modules."""

    _instance: Optional["ModuleRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._modules: Dict[str, AstraModule] = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, module: AstraModule) -> None:
        if module.name in self._modules:
            logger.warning(f"⚠️  Module '{module.name}' already registered, overwriting")
        self._modules[module.name] = module
        logger.info(f"📝 Registered module: {module.name} (v{module.version})")

    def register_class(self, cls, enabled: bool = True):
        if not enabled:
            return
        instance = cls()
        if instance.name in self._modules:      # ⬅️ ADD
            return                              #    skip duplicate
        self._modules[instance.name] = instance
        logger.info(f"📝 Registered module: {instance.name} (v{instance.version})")
    
    def get(self, name: str) -> Optional[AstraModule]:
        return self._modules.get(name)

    def all(self) -> Dict[str, AstraModule]:
        return self._modules.copy()

    def enabled_modules(self) -> List[AstraModule]:
        return [m for m in self._modules.values() if m.enabled]

    def get_dependency_order(self) -> List[str]:
        visited: Dict[str, bool] = {}
        result: List[str] = []

        def visit(name: str) -> None:
            if name in visited:
                if visited[name]:
                    return
                raise RuntimeError(f"Circular dependency detected at module '{name}'")
            visited[name] = False
            module = self._modules.get(name)
            if not module:
                raise RuntimeError(f"Dependency '{name}' is not registered")
            for dep in module.dependencies:
                visit(dep)
            visited[name] = True
            result.append(name)

        for name in self._modules:
            visit(name)

        return result

    def initialize_all(self, app):
        ordered = self.get_dependency_order()
        logger.info(f"🔧 Initializing {len(ordered)} module(s) in order: {ordered}")
        for name in ordered:
            module = self._modules.get(name)
            if module is None:
                logger.warning(f"Module '{name}' not found during initialization; skipping")
                continue
            module.initialize(app)
        logger.info("✅ All modules initialized")

    def shutdown_all(self) -> None:
        for name in reversed(self.get_dependency_order()):
            module = self._modules.get(name)
            if module:
                module.shutdown()
        self._initialized = False

    def get_status(self) -> Dict[str, dict]:
        return {name: module.get_health() for name, module in self._modules.items()}

    def get_metadata_all(self) -> List[dict]:
        return [m.get_metadata() for m in self._modules.values()]


registry = ModuleRegistry()