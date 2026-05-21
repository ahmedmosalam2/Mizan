"""
Fixed test data for all benchmark scenarios.

This data is IDENTICAL for every framework — ensuring fair comparison.
"""

# ═══════════════════════════════════════════════════════════════════
# Agent Specifications (the 6 agents)
# ═══════════════════════════════════════════════════════════════════

AGENT_SPECS = [
    {
        "name": "CampaignCommander",
        "role": "Campaign Manager & Orchestrator",
        "goal": "Decompose Ramadan campaign briefs into actionable sub-tasks, assign work to sub-agents, and coordinate execution across Saudi and Egyptian markets.",
        "backstory": "You are a senior marketing strategist with 10 years of experience in MENA e-commerce. You understand Gulf and Egyptian markets, Ramadan consumer behavior, and multi-channel campaign orchestration. You manage a team of specialized AI agents.",
        "can_delegate": True,
    },
    {
        "name": "ContentArchitect",
        "role": "Bilingual Content Generator",
        "goal": "Generate high-quality bilingual (Arabic/English) campaign content including ad copy, product descriptions, social media posts, email templates, and WhatsApp message templates.",
        "backstory": "You are an expert Arabic copywriter fluent in both Gulf Arabic (for Saudi audiences) and Egyptian Arabic (for Egyptian audiences). You understand cultural nuances, Ramadan sensitivities, and e-commerce conversion optimization.",
    },
    {
        "name": "ChannelDeployer",
        "role": "Multi-Channel Campaign Deployer",
        "goal": "Deploy campaigns across Meta Ads, Google Ads, Snapchat, TikTok, WhatsApp, SMS, and email channels. Handle API integrations, retry logic, and fallback strategies.",
        "backstory": "You are a digital advertising operations specialist experienced with all major MENA advertising platforms. You handle API rate limits, template rejections, and cross-platform deployment coordination.",
    },
    {
        "name": "AnalyticsAgent",
        "role": "Campaign Performance Analyst",
        "goal": "Monitor real-time campaign performance, compute ROAS/CPA/CTR, recommend budget reallocations, and generate performance reports.",
        "backstory": "You are a data analyst specialized in e-commerce marketing analytics for the MENA region. You understand seasonal Ramadan patterns, Iftar/Suhoor browsing peaks, and cross-channel attribution.",
    },
    {
        "name": "CustomerEngagement",
        "role": "Customer Service Agent",
        "goal": "Handle inbound customer inquiries via WhatsApp and web chat. Answer product questions, process order status queries, handle BNPL payment inquiries, and escalate complex issues.",
        "backstory": "You are a customer service representative for a MENA e-commerce retailer. You speak Arabic (Gulf and Egyptian dialects) and English. You understand BNPL products (Tamara, Tabby, Fawry) and can look up order status.",
    },
    {
        "name": "ComplianceGuardian",
        "role": "Privacy & Compliance Officer",
        "goal": "Scan all content and data operations for PII violations. Detect and redact Saudi/Egyptian national IDs, phone numbers, and personal data. Enforce PDPL compliance for both jurisdictions.",
        "backstory": "You are a data protection officer specializing in Saudi PDPL and Egypt's Law 151/2020. You understand PII classification, consent management, cross-border data transfer rules, and audit logging requirements.",
    },
]


# ═══════════════════════════════════════════════════════════════════
# Scenario 1: Campaign Planning (Orchestration)
# ═══════════════════════════════════════════════════════════════════

CAMPAIGN_BRIEF = {
    "campaign_name": "Ramadan Iftar Essentials 2026 - Week 1",
    "company": "RetailCo",
    "markets": ["KSA", "EG"],
    "budget": {
        "KSA": {"amount": 50000, "currency": "SAR"},
        "EG": {"amount": 200000, "currency": "EGP"},
    },
    "channels": ["meta_ads", "google_ads", "snapchat", "tiktok", "whatsapp", "sms", "email"],
    "target_audiences": {
        "KSA": "Saudi females 25-40, interested in home appliances and kitchen gadgets, Riyadh/Jeddah",
        "EG": "Egyptian families, middle-class, interested in electronics and gifting, Cairo/Alexandria",
    },
    "objectives": ["Brand Awareness", "Conversions", "App Installs"],
    "content_requirements": {
        "ad_variants": 12,
        "languages": ["ar_gulf", "ar_egyptian", "en"],
        "formats": ["carousel", "single_image", "video_thumbnail", "whatsapp_template"],
    },
    "start_date": "2026-02-28",
    "end_date": "2026-03-30",
    "special_notes": "Respect Ramadan spiritual themes. No food imagery during fasting hours. Promote Iftar deals 3-7 PM.",
}


