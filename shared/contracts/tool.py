"""
Tool Contract — Abstract interface for all tools/actions available to agents.

A Tool is a capability that agents can invoke:
    - API calls (Meta Ads, Salla, Fawry, WhatsApp)
    - LLM functions (generation, classification, entity extraction)
    - Code execution (analytics, A/B test significance)
    - RAG retrieval (product catalog, customer history)
    - Compliance checks (PII detection, consent validation)

Tools are strictly separated from agent logic (Single Responsibility).
Every invocation is logged for observability and cost tracking.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import asyncio


class ToolCategory(Enum):
    """Categories of tools available to agents."""

    RAG_RETRIEVAL = "rag_retrieval"
    LLM_GENERATION = "llm_generation"
    API_CALL = "api_call"
    CODE_EXECUTION = "code_execution"
    DATABASE_QUERY = "database_query"
    COMPLIANCE_CHECK = "compliance_check"
    SEARCH = "search"


@dataclass
class ToolParameter:
    """Definition of a tool parameter with optional validation."""

    name: str
    type: str  # "string", "int", "float", "dict", "list", "bool"
    description: str
    required: bool = True
    default: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None
    validation_fn: Optional[Callable] = None


@dataclass
class ToolExecutionResult:
    """Result of a tool execution."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for message passing."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class ToolInvocation:
    """Record of a tool call for observability."""

    tool_name: str
    agent_id: str
    parameters: Dict[str, Any]
    result: ToolExecutionResult
    timestamp: datetime
    execution_time_ms: float
    tokens_used: Optional[Dict[str, int]] = None
    cost_usd: Optional[float] = None


class Tool(ABC):
    """
    Abstract base class for all tools.

    Handles:
        - Parameter validation (schema-based)
        - Retry logic (exponential backoff)
        - Invocation logging (observability)
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        parameters: List[ToolParameter],
        max_retries: int = 3,
        timeout_seconds: int = 30,
        on_invocation: Optional[Callable[[ToolInvocation], None]] = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.parameters = {p.name: p for p in parameters}
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.on_invocation = on_invocation

        self._invocation_count = 0
        self._total_execution_time = 0.0

    async def execute(self, agent_id: str, **kwargs) -> ToolExecutionResult:
        """
        Execute tool with validation, retry, and logging.

        Args:
            agent_id: ID of agent invoking the tool
            **kwargs: Parameters for the tool
        """
        # Validate parameters
        validation_error = self._validate_parameters(**kwargs)
        if validation_error:
            return ToolExecutionResult(success=False, error=validation_error)

        # Execute with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                start = datetime.now()
                result = await asyncio.wait_for(
                    self._execute_impl(**kwargs),
                    timeout=self.timeout_seconds,
                )
                exec_time = (datetime.now() - start).total_seconds() * 1000

                # Log invocation
                invocation = ToolInvocation(
                    tool_name=self.name,
                    agent_id=agent_id,
                    parameters=kwargs,
                    result=result,
                    timestamp=start,
                    execution_time_ms=exec_time,
                )
                self._invocation_count += 1
                self._total_execution_time += exec_time

                if self.on_invocation:
                    self.on_invocation(invocation)

                return result

            except asyncio.TimeoutError:
                last_error = f"Tool execution timed out after {self.timeout_seconds}s"
            except Exception as e:
                last_error = str(e)

            if attempt < self.max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        return ToolExecutionResult(
            success=False,
            error=f"Failed after {self.max_retries} retries: {last_error}",
        )

    @abstractmethod
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        """Actual implementation. Override in subclasses."""
        pass

    def _validate_parameters(self, **kwargs) -> Optional[str]:
        """Validate parameters against the schema."""
        for param_name, param in self.parameters.items():
            if param.required and param_name not in kwargs:
                return f"Missing required parameter: {param_name}"
            if param_name in kwargs:
                value = kwargs[param_name]
                if param.allowed_values and value not in param.allowed_values:
                    return f"Parameter {param_name} must be one of {param.allowed_values}"
                if param.validation_fn:
                    try:
                        param.validation_fn(value)
                    except Exception as e:
                        return f"Validation failed for {param_name}: {e}"
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get invocation statistics for this tool."""
        return {
            "invocation_count": self._invocation_count,
            "total_execution_time_ms": self._total_execution_time,
            "avg_execution_time_ms": (
                self._total_execution_time / self._invocation_count
                if self._invocation_count > 0
                else 0
            ),
        }


# ── Specialized Tool Types ──────────────────────────────────────


class APITool(Tool):
    """Tool for calling external APIs (Meta, Salla, Fawry, etc.)."""

    def __init__(
        self,
        name: str,
        api_endpoint: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        super().__init__(name=name, category=ToolCategory.API_CALL, **kwargs)
        self.api_endpoint = api_endpoint
        self.method = method
        self.headers = headers or {}


class LLMTool(Tool):
    """Tool for LLM-based operations (generation, classification, etc.)."""

    def __init__(
        self,
        name: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        **kwargs,
    ):
        super().__init__(name=name, category=ToolCategory.LLM_GENERATION, **kwargs)
        self.model = model
        self.temperature = temperature


class RAGTool(Tool):
    """Tool for retrieving information from vector DB."""

    def __init__(
        self,
        name: str,
        vector_db: str = "qdrant",
        index_name: str = "",
        **kwargs,
    ):
        super().__init__(name=name, category=ToolCategory.RAG_RETRIEVAL, **kwargs)
        self.vector_db = vector_db
        self.index_name = index_name
