"""Orchestrated Campaign Optimization Use Case.

This use case demonstrates a complete AI workflow:
1. Analyze campaign data
2. Generate optimization recommendations
3. Validate against business rules
4. Execute the optimizations
"""

from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import logging

from core.domain.agents.orchestrator import SerialAgentOrchestrator, AgentOrchestratorPort
from core.domain.agents.agent_context import AgentContext
from core.domain.agents.agent_result import AgentResult
from core.domain.agents.specialized_agents import (
    AnalysisAgent,
    OptimizationAgent,
    ValidatorAgent,
    ExecutorAgent
)
from core.domain.entities.agent_helper import Task
from core.domain.entities.campaign import Campaign
from core.ports.Campaign_Repository_Port import CampaignRepositoryPort
from core.ports.llm_ports import LLMPort


logger = logging.getLogger(__name__)


class OptimizeCampaignWithAgentsUseCase:
    """
    Use case for orchestrated campaign optimization.
    
    Workflow:
    1. AnalysisAgent: Analyzes campaign performance
    2. OptimizationAgent: Generates optimization plan
    3. ValidatorAgent: Validates against business rules
    4. ExecutorAgent: Executes the optimizations
    """
    
    def __init__(self,
                 campaign_repo: CampaignRepositoryPort,
                 llm_port: LLMPort,
                 executor_port: Any,
                 orchestrator: Optional[AgentOrchestratorPort] = None,
                 validation_rules: Optional[Dict[str, Callable]] = None):
        """
        Initialize use case.
        
        Args:
            campaign_repo: Campaign repository
            llm_port: LLM port for agents
            executor_port: Port for executing actions
            orchestrator: Agent orchestrator (creates default if None)
            validation_rules: Custom validation rules
        """
        self.campaign_repo = campaign_repo
        self.llm_port = llm_port
        self.executor_port = executor_port
        self.orchestrator = orchestrator or SerialAgentOrchestrator(debug=True)
        self.validation_rules = validation_rules or self._default_validation_rules()
    
    async def execute(self, campaign_id: str) -> AgentResult:
        """
        Execute orchestrated campaign optimization.
        
        Args:
            campaign_id: ID of campaign to optimize
            
        Returns:
            Final AgentResult with optimization outcomes
        """
        # Fetch campaign
        campaign = await self.campaign_repo.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # Create task for agents
        task = self._create_optimization_task(campaign)
        
        # Create context for agent communication
        context = self._create_agent_context(campaign)
        
        # Build agent pipeline
        agents = self._build_agent_pipeline()
        
        # Execute orchestration
        logger.info(f"Starting orchestrated optimization for campaign {campaign_id}")
        
        try:
            final_result = await self.orchestrator.orchestrate(
                agents=agents,
                task=task,
                context=context
            )
            
            # Persist results
            await self._persist_optimization_results(campaign, context)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Orchestration failed: {str(e)}")
            raise
    
    async def execute_parallel_analysis(self, 
                                       campaigns: List[Campaign]) -> Dict[str, AgentResult]:
        """
        Execute analysis agents in parallel on multiple campaigns.
        
        Args:
            campaigns: List of campaigns to analyze
            
        Returns:
            Dictionary mapping campaign IDs to analysis results
        """
        # Create analysis agents
        analysis_agents = [
            AnalysisAgent(self.llm_port) for _ in campaigns
        ]
        
        # Create task
        task = Task(
            goal="Analyze campaign performance",
            context="Parallel analysis of multiple campaigns",
            constraints="Complete within timeout",
            expected_output="Analysis results for each campaign"
        )
        
        # Execute in parallel
        results = await self.orchestrator.orchestrate_parallel(
            agents=analysis_agents,
            task=task
        )
        
        return results
    
    # ============== Private Methods ==============
    
    def _create_optimization_task(self, campaign: Campaign) -> Task:
        """Create optimization task from campaign."""
        return Task(
            goal=f"Optimize campaign '{campaign.name}' for maximum ROI",
            context={
                "name": campaign.name,
                "market": campaign.market if isinstance(campaign.market, str) else campaign.market.value,
                "channels": [c if isinstance(c, str) else c.value for c in campaign.channels],
                "total_budget": campaign.total_budget,
                "current_spend": campaign.total_spend,
                "currency": campaign.currency,
                "status": campaign.status.value if hasattr(campaign.status, 'value') else str(campaign.status)
            },
            constraints=[
                f"budget_limit: {campaign.total_budget} {campaign.currency}",
                f"approved_channels: {', '.join([c if isinstance(c, str) else c.value for c in campaign.channels])}",
                f"target_audience: {', '.join(campaign.target_audiences)}",
                f"languages: {', '.join(campaign.languages)}"
            ],
            expected_output="JSON with optimization plan including actions and expected ROI improvement"
        )
    
    def _create_agent_context(self, campaign: Campaign) -> AgentContext:
        """Create context with campaign data."""
        context = AgentContext(
            workflow_id=f"optimize_{campaign.id}_{datetime.now().timestamp()}",
            task_id=f"task_{campaign.id}",
            campaign_id=campaign.id,
            market=campaign.market if isinstance(campaign.market, str) else campaign.market.value
        )
        
        # Add campaign data to context
        context.set_data("campaign", campaign.model_dump())
        context.set_data("current_spend", campaign.total_spend)
        context.set_data("total_budget", campaign.total_budget)
        context.set_data("channels", [c if isinstance(c, str) else c.value for c in campaign.channels])
        
        return context
    
    def _build_agent_pipeline(self) -> List[Any]:
        """Build the agent pipeline."""
        return [
            AnalysisAgent(self.llm_port),
            OptimizationAgent(self.llm_port),
            ValidatorAgent(self.validation_rules),
            ExecutorAgent(self.executor_port)
        ]
    
    def _default_validation_rules(self) -> Dict[str, Callable]:
        """Default validation rules."""
        return {
            "budget_constraint": lambda task, plan: plan is None or 
                                 plan.get("estimated_improvement", 0) >= 0,
            "market_compliance": lambda task, plan: "market" in task.context or plan is not None,
            "channel_coverage": lambda task, plan: plan is None or 
                               len(plan.get("actions", [])) > 0
        }
    
    async def _persist_optimization_results(self, 
                                           campaign: Campaign,
                                           context: AgentContext) -> None:
        """Persist optimization results."""
        optimization_plan = context.get_data("optimization_plan")
        execution_results = context.get_data("execution_results")
        
        if optimization_plan:
            logger.info(f"Optimization plan for {campaign.id}: {optimization_plan}")
        
        if execution_results:
            logger.info(f"Execution results for {campaign.id}: {execution_results}")
        
        # Here you would typically save to database
        # For now, we're just logging


class CampaignOptimizationPipeline:
    """
    High-level API for campaign optimization orchestration.
    Simplifies multi-agent workflow execution.
    """
    
    def __init__(self, 
                 use_case: OptimizeCampaignWithAgentsUseCase):
        """Initialize pipeline with use case."""
        self.use_case = use_case
    
    async def optimize_single_campaign(self, campaign_id: str) -> AgentResult:
        """Optimize a single campaign."""
        return await self.use_case.execute(campaign_id)
    
    async def optimize_campaigns_in_parallel(self, 
                                            campaigns: List[Campaign]) -> Dict[str, AgentResult]:
        """Analyze multiple campaigns in parallel."""
        return await self.use_case.execute_parallel_analysis(campaigns)
    
    async def optimize_batch(self, 
                            campaign_ids: List[str]) -> List[AgentResult]:
        """
        Optimize a batch of campaigns sequentially.
        
        Args:
            campaign_ids: List of campaign IDs
            
        Returns:
            List of optimization results
        """
        results = []
        for campaign_id in campaign_ids:
            try:
                result = await self.use_case.execute(campaign_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to optimize campaign {campaign_id}: {str(e)}")
                results.append(None)
        
        return results
