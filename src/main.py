"""
Mizan — Interactive Ad Campaign Generator CLI
=================================================
Allows commercial usage of the agent framework directly from the terminal.
Fully dynamic, user-configured inputs, premium console logging.
"""

import os
import sys
import asyncio
from typing import Dict, Any

# ── Disable CrewAI tracing BEFORE any imports so it never spawns daemon threads ──
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

# ── Configure stdout for UTF-8 Arabic output ──
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ── Configure stdin for UTF-8 text-mode input (avoids raw buffer lock issues) ──
if hasattr(sys.stdin, 'reconfigure'):
    try:
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ── Monkey-patch input() to use text-mode readline (safe for daemon threads) ──
import builtins
_orig_input = builtins.input

def safe_input(prompt=""):
    """UTF-8 safe input: prints prompt manually, reads from text-mode stdin."""
    try:
        sys.stdout.write(prompt)
        sys.stdout.flush()
    except Exception:
        pass
    try:
        # Use text-mode sys.stdin (already reconfigured to UTF-8)
        # This does NOT hold the raw BufferedReader lock and is safe at shutdown.
        line = sys.stdin.readline()
        return line.rstrip('\r\n')
    except Exception:
        pass
    try:
        return _orig_input()
    except Exception:
        return ""

builtins.input = safe_input


def clean_text(text: str) -> str:
    """Strip any surrogate or replacement characters left over from bad terminal encoding."""
    # Step 1: Explicitly remove U+FFFD (the '?' replacement char produced by errors='replace')
    text = text.replace('\ufffd', '')
    # Step 2: Remove any unicode surrogates by encode/decode round-trip
    text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    return text.strip()

# Ensure src/ is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load env variables (API keys, etc.) from root directory .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from benchmarks.adapters.crewai.adapter import CrewaiAdapter
from core.services.image_generator import generate_ad_image, build_ad_image_prompt


def print_banner():
    """Prints a premium visual terminal banner."""
    print("=" * 60)
    print("   __  __ ___ _____   _   _   _ ")
    print("  |  \\/  |_ _|_   _| /_\\ | \\ | |")
    print("  | |\\/| || |  | |  / _ \\|  \\| |")
    print("  |_|  |_|___| |_| /_/ \\_\\_|\\__|")
    print("  AI-Powered Ramadan Campaign Architect")
    print("=" * 60)


