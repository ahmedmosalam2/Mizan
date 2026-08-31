"""
Shared conftest — Common test fixtures for all Mizan tests.
"""

import pytest
from shared.testing.mock_llm import MockLLM
from shared.testing.seeds import set_all_seeds, DEFAULT_SEED


@pytest.fixture(autouse=True)
def seed_everything():
    """Ensure all tests run with deterministic seeds."""
    set_all_seeds(DEFAULT_SEED)


@pytest.fixture
def mock_llm():
    """Provide a fresh MockLLM instance."""
    return MockLLM(seed=DEFAULT_SEED)
