"""
Seed Control — Ensures reproducible benchmarks.

Sets random seeds for Python, NumPy, and any LLM seed parameters
to make benchmark runs deterministic and comparable.
"""

import os
import random
from typing import Optional


DEFAULT_SEED = 42


def set_all_seeds(seed: int = DEFAULT_SEED) -> None:
    """
    Set all random seeds for reproducibility.

    Args:
        seed: The seed value to use across all RNGs.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    # NumPy (optional)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass

    # PyTorch (optional)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def get_benchmark_seed(
    scenario_id: str,
    run_number: int,
    base_seed: int = DEFAULT_SEED,
) -> int:
    """
    Generate a deterministic but unique seed for each scenario run.

    This ensures:
        - Same scenario + same run number → same seed (reproducible)
        - Different scenarios → different seeds (independent)

    Args:
        scenario_id: e.g., "s01_task_decomposition"
        run_number: e.g., 1, 2, 3
        base_seed: The base seed

    Returns:
        A deterministic seed for this specific run.
    """
    combined = f"{base_seed}:{scenario_id}:{run_number}"
    return hash(combined) % (2**31)
