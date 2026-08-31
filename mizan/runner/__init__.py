"""Runner package for Mizan benchmark."""
from mizan.runner.run import run_framework
from mizan.runner.matrix import run_matrix

__all__ = ["run_framework", "run_matrix"]