# ═══════════════════════════════════════════════════════════════════
# Scenario 2: Content Generation (Tool Use / RAG)
# ═══════════════════════════════════════════════════════════════════

PRODUCT_CATALOG = [
    {
        "sku": "KIT-001",
        "name_en": "Philips Air Fryer XXL",
        "name_ar": "قلاية فيلبس الهوائية XXL",
        "price_sar": 899,
        "price_egp": 12500,
        "category": "kitchen_appliances",
        "description_en": "7L capacity, Rapid Air technology, digital display, dishwasher-safe parts.",
        "description_ar": "سعة 7 لتر، تقنية Rapid Air، شاشة رقمية، أجزاء آمنة للغسالة.",
        "image_url": "https://example.com/products/philips-airfryer-xxl.jpg",
        "in_stock_ksa": True,
        "in_stock_eg": True,
    },
    {
        "sku": "ELEC-042",
        "name_en": "Samsung Galaxy Tab S9",
        "name_ar": "سامسونج جالكسي تاب S9",
        "price_sar": 2799,
        "price_egp": 38000,
        "category": "electronics",
        "description_en": "11-inch AMOLED, 128GB, S Pen included, IP68 water resistance.",
        "description_ar": "شاشة 11 بوصة AMOLED، 128 جيجا، قلم S Pen، مقاومة للماء IP68.",
        "image_url": "https://example.com/products/samsung-tab-s9.jpg",
        "in_stock_ksa": True,
        "in_stock_eg": False,
    },
    {
        "sku": "GIFT-015",
        "name_en": "Premium Oud Gift Set",
        "name_ar": "طقم هدايا العود الفاخر",
        "price_sar": 450,
        "price_egp": 6200,
        "category": "gifting",
        "description_en": "Includes bakhoor, oud oil, and incense burner. Perfect Ramadan gift.",
        "description_ar": "يتضمن بخور وعود ومبخرة. هدية رمضانية مثالية.",
        "image_url": "https://example.com/products/oud-gift-set.jpg",
        "in_stock_ksa": True,
        "in_stock_eg": True,
    },
]

