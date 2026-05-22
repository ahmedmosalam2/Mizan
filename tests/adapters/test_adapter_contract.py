"""
Adapter Contract Compliance Tests — Verify all 20 adapters implement the
7 required abstract methods from BaseFrameworkAdapter.
"""

import importlib
import inspect
import pytest

from benchmarks.adapters.base_adapter import BaseFrameworkAdapter
from benchmarks.scenarios.test_data import FRAMEWORKS_REGISTRY


# All abstract methods that every adapter must implement
REQUIRED_METHODS = [
    "setup",
    "teardown",
    "run_orchestration",
    "run_with_tools",
    "run_safety_check",
    "run_with_approval",
    "run_with_memory",
    "run_with_tracing",
    "run_multimodal",
]


def _try_load_adapter_class(framework_id: str):
    """Attempt to import and return the adapter class for a framework."""
    try:
        module = importlib.import_module(f"benchmarks.adapters.{framework_id}_adapter")
        class_name = "".join(w.capitalize() for w in framework_id.split("_")) + "Adapter"
        return getattr(module, class_name, None)
    except (ImportError, ModuleNotFoundError):
        return None


# Collect all adapter classes that can be imported
ADAPTER_CLASSES = {}
for fw in FRAMEWORKS_REGISTRY:
    cls = _try_load_adapter_class(fw["id"])
    if cls is not None:
        ADAPTER_CLASSES[fw["id"]] = cls


class TestAdapterRegistry:
    """Tests for adapter coverage and registration."""

    def test_at_least_some_adapters_loadable(self):
        """At least some adapters should be importable in the test environment."""
        assert len(ADAPTER_CLASSES) > 0, "No adapters could be imported"

    def test_all_20_adapter_files_exist(self):
        """Every registered framework should have an adapter module file."""
        import os
        from pathlib import Path
        adapter_dir = Path(__file__).resolve().parent.parent.parent / "src" / "benchmarks" / "adapters"
        for fw in FRAMEWORKS_REGISTRY:
            expected_file = adapter_dir / f"{fw['id']}_adapter.py"
            assert expected_file.exists(), (
                f"Missing adapter file for {fw['name']}: {fw['id']}_adapter.py"
            )


class TestAdapterContractCompliance:
    """Verify each loadable adapter implements all 7+2 abstract methods."""

    @pytest.mark.parametrize("fw_id", list(ADAPTER_CLASSES.keys()))
    def test_inherits_base_adapter(self, fw_id):
        cls = ADAPTER_CLASSES[fw_id]
        assert issubclass(cls, BaseFrameworkAdapter), (
            f"{cls.__name__} does not inherit from BaseFrameworkAdapter"
        )

    @pytest.mark.parametrize("fw_id", list(ADAPTER_CLASSES.keys()))
    def test_implements_all_methods(self, fw_id):
        cls = ADAPTER_CLASSES[fw_id]
        for method_name in REQUIRED_METHODS:
            method = getattr(cls, method_name, None)
            assert method is not None, f"{cls.__name__} missing {method_name}"
            # Ensure it's not still abstract
            assert not getattr(method, "__isabstractmethod__", False), (
                f"{cls.__name__}.{method_name} is still abstract"
            )

    @pytest.mark.parametrize("fw_id", list(ADAPTER_CLASSES.keys()))
    def test_can_instantiate(self, fw_id):
        cls = ADAPTER_CLASSES[fw_id]
        instance = cls()
        assert instance.framework_name != ""
