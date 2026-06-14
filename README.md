<div align="center">

# ⚖️ Mizan

### AI Agentic Framework Benchmark for MENA E-Commerce

**Compare 20 AI agent frameworks on a real-world Ramadan campaign scenario**
**across Saudi Arabia & Egypt — 7 dimensions, automated scoring, production-grade reports.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Frameworks](https://img.shields.io/badge/Frameworks-20-purple.svg)](#frameworks)

</div>

---

## 🎯 What is Mizan?

**Mizan** (ميزان — Arabic for "scale/balance") is a benchmark platform that evaluates **20 AI agentic frameworks** on a standardized, real-world MENA e-commerce scenario. Instead of synthetic tests, Mizan uses an **Omnichannel Ramadan Campaign Orchestrator** — the exact type of system that companies like Noon, Jarir, and B.TECH deploy every Ramadan season.

Each framework is tested across **7 evaluation dimensions** using identical scenarios, prompts, and scoring rubrics to produce a fair, differentiated comparison.

### Why This Matters

- **$6.2B+ MENA Ramadan e-commerce market** demands production-ready AI orchestration
- **Saudi PDPL** (48 enforcement actions in Year 1) and **Egypt Law 151/2020** (criminal penalties) make compliance testing critical
- **No existing benchmark** evaluates agentic frameworks on Arabic-first, MENA-specific workloads
- **Framework selection** is a high-stakes decision — Mizan provides data-driven guidance

---

## 📖 Architecture & Getting Started

**New to the codebase?** Read these first:

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Design philosophy, abstractions, and patterns
   - Framework-agnostic architecture
   - Core abstractions (Agent, Tool, Message, State, Orchestrator)
   - Design patterns (Strategy, Chain of Responsibility, Observer, Builder)
   - Phase 1-3 implementation roadmap

2. **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
   - Install dependencies
   - Run example tests and workflows
   - Create your first agent
   - Understand the abstractions through code

**TL;DR**: The framework is built on explicit abstractions that are **framework-agnostic**. Each agent framework (CrewAI, LangGraph, Agno) is implemented as an adapter, not core logic. This enables fair comparison and switching without rewriting agents.

---

## 📊 The 7 Evaluation Dimensions

| # | Dimension | Weight | What It Tests |
|---|-----------|--------|---------------|
| 1 | **Orchestration** | 20% | Multi-agent coordination, task decomposition, parallel execution |
| 2 | **Tool Use** | 15% | Function calling, RAG retrieval, API integration, tool chaining |
| 3 | **Safety & Privacy** | 15% | PII detection (Saudi/Egyptian IDs), redaction, PDPL compliance |
| 4 | **Human-in-the-Loop** | 15% | Approval gates, feedback injection, conditional triggers |
| 5 | **Memory & State** | 10% | Cross-session recall, shared state, checkpointing |
| 6 | **Observability** | 10% | Execution tracing, token/cost tracking, error handling |
| 7 | **Multimodal** | 15% | Image understanding, document handling, format compliance |

---

## 🏗️ The 20 Frameworks

<table>
<tr><th colspan="2">Code-First Frameworks</th><th colspan="2">Low-Code Platforms</th></tr>
<tr><td>1</td><td>CrewAI</td><td>17</td><td>Langflow</td></tr>
<tr><td>2</td><td>LangGraph</td><td>18</td><td>Flowise</td></tr>
<tr><td>3</td><td>AutoGen</td><td>19</td><td>n8n</td></tr>
<tr><td>4</td><td>OpenAI Agents SDK</td><td>20</td><td>Dify</td></tr>
<tr><td>5</td><td>OpenAI Swarm</td><td></td><td></td></tr>
<tr><td>6</td><td>Google ADK</td><td></td><td></td></tr>
<tr><td>7</td><td>PydanticAI</td><td></td><td></td></tr>
<tr><td>8</td><td>SmolAgents (HuggingFace)</td><td></td><td></td></tr>
<tr><td>9</td><td>LlamaIndex</td><td></td><td></td></tr>
<tr><td>10</td><td>Haystack (deepset)</td><td></td><td></td></tr>
<tr><td>11</td><td>Agno (ex-Phidata)</td><td></td><td></td></tr>
<tr><td>12</td><td>Mastra</td><td></td><td></td></tr>
<tr><td>13</td><td>Atomic Agents</td><td></td><td></td></tr>
<tr><td>14</td><td>CAMEL-AI</td><td></td><td></td></tr>
<tr><td>15</td><td>TaskFlowAI</td><td></td><td></td></tr>
<tr><td>16</td><td>ControlFlow</td><td></td><td></td></tr>
</table>

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/ahmedmosalam2/Mizan.git
cd Mizan

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install core + desired frameworks
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   GROQ_API_KEY=gsk_...
```

### 3. Run Benchmark

```bash
# Benchmark specific frameworks
cd src
python -m benchmarks.runner --frameworks crewai langgraph autogen

# Benchmark all 20
python -m benchmarks.runner

# Custom LLM model
python -m benchmarks.runner --frameworks crewai --llm-model llama-3.3-70b-versatile
```

### 3.5 Bypassing Rate Limits (LLM Gateway)

To avoid Groq's Tokens Per Minute (TPM) limits during complex multi-agent benchmark runs, you can route all LLM calls through the built-in **LLM Gateway Middleware**:

1. Start the LLM Gateway server:
   ```bash
   cd src
   python -m uvicorn main:app --host 127.0.0.1 --port 8085 --reload
   ```

2. Run the benchmarks with the `LLM_GATEWAY_URL` environment variable:
   ```bash
   # On Windows PowerShell:
   $env:LLM_GATEWAY_URL="http://127.0.0.1:8085/api/v1/llm"
   py -3.10 -m benchmarks.runner --frameworks crewai

   # On Linux/WSL/macOS:
   LLM_GATEWAY_URL="http://127.0.0.1:8085/api/v1/llm" python -m benchmarks.runner --frameworks crewai
   ```
   This activates prompt caching (extremely fast subsequent runs), multi-provider failover, and metrics tracking!

### 4. View Results

```bash
# Results are saved to:
benchmark_results/
├── benchmark_20260522_003000.json    # Raw scoring data
└── report_20260522_003000.html       # 📊 Visual report (open in browser)
```

### 5. API Mode

```bash
cd src
uvicorn main:app --host 0.0.0.0 --port 8001

# Then:
# GET  /api/v1/benchmark/frameworks     — List all 20 frameworks
# POST /api/v1/benchmark/run            — Start benchmark run
# GET  /api/v1/benchmark/status         — Check if running
# GET  /api/v1/benchmark/results        — Get latest results
```

---

## 📁 Project Structure

```
Mizan/
├── src/
│   ├── main.py                           # FastAPI entry point
│   ├── benchmarks/
│   │   ├── runner.py                     # CLI + orchestration engine
│   │   ├── adapters/
│   │   │   ├── base_adapter.py           # Abstract contract (7 methods)
│   │   │   ├── crewai_adapter.py         # Framework 1
│   │   │   ├── langgraph_adapter.py      # Framework 2
│   │   │   ├── ...                       # 18 more adapters
│   │   │   └── dify_adapter.py           # Framework 20
│   │   ├── scenarios/
│   │   │   └── test_data.py              # 7 deterministic test scenarios
│   │   ├── scoring/
│   │   │   ├── rubrics.py                # 0-10 rubrics per dimension
│   │   │   └── scorer.py                 # Automated scoring engine
│   │   └── reporting/
│   │       └── report_generator.py       # HTML report with radar charts
│   ├── core/
│   │   └── domain/agents/               # 6 specialized agent definitions
│   └── adapters/
│       ├── driving/api/routes/           # REST API endpoints
│       └── driven/llm/                   # Groq + Gemini LLM providers
├── docs/                                 # Architecture documentation
├── requirements.txt                      # All 20 framework dependencies
└── .env.example                          # Required environment variables
```

---

## 🔬 The Benchmark Scenario

### Business Context

**RetailCo** — a consumer electronics e-commerce retailer operating in Saudi Arabia (Salla + Noon) and Egypt (WooCommerce + Jumia) — needs to execute its **Ramadan 2026 campaign** across 7 channels simultaneously.

### The 7 Test Scenarios

| Scenario | Dimension | What Happens |
|----------|-----------|--------------|
| **Campaign Planning** | Orchestration | 6 agents decompose a campaign brief into sub-tasks |
| **Content Generation** | Tool Use | Agent uses RAG to search product catalog and generate Arabic ad copy |
| **PII Scan** | Safety | Detect Saudi National IDs (10-digit) and Egyptian IDs (14-digit) in Arabic text |
| **Budget Approval** | HITL | Budget reallocation >20% triggers approval gate with feedback injection |
| **Customer Memory** | Memory | Agent recalls product, price, color from a conversation 2 days ago |
| **Channel Deploy** | Observability | Deploy to 6 channels — Snapchat rate-limits, WhatsApp template rejected |
| **Ad Creative** | Multimodal | Generate Gulf Arabic Meta carousel ad from product data |

### The 6 Agents

1. **Campaign Commander** — Orchestrator, decomposes briefs, coordinates agents
2. **Content Architect** — Bilingual Arabic/English content generation (Gulf + Egyptian)
3. **Channel Deployer** — Multi-channel deployment with retry/fallback
4. **Analytics Engine** — ROAS/CPA analysis, budget reallocation recommendations
5. **Customer Engagement** — WhatsApp customer service with memory
6. **Compliance Guardian** — PII detection, PDPL enforcement, audit logging

---

## 🧩 Adding a New Framework

Create `src/benchmarks/adapters/myframework_adapter.py`:

```python
from benchmarks.adapters.base_adapter import BaseFrameworkAdapter

class MyframeworkAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="MyFramework")

    async def setup(self, llm_config):
        # Initialize the framework
        ...

    async def teardown(self):
        # Cleanup
        ...

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        # Implement using your framework's multi-agent pattern
        ...

    async def run_with_tools(self, agent_specs, task, tools):
        # Implement tool calling
        ...

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        # Implement PII detection
        ...

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        # Implement HITL approval gate
        ...

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        # Implement cross-session memory
        ...

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        # Implement observability with error injection
        ...

    async def run_multimodal(self, image_path, document_path, task):
        # Implement multimodal content generation
        ...
```

Then register it in `src/benchmarks/scenarios/test_data.py` → `FRAMEWORKS_REGISTRY`.

---

## 📖 Key Design Decisions

- **Same LLM for all**: Groq/Llama-3.3-70b by default — isolates framework differences from model differences
- **Deterministic test data**: Every framework gets identical Arabic PII samples, campaign briefs, and conversation history
- **Automated scoring**: 30+ sub-criteria scored programmatically — no subjective manual evaluation
- **Low-code via API**: Langflow/Flowise/n8n/Dify adapters call pre-deployed flows via REST — evaluating the platform's orchestration, not just the LLM

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for the MENA AI ecosystem**

*Mizan — ميزان — Because choosing the right framework should be balanced.*

</div>
