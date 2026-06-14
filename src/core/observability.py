"""
Observability infrastructure: tracing, logging, and metrics.

Every agent call, tool invocation, and state change must be observable.
This enables:
1. End-to-end tracing for debugging
2. Token cost tracking for LLM calls
3. Performance monitoring (latency, throughput)
4. Audit logs for compliance
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json


class EventLevel(Enum):
    """Log level for observability events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ObservabilityEvent:
    """Base event for observability."""
    event_type: str
    timestamp: datetime
    trace_id: str
    agent_id: Optional[str] = None
    level: EventLevel = EventLevel.INFO
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "level": self.level.value,
            "message": self.message,
            "metadata": self.metadata,
        }


@dataclass
class LLMCallEvent(ObservabilityEvent):
    """Event for LLM API calls."""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        data = super().to_dict()
        data.update({
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
        })
        return data


@dataclass
class ToolCallEvent(ObservabilityEvent):
    """Event for tool invocations."""
    tool_name: str = ""
    success: bool = True
    error_message: Optional[str] = None
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        data = super().to_dict()
        data.update({
            "tool_name": self.tool_name,
            "success": self.success,
            "error_message": self.error_message,
            "latency_ms": self.latency_ms,
        })
        return data


class ObservabilityCollector:
    """
    Collects observability events from the entire system.
    
    Responsibilities:
    - Receive events from agents, tools, orchestrator
    - Aggregate metrics (token costs, latencies)
    - Stream to external sinks (logging, monitoring, database)
    """
    
    def __init__(self):
        """Initialize collector."""
        self.events: List[ObservabilityEvent] = []
        self._sinks: List[Any] = []
    
    def collect(self, event: ObservabilityEvent) -> None:
        """
        Collect an event.
        
        Args:
            event: The event to collect
        """
        self.events.append(event)
        
        # Stream to sinks
        for sink in self._sinks:
            try:
                sink.handle_event(event)
            except Exception as e:
                # Don't let sink errors break observability
                pass
    
    def add_sink(self, sink: Any) -> None:
        """Add an event sink (logger, metrics exporter, etc.)."""
        self._sinks.append(sink)
    
    def get_metrics(
        self,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute metrics for a trace or agent.
        
        Args:
            trace_id: Filter by trace ID
            agent_id: Filter by agent ID
        
        Returns:
            Metrics dict (token counts, costs, latencies, etc.)
        """
        events = self.events
        
        if trace_id:
            events = [e for e in events if e.trace_id == trace_id]
        
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        
        # Compute metrics
        total_tokens = sum(
            getattr(e, "total_tokens", 0)
            for e in events
            if isinstance(e, LLMCallEvent)
        )
        
        total_cost_usd = sum(
            getattr(e, "cost_usd", 0.0)
            for e in events
            if isinstance(e, LLMCallEvent)
        )
        
        tool_calls = len([e for e in events if isinstance(e, ToolCallEvent)])
        tool_errors = len([e for e in events if isinstance(e, ToolCallEvent) and not e.success])
        
        return {
            "event_count": len(events),
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
            "tool_calls": tool_calls,
            "tool_errors": tool_errors,
        }
    
    def export_trace(self, trace_id: str) -> str:
        """
        Export a complete trace as JSON for debugging.
        
        Args:
            trace_id: Trace ID to export
        
        Returns:
            JSON string containing all events in the trace
        """
        events = [e for e in self.events if e.trace_id == trace_id]
        return json.dumps(
            [e.to_dict() for e in events],
            indent=2,
            default=str,
        )


# Global collector instance (singleton)
_collector: Optional[ObservabilityCollector] = None


def get_collector() -> ObservabilityCollector:
    """Get global observability collector."""
    global _collector
    if _collector is None:
        _collector = ObservabilityCollector()
    return _collector


def set_collector(collector: ObservabilityCollector) -> None:
    """Set global observability collector."""
    global _collector
    _collector = collector
