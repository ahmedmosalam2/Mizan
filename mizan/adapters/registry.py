"""
Adapter Registry for Mizan Framework Benchmark.
"""

from __future__ import annotations
from typing import Dict, Type, List
from mizan.adapters.base import BaseAdapter


_ADAPTERS: Dict[str, Type[BaseAdapter]] = {}


def register_adapter(name: str):
    """Decorator to register a framework adapter."""
    def decorator(cls: Type[BaseAdapter]):
        _ADAPTERS[name.lower()] = cls
        cls.framework_name = name.lower()
        return cls
    return decorator


def get_adapter(name: str) -> BaseAdapter:
    """Retrieve and instantiate a framework adapter by name."""
    name_norm = name.lower().strip()
    if name_norm not in _ADAPTERS:
        # Attempt dynamic import
        try:
            if name_norm == "native":
                import mizan.adapters.native.adapter
            elif name_norm == "crewai":
                import mizan.adapters.crewai.adapter
            elif name_norm == "langgraph":
                import mizan.adapters.langgraph.adapter
            elif name_norm == "autogen":
                import mizan.adapters.autogen.adapter
            elif name_norm == "agno":
                import mizan.adapters.agno.adapter
        except ImportError as e:
            raise ImportError(f"Failed to import adapter for framework '{name}': {e}")

    if name_norm not in _ADAPTERS:
        available = list(_ADAPTERS.keys())
        raise ValueError(f"Unknown framework '{name}'. Available registered adapters: {available}")

    return _ADAPTERS[name_norm]()


def list_available_frameworks() -> List[str]:
    """List all registered framework adapter names."""
    # Ensure standard ones are imported
    for mod in ["native", "crewai", "langgraph", "autogen", "agno"]:
        try:
            if mod == "native":
                import mizan.adapters.native.adapter
            elif mod == "crewai":
                import mizan.adapters.crewai.adapter
            elif mod == "langgraph":
                import mizan.adapters.langgraph.adapter
            elif mod == "autogen":
                import mizan.adapters.autogen.adapter
            elif mod == "agno":
                import mizan.adapters.agno.adapter
        except Exception:
            pass
    return sorted(list(_ADAPTERS.keys()))
