import asyncio
import os
import sys
import uuid
from pathlib import Path
try:
    from dotenv import load_dotenv
except Exception:
    # Allow running without python-dotenv installed (CI / minimal environments)
    def load_dotenv(*args, **kwargs):
        return None

sys.path.append(str(Path(__file__).parent.parent / "src"))

from adapters.driven.llm.groq_adapter import GroqAdapter
from adapters.driven.approval.auto_approve_adapter import AutoApproveAdapter
from adapters.driven.repositories.campaign_repository import CampaignRepository
from core.domain.agents.campaign_commander import CampaignCommanderAgent
from core.domain.agents.content_architect import ContentArchitectAgent
from core.domain.agents.channel_deployer import ChannelDeployerAgent
from core.domain.agents.analytics_agent import AnalyticsAgent
from core.domain.agents.budget_optimizer_agent import BudgetOptimizerAgent
from core.domain.entities.agent_helper import Task
from core.domain.agents.agent_context import AgentContext
from core.services.export_service import DataExportService


async def main():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip('"')

    # Initialize services
    llm = GroqAdapter(api_key=api_key)
    approval = AutoApproveAdapter()
    repo = CampaignRepository()
    exporter = DataExportService("outputs/ramadan_2026")

    # Campaign data
    campaign_id = f"campaign_{uuid.uuid4().hex[:8]}"
    brief_data = {
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

    # Save campaign to database
    repo.save_campaign(campaign_id, brief_data["name"], brief_data)
    print(f"✅ Campaign saved: {campaign_id}\n")

    # Initialize agents
    commander = CampaignCommanderAgent(llm=llm, approval_port=approval)
    content_architect = ContentArchitectAgent(llm=llm)
    deployer = ChannelDeployerAgent(llm=llm)
    analytics = AnalyticsAgent(llm=llm)
    optimizer = BudgetOptimizerAgent(llm=llm)

    context = AgentContext(workflow_id=campaign_id, task_id="plan-campaign")

    # Execute agents
    agents_results = {}

    # 1. Campaign Commander
    print("🚀 Running Campaign Commander...")
    task = Task(goal="Plan Ramadan Week 1 campaign", context={"brief": brief_data}, constraints=[])
    commander_result = await commander.execute(task, context)
    agents_results["CampaignCommander"] = commander_result
    repo.save_agent_execution(f"exec_{uuid.uuid4().hex[:8]}", campaign_id, "CampaignCommander",
                             str(commander_result.status), commander_result.data, commander_result.execution_time_ms)
    print(f"✅ Commander: {commander_result.status.name}\n")

    # Extract sub-tasks
    sub_tasks = commander_result.data.get("sub_tasks", [])

    # 2. Content Architect
    print("🎨 Running Content Architect...")
    content_task = None
    for sub_task in sub_tasks:
        if sub_task.get("agent") == "ContentArchitect":
            content_task = sub_task
            break

    if content_task:
        task = Task(goal="Generate campaign content", 
                   context={"brief": brief_data, "details": content_task.get("details")},
                   constraints=[])
        content_result = await content_architect.execute(task, context)
        agents_results["ContentArchitect"] = content_result
        repo.save_agent_execution(f"exec_{uuid.uuid4().hex[:8]}", campaign_id, "ContentArchitect",
                                 str(content_result.status), content_result.data, content_result.execution_time_ms)
        print(f"✅ Content Architect: {content_result.status.name}\n")

    # 3. Channel Deployer
    print("📢 Running Channel Deployer...")
    deploy_task = None
    for sub_task in sub_tasks:
        if sub_task.get("agent") == "ChannelDeployer":
            deploy_task = sub_task
            break

    if deploy_task:
        task = Task(goal="Create deployment plan",
                   context={"brief": brief_data, "details": deploy_task.get("details")},
                   constraints=[])
        deployer_result = await deployer.execute(task, context)
        agents_results["ChannelDeployer"] = deployer_result
        repo.save_agent_execution(f"exec_{uuid.uuid4().hex[:8]}", campaign_id, "ChannelDeployer",
                                 str(deployer_result.status), deployer_result.data, deployer_result.execution_time_ms)
        print(f"✅ Channel Deployer: {deployer_result.status.name}\n")

    # 4. Analytics Agent
    print("📊 Running Analytics Agent...")
    task = Task(goal="Analyze campaign performance",
               context={"brief": brief_data, "deployment_data": deployer_result.data if deploy_task else {}},
               constraints=[])
    analytics_result = await analytics.execute(task, context)
    agents_results["AnalyticsAgent"] = analytics_result
    repo.save_agent_execution(f"exec_{uuid.uuid4().hex[:8]}", campaign_id, "AnalyticsAgent",
                             str(analytics_result.status), analytics_result.data, analytics_result.execution_time_ms)
    print(f"✅ Analytics: {analytics_result.status.name}\n")

    # 5. Budget Optimizer Agent
    print("💰 Running Budget Optimizer...")
    task = Task(goal="Optimize budget allocation",
               context={"brief": brief_data, "deployment_plan": deployer_result.data if deploy_task else {}},
               constraints=[])
    optimizer_result = await optimizer.execute(task, context)
    agents_results["BudgetOptimizer"] = optimizer_result
    repo.save_agent_execution(f"exec_{uuid.uuid4().hex[:8]}", campaign_id, "BudgetOptimizer",
                             str(optimizer_result.status), optimizer_result.data, optimizer_result.execution_time_ms)
    print(f"✅ Budget Optimizer: {optimizer_result.status.name}\n")

    # Export results
    print("📁 Exporting campaign report...")
    exported_files = exporter.export_campaign_report(brief_data, agents_results)
    for format_type, filepath in exported_files.items():
        print(f"  ✓ {format_type}: {filepath}")

    # Display summary
    print("\n" + "="*60)
    print("📋 CAMPAIGN EXECUTION SUMMARY")
    print("="*60)
    print(f"Campaign ID: {campaign_id}")
    print(f"Name: {brief_data['name']}")
    print(f"Market: {brief_data['market']}")
    print(f"Budget: {brief_data['total_budget']} {brief_data['currency']}")
    print(f"\nAgent Results:")
    for agent_name, result in agents_results.items():
        print(f"  • {agent_name}: {result.status.name} ({result.execution_time_ms:.0f}ms)")
    print(f"\nDatabase: {repo.db_path}")
    print(f"Exports: {exporter.output_dir}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())