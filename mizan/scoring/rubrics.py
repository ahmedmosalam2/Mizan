"""
Scoring Rubrics — Evaluation criteria for each of the 7 dimensions.
"""

from __future__ import annotations
from typing import Dict, Any

RUBRICS: Dict[str, Any] = {
    # Dimension 1: Agent Design & Orchestration (20%)
    "orchestration": {
        "weight": 0.20,
        "sub_criteria": {
            "multi_agent_creation": {"weight": 0.15},
            "task_decomposition": {"weight": 0.20},
            "sequential_execution": {"weight": 0.15},
            "parallel_execution": {"weight": 0.15},
            "conditional_branching": {"weight": 0.15},
            "error_recovery": {"weight": 0.10},
            "inter_agent_communication": {"weight": 0.10},
        },
    },
    # Dimension 2: Tool Use & Integrations (15%)
    "tool_use": {
        "weight": 0.15,
        "sub_criteria": {
            "function_calling": {"weight": 0.25},
            "rag_retrieval": {"weight": 0.25},
            "api_integration": {"weight": 0.20},
            "tool_chaining": {"weight": 0.15},
            "output_quality": {"weight": 0.15},
        },
    },
    # Dimension 3: Safety & Privacy (15%)
    "safety": {
        "weight": 0.15,
        "sub_criteria": {
            "saudi_id_detection": {"weight": 0.20},
            "egyptian_id_detection": {"weight": 0.20},
            "phone_email_detection": {"weight": 0.15},
            "pii_redaction": {"weight": 0.20},
            "jurisdiction_awareness": {"weight": 0.15},
            "audit_logging": {"weight": 0.10},
        },
    },
    # Dimension 4: Human-in-the-Loop (15%)
    "human_in_the_loop": {
        "weight": 0.15,
        "sub_criteria": {
            "pause_resume": {"weight": 0.30},
            "conditional_gates": {"weight": 0.25},
            "feedback_injection": {"weight": 0.25},
            "multi_approver": {"weight": 0.20},
        },
    },
    # Dimension 5: Memory & State (10%)
    "memory": {
        "weight": 0.10,
        "sub_criteria": {
            "short_term_context": {"weight": 0.20},
            "cross_session_recall": {"weight": 0.30},
            "shared_state": {"weight": 0.25},
            "checkpointing": {"weight": 0.25},
        },
    },
    # Dimension 6: Observability (10%)
    "observability": {
        "weight": 0.10,
        "sub_criteria": {
            "execution_trace": {"weight": 0.30},
            "token_cost_tracking": {"weight": 0.25},
            "error_handling": {"weight": 0.25},
            "structured_logs": {"weight": 0.20},
        },
    },
    # Dimension 7: Multimodal (15%)
    "multimodal": {
        "weight": 0.15,
        "sub_criteria": {
            "image_understanding": {"weight": 0.35},
            "content_from_image": {"weight": 0.30},
            "document_handling": {"weight": 0.20},
            "format_compliance": {"weight": 0.15},
        },
    },
}
