"""Unit Tests for Agent Orchestration System."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from core.domain.agents import (
    SerialAgentOrchestrator,
    AnalysisAgent,
    OptimizationAgent,
    ValidatorAgent,
    ExecutorAgent,
    AgentContext,
    AgentResultBuilder,
    ResultStatus
)
from core.domain.entities.agent_helper import Task


class TestAgentResult:
    """Test AgentResult and AgentResultBuilder."""
    
    def test_result_builder_success(self):
        """Test successful result building."""
        result = AgentResultBuilder("TestAgent", "task_1") \
            .success({"data": "test"}) \
            .build()
        
        assert result.status == ResultStatus.SUCCESS
        assert result.agent_name == "TestAgent"
        assert result.task_id == "task_1"
        assert result.data == {"data": "test"}
    
    def test_result_builder_failure(self):
        """Test failure result building."""
        result = AgentResultBuilder("TestAgent", "task_1") \
            .failure("Error message", "TestError") \
            .build()
        
        assert result.status == ResultStatus.FAILURE
        assert result.error == "Error message"
        assert result.error_type == "TestError"
    
    def test_result_builder_with_metadata(self):
        """Test result with metadata."""
        result = AgentResultBuilder("TestAgent", "task_1") \
            .success({"data": "test"}) \
            .with_metadata("key1", "value1") \
            .with_metadata("key2", "value2") \
            .build()
        
        assert result.metadata["key1"] == "value1"
        assert result.metadata["key2"] == "value2"
    
    def test_result_builder_next_step(self):
        """Test next step configuration."""
        result = AgentResultBuilder("Agent1", "task_1") \
            .success({}) \
            .next_step("Agent2", can_continue=True) \
            .build()
        
        assert result.next_agent == "Agent2"
        assert result.can_continue is True


class TestAgentContext:
    """Test AgentContext functionality."""
    
    def test_context_creation(self):
        """Test context initialization."""
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        
        assert context.workflow_id == "wf_1"
        assert context.task_id == "task_1"
        assert context.shared_data == {}
        assert context.step_count == 0
    
    def test_set_and_get_data(self):
        """Test data storage and retrieval."""
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        
        context.set_data("key1", "value1")
        assert context.get_data("key1") == "value1"
        
        context.set_data("key2", {"nested": "data"})
        assert context.get_data("key2")["nested"] == "data"
    
    def test_get_all_data(self):
        """Test getting all shared data."""
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        context.set_data("key1", "value1")
        context.set_data("key2", "value2")
        
        all_data = context.get_all_data()
        assert all_data["key1"] == "value1"
        assert all_data["key2"] == "value2"
    
    def test_message_history(self):
        """Test message recording."""
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        
        context.add_message("Agent1", "analysis", {"status": "done"})
        context.add_message("Agent2", "optimization", {"actions": 3})
        
        messages = context.get_messages()
        assert len(messages) == 2
        assert messages[0]["agent"] == "Agent1"
    
    def test_get_messages_by_agent(self):
        """Test filtering messages by agent."""
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        
        context.add_message("Agent1", "analysis", {"data": 1})
        context.add_message("Agent2", "optimization", {"data": 2})
        context.add_message("Agent1", "analysis", {"data": 3})
        
        agent1_messages = context.get_messages("Agent1")
        assert len(agent1_messages) == 2
    
    def test_error_tracking(self):
        """Test error count tracking."""
        context = AgentContext(workflow_id="wf_1", task_id="task_1", max_errors=3)
        
        assert context.increment_errors() is False  # Under limit
        assert context.increment_errors() is False  # Under limit
        assert context.increment_errors() is True   # At limit
        assert context.should_stop() is True
    
    def test_execution_stop(self):
        """Test stopping execution."""
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        
        assert context.should_stop() is False
        context.stop_execution("Test stop")
        assert context.should_stop() is True


class TestAnalysisAgent:
    """Test AnalysisAgent."""
    
    @pytest.mark.asyncio
    async def test_analysis_agent_execution(self):
        """Test analysis agent execution."""
        # Mock LLM
        llm_port = AsyncMock()
        llm_port.generate.return_value = '{"insights": ["insight1"], "data_quality": 85, "recommendations": []}'
        
        agent = AnalysisAgent(llm_port)
        
        task = Task(
            goal="Analyze campaign",
            context={"campaign": "test"},
            constraints=["constraint1"],
            expected_output="Analysis"
        )
        
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        result = await agent.execute(task, context)
        
        assert result["type"] == "analysis"
        assert "insights" in result
        assert "data_quality_score" in result


class TestOptimizationAgent:
    """Test OptimizationAgent."""
    
    @pytest.mark.asyncio
    async def test_optimization_agent_execution(self):
        """Test optimization agent execution."""
        # Mock LLM
        llm_port = AsyncMock()
        llm_port.generate.return_value = '{"actions": [], "estimated_improvement": 30, "priority": "high", "implementation_steps": []}'
        
        agent = OptimizationAgent(llm_port)
        
        task = Task(
            goal="Optimize campaign",
            context={"campaign": "test"},
            constraints=[],
            expected_output="Optimization plan"
        )
        
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        context.set_data("analysis_results", {"insights": []})
        
        result = await agent.execute(task, context)
        
        assert result["type"] == "optimization"
        assert "actions" in result
        assert "estimated_improvement" in result


class TestValidatorAgent:
    """Test ValidatorAgent."""
    
    @pytest.mark.asyncio
    async def test_validator_agent_passes(self):
        """Test validator agent with valid plan."""
        agent = ValidatorAgent()
        
        task = Task(
            goal="Validate plan",
            context={},
            constraints=[],
            expected_output="Validation result"
        )
        
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        context.set_data("optimization_plan", {
            "actions": [{"channel": "META", "action": "increase"}],
            "estimated_improvement": 25
        })
        
        result = await agent.execute(task, context)
        
        assert result["type"] == "validation"
        assert result["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_validator_agent_with_custom_rules(self):
        """Test validator with custom rules."""
        def my_rule(task, plan):
            return plan is not None and plan.get("estimated_improvement", 0) >= 50
        
        agent = ValidatorAgent({"my_rule": my_rule})
        
        task = Task(
            goal="Validate",
            context={},
            constraints=[],
            expected_output="Validation"
        )
        
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        context.set_data("optimization_plan", {"estimated_improvement": 30})
        
        result = await agent.execute(task, context)
        
        assert result["is_valid"] is False


class TestExecutorAgent:
    """Test ExecutorAgent."""
    
    @pytest.mark.asyncio
    async def test_executor_agent_executes_actions(self):
        """Test executor executes actions."""
        executor_port = AsyncMock()
        executor_port.execute.return_value = {"status": "success"}
        
        agent = ExecutorAgent(executor_port)
        
        task = Task(
            goal="Execute",
            context={},
            constraints=[],
            expected_output="Execution result"
        )
        
        context = AgentContext(workflow_id="wf_1", task_id="task_1")
        context.set_data("validation_results", {"is_valid": True})
        context.set_data("optimization_plan", {
            "actions": [{"channel": "META", "amount": 5000}]
        })
        
        result = await agent.execute(task, context)
        
        assert result["type"] == "execution"
        assert len(result["executed_actions"]) == 1


class TestSerialAgentOrchestrator:
    """Test SerialAgentOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_orchestrate_serial_execution(self):
        """Test serial execution of agents."""
        # Mock agents
        agent1 = AsyncMock()
        agent1.execute.return_value = {"result": "agent1"}
        agent1.__class__.__name__ = "Agent1"
        
        agent2 = AsyncMock()
        agent2.execute.return_value = {"result": "agent2"}
        agent2.__class__.__name__ = "Agent2"
        
        orchestrator = SerialAgentOrchestrator()
        
        task = Task(
            goal="Test",
            context={},
            constraints=[],
            expected_output="Result"
        )
        
        result = await orchestrator.orchestrate([agent1, agent2], task)
        
        assert result.status == ResultStatus.SUCCESS
        assert agent1.execute.called
        assert agent2.execute.called
    
    @pytest.mark.asyncio
    async def test_orchestrate_with_failure(self):
        """Test orchestration with agent failure."""
        # Mock agent that fails
        agent1 = AsyncMock()
        agent1.execute.side_effect = Exception("Agent failed")
        agent1.__class__.__name__ = "FailingAgent"
        
        orchestrator = SerialAgentOrchestrator(max_retries=2)
        
        task = Task(
            goal="Test",
            context={},
            constraints=[],
            expected_output="Result"
        )
        
        result = await orchestrator.orchestrate([agent1], task)
        
        assert result.status == ResultStatus.FAILURE
    
    @pytest.mark.asyncio
    async def test_orchestrate_parallel_execution(self):
        """Test parallel execution of agents."""
        # Mock agents
        agents = []
        for i in range(3):
            agent = AsyncMock()
            agent.execute.return_value = {"result": f"agent{i}"}
            agent.__class__.__name__ = f"Agent{i}"
            agents.append(agent)
        
        orchestrator = SerialAgentOrchestrator()
        
        task = Task(
            goal="Test",
            context={},
            constraints=[],
            expected_output="Result"
        )
        
        results = await orchestrator.orchestrate_parallel(agents, task)
        
        assert len(results) == 3
        for agent_name, result in results.items():
            assert result.status == ResultStatus.SUCCESS


class TestOrchestrationIntegration:
    """Integration tests for orchestration."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test complete orchestration pipeline."""
        # Mock LLM
        llm_port = AsyncMock()
        llm_port.generate.side_effect = [
            '{"insights": [], "data_quality": 85, "recommendations": []}', 
            '{"actions": [], "estimated_improvement": 30, "priority": "high", "implementation_steps": []}',  
        ]
        
        # Mock executor
        executor_port = AsyncMock()
        executor_port.execute.return_value = {"status": "success"}
        
        # Create agents
        agents = [
            AnalysisAgent(llm_port),
            OptimizationAgent(llm_port),
            ValidatorAgent(),
            ExecutorAgent(executor_port)
        ]
        
        # Create task
        task = Task(
            goal="Optimize campaign",
            context={"campaign": "test"},
            constraints=[],
            expected_output="Optimization plan"
        )
        
        # Execute
        orchestrator = SerialAgentOrchestrator()
        result = await orchestrator.orchestrate(agents, task)
        
        assert result.status == ResultStatus.SUCCESS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
