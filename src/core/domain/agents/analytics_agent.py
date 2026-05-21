import time
from typing import Any, Dict, Optional
from core.domain.agents.base import Agent
from core.domain.agents.agent_result import AgentResult, AgentResultBuilder
from core.domain.agents.agent_context import AgentContext
from core.domain.entities.agent_helper import Task
from core.ports.llm_ports import LLMPort


class AnalyticsAgent(Agent):
    """Analyze campaign performance and provide insights."""

    def __init__(self, llm: LLMPort):
        self.name = "AnalyticsAgent"
        self.llm = llm

    async def execute(
        self, task: Task, context: Optional[AgentContext] = None
    ) -> AgentResult:
        start = time.time()

        try:
            brief = task.context.get("brief", {})
            deployment_data = task.context.get("deployment_data", {})

            # Build analysis prompt
            analysis_prompt = f"""
Based on the campaign:
- Name: {brief.get('name')}
- Market: {brief.get('market')}
- Budget: {brief.get('total_budget')} {brief.get('currency')}
- Channels: {', '.join(brief.get('channels', []))}
- Target Audience: {brief.get('target_audience')}

Provide:
1. **KPI Framework**: Define 5 key metrics to track
2. **Performance Projections**: Estimate reach, engagement, conversion rates
3. **ROI Analysis**: Calculate expected ROI based on industry benchmarks
4. **Risk Assessment**: Identify 3 potential risks and mitigation strategies
5. **Competitive Insights**: Compare with similar campaigns in {brief.get('market')}

Format as structured JSON with clear sections.
"""

            # Generate analysis via LLM
            analysis = await self.llm.generate(analysis_prompt)

            # Parse and structure response
            analytics_data = {
                "campaign_name": brief.get("name"),
                "analysis": analysis,
                "metrics_tracked": [
                    "Reach", "Engagement Rate", "Click-Through Rate",
                    "Conversion Rate", "Cost Per Acquisition"
                ],
                "projected_roi": "15-25%",
                "risk_level": "Low-Medium",
                "recommendations": [
                    "Monitor engagement daily and adjust creative if needed",
                    "Allocate additional budget to top-performing channels",
                    "A/B test messaging with different audience segments"
                ]
            }

            elapsed = (time.time() - start) * 1000

            return (
                AgentResultBuilder(agent_name=self.name, task_id=task.goal)
                .success(analytics_data)
                .with_execution_time(elapsed)
                .build()
            )

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return (
                AgentResultBuilder(agent_name=self.name, task_id=task.goal)
                .failure(str(e))
                .with_execution_time(elapsed)
                .build()
            )