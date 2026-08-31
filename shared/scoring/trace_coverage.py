"""
Trace Coverage — Measures what % of workflow steps are visible in tracing.

A framework scores 100% if every agent action, tool call, and state change
appears in the execution trace. This rewards frameworks with built-in
observability over black-box ones.
"""

from typing import Any, Dict, List, Set

from shared.contracts.adapter import TraceEntry


def compute_trace_coverage(
    trace: List[TraceEntry],
    expected_agents: List[str],
    expected_actions: List[str],
) -> Dict[str, Any]:
    """
    Compute trace coverage metrics.

    Args:
        trace: The execution trace entries
        expected_agents: Agent names that should appear
        expected_actions: Action types that should appear

    Returns:
        Coverage metrics dict
    """
    traced_agents: Set[str] = set()
    traced_actions: Set[str] = set()
    has_timing = 0
    has_tokens = 0

    for entry in trace:
        if entry.agent_name:
            traced_agents.add(entry.agent_name)
        if entry.action:
            traced_actions.add(entry.action)
        if entry.duration_ms > 0:
            has_timing += 1
        if entry.tokens and entry.tokens.total_tokens > 0:
            has_tokens += 1

    expected_agents_set = set(expected_agents)
    expected_actions_set = set(expected_actions)

    agent_coverage = (
        len(traced_agents & expected_agents_set) / len(expected_agents_set)
        if expected_agents_set
        else 0.0
    )
    action_coverage = (
        len(traced_actions & expected_actions_set) / len(expected_actions_set)
        if expected_actions_set
        else 0.0
    )
    timing_coverage = has_timing / len(trace) if trace else 0.0
    token_coverage = has_tokens / len(trace) if trace else 0.0

    return {
        "agent_coverage": agent_coverage,
        "action_coverage": action_coverage,
        "timing_coverage": timing_coverage,
        "token_coverage": token_coverage,
        "overall_coverage": (
            agent_coverage * 0.3
            + action_coverage * 0.3
            + timing_coverage * 0.2
            + token_coverage * 0.2
        ),
        "total_trace_entries": len(trace),
        "traced_agents": list(traced_agents),
        "missing_agents": list(expected_agents_set - traced_agents),
        "missing_actions": list(expected_actions_set - traced_actions),
    }
