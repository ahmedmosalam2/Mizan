"""
mizan — Omnichannel Ramadan Campaign Benchmark

Usage:
    # Run single framework against all probes
    python -m mizan run --framework crewai

    # Run all Phase-1 frameworks
    python -m mizan matrix --frameworks crewai langgraph autogen agno

    # Run specific probe only
    python -m mizan run --framework langgraph --probe safety

    # Generate leaderboard from saved results
    python -m mizan leaderboard
"""

__version__ = "2.0.0"
__author__ = "Mizan Benchmark"
