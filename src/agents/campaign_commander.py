"""
Campaign Commander Agent - The orchestrator of Ramadan campaigns.

This agent is responsible for:
1. Receiving a campaign specification
2. Decomposing it into sub-tasks (content creation, deployment, analytics)
3. Delegating to other agents
4. Monitoring overall progress
5. Making strategic decisions (e.g., budget reallocation)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.core.abstractions import (
    Agent, AgentCapabilities, AgentRole, AgentState,
    Message, MessageType,
    Tool, ToolExecutionResult, ToolParameter, ToolCategory,
)
from src.domain.campaign import Campaign, Channel, ChannelBudget


class CampaignDecompositionTool(Tool):
    """
    Tool to break down a campaign into subtasks.
    
    Output:
    {
        "tasks": [
            {"type": "create_content", "products": [...], "channels": [...]},
            {"type": "deploy_campaign", "channel": "meta_facebook", "budget": 1000},
            {"type": "monitor_analytics", "interval_minutes": 30},
        ]
    }
    """
    
    def __init__(self):
        super().__init__(
            name="campaign_decomposition",
            description="Break down a campaign into executable subtasks",
            category=ToolCategory.CODE_EXECUTION,
            parameters=[
                ToolParameter(
                    name="campaign_json",
                    type="dict",
                    description="Campaign object as dict",
                    required=True,
                )
            ],
        )
    
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        """Break down campaign into tasks."""
        try:
            campaign_data = kwargs.get("campaign_json", {})
            
            tasks = []
            
            # Task 1: Content Creation
            tasks.append({
                "type": "create_content",
                "description": f"Create bilingual content for {len(campaign_data.get('products', []))} products",
                "products": campaign_data.get("products", []),
                "target_audience": campaign_data.get("target_countries", []),
                "languages": ["ar", "en"],
            })
            
            # Task 2: Deploy to each channel
            for channel_budget in campaign_data.get("channel_budgets", []):
                tasks.append({
                    "type": "deploy_campaign",
                    "description": f"Deploy to {channel_budget.get('channel')}",
                    "channel": channel_budget.get("channel"),
                    "budget": channel_budget.get("budget_usd"),
                })
            
            # Task 3: Monitor analytics
            tasks.append({
                "type": "monitor_analytics",
                "description": "Monitor campaign performance and optimize",
                "interval_minutes": 30,
                "kpis_to_track": ["impressions", "clicks", "conversions", "roas"],
            })
            
            return ToolExecutionResult(
                success=True,
                data={
                    "tasks": tasks,
                    "total_tasks": len(tasks),
                    "estimated_duration_hours": 24,
                },
            )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=str(e),
            )


class BudgetOptimizationTool(Tool):
    """
    Tool to recommend budget reallocation based on performance.
    
    Input:
    {
        "current_budgets": {...},
        "channel_performance": {...}
    }
    
    Output:
    {
        "recommendations": [
            {"channel": "meta_facebook", "action": "increase", "amount": 500, "reason": "High ROAS"},
            {"channel": "snapchat", "action": "decrease", "amount": 200, "reason": "Low ROAS"},
        ]
    }
    """
    
    def __init__(self):
        super().__init__(
            name="budget_optimization",
            description="Recommend budget reallocation based on channel performance",
            category=ToolCategory.CODE_EXECUTION,
            parameters=[
                ToolParameter(
                    name="channel_metrics",
                    type="dict",
                    description="Performance metrics per channel",
                    required=True,
                ),
            ],
        )
    
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        """Generate budget optimization recommendations."""
        try:
            metrics = kwargs.get("channel_metrics", {})
            
            recommendations = []
            
            # Simple heuristic: ROAS-based optimization
            best_roas = 0
            worst_roas = float('inf')
            best_channel = None
            worst_channel = None
            
            for channel, performance in metrics.items():
                roas = performance.get("roas", 0)
                if roas > best_roas:
                    best_roas = roas
                    best_channel = channel
                if roas < worst_roas and roas > 0:
                    worst_roas = roas
                    worst_channel = channel
            
            # Recommend shifting budget from worst to best
            if best_channel and worst_channel and worst_roas > 0:
                # 5% shift
                shift_amount = 100  # Example
                
                recommendations.append({
                    "channel": best_channel,
                    "action": "increase",
                    "amount": shift_amount,
                    "reason": f"High ROAS ({best_roas:.1f})",
                })
                
                recommendations.append({
                    "channel": worst_channel,
                    "action": "decrease",
                    "amount": shift_amount,
                    "reason": f"Low ROAS ({worst_roas:.1f})",
                })
            
            return ToolExecutionResult(
                success=True,
                data={
                    "recommendations": recommendations,
                    "needs_approval": True if recommendations else False,
                },
            )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=str(e),
            )


class CampaignCommanderAgent(Agent):
    """
    Campaign Commander - The orchestrator agent.
    
    Responsibilities:
    1. Understand the campaign requirements
    2. Break down into sub-tasks
    3. Delegate to specialized agents
    4. Monitor overall progress
    5. Make tactical decisions
    """
    
    def __init__(self, agent_id: str = "campaign_commander"):
        capabilities = AgentCapabilities(
            name="Campaign Commander",
            description="Orchestrates multi-channel Ramadan campaigns",
            role=AgentRole.ORCHESTRATOR,
            tools={"campaign_decomposition", "budget_optimization"},
            max_iterations=10,
            timeout_seconds=600,
        )
        
        tools = {
            "campaign_decomposition": CampaignDecompositionTool(),
            "budget_optimization": BudgetOptimizationTool(),
        }
        
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities,
            allowed_tools=tools,
        )
        
        # Campaign memory
        self._current_campaign: Optional[Campaign] = None
        self._task_queue: List[Dict[str, Any]] = []
        self._delegations_sent: Dict[str, Message] = {}
        self._responses_received: Dict[str, Message] = {}
    
    async def process_message(self, message: Message) -> Message:
        """
        Main decision loop for the Campaign Commander.
        
        Handles:
        - TASK_REQUEST: New campaign to orchestrate
        - TASK_RESPONSE: Responses from delegated agents
        - STATE_UPDATE: Updates from analytics or monitoring
        """
        self._set_state(AgentState.THINKING)
        
        try:
            message_type = message.message_type
            content = message.content
            
            if message_type == MessageType.TASK_REQUEST:
                return await self._handle_new_campaign(message)
            
            elif message_type == MessageType.TASK_RESPONSE:
                return await self._handle_agent_response(message)
            
            elif message_type == MessageType.STATE_UPDATE:
                return await self._handle_state_update(message)
            
            else:
                return message.create_response(
                    response_type=MessageType.ERROR,
                    sender_id=self.agent_id,
                    content={"error": f"Unknown message type: {message_type}"},
                )
        
        except Exception as e:
            self._set_state(AgentState.ERROR)
            return message.create_response(
                response_type=MessageType.ERROR,
                sender_id=self.agent_id,
                content={"error": str(e)},
            )
    
    async def _handle_new_campaign(self, message: Message) -> Message:
        """Handle a new campaign request."""
        content = message.content
        
        # Extract campaign data
        campaign_data = content.get("campaign")
        if not campaign_data:
            return message.create_response(
                response_type=MessageType.ERROR,
                sender_id=self.agent_id,
                content={"error": "No campaign data provided"},
            )
        
        # Store campaign
        self._current_campaign = campaign_data
        
        # Decompose into tasks
        decomposition_result = await self.execute_tool(
            "campaign_decomposition",
            campaign_json=campaign_data,
        )
        
        if not decomposition_result.success:
            return message.create_response(
                response_type=MessageType.ERROR,
                sender_id=self.agent_id,
                content={"error": f"Decomposition failed: {decomposition_result.error}"},
            )
        
        # Store tasks in queue
        self._task_queue = decomposition_result.data.get("tasks", [])
        
        # Return confirmation with task list
        response = message.create_response(
            response_type=MessageType.TASK_RESPONSE,
            sender_id=self.agent_id,
            content={
                "campaign_id": self._current_campaign.get("campaign_id"),
                "campaign_name": self._current_campaign.get("name"),
                "tasks_created": decomposition_result.data.get("total_tasks"),
                "tasks": self._task_queue,
                "status": "campaign_decomposed",
                "next_step": "Waiting for agent delegations",
            },
        )
        
        self._set_state(AgentState.COMPLETED)
        return response
    
    async def _handle_agent_response(self, message: Message) -> Message:
        """Handle response from a delegated agent."""
        content = message.content
        sender = message.sender_id
        
        # Record response
        self._responses_received[sender] = message
        
        # Simple aggregation: if we have responses from key agents, mark progress
        response = message.create_response(
            response_type=MessageType.STATE_UPDATE,
            sender_id=self.agent_id,
            content={
                "status": "response_received",
                "from_agent": sender,
                "responses_count": len(self._responses_received),
                "acknowledged": True,
            },
        )
        
        self._set_state(AgentState.COMPLETED)
        return response
    
    async def _handle_state_update(self, message: Message) -> Message:
        """Handle state update from monitoring agents."""
        content = message.content
        event_type = content.get("event_type")
        
        # If we have performance metrics, optimize budget
        if event_type == "performance_update" and "channel_metrics" in content:
            optimization_result = await self.execute_tool(
                "budget_optimization",
                channel_metrics=content.get("channel_metrics"),
            )
            
            if optimization_result.success and optimization_result.data.get("recommendations"):
                # Create approval gate for budget reallocation
                response = message.create_response(
                    response_type=MessageType.APPROVAL_REQUEST,
                    sender_id=self.agent_id,
                    content={
                        "action": "budget_reallocation",
                        "recommendations": optimization_result.data.get("recommendations"),
                        "requires_approval_from": ["marketing_manager"],
                    },
                )
                self._set_state(AgentState.WAITING_FOR_APPROVAL)
                return response
        
        # Default response
        return message.create_response(
            response_type=MessageType.TASK_RESPONSE,
            sender_id=self.agent_id,
            content={
                "status": "state_update_processed",
                "event_type": event_type,
            },
        )
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolExecutionResult:
        """Execute a tool."""
        self._set_state(AgentState.EXECUTING)
        
        if tool_name not in self.allowed_tools:
            return ToolExecutionResult(
                success=False,
                error=f"Tool {tool_name} not available",
            )
        
        tool = self.allowed_tools[tool_name]
        return await tool.execute(agent_id=self.agent_id, **kwargs)
    
    def get_memory_context(self, context_type: str = "short_term") -> Dict[str, Any]:
        """Get agent memory."""
        return {
            "current_campaign": self._current_campaign,
            "task_queue_length": len(self._task_queue),
            "delegations_sent": len(self._delegations_sent),
            "responses_received": len(self._responses_received),
        }
    
    def update_memory(self, key: str, value: Any, context_type: str = "short_term") -> None:
        """Update memory (placeholder)."""
        pass
