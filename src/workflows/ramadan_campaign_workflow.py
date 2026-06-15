"""
Ramadan Campaign Workflow - End-to-end example of campaign orchestration.

This demonstrates:
1. Creating a campaign with products
2. Campaign Commander decomposing the campaign
3. Content Architect generating multilingual content
4. Simulating deployment and analytics
"""

from typing import Dict, Any
from datetime import datetime

from src.core.abstractions import Message, MessageType
from src.domain.campaign import (
    Campaign, Product, Channel, Country, Currency,
    CampaignMetrics,
)
from src.agents.campaign_commander import CampaignCommanderAgent
from src.agents.content_architect import ContentArchitectAgent


async def create_sample_campaign() -> Campaign:
    """Create a sample Ramadan campaign."""
    
    # Create products
    products = [
        Product(
            name_ar="سامسونج جالاكسي S25 الترا",
            name_en="Samsung Galaxy S25 Ultra",
            description_ar="أحدث هاتف ذكي مع كاميرا 200 ميجابكسل وتصميم تيتانيوم فاخر",
            description_en="Latest flagship with 200MP camera and premium titanium design",
            category="smartphones",
            price_sar=4999,
            price_egp=65000,
            image_url="https://example.com/s25ultra.jpg",
        ),
        Product(
            name_ar="سماعات سوني WH-1000XM5",
            name_en="Sony WH-1000XM5 Headphones",
            description_ar="سماعات فاخرة مع إلغاء ضجيج متقدم وبطارية 30 ساعة",
            description_en="Premium headphones with advanced noise cancellation, 30hr battery",
            category="audio",
            price_sar=1299,
            price_egp=12000,
            image_url="https://example.com/sony-xm5.jpg",
        ),
    ]
    
    # Create campaign
    campaign = Campaign(
        name="Ramadan Flash Sale 2026",
        company_name="TechStore MENA",
        description="Big savings on latest tech during Ramadan",
        start_date=datetime(2026, 2, 1),
        end_date=datetime(2026, 3, 1),
        target_countries=[Country.SAUDI_ARABIA, Country.EGYPT],
        objectives=[
            "Drive online sales",
            "Increase brand awareness",
            "Build customer loyalty",
        ],
        created_by="ramadan_campaign_system",
    )
    
    # Add products
    for product in products:
        campaign.add_product(product)
    
    # Add channel budgets
    campaign.add_channel_budget(Channel.META_FACEBOOK, 5000)
    campaign.add_channel_budget(Channel.GOOGLE_SEARCH, 3000)
    campaign.add_channel_budget(Channel.WHATSAPP, 1000)
    campaign.add_channel_budget(Channel.EMAIL, 500)
    
    return campaign


