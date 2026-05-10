"""Example Implementation - Complete working example of Agent Orchestration."""

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock
import json

# Imports
from core.domain.agents.orchestrator import SerialAgentOrchestrator
from core.domain.agents.agent_context import AgentContext
from core.domain.agents.specialized_agents import (
    AnalysisAgent,
    OptimizationAgent,
    ValidatorAgent,
    ExecutorAgent
)
from core.domain.entities.agent_helper import Task
from core.domain.entities.campaign import Campaign, Market, CampaignStatus, Channel
from core.use_cases.optimize_campaign_with_agents import (
    OptimizeCampaignWithAgentsUseCase,
    CampaignOptimizationPipeline
)


class MockLLMPort:
    """Mock LLM port for demonstration."""
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate mock response based on prompt."""
        await asyncio.sleep(0.1)  # Simulate API latency
        
        if "Analyze" in prompt or "analyze" in prompt:
            return json.dumps({
                "insights": [
                    "Campaign is underperforming in mobile channels",
                    "High engagement on Meta and TikTok",
                    "Low conversion rate on SMS channel"
                ],
                "data_quality": 85,
                "recommendations": [
                    "Increase Meta budget by 20%",
                    "Test new audience segments",
                    "Reduce SMS campaigns"
                ]
            })
        
        elif "Optim" in prompt or "optim" in prompt:
            return json.dumps({
                "actions": [
                    {"channel": "META", "action": "increase_budget", "amount": 5000},
                    {"channel": "TIKTOK", "action": "increase_budget", "amount": 3000},
                    {"channel": "SMS", "action": "decrease_budget", "amount": 2000}
                ],
                "estimated_improvement": 35,
                "priority": "high",
                "implementation_steps": [
                    "Update campaign allocation in system",
                    "Deploy new targeting parameters",
                    "Monitor metrics hourly for first 24 hours"
                ]
            })
        
        return json.dumps({"status": "ok", "data": "mock response"})
    
    async def embed(self, text: str) -> list:
        """Generate mock embedding."""
        return [0.1, 0.2, 0.3, 0.4, 0.5] * 204  # 1020 dimensions
    
    def count_tokens(self, text: str) -> int:
        """Count mock tokens."""
        return len(text.split())


class MockCampaignRepository:
    """Mock campaign repository."""
    
    def __init__(self):
        self.campaigns = {}
    
    async def get(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID."""
        return self.campaigns.get(campaign_id)
    
    async def save(self, campaign: Campaign) -> Campaign:
        """Save campaign."""
        self.campaigns[campaign.id] = campaign
        return campaign
    
    def create_sample_campaign(self) -> Campaign:
        """Create a sample campaign for testing."""
        campaign = Campaign(
            id="campaign_001",
            name="Ramadan Campaign 2024",
            market=Market.SAUDI_ARABIA,
            status=CampaignStatus.DRAFT,
            total_spend=50000,
            total_budget=100000,
            currency="SAR",
            channels=[Channel.META, Channel.GOOGLE, Channel.TIKTOK, Channel.SMS],
            target_audiences=["18-35", "35-50", "50+"],
            languages=["ar", "en"],
            channel_allocations={
                Channel.META: 40000,
                Channel.GOOGLE: 30000,
                Channel.TIKTOK: 20000,
                Channel.SMS: 10000
            }
        )
        self.campaigns[campaign.id] = campaign
        return campaign


class MockExecutorPort:
    """Mock executor port for testing."""
    
    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action."""
        await asyncio.sleep(0.05)  # Simulate execution
        return {
            "status": "executed",
            "action": action,
            "result": f"Successfully executed {action.get('action', 'unknown')}"
        }


async def example_1_basic_orchestration():
    """Example 1: Basic agent orchestration workflow."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Agent Orchestration")
    print("="*70)
    
    # Setup
    llm_port = MockLLMPort()
    executor_port = MockExecutorPort()
    
    # Create agents
    analysis_agent = AnalysisAgent(llm_port)
    optimization_agent = OptimizationAgent(llm_port)
    validator_agent = ValidatorAgent()
    executor_agent = ExecutorAgent(executor_port)
    
    # Create task
    task = Task(
        goal="Optimize campaign for maximum ROI",
        context="Marketing campaign optimization",
        constraints=["budget_limit: 100000 SAR"],
        expected_output="Optimization plan with actions and expected ROI"
    )
    
    # Create context
    context = AgentContext(
        workflow_id="wf_example_1",
        task_id="task_1",
        campaign_id="campaign_001",
        market="KSA"
    )
    
    # Initialize orchestrator
    orchestrator = SerialAgentOrchestrator(max_retries=2, debug=True)
    
    # Execute orchestration
    print("\n🚀 Starting orchestration...")
    result = await orchestrator.orchestrate(
        agents=[analysis_agent, optimization_agent, validator_agent, executor_agent],
        task=task,
        context=context
    )
    
    # Print results
    print(f"\n✅ Orchestration Complete!")
    print(f"Status: {result.status}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")
    print(f"Final Result Data: {json.dumps(result.data, indent=2, ensure_ascii=False)}")
    
    # Print context messages
    print(f"\n📋 Agent Communications ({len(context.messages)} messages):")
    for msg in context.get_messages():
        print(f"  - [{msg['agent']}] {msg['type']}: {msg['content']}")
    
    # Print execution log
    print(f"\n⏱️ Execution Log:")
    for log in orchestrator.get_execution_log():
        print(f"  - {log['agent']}: {log['status']} ({log['time_ms']:.2f}ms)")


