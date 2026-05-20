import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent / "src"))

from adapters.driven.llm.groq_adapter import GroqAdapter
from adapters.driven.approval.auto_approve_adapter import AutoApproveAdapter
from core.domain.agents.campaign_commander import CampaignCommanderAgent
from core.domain.entities.agent_helper import Task
from core.domain.agents.agent_context import AgentContext


async def main():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip('"')

    llm = GroqAdapter(api_key=api_key)
    approval = AutoApproveAdapter()
    commander = CampaignCommanderAgent(llm=llm, approval_port=approval)

    task = Task(
        goal="Plan Ramadan Week 1 campaign",
        context={
            "brief": {
                "name": "Ramadan 2026 - Iftar Essentials",
                "market": "KSA",
                "total_budget": 50000.0,
                "currency": "SAR",
                "channels": ["META", "SNAPCHAT", "WHATSAPP"],
                "target_audience": "Saudi females 25-40 interested in home appliances",
                "start_date": "2026-03-01T00:00:00",
                "end_date": "2026-03-30T00:00:00",
                "objectives": [
                    "Increase sales by 30%",
                    "Grow WhatsApp subscriber list by 5000",
                ],
                "language": "ar",
            }
        },
        constraints=[],
    )

    context = AgentContext(workflow_id="ramadan-2026-w1", task_id="plan-campaign")
    print("Running Campaign Commander...\n")
    result = await commander.execute(task, context)

    print(f"\nStatus: {result.status}")
    print(f"Execution Time: {result.execution_time_ms:.0f}ms")
    print(f"Brief: {result.data.get('brief_name')}")
    print(f"Market: {result.data.get('market')}")
    print(f"Sub-tasks: {result.data.get('sub_tasks_count')}")
    print(f"\nSub-tasks breakdown:")
    for i, t in enumerate(result.data.get("sub_tasks", []), 1):
        agent = t.get("agent", "?")
        action = t.get("action", "?")
        priority = t.get("priority", "?")
        print(f"  {i}. [{priority}] {agent}: {action}")


if __name__ == "__main__":
    asyncio.run(main())
