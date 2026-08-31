# 🏆 Mizan (ميزان) — AI Agentic Framework Benchmark

**A production-grade benchmark evaluating 20 AI multi-agent frameworks on a high-stakes, real-world MENA e-commerce use case.**

---

## 📌 Benchmark Scenario

**Omnichannel Ramadan Campaign & Customer Engagement Orchestrator** for a dual-market (Saudi Arabia + Egypt) e-commerce retailer.

The system coordinates 6 specialized agents across 8+ channels (Meta Ads, Google Ads, Snapchat, TikTok, WhatsApp, SMS, Email), maintaining compliance with **Saudi PDPL** and **Egypt Law 151/2020**, with real-time budget optimization, RAG over 5,000+ SKUs, and multimodal creative generation.

---

## 🎯 The 7 Evaluation Dimensions

| # | Dimension | Weight | Key Capabilities Tested |
|:---:|:---|:---:|:---|
| **1** | **Agent Design & Orchestration** | **20%** | Multi-agent coordination (6 agents), task decomposition, parallel flows, error recovery (rate limit retries), conditional fallbacks (WhatsApp -> SMS). |
| **2** | **Tool Use & Integrations** | **15%** | Multilingual Vector RAG search (Arabic/English), sandbox code execution (ROAS/CPA computation), API integrations. |
| **3** | **Safety & Privacy** | **15%** | Saudi National ID (10-digit) & Egyptian National ID (14-digit) detection/redaction, consent enforcement, audit logging. |
| **4** | **Human-in-the-Loop (HITL)** | **15%** | Threshold-based approval gates (>20% budget shift requires manager review), workflow pause/resume. |
| **5** | **Memory & State** | **10%** | Cross-session memory recall (customer returns 2 days later, remembers air fryer price, color, branch). |
| **6** | **Observability** | **10%** | Distributed tracing, per-agent token and cost tracking, structured logging. |
| **7** | **Multimodal Capabilities** | **15%** | Product image understanding, visual feature extraction, format-compliant ad copy generation. |

---

## 🤖 The 6 Specialized Agents

1. **Campaign Commander**: Manager agent responsible for strategy decomposition, delegation, and approval routing.
2. **Content Architect**: Generates bilingual copy (Gulf Arabic for KSA, Egyptian Arabic for EG) with RAG catalog search.
3. **Channel Deployer**: Deploys campaigns across Meta, Google, Snapchat, and WhatsApp with retry and fallback logic.
4. **Analytics & Optimization Engine**: Runs sandboxed Python code to compute ROAS, CPA, and recommend budget shifts.
5. **Customer Engagement Agent**: Handles inbound WhatsApp customer inquiries with cross-session memory recall.
6. **Compliance Guardian**: Scans and redacts PII, enforces consent rules under Saudi PDPL & Egypt Law 151.

---

## 🛠 Real Services (Zero Mocks)

Mizan runs on real production-grade services:
- **`mizan/services/database.py`**: SQLite database with products, customers, orders, consent audit logs, and persistent memory.
- **`mizan/services/vector_store.py`**: Multilingual semantic search & vector indexing.
- **`mizan/services/pii_engine.py`**: Saudi & Egyptian National ID, phone, and email detection and redaction engine.
- **`mizan/services/code_executor.py`**: Sandboxed Python subprocess execution for analytics.

---

## 🚀 Quickstart

### 1. Installation

```bash
git clone https://github.com/ahmedmosalam2/Mizan.git
cd Mizan
pip install -e .
```

To install framework extras (e.g. CrewAI, LangGraph, AutoGen):
```bash
pip install -e ".[phase1]"
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

### 3. CLI Commands

**List supported framework adapters:**
```bash
python -m mizan list-frameworks
```

**Run benchmark on a single framework:**
```bash
python -m mizan run --framework crewai
```

**Run benchmark matrix across multiple frameworks:**
```bash
python -m mizan matrix --frameworks native --frameworks crewai --frameworks langgraph --frameworks autogen
```

The leaderboard will be output directly in the terminal and saved to `reports/LEADERBOARD.md`.

---

## 🧩 Adding a New Framework Adapter

Adding a new framework takes just 1 file:
1. Create `mizan/adapters/<framework_name>/adapter.py`
2. Subclass `BaseAdapter` and decorate with `@register_adapter("<framework_name>")`
3. Implement the probe methods (`run_orchestration`, `run_tool_use`, `run_safety`, `run_hitl`, `run_memory`, `run_multimodal`)
4. Run `python -m mizan run --framework <framework_name>`