async def example_2_parallel_analysis():
    """Example 2: Parallel agent execution."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Parallel Analysis")
    print("="*70)
    
    # Setup
    llm_port = MockLLMPort()
    
    # Create multiple analysis agents
    agents = [
        AnalysisAgent(llm_port) for _ in range(3)
    ]
    
    # Create task
    task = Task(
        goal="Analyze multiple campaigns",
        context="Parallel analysis of campaign performance",
        constraints=["Complete within timeout"],
        expected_output="Analysis results for each campaign"
    )
    
    # Initialize orchestrator
    orchestrator = SerialAgentOrchestrator(debug=True)
    
    # Execute parallel
    print("\n🚀 Starting parallel analysis...")
    results = await orchestrator.orchestrate_parallel(
        agents=agents,
        task=task
    )
    
    # Print results
    print(f"\n✅ Parallel Execution Complete!")
    print(f"Results: {len(results)} agents executed")
    for agent_name, result in results.items():
        print(f"  - {agent_name}: {result.status} ({result.execution_time_ms:.2f}ms)")


async def example_3_complete_use_case():
    """Example 3: Complete use case with repository."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Complete Campaign Optimization Use Case")
    print("="*70)
    
    # Setup
    campaign_repo = MockCampaignRepository()
    llm_port = MockLLMPort()
    executor_port = MockExecutorPort()
    
    # Create sample campaign
    campaign = campaign_repo.create_sample_campaign()
    print(f"\n📊 Campaign: {campaign.name}")
    print(f"   Market: {campaign.market}")
    print(f"   Budget: {campaign.total_budget} {campaign.currency}")
    print(f"   Channels: {', '.join([c.value for c in campaign.channels])}")
    
    # Create use case
    use_case = OptimizeCampaignWithAgentsUseCase(
        campaign_repo=campaign_repo,
        llm_port=llm_port,
        executor_port=executor_port
    )
    
    # Execute optimization
    print(f"\n🚀 Starting campaign optimization...")
    result = await use_case.execute(campaign.id)
    
    # Print results
    print(f"\n✅ Optimization Complete!")
    print(f"Status: {result.status}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")
    if result.data:
        print(f"Result: {json.dumps(result.data, indent=2, ensure_ascii=False)}")


async def example_4_error_handling():
    """Example 4: Error handling and recovery."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Error Handling & Recovery")
    print("="*70)
    
    # Setup with failing LLM
    class FailingLLMPort:
        async def generate(self, prompt: str, **kwargs) -> str:
            raise Exception("LLM service unavailable")
        
        async def embed(self, text: str) -> list:
            raise Exception("Embedding service unavailable")
        
        def count_tokens(self, text: str) -> int:
            return len(text.split())
    
    llm_port = FailingLLMPort()
    
    # Create agents
    analysis_agent = AnalysisAgent(llm_port)
    
    # Create task
    task = Task(
        goal="Analyze campaign",
        context="Test error handling",
        constraints=[],
        expected_output="Analysis results"
    )
    
    # Initialize orchestrator with retry
    orchestrator = SerialAgentOrchestrator(max_retries=3, debug=True)
    
    # Execute
    print(f"\n🚀 Starting with intentional failures...")
    result = await orchestrator.orchestrate(
        agents=[analysis_agent],
        task=task
    )
    
    # Print results
    print(f"\n✅ Orchestration Complete (with errors)!")
    print(f"Status: {result.status}")
    print(f"Error: {result.error}")
    print(f"Error Type: {result.error_type}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")


async def example_5_custom_validation():
    """Example 5: Custom validation rules."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Custom Validation Rules")
    print("="*70)
    
    # Define custom validation rules
    def rule_roi_improvement(task: Task, plan: Optional[Dict]) -> bool:
        """Validate minimum ROI improvement."""
        if plan is None:
            return True
        estimated_improvement = plan.get("estimated_improvement", 0)
        return estimated_improvement >= 20  # At least 20% improvement
    
    def rule_budget_limit(task: Task, plan: Optional[Dict]) -> bool:
        """Validate budget constraints."""
        if plan is None:
            return True
        for action in plan.get("actions", []):
            if action.get("amount", 0) > 10000:
                return False
        return True
    
    # Setup
    llm_port = MockLLMPort()
    executor_port = MockExecutorPort()
    
    validation_rules = {
        "roi_improvement": rule_roi_improvement,
        "budget_limit": rule_budget_limit
    }
    
    # Create agents with custom rules
    analysis_agent = AnalysisAgent(llm_port)
    optimization_agent = OptimizationAgent(llm_port)
    validator_agent = ValidatorAgent(validation_rules)
    executor_agent = ExecutorAgent(executor_port)
    
    # Create task
    task = Task(
        goal="Optimize with strict rules",
        context="Testing custom validation",
        constraints=["roi_improvement >= 20%", "action_amount <= 10000"],
        expected_output="Validated plan"
    )
    
    # Execute
    orchestrator = SerialAgentOrchestrator(debug=True)
    print(f"\n🚀 Starting with custom validation rules...")
    result = await orchestrator.orchestrate(
        agents=[analysis_agent, optimization_agent, validator_agent, executor_agent],
        task=task
    )
    
    print(f"\n✅ Execution Complete!")
    print(f"Status: {result.status}")
    print(f"Validation Passed: {result.data.get('is_valid', False)}")


async def main():
    """Run all examples."""
    print("\n" + "🎯 "*20)
    print("AGENT ORCHESTRATION EXAMPLES")
    print("🎯 "*20)
    
    try:
        # Run examples
        await example_1_basic_orchestration()
        await example_2_parallel_analysis()
        await example_3_complete_use_case()
        await example_4_error_handling()
        await example_5_custom_validation()
        
        print("\n" + "✅ "*20)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("✅ "*20 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