async def run_ramadan_campaign_workflow() -> Dict[str, Any]:
    """
    Execute the complete Ramadan campaign workflow.
    
    Flow:
    1. Create campaign
    2. Campaign Commander processes it → decompose into tasks
    3. Content Architect generates multilingual content
    4. (In real flow) Channel Deployer pushes to ads platforms
    5. (In real flow) Analytics Engine monitors performance
    """
    
    print("\n" + "="*70)
    print("🌙 RAMADAN CAMPAIGN WORKFLOW - STARTING")
    print("="*70)
    
    # Step 1: Create sample campaign
    print("\n[Step 1] Creating sample campaign...")
    campaign = await create_sample_campaign()
    print(f"  ✓ Campaign: {campaign.name}")
    print(f"  ✓ Products: {len(campaign.products)}")
    print(f"  ✓ Target countries: {len(campaign.target_countries)}")
    print(f"  ✓ Total budget: ${campaign.total_budget_usd}")
    
    # Step 2: Initialize agents
    print("\n[Step 2] Initializing agents...")
    commander = CampaignCommanderAgent(agent_id="commander_001")
    content_architect = ContentArchitectAgent(agent_id="architect_001")
    print(f"  ✓ {commander.capabilities.name} initialized")
    print(f"  ✓ {content_architect.capabilities.name} initialized")
    
    # Step 3: Send campaign to Commander
    print("\n[Step 3] Campaign Commander analyzing campaign...")
    
    campaign_dict = {
        "campaign_id": campaign.campaign_id,
        "name": campaign.name,
        "products": [
            {
                "product_id": p.product_id,
                "name_ar": p.name_ar,
                "name_en": p.name_en,
                "price_sar": p.price_sar,
                "price_egp": p.price_egp,
            }
            for p in campaign.products
        ],
        "target_countries": [c.value for c in campaign.target_countries],
        "channel_budgets": [
            {
                "channel": b.channel.value,
                "budget_usd": b.budget_usd,
            }
            for b in campaign.channel_budgets
        ],
    }
    
    commander_request = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="system",
        recipient_id=commander.agent_id,
        content={"campaign": campaign_dict},
    )
    
    commander_response = await commander.process_message(commander_request)
    commander_output = commander_response.content
    
    print(f"  ✓ Campaign decomposed into {commander_output.get('tasks_created')} tasks")
    tasks = commander_output.get("tasks", [])
    for i, task in enumerate(tasks, 1):
        print(f"    • Task {i}: {task.get('type')} - {task.get('description')}")
    
    # Step 4: Send content creation task to Architect
    print("\n[Step 4] Content Architect generating multilingual content...")
    
    content_request = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id=commander.agent_id,
        recipient_id=content_architect.agent_id,
        content={
            "products": [
                {
                    "product_id": p.product_id,
                    "name_ar": p.name_ar,
                    "name_en": p.name_en,
                    "description_ar": p.description_ar,
                    "description_en": p.description_en,
                }
                for p in campaign.products
            ],
            "languages": ["ar", "en"],
            "content_types": ["ad_copy", "product_description"],
            "tone": "professional",
            "brand_guidelines": {
                "brand_voice": "friendly and trustworthy",
                "target_audience": "tech enthusiasts in MENA",
            },
        },
    )
    
    architect_response = await content_architect.process_message(content_request)
    architect_output = architect_response.content
    
    print(f"  ✓ Generated content for {architect_output.get('products_processed')} products")
    print(f"  ✓ Total content items created: {architect_output.get('content_items')}")
    
    # Display sample content
    generated_content = architect_output.get("generated_content", {})
    for product_id, content_items in generated_content.items():
        if content_items:
            first_item = content_items[0]
            print(f"\n    Sample content (Product {product_id[:8]}...):")
            print(f"    Language: {first_item.get('language').upper()}")
            print(f"    Content: {first_item.get('content')[:100]}...")
            break
    
    # Step 5: Simulate analytics update
    print("\n[Step 5] Simulating analytics update and budget optimization...")
    
    # Mock channel metrics
    channel_metrics = {
        "meta_facebook": {
            "impressions": 50000,
            "clicks": 2500,
            "conversions": 125,
            "spend": 1000,
            "revenue": 5000,
            "roas": 5.0,
        },
        "google_search": {
            "impressions": 30000,
            "clicks": 1500,
            "conversions": 75,
            "spend": 800,
            "revenue": 2400,
            "roas": 3.0,
        },
        "whatsapp": {
            "impressions": 10000,
            "clicks": 300,
            "conversions": 10,
            "spend": 200,
            "revenue": 400,
            "roas": 2.0,
        },
    }
    
    analytics_update = Message(
        message_type=MessageType.STATE_UPDATE,
        sender_id="analytics_engine",
        recipient_id=commander.agent_id,
        content={
            "event_type": "performance_update",
            "channel_metrics": channel_metrics,
            "timestamp": datetime.now().isoformat(),
        },
    )
    
    budget_response = await commander.process_message(analytics_update)
    budget_output = budget_response.content
    
    print(f"  ✓ Status: {budget_output.get('status')}")
    
    if budget_output.get("action") == "budget_reallocation":
        recommendations = budget_output.get("recommendations", [])
        print(f"  ✓ Budget optimization recommendations:")
        for rec in recommendations:
            action = rec.get("action").upper()
            amount = rec.get("amount")
            reason = rec.get("reason")
            channel = rec.get("channel")
            print(f"    • {action} ${amount} to {channel} ({reason})")
    
    # Step 6: Summary
    print("\n" + "="*70)
    print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
    print("="*70)
    
    summary = {
        "campaign_name": campaign.name,
        "campaign_id": campaign.campaign_id,
        "products_processed": len(campaign.products),
        "tasks_created": commander_output.get("tasks_created", 0),
        "content_items_generated": architect_output.get("content_items", 0),
        "channel_performance": {
            "best_roas": max((m.get("roas", 0) for m in channel_metrics.values()), default=0),
            "channels_analyzed": len(channel_metrics),
        },
        "agents_used": [
            commander.capabilities.name,
            content_architect.capabilities.name,
        ],
        "workflow_status": "success",
        "timestamp": datetime.now().isoformat(),
    }
    
    print(f"\n📊 Campaign Summary:")
    print(f"  • Campaign: {summary['campaign_name']}")
    print(f"  • Products: {summary['products_processed']}")
    print(f"  • Tasks decomposed: {summary['tasks_created']}")
    print(f"  • Content generated: {summary['content_items_generated']} items")
    print(f"  • Best channel ROAS: {summary['channel_performance']['best_roas']:.1f}x")
    print(f"  • Status: {summary['workflow_status'].upper()}")
    print()
    
    return summary


if __name__ == "__main__":
    import asyncio
    import json
    
    result = asyncio.run(run_ramadan_campaign_workflow())
    print("\n📋 Workflow Output (JSON):")
    print(json.dumps(result, indent=2, default=str))