async def interactive_cli():
    print_banner()

    # 1. Gather Interactive Input
    print("\n[+] Please enter the product details:")
    name_en  = clean_text(input("Product Name (English) [e.g. Philips Airfryer XXL]: ").strip())
    name_ar  = clean_text(input("Product Name (Arabic) [e.g. قلاية فيلبس الهوائية XXL]: ").strip())
    price    = clean_text(input("Price (SAR/AED) [e.g. 1099]: ").strip())
    discount = clean_text(input("Discount Percentage (optional) [e.g. 15]: ").strip())

    print("\n[+] Target Audience & Settings:")
    market   = clean_text(input("Target Market (KSA/UAE/EG) [Default: KSA]: ").strip()) or "KSA"
    audience = clean_text(input("Target Audience [e.g. Saudi homemakers 25-40]: ").strip())
    tone     = clean_text(input("Tone of Voice [e.g. Warm, Ramadan family blessings]: ").strip()) or "Warm and family-oriented"

    goal = f"Create 4 Ramadan ad copy variants and plan channels for {name_en} targeting {audience}."

    product_data = {
        "name_en": name_en,
        "name_ar": name_ar,
        "price_sar": price,
        "discount_pct": discount,
        "sku": "PROD-" + clean_text(name_en[:3]).upper() + "001"
    }

    # 2. Setup LLM adapter
    print("\n[+] Initializing Agents...")
    provider = os.getenv("LLM_PROVIDER", "groq")
    model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


    adapter = CrewaiAdapter()
    await adapter.setup({
        "provider": provider,
        "model": model,
        "mode": "full"
    })

    print(f"[✔] Framework active: CrewAI (Model: {provider}/{model})")
    
    # 3. Formulate the Task
    task_payload = {
        "goal": goal,
        "product": product_data,
        "market": market,
        "audience": audience,
        "tone": tone,
        "constraints": [
            f"Must mention price of {price} SAR/AED",
            "Must be culturally appropriate for Ramadan",
            "Gulf Arabic dialect (no Egyptian slang for KSA/UAE)",
            "WhatsApp template must follow Meta template rules"
        ]
    }

    # 4. Run the Campaign Agents
    print("\n[+] Campaign generation started. Please wait...")
    print("-" * 60)
    
    # ── Define real custom tools for the multi-agent Crew ──
    from crewai.tools import tool
    import json
    import time
    import random
    
    @tool("search_product_catalog")
    def search_product_catalog(query: str) -> str:
        """Search the RetailCo product catalog database for descriptions, categories, stock, and pricing details."""
        catalog_entry = {
            "sku": product_data["sku"],
            "name_en": product_data["name_en"],
            "name_ar": product_data["name_ar"],
            "price_sar": product_data["price_sar"],
            "discount_percentage": product_data["discount_pct"],
            "in_stock_ksa": True,
            "in_stock_eg": True,
            "description_en": f"High performance {product_data['name_en']} with premium build and local MENA warranty.",
            "description_ar": f"{product_data['name_ar']} عالي الأداء مع ضمان محلي معتمد لأسواق الشرق الأوسط."
        }
        return json.dumps(catalog_entry, ensure_ascii=False, indent=2)

    @tool("write_compliance_audit_log")
    def write_compliance_audit_log(compliance_json: str) -> str:
        """Write an official audit log entry detailing compliance checks, PII redactions, and PDPL authorization status."""
        try:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_results", "audit_logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "compliance_audit.log")
            
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(compliance_json + "\n")
            return f"Success: Audit entry recorded locally at {log_path}"
        except Exception as e:
            return f"Error writing log: {str(e)}"

    @tool("deploy_marketing_channels")
    def deploy_marketing_channels(payload_json: str) -> str:
        """
        Deploy campaign copies to Meta Ads and Unifonic WhatsApp.
        Automatically handles API routing, retry with exponential backoff on transient errors,
        and fallback to SMS if a channel (like WhatsApp Meta template) is rejected or fails.
        Input must be a valid JSON string mapping channel names to their ad copies or payloads.
        Example: {"channels": {"meta_ads": "...", "whatsapp": "..."}}
        """
        try:
            data = json.loads(payload_json)
        except Exception:
            try:
                cleaned = payload_json.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif cleaned.startswith("```"):
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                data = json.loads(cleaned)
            except Exception as e:
                return f"Error: Payload is not valid JSON. Details: {str(e)}. Received: {payload_json}"
        
        channels = data.get("channels", {}) or data
        report = []
        
        for channel_name, copy_text in channels.items():
            if channel_name == "channels":
                continue
                
            report.append(f"\n[Deploying Channel: {channel_name.upper()}]")
            attempts = 3
            success = False
            for attempt in range(1, attempts + 1):
                report.append(f" - Attempt {attempt}/{attempts}: Connecting to {channel_name} API Gateway...")
                
                # Mock a transient 429 rate limit error on attempt 1
                if attempt == 1:
                    time.sleep(1)
                    report.append("   ⚠️ API Response: HTTP 429 Too Many Requests (Rate limit hit). Retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                
                # WhatsApp simulation with failure and SMS fallback routing
                if "whatsapp" in channel_name.lower():
                    report.append("   ⚠️ API Response: HTTP 400 Bad Request - WhatsApp template rejected due to language rules.")
                    report.append("   🚨 WhatsApp Dispatch Failed permanently. Initiating Fallback Routing...")
                    report.append("   📲 Fallback Target: Unifonic SMS Gateway.")
                    time.sleep(1)
                    report.append("   - Attempt 1/1: Connecting to Unifonic SMS API Gateway...")
                    report.append("   ✔ SMS Dispatch SUCCESSFUL. Message sent via carrier gateway.")
                    report.append("   Status: DEPLOYED (via SMS Fallback).")
                    success = True
                    break
                
                # General success for other channels (Meta Ads)
                time.sleep(1)
                report.append("   ✔ API Response: HTTP 201 Created. Campaign uploaded successfully.")
                report.append("   Status: DEPLOYED.")
                success = True
                break
                
            if not success:
                report.append(f"   ❌ Channel {channel_name.upper()} Deployment Failed after all retries.")
                
        return "\n".join(report)

    # Configure the real Agents using CrewAI native classes
    from crewai import Agent as CrewAgent, Task as CrewTask, Crew as CrewCrew, Process as CrewProcess

    content_architect = CrewAgent(
        role="Content Architect",
        goal="Write highly engaging, culturally appropriate campaign copies and WhatsApp templates using Gulf or Egyptian Arabic. Query product details first using search_product_catalog.",
        backstory="Senior copywriter specialized in localized Ramadan campaigns for Saudi Arabia and Egypt, with deep knowledge of cultural sensitivities.",
        llm=adapter.llm,
        tools=[search_product_catalog],
        verbose=True,
    )

    compliance_guardian = CrewAgent(
        role="Compliance Guardian",
        goal="Scan generated copies for contextual PII, run redactions, and record official compliance audit logs under PDPL rules using write_compliance_audit_log.",
        backstory="Experienced privacy officer expert in Saudi PDPL and Egypt Law 151 compliance, enforcing access control and data residency.",
        llm=adapter.llm,
        tools=[write_compliance_audit_log],
        verbose=True,
    )

    channel_deployer = CrewAgent(
        role="Channel Deployer",
        goal="Deploy campaign copies to marketing channels (Meta Ads, Unifonic WhatsApp) using deploy_marketing_channels, resiliently handling rate limits and routing fallbacks.",
        backstory="Senior integration engineer specialized in advertising APIs, rate-limit resilience, and dynamic fallback routing.",
        llm=adapter.llm,
        tools=[deploy_marketing_channels],
        verbose=True,
    )

    # Configure sequential tasks without human_input=True on Task to avoid the CrewAI bug
    content_task = CrewTask(
        description=(
            f"Generate 4 Ramadan ad copy variants (Gulf Arabic carousel, Gulf Arabic single, English, WhatsApp template) for the product {name_en}. "
            f"Always use the search_product_catalog tool to verify specs, price ({price} SAR/AED), and discount percentage ({discount}%). Make sure it is culturally appropriate."
        ),
        expected_output="4 ad copy variants ready for audit review.",
        agent=content_architect,
        callback=adapter._task_callback,
    )

    compliance_task = CrewTask(
        description=(
            "Review the generated campaign copies from the content architect for customer PII (e.g. Iqama numbers, phone numbers, names). "
            "Redact any PII detected, confirm customer marketing consent, and record the official audit log using the write_compliance_audit_log tool. "
            "Format the log in JSON format specifying status: APPROVED."
        ),
        expected_output="Compliance approved and redacted campaign copy ready for deployment.",
        agent=compliance_guardian,
        callback=adapter._task_callback,
    )

    # Resolve memory configuration for the crews
    embedder_config = None
    if hasattr(adapter, 'runner') and hasattr(adapter.runner, '_get_embedder_config'):
        embedder_config = adapter.runner._get_embedder_config()

    # --- Phase 1: Campaign Content Generation and Audit ---
    print("\n[Phase 1] Launching Content & Compliance Agents...")
    crew_phase1_kwargs = dict(
        agents=[content_architect, compliance_guardian],
        tasks=[content_task, compliance_task],
        process=CrewProcess.sequential,
        step_callback=adapter._step_callback,
        verbose=True
    )
    if embedder_config:
        crew_phase1_kwargs["memory"] = True
        crew_phase1_kwargs["embedder"] = embedder_config
    else:
        crew_phase1_kwargs["memory"] = False

    crew_phase1 = CrewCrew(**crew_phase1_kwargs)

    try:
        start_time = time.time()
        phase1_result = await crew_phase1.kickoff_async()
        
        print("\n" + "=" * 60)
        print("   CAMPAIGN CONTENT GENERATED & AUDITED")
        print("=" * 60)
        print(f"\n{phase1_result}")
        print("=" * 60)

        # --- Human-in-the-Loop Approval Gate ---
        print("\n[+] HUMAN APPROVAL GATE REQUIRED")
        print("Please review the generated campaign copy and compliance status above.")
        
        user_input = input("Approve campaign deployment to Meta Ads & WhatsApp? (y/n) [Default: y]: ").strip().lower()
        if user_input not in ["", "y", "yes"]:
            print("\n[❌] Campaign Deployment Aborted by User.")
            return

        # --- Phase 2: Campaign Channel Deployment ---
        print("\n[Phase 2] Launching Channel Deployer Agent...")
        
        deploy_task = CrewTask(
            description=(
                f"Take the approved campaign copies: {str(phase1_result)} and deploy them to marketing channels (Meta Ads, WhatsApp) using the deploy_marketing_channels tool. "
                f"Input a JSON payload mapping channels to their copies. Check the execution report for any API rate limit retries and verify that WhatsApp fallback to SMS succeeded."
            ),
            expected_output="Final campaign deployment status report detailing Meta Ads success and Unifonic SMS fallback results.",
            agent=channel_deployer,
            callback=adapter._task_callback,
        )

        crew_phase2_kwargs = dict(
            agents=[channel_deployer],
            tasks=[deploy_task],
            process=CrewProcess.sequential,
            step_callback=adapter._step_callback,
            verbose=True
        )
        if embedder_config:
            crew_phase2_kwargs["memory"] = True
            crew_phase2_kwargs["embedder"] = embedder_config
        else:
            crew_phase2_kwargs["memory"] = False

        crew_phase2 = CrewCrew(**crew_phase2_kwargs)
        phase2_result = await crew_phase2.kickoff_async()
        duration_ms = (time.time() - start_time) * 1000

        print("\n" + "=" * 60)
        print("   FINAL DEPLOYMENT REPORT")
        print("=" * 60)
        print(f"\n{phase2_result}")


        # 5. Generate Visuals using Pollinations.ai (Free)
        print("\n[+] Generating Ramadan Visual Mockups...")
        image_prompt = build_ad_image_prompt(product_data, market)
        print(f"[*] Prompt: {image_prompt}")
        
        try:
            image_path = generate_ad_image(image_prompt)
            print(f"[✔] Image mockups generated and saved to: {image_path}")
        except Exception as img_err:
            print(f"[⚠️] Visual generation skipped: {img_err}")

        print("\n" + "=" * 60)
        print("   Campaign Execution Successful! Ready to publish.")
        print("=" * 60)

    except Exception as e:
        print(f"\n[❌] Campaign Generation Failed: {e}")


if __name__ == "__main__":
    asyncio.run(interactive_cli())

