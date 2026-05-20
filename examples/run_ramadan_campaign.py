import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent / "src"))

from adapters.driven.llm.groq_adapter import GroqAdapter
from adapters.driven.approval.auto_approve_adapter import AutoApproveAdapter
from core.domain.agents.campaign_commander import CampaignCommanderAgent
from core.domain.agents.content_architect import ContentArchitectAgent
from core.domain.entities.agent_helper import Task
from core.domain.agents.agent_context import AgentContext


async def main():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip('"')

    llm = GroqAdapter(api_key=api_key)
    approval = AutoApproveAdapter()

    commander = CampaignCommanderAgent(llm=llm, approval_port=approval)
    content_architect = ContentArchitectAgent(llm=llm)

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
                    "Grow WhatsApp subscriber list by 5000"
                ],
                "language": "ar",
            }
        },
        constraints=[],
    )

    context = AgentContext(workflow_id="ramadan-2026-w1", task_id="plan-campaign")

    print("Running Campaign Commander...")
    commander_result = await commander.execute(task, context)

    print("\nCommander Result:", commander_result.status)
    print("Sub-tasks count:", commander_result.data.get("sub_tasks_count"))

    sub_tasks = commander_result.data.get("sub_tasks", [])
    first_content_task = None
    for sub_task in sub_tasks:
        if sub_task.get("agent") == "ContentArchitect":
            first_content_task = sub_task
            break

    if not first_content_task:
        print("No ContentArchitect task found.")
        return

    content_task = Task(
        goal="Generate Ramadan campaign content",
        context={
            "brief": task.context["brief"],
            "details": first_content_task.get("details", "Create core campaign content")
        },
        constraints=[],
    )

    print("\nRunning Content Architect...")
    content_result = await content_architect.execute(content_task, context)

    print("\nContent Architect Result:", content_result.status)
    print("Generated content:")
    print(content_result.data.get("content"))


if __name__ == "__main__":
    asyncio.run(main())