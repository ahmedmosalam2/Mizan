"""
Scoring Rubrics — Evaluation criteria for each of the 7 dimensions.

Each dimension is scored 0-10. Sub-criteria have weights that sum to 1.0.
Weights across dimensions sum to 1.0 (normalized to 10-point scale).

Dimensions:
    1. Orchestration (20%)  — task decomposition, parallel, branching, recovery
    2. Tool Use (15%)       — function calling, RAG, API, chaining, output quality
    3. Safety (15%)         — PII detection (SA/EG), redaction, jurisdiction, audit
    4. HITL (15%)           — pause/resume, conditional gates, feedback, multi-approver
    5. Memory (10%)         — short-term, cross-session, shared state, checkpointing
    6. Observability (10%)  — tracing, cost tracking, error handling, logs
    7. Multimodal (15%)     — image understanding, content from image, docs, format
"""

RUBRICS = {
    # ═══════════════════════════════════════════════════════════════
    # Dimension 1: Agent Design & Orchestration (20%)
    # ═══════════════════════════════════════════════════════════════
    "orchestration": {
        "weight": 0.20,
        "sub_criteria": {
            "multi_agent_creation": {
                "weight": 0.15,
                "levels": {
                    10: "Creates all 6 agents with distinct roles and tool access",
                    7: "Creates 4-5 agents with roles",
                    4: "Creates 2-3 agents",
                    0: "Single agent or fails to create",
                },
            },
            "task_decomposition": {
                "weight": 0.20,
                "levels": {
                    10: "Decomposes brief into 4+ sub-tasks with correct agent assignment",
                    7: "Decomposes into 2-3 sub-tasks",
                    4: "Partial decomposition",
                    0: "No decomposition — runs as monolithic task",
                },
            },
            "sequential_execution": {
                "weight": 0.15,
                "levels": {
                    10: "Correct sequential ordering with dependency awareness",
                    5: "Sequential but no dependency tracking",
                    0: "Cannot run sequentially",
                },
            },
            "parallel_execution": {
                "weight": 0.15,
                "levels": {
                    10: "True parallel execution with result aggregation",
                    5: "Simulated parallel (async but sequential)",
                    0: "No parallel support",
                },
            },
            "conditional_branching": {
                "weight": 0.15,
                "levels": {
                    10: "Dynamic branching based on runtime conditions",
                    5: "Static branching (pre-configured)",
                    0: "No branching capability",
                },
            },
            "error_recovery": {
                "weight": 0.10,
                "levels": {
                    10: "Automatic retry with backoff + graceful degradation",
                    5: "Simple retry without backoff",
                    0: "Pipeline crashes on first error",
                },
            },
            "inter_agent_communication": {
                "weight": 0.10,
                "levels": {
                    10: "Rich shared context with message passing between agents",
                    5: "Basic result forwarding only",
                    0: "No inter-agent communication",
                },
            },
        },
    },

    # ═══════════════════════════════════════════════════════════════
    # Dimension 2: Tool Use & Integrations (15%)
    # ═══════════════════════════════════════════════════════════════
    "tool_use": {
        "weight": 0.15,
        "sub_criteria": {
            "function_calling": {
                "weight": 0.25,
                "levels": {
                    10: "Correct tool selection and parameter passing for all tools",
                    7: "Correct for most tools, minor parameter errors",
                    4: "Calls tools but with frequent errors",
                    0: "Cannot call tools",
                },
            },
            "rag_retrieval": {
                "weight": 0.25,
                "levels": {
                    10: "Retrieves correct product info and incorporates into output",
                    7: "Retrieves correct info but integration is rough",
                    4: "Retrieves but with factual errors",
                    0: "No RAG capability",
                },
            },
            "api_integration": {
                "weight": 0.20,
                "levels": {
                    10: "Handles 5+ API integrations including auth and error handling",
                    7: "Handles 3-4 APIs",
                    4: "Handles 1-2 APIs",
                    0: "No API integration",
                },
            },
            "tool_chaining": {
                "weight": 0.15,
                "levels": {
                    10: "Chains multiple tools in sequence with data flow between them",
                    5: "Single tool calls only",
                    0: "No tool chaining",
                },
            },
            "output_quality": {
                "weight": 0.15,
                "levels": {
                    10: "Generated content is accurate, culturally appropriate, and bilingual",
                    7: "Content is mostly accurate",
                    4: "Content has errors or wrong dialect",
                    0: "Content is unusable",
                },
            },
        },
    },

    # ═══════════════════════════════════════════════════════════════
    # Dimension 3: Safety & Privacy (15%)
    # ═══════════════════════════════════════════════════════════════
    "safety": {
        "weight": 0.15,
        "sub_criteria": {
            "saudi_id_detection": {
                "weight": 0.20,
                "levels": {
                    10: "Detects 100% of Saudi national IDs (10-digit, starts with 1/2)",
                    7: "Detects 70%+",
                    4: "Detects some but misses patterns",
                    0: "No detection",
                },
            },
            "egyptian_id_detection": {
                "weight": 0.20,
                "levels": {
                    10: "Detects 100% of Egyptian national IDs (14-digit)",
                    7: "Detects 70%+",
                    4: "Detects some",
                    0: "No detection",
                },
            },
            "phone_email_detection": {
                "weight": 0.15,
                "levels": {
                    10: "Detects all phone numbers and emails in Arabic/English text",
                    7: "Detects most",
                    4: "Misses Arabic-embedded numbers",
                    0: "No detection",
                },
            },
            "pii_redaction": {
                "weight": 0.20,
                "levels": {
                    10: "Redacts all detected PII with appropriate masking",
                    7: "Redacts most PII",
                    4: "Inconsistent redaction",
                    0: "No redaction capability",
                },
            },
            "jurisdiction_awareness": {
                "weight": 0.15,
                "levels": {
                    10: "Applies KSA PDPL and Egypt Law 151/2020 rules correctly",
                    5: "Basic compliance awareness",
                    0: "No jurisdiction awareness",
                },
            },
            "audit_logging": {
                "weight": 0.10,
                "levels": {
                    10: "Complete audit log of all PII operations with timestamps",
                    5: "Partial logging",
                    0: "No audit logging",
                },
            },
        },
    },

    # ═══════════════════════════════════════════════════════════════
    # Dimension 4: Human-in-the-Loop (15%)
    # ═══════════════════════════════════════════════════════════════
    "human_in_the_loop": {
        "weight": 0.15,
        "sub_criteria": {
            "pause_resume": {
                "weight": 0.30,
                "levels": {
                    10: "Workflow pauses, serializes state, resumes after approval",
                    7: "Pauses but state is partially lost",
                    4: "Can pause but cannot resume cleanly",
                    0: "No pause/resume capability",
                },
            },
            "conditional_gates": {
                "weight": 0.25,
                "levels": {
                    10: "Conditional approval (e.g., auto-approve < 20%, manual > 20%)",
                    5: "All-or-nothing approval gates",
                    0: "No approval gates",
                },
            },
            "feedback_injection": {
                "weight": 0.25,
                "levels": {
                    10: "Human feedback modifies agent behavior mid-workflow",
                    5: "Feedback accepted but not incorporated",
                    0: "No feedback mechanism",
                },
            },
            "multi_approver": {
                "weight": 0.20,
                "levels": {
                    10: "Supports multiple approvers (marketing + compliance)",
                    5: "Single approver only",
                    0: "No multi-approver support",
                },
            },
        },
    },

    # ═══════════════════════════════════════════════════════════════
    # Dimension 5: Memory & State (10%)
    # ═══════════════════════════════════════════════════════════════
    "memory": {
        "weight": 0.10,
        "sub_criteria": {
            "short_term_context": {
                "weight": 0.20,
                "levels": {
                    10: "Maintains coherent context within a multi-step task",
                    5: "Partial context retention",
                    0: "No short-term memory",
                },
            },
            "cross_session_recall": {
                "weight": 0.30,
                "levels": {
                    10: "Recalls specific details from previous sessions (product, price, color)",
                    7: "Recalls general topic but misses details",
                    4: "Vague recall",
                    0: "No cross-session memory",
                },
            },
            "shared_state": {
                "weight": 0.25,
                "levels": {
                    10: "Shared state accessible and writable by multiple agents",
                    5: "Read-only shared state",
                    0: "No shared state",
                },
            },
            "checkpointing": {
                "weight": 0.25,
                "levels": {
                    10: "Full checkpoint/resume with idempotent operations",
                    5: "Basic checkpoint but replay issues",
                    0: "No checkpointing",
                },
            },
        },
    },

    # ═══════════════════════════════════════════════════════════════
    # Dimension 6: Observability (10%)
    # ═══════════════════════════════════════════════════════════════
    "observability": {
        "weight": 0.10,
        "sub_criteria": {
            "execution_trace": {
                "weight": 0.30,
                "levels": {
                    10: "End-to-end trace with agent, tool, timing for every step",
                    7: "Trace with most steps",
                    4: "Partial trace",
                    0: "No tracing",
                },
            },
            "token_cost_tracking": {
                "weight": 0.25,
                "levels": {
                    10: "Per-agent, per-task token and cost tracking",
                    5: "Aggregate token count only",
                    0: "No token tracking",
                },
            },
            "error_handling": {
                "weight": 0.25,
                "levels": {
                    10: "Handles injected failure with retry + fallback + reporting",
                    7: "Retry but no fallback",
                    4: "Error caught but not handled",
                    0: "Crashes on error",
                },
            },
            "structured_logs": {
                "weight": 0.20,
                "levels": {
                    10: "JSON-structured logs with correlation IDs",
                    5: "Text logs with some structure",
                    0: "No logging",
                },
            },
        },
    },

    # ═══════════════════════════════════════════════════════════════
    # Dimension 7: Multimodal (15%)
    # ═══════════════════════════════════════════════════════════════
    "multimodal": {
        "weight": 0.15,
        "sub_criteria": {
            "image_understanding": {
                "weight": 0.35,
                "levels": {
                    10: "Accurately describes product from image and generates relevant copy",
                    7: "Describes image but with some inaccuracies",
                    4: "Generic description not product-specific",
                    0: "Cannot process images",
                },
            },
            "content_from_image": {
                "weight": 0.30,
                "levels": {
                    10: "Generated ad copy references specific visual details from image",
                    5: "Generic copy that could apply to any product",
                    0: "No image-to-text capability",
                },
            },
            "document_handling": {
                "weight": 0.20,
                "levels": {
                    10: "Can parse PDFs and extract structured data",
                    5: "Basic text extraction from documents",
                    0: "No document handling",
                },
            },
            "format_compliance": {
                "weight": 0.15,
                "levels": {
                    10: "Output meets platform format rules (character limits, etc.)",
                    5: "Partially compliant",
                    0: "No format awareness",
                },
            },
        },
    },
}


def get_max_possible_score() -> float:
    """Total max score across all dimensions (normalized to 10)."""
    return 10.0


def get_dimension_weights() -> dict:
    """Return dimension weights."""
    return {dim: info["weight"] for dim, info in RUBRICS.items()}
