"""
Mizan Shared — Framework-agnostic core contracts, scoring, and utilities.

This package contains everything that is shared across all framework adapters:
- contracts/  : Abstract interfaces (Agent, Orchestrator, Adapter, Message, etc.)
- schemas.py  : Pydantic models for briefs, results, and structured output
- scoring/    : Rubrics, scorer, PII scorer, LLM judge, trace coverage
- prompts/    : Agent system prompts (Markdown files)
- services/   : LLM gateway, API client
- testing/    : Shared test fixtures, mock LLM, seed control
"""

__version__ = "2.0.0"
