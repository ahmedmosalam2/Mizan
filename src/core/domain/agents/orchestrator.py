"""Agent Orchestrator - Controls and coordinates multiple agents."""

from typing import List, Dict, Optional, Callable, Any
from abc import ABC, abstractmethod
import time
from datetime import datetime

from core.domain.agents.base import Agent
from core.domain.agents.agent_result import AgentResult, AgentResultBuilder
from core.domain.agents.agent_context import AgentContext
from core.domain.entities.agent_helper import Task


class AgentOrchestratorPort(ABC):
    """Port (Interface) for Agent Orchestration."""
    
    @abstractmethod
    async def orchestrate(self, 
                         agents: List[Agent], 
                         task: Task,
                         context: Optional[AgentContext] = None) -> AgentResult:
        """Execute a sequence of agents."""
        pass
    
    @abstractmethod
    async def orchestrate_parallel(self,
                                   agents: List[Agent],
                                   task: Task,
                                   context: Optional[AgentContext] = None) -> Dict[str, AgentResult]:
        """Execute agents in parallel."""
        pass


class SerialAgentOrchestrator(AgentOrchestratorPort):
    """Executes agents sequentially, passing results between them."""
    
    def __init__(self, 
                 max_retries: int = 2,
                 timeout_per_agent: float = 60.0,
                 debug: bool = False):
        """
        Initialize orchestrator.
        
        Args:
            max_retries: Maximum retries per agent
            timeout_per_agent: Timeout in seconds per agent
            debug: Enable debug logging
        """
        self.max_retries = max_retries
        self.timeout_per_agent = timeout_per_agent
        self.debug = debug
        self.execution_log: List[Dict[str, Any]] = []
    
    async def orchestrate(self,
                         agents: List[Agent],
                         task: Task,
                         context: Optional[AgentContext] = None) -> AgentResult:
        """
        Execute agents sequentially.
        
        Each agent receives the context, executes, and passes results to next agent.
        If an agent fails, execution stops.
        
        Args:
            agents: List of agents to execute in order
            task: Initial task
            context: Shared context between agents
            
        Returns:
            Final AgentResult from last agent
        """
        if not agents:
            raise ValueError("At least one agent is required")
        
        # Initialize context if not provided
        if context is None:
            context = AgentContext(
                workflow_id=f"wf_{datetime.now().timestamp()}",
                task_id=task.id or "task_1"
            )
        
        # Store initial task
        context.set_data("initial_task", task.model_dump() if hasattr(task, 'model_dump') else str(task))
        
        final_result = None
        
        for agent_index, agent in enumerate(agents):
            # Check if we should stop
            if context.should_stop():
                break
            
            agent_name = agent.__class__.__name__
            context.increment_step()
            
            if self.debug:
                print(f"[DEBUG] Executing Agent {agent_index + 1}/{len(agents)}: {agent_name}")
            
            # Execute agent with retry logic
            result = await self._execute_agent_with_retry(agent, task, context, agent_name)
            final_result = result
            
            # Log execution
            self._log_execution(agent_name, result)
            
            # Update context with result
            context.set_data(f"agent_{agent_index}_result", result.model_dump())
            context.add_message(agent_name, "execution", {
                "status": result.status,
                "data": result.data,
                "time_ms": result.execution_time_ms
            })
            
            # Check if we should stop due to failure
            if result.status == "failure" and not result.can_continue:
                context.stop_execution(f"Agent {agent_name} failed")
                break
            
            # Update task for next agent
            if result.data:
                task = self._prepare_next_task(task, result)
        
        return final_result or self._create_empty_result("Orchestrator", context.task_id)
    
    async def orchestrate_parallel(self,
                                   agents: List[Agent],
                                   task: Task,
                                   context: Optional[AgentContext] = None) -> Dict[str, AgentResult]:
        """
        Execute agents in parallel.
        
        Each agent executes independently on the same task/context.
        Results are returned as a dictionary keyed by agent name.
        
        Args:
            agents: List of agents to execute in parallel
            task: Task for all agents
            context: Shared context between agents
            
        Returns:
            Dictionary mapping agent names to their results
        """
        if not agents:
            raise ValueError("At least one agent is required")
        
        # Initialize context if not provided
        if context is None:
            context = AgentContext(
                workflow_id=f"wf_parallel_{datetime.now().timestamp()}",
                task_id=task.id or "task_1"
            )
        
        # Execute all agents in parallel
        import asyncio
        
        tasks = [
            self._execute_agent_with_retry(agent, task, context, agent.__class__.__name__)
            for agent in agents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results to agent names
        result_dict = {}
        for agent, result in zip(agents, results):
            agent_name = agent.__class__.__name__
            if isinstance(result, Exception):
                result_dict[agent_name] = self._create_error_result(
                    agent_name, 
                    context.task_id,
                    str(result),
                    "ExecutionException"
                )
            else:
                result_dict[agent_name] = result
                context.add_message(agent_name, "parallel_execution", {
                    "status": result.status,
                    "time_ms": result.execution_time_ms
                })
        
        return result_dict
    
    # ============== Private Methods ==============
    
    async def _execute_agent_with_retry(self,
                                       agent: Agent,
                                       task: Task,
                                       context: AgentContext,
                                       agent_name: str) -> AgentResult:
        """Execute agent with retry logic."""
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                # Execute agent
                result_data = await agent.execute(task)
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Create result
                result = AgentResultBuilder(agent_name, context.task_id) \
                    .success(result_data) \
                    .with_execution_time(execution_time_ms) \
                    .build()
                
                return result
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Last attempt failed
                    error_msg = f"Agent failed after {self.max_retries} attempts: {str(e)}"
                    context.increment_errors()
                    
                    return self._create_error_result(
                        agent_name,
                        context.task_id,
                        error_msg,
                        type(e).__name__
                    )
                
                # Retry
                if self.debug:
                    print(f"[DEBUG] {agent_name} attempt {attempt + 1} failed, retrying...")
                
                await self._backoff_delay(attempt)
        
        # Should not reach here
        return self._create_error_result(
            agent_name,
            context.task_id,
            "Unknown error",
            "UnknownError"
        )
    
    async def _backoff_delay(self, attempt: int) -> None:
        """Exponential backoff delay."""
        import asyncio
        delay = (2 ** attempt) * 0.1  # 0.1s, 0.2s, 0.4s, etc.
        await asyncio.sleep(delay)
    
    def _prepare_next_task(self, current_task: Task, result: AgentResult) -> Task:
        """Prepare task for next agent based on previous result."""
        # If result has data, create new context but keep original goal
        if result.data:
            # This is a simplified version - can be enhanced based on needs
            return current_task
        return current_task
    
    def _create_empty_result(self, agent_name: str, task_id: str) -> AgentResult:
        """Create empty result."""
        return AgentResultBuilder(agent_name, task_id) \
            .success(None) \
            .build()
    
    def _create_error_result(self, 
                            agent_name: str, 
                            task_id: str,
                            error: str,
                            error_type: str) -> AgentResult:
        """Create error result."""
        return AgentResultBuilder(agent_name, task_id) \
            .failure(error, error_type) \
            .build()
    
    def _log_execution(self, agent_name: str, result: AgentResult) -> None:
        """Log execution for debugging."""
        self.execution_log.append({
            "agent": agent_name,
            "status": result.status,
            "time_ms": result.execution_time_ms,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get execution log."""
        return self.execution_log
