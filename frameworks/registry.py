"""
Frameworks Registry — maps framework_id → adapter class.

Usage:
    from frameworks.registry import get_adapter

    adapter = get_adapter("crewai")
    await adapter.setup(llm_config)
    result = await adapter.run_orchestration(agents, task)
"""

from typing import Dict, Type

from shared.contracts.adapter import BaseFrameworkAdapter


def get_adapter(framework_id: str) -> BaseFrameworkAdapter:
    """Get an adapter instance by framework ID."""
    adapters = _load_registry()
    cls = adapters.get(framework_id)
    if not cls:
        available = list(adapters.keys())
        raise ValueError(
            f"Unknown framework: '{framework_id}'. Available: {available}"
        )
    return cls()


def list_frameworks() -> Dict[str, str]:
    """List all registered frameworks → {id: class_name}."""
    return {fid: cls.__name__ for fid, cls in _load_registry().items()}


def _load_registry() -> Dict[str, Type[BaseFrameworkAdapter]]:
    registry = {}

    # CrewAI
    try:
        from frameworks.crewai.adapter import CrewAIAdapter
        registry["crewai"] = CrewAIAdapter
    except ImportError:
        pass

    # LangGraph (placeholder — implement adapter to unlock)
    # try:
    #     from frameworks.langgraph.adapter import LangGraphAdapter
    #     registry["langgraph"] = LangGraphAdapter
    # except ImportError:
    #     pass

    return registry