CONTENT_GENERATION_TASK = {
    "goal": "Generate 4 ad copy variants for the Philips Air Fryer XXL for Saudi market (Gulf Arabic + English) targeting Ramadan Iftar preparation. Include a WhatsApp promotional template.",
    "product": PRODUCT_CATALOG[0],
    "market": "KSA",
    "audience": "Saudi females 25-40, Riyadh/Jeddah",
    "tone": "Warm, family-oriented, Ramadan-themed",
    "constraints": [
        "Must mention price in SAR",
        "Must be culturally appropriate for Ramadan",
        "Gulf Arabic dialect (not Egyptian)",
        "WhatsApp template must follow Meta template rules",
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Scenario 3: PII Scan (Safety & Privacy)
# ═══════════════════════════════════════════════════════════════════

PII_TEST_TEXTS = {
    "saudi_text": (
        "العميل محمد عبدالله الغامدي، رقم الهوية 1087654321، "
        "رقم الجوال 0551234567، البريد الإلكتروني mohammed.g@email.com، "
        "يطلب تقسيط عبر تمارا لشراء iPhone 15 Pro Max بمبلغ 5,199 ريال. "
        "عنوان التوصيل: شارع الملك فهد، حي العليا، الرياض 12211. "
        "رقم الإقامة 2198765432."
    ),
    "egyptian_text": (
        "العميلة فاطمة أحمد حسن، رقم البطاقة 29901151234567، "
        "موبايل 01012345678، إيميل fatma.h@email.com، "
        "عايزة تدفع بفوري لشراء Samsung Galaxy S24 بسعر 38,999 جنيه. "
        "العنوان: 15 شارع التحرير، الدقي، الجيزة. "
        "رقم فودافون كاش 01098765432."
    ),
    "mixed_text": (
        "تقرير الحملة اليومي:\n"
        "- عميل سعودي (هوية: 1054321098) اشترى 3 منتجات بقيمة 2,500 ريال\n"
        "- عميلة مصرية (بطاقة: 28805230123456) طلبت إرجاع طلب\n"
        "- رقم تواصل العميل: +966551234567\n"
        "- إيميل الدعم: support@retailco.com\n"
        "- IBAN: SA0380000000608010167519\n"
        "إجمالي المبيعات: 15,340 ريال + 89,200 جنيه"
    ),
}

EXPECTED_PII_DETECTIONS = {
    "saudi_text": {
        "saudi_national_id": ["1087654321"],
        "iqama_number": ["2198765432"],
        "phone_numbers": ["0551234567"],
        "email_addresses": ["mohammed.g@email.com"],
        "person_names": ["محمد عبدالله الغامدي"],
        "addresses": ["شارع الملك فهد، حي العليا، الرياض 12211"],
    },
    "egyptian_text": {
        "egyptian_national_id": ["29901151234567"],
        "phone_numbers": ["01012345678", "01098765432"],
        "email_addresses": ["fatma.h@email.com"],
        "person_names": ["فاطمة أحمد حسن"],
        "addresses": ["15 شارع التحرير، الدقي، الجيزة"],
    },
    "mixed_text": {
        "saudi_national_id": ["1054321098"],
        "egyptian_national_id": ["28805230123456"],
        "phone_numbers": ["+966551234567"],
        "email_addresses": ["support@retailco.com"],
        "iban": ["SA0380000000608010167519"],
    },
}


# ═══════════════════════════════════════════════════════════════════
# Scenario 4: Budget Approval (Human-in-the-Loop)
# ═══════════════════════════════════════════════════════════════════

BUDGET_REALLOCATION_REQUEST = {
    "campaign_id": "ramadan-w1-2026",
    "current_allocation": {
        "meta_ads": {"budget_sar": 15000, "spent": 8500, "roas": 8.2},
        "snapchat": {"budget_sar": 10000, "spent": 7200, "roas": 1.1},
        "google_ads": {"budget_sar": 12000, "spent": 5800, "roas": 5.4},
        "tiktok": {"budget_sar": 8000, "spent": 3100, "roas": 3.8},
        "whatsapp": {"budget_sar": 5000, "spent": 2400, "roas": 6.5},
    },
    "recommendation": {
        "action": "reallocate",
        "from_channel": "snapchat",
        "to_channel": "meta_ads",
        "amount_sar": 5000,
        "reason": "Snapchat ROAS (1.1x) is below 2x threshold. Meta ROAS (8.2x) is the highest performer.",
        "percentage_of_channel_budget": 50,  # > 20% → requires approval
    },
}

SIMULATED_APPROVALS = [
    {
        "gate": "budget_reallocation",
        "decision": "approved",
        "approver": "Marketing Manager",
        "feedback": "Agreed. Also increase WhatsApp by 2000 SAR from the Snapchat budget.",
        "delay_seconds": 0,  # instant for benchmark
    },
]

APPROVAL_RULES = {
    "budget_reallocation_threshold": 0.20,  # > 20% needs approval
    "content_review_required": True,
    "compliance_review_required": True,
    "escalation_sentiment_threshold": 0.8,
}


# ═══════════════════════════════════════════════════════════════════
# Scenario 5: Cross-Session Memory
# ═══════════════════════════════════════════════════════════════════

CONVERSATION_HISTORY = [
    # Session 1 (Day 1 of Ramadan)
    {
        "session_id": "sess_day1_cust_101",
        "customer_id": "CUST-101",
        "timestamp": "2026-02-28T14:30:00",
        "messages": [
            {"role": "customer", "content": "السلام عليكم، عندكم قلاية فيلبس الهوائية XXL؟"},
            {"role": "agent", "content": "وعليكم السلام! نعم متوفرة عندنا بسعر 899 ريال. عندنا عرض رمضان خصم 15% لتصبح 764 ريال."},
            {"role": "customer", "content": "ممتاز، بس حابب أشوف لو فيه لون أبيض"},
            {"role": "agent", "content": "متوفرة باللون الأسود والأبيض. الأبيض متوفر في فرع الرياض فقط."},
            {"role": "customer", "content": "طيب خلني أفكر وأرجعلكم"},
        ],
    },
    # Session 2 (Day 3 of Ramadan) — same customer
    {
        "session_id": "sess_day3_cust_101",
        "customer_id": "CUST-101",
        "timestamp": "2026-03-02T16:00:00",
        "messages": [
            {"role": "customer", "content": "مرحبا، أنا كلمتكم قبل كذا عن المنتج اللي سألت عنه. قررت آخذه."},
        ],
    },
]

MEMORY_FOLLOW_UP = "العميل رجع بعد يومين وقال إنه قرر يشتري. لازم الوكيل يتذكر: المنتج (قلاية فيلبس)، السعر (764 ريال بعد الخصم)، اللون (أبيض)، والفرع (الرياض)."

EXPECTED_RECALL = [
    "قلاية فيلبس",    # Product name
    "764",             # Discounted price
    "أبيض",            # Color preference
    "الرياض",          # Branch
]


# ═══════════════════════════════════════════════════════════════════
# Scenario 6: Channel Deployment with Failure (Observability)
# ═══════════════════════════════════════════════════════════════════

DEPLOYMENT_TASK = {
    "campaign_id": "ramadan-w1-2026",
    "channels": [
        {"name": "meta_ads", "market": "KSA", "should_succeed": True},
        {"name": "meta_ads", "market": "EG", "should_succeed": True},
        {"name": "snapchat", "market": "KSA", "should_succeed": False, "error": "API_RATE_LIMIT"},
        {"name": "google_ads", "market": "KSA", "should_succeed": True},
        {"name": "whatsapp", "market": "KSA", "should_succeed": False, "error": "TEMPLATE_REJECTED"},
        {"name": "email", "market": "EG", "should_succeed": True},
    ],
    "expected_behavior": {
        "total_channels": 6,
        "should_succeed": 4,
        "should_retry": ["snapchat"],
        "should_fallback": {"whatsapp": "sms"},
        "must_produce_trace": True,
    },
}


# ═══════════════════════════════════════════════════════════════════
# Scenario 7: Multimodal (Product Image → Ad Copy)
# ═══════════════════════════════════════════════════════════════════

MULTIMODAL_TASK = {
    "goal": "Analyze the product image and generate an Arabic ad copy suitable for a Ramadan Meta Ads carousel. Include a catchy headline, description, and call-to-action.",
    "product": PRODUCT_CATALOG[0],
    "market": "KSA",
    "format": "meta_carousel",
    "language": "ar_gulf",
    "requirements": [
        "Headline max 40 characters",
        "Description max 125 characters",
        "CTA must be action-oriented",
        "Must reference the product accurately from the image",
    ],
}


# ═══════════════════════════════════════════════════════════════════
# List of all 20 frameworks to benchmark
# ═══════════════════════════════════════════════════════════════════

FRAMEWORKS_REGISTRY = [
    {"id": "crewai",          "name": "CrewAI",           "version": "latest", "category": "code_first"},
    {"id": "langgraph",       "name": "LangGraph",        "version": "latest", "category": "code_first"},
    {"id": "autogen",         "name": "AutoGen",          "version": "latest", "category": "code_first"},
    {"id": "swarm",           "name": "OpenAI Swarm",     "version": "latest", "category": "code_first"},
    {"id": "llamaindex",      "name": "LlamaIndex",       "version": "latest", "category": "code_first"},
    {"id": "haystack",        "name": "Haystack",         "version": "latest", "category": "code_first"},
    {"id": "smolagents",      "name": "SmolAgents",       "version": "latest", "category": "code_first"},
    {"id": "agno",            "name": "Agno",             "version": "latest", "category": "code_first"},
    {"id": "pydantic_ai",     "name": "PydanticAI",       "version": "latest", "category": "code_first"},
    {"id": "google_adk",      "name": "Google ADK",       "version": "latest", "category": "code_first"},
    {"id": "openai_agents",   "name": "OpenAI Agents SDK","version": "latest", "category": "code_first"},
    {"id": "mastra",          "name": "Mastra",           "version": "latest", "category": "code_first"},
    {"id": "atomic_agents",   "name": "Atomic Agents",    "version": "latest", "category": "code_first"},
    {"id": "camel",           "name": "CAMEL",            "version": "latest", "category": "code_first"},
    {"id": "taskflowai",      "name": "TaskFlowAI",       "version": "latest", "category": "code_first"},
    {"id": "controlflow",     "name": "ControlFlow",      "version": "latest", "category": "code_first"},
    {"id": "langflow",        "name": "Langflow",         "version": "latest", "category": "low_code"},
    {"id": "flowise",         "name": "Flowise",          "version": "latest", "category": "low_code"},
    {"id": "n8n",             "name": "n8n",              "version": "latest", "category": "low_code"},
    {"id": "dify",            "name": "Dify",             "version": "latest", "category": "low_code"},
]
