"""
Tool abstraction - the interface for all tools/actions available to agents.

A Tool is a capability that agents can invoke:
- External API calls (Meta Ads API, Salla API, etc.)
- LLM functions (content generation, classification)
- Code execution (analytics, data transformation)
- Database queries (product catalog RAG, customer history)

Tools are strictly separated from agent logic (Single Responsibility).
This enables:
1. Easy addition of new tools without modifying agents
2. Tool caching and batching
3. Cost tracking per tool
4. Audit logging of tool invocations
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Callable
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
import json


class ToolCategory(Enum):
    """Categories of tools available to agents."""
    RAG_RETRIEVAL = "rag_retrieval"                # Vector DB queries for product catalog, FAQ
    LLM_GENERATION = "llm_generation"              # Content generation, summarization
    API_CALL = "api_call"                          # External API integrations
    CODE_EXECUTION = "code_execution"              # Sandboxed code (analytics, data processing)
    DATABASE_QUERY = "database_query"              # Direct DB access (orders, customer data)
    COMPLIANCE_CHECK = "compliance_check"          # PII detection, consent validation
    SEARCH = "search"                              # Web search, competitor monitoring


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str                                       # "string", "int", "dict", "list"
    description: str
    required: bool = True
    default: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None     # For enums
    validation_fn: Optional[Callable] = None       # Custom validation


@dataclass
class ToolExecutionResult:
    """Result of a tool execution."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # Execution time, tokens used, etc.
    
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
    tokens_used: Optional[Dict[str, int]] = None  # For LLM tools
    cost_usd: Optional[float] = None


class Tool(ABC):
    """
    Abstract base class for all tools.
    
    Principles:
    - Pure functions: same input -> same output
    - Idempotent: safe to retry
    - Stateless or minimal state
    - Observable: every invocation logged
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
        """
        Initialize a tool.
        
        Args:
            name: Unique tool identifier
            description: What this tool does
            category: Category of the tool
            parameters: List of parameters
            max_retries: How many times to retry on failure
            timeout_seconds: Max execution time
            on_invocation: Callback for logging/observability
        """
        self.name = name
        self.description = description
        self.category = category
        self.parameters = {p.name: p for p in parameters}
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.on_invocation = on_invocation
        
        self._invocation_count = 0
        self._total_execution_time = 0.0
    
    async def execute(
        self,
        agent_id: str,
        **kwargs
    ) -> ToolExecutionResult:
        """
        Execute this tool.
        
        Handles:
        1. Parameter validation
        2. Retry logic
        3. Timeout enforcement
        4. Invocation logging
        
        Args:
            agent_id: ID of agent invoking the tool
            **kwargs: Parameters for the tool
        
        Returns:
            ToolExecutionResult
        """
        # Validate parameters
        validation_error = self._validate_parameters(**kwargs)
        if validation_error:
            return ToolExecutionResult(
                success=False,
                error=validation_error,
            )
        
        # Execute with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = await self._execute_impl(**kwargs)
                
                # Log invocation
                invocation = ToolInvocation(
                    tool_name=self.name,
                    agent_id=agent_id,
                    parameters=kwargs,
                    result=result,
                    timestamp=datetime.now(),
                    execution_time_ms=0,  # Set by implementation
                )
                
                if self.on_invocation:
                    self.on_invocation(invocation)
                
                self._invocation_count += 1
                return result
                
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    # In real implementation, await asyncio.sleep(wait_time)
                    continue
        
        return ToolExecutionResult(
            success=False,
            error=f"Tool execution failed after {self.max_retries} retries: {last_error}",
        )
    
    @abstractmethod
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        """
        Actual implementation of the tool. Override in subclasses.
        
        Args:
            **kwargs: Validated parameters
        
        Returns:
            ToolExecutionResult
        """
        pass
    
    def _validate_parameters(self, **kwargs) -> Optional[str]:
        """
        Validate parameters against the schema.
        
        Returns:
            Error message if validation fails, None if valid
        """
        # Check required parameters
        for param_name, param in self.parameters.items():
            if param.required and param_name not in kwargs:
                return f"Missing required parameter: {param_name}"
            
            if param_name in kwargs:
                value = kwargs[param_name]
                
                # Check allowed values
                if param.allowed_values and value not in param.allowed_values:
                    return f"Parameter {param_name} must be one of {param.allowed_values}"
                
                # Run custom validation
                if param.validation_fn:
                    try:
                        param.validation_fn(value)
                    except Exception as e:
                        return f"Validation failed for {param_name}: {str(e)}"
        
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


# Specialized tool classes for specific categories

class APITool(Tool):
    """Tool for calling external APIs."""
    
    def __init__(
        self,
        name: str,
        api_endpoint: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        super().__init__(
            name=name,
            category=ToolCategory.API_CALL,
            **kwargs
        )
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
        **kwargs
    ):
        super().__init__(
            name=name,
            category=ToolCategory.LLM_GENERATION,
            **kwargs
        )
        self.model = model
        self.temperature = temperature


class RAGTool(Tool):
    """Tool for retrieving information from vector DB."""
    
    def __init__(
        self,
        name: str,
        vector_db: str = "pinecone",
        index_name: str = "",
        **kwargs
    ):
        super().__init__(
            name=name,
            category=ToolCategory.RAG_RETRIEVAL,
            **kwargs
        )
        self.vector_db = vector_db
        self.index_name = index_name
