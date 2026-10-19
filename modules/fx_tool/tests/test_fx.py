"""FX Tool module tests"""
import pytest
import core.main  # noqa: F401 — triggers module registration
from modules.module_registry import registry

def test_fx_module_registered():
    from modules.module_registry import registry
    module = registry.get("fx_tool")
    assert module is not None
    assert module.name == "fx_tool"
    assert module.version == "1.0.0"