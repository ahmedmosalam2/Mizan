# Mizan Benchmark — Phase 0: Project Audit Report

**Document ID**: `reports/phase_00_audit.md`  
**Date**: 2026-08-31  
**Author**: Lead AI Benchmark Engineer & Evaluation Scientist  
**Status**: **PASS (Audit Complete)**

---

## 1. Executive Summary

Mizan is a scientific, empirical benchmark for evaluating **Agentic Frameworks / Agentic Scaffolds** (~20 candidate frameworks) under controlled, repeatable conditions.

### Primary Research Questions:
1. **Framework Performance**: How do different agentic frameworks/scaffolds perform when executing identical, realistic multi-agent enterprise workloads (the Ramadan Omnichannel RetailCo scenario across Saudi Arabia and Egypt)?
2. **Benchmark Reduction & Ranking Fidelity**: Can we scientifically reduce the benchmark evaluation suite (using empirical difficulty / midrange filtering / IRT) to minimize inference cost while preserving the relative rank order ($\text{Spearman } \rho$, $\text{Kendall } \tau_b$) of frameworks?

---

## 2. Current Codebase State Analysis

### 2.1 Existing Assets & Working Components
| Component | Location | Status | Capabilities Verified |
|---|---|---|---|
| **Database Service** | `mizan/services/database.py` | ✅ Working | Real SQLite schema (`products`, `customers`, `campaigns`, `consent_audit_log`, `customer_memory`). |
| **Vector Store** | `mizan/services/vector_store.py` | ✅ Working | Multilingual (Arabic/English) semantic search over 5,000+ SKU catalog with OpenAI / local TF-IDF vector space fallback. |
| **PII & Compliance Engine** | `mizan/services/pii_engine.py` | ✅ Working | Regex/pattern extraction for Saudi National ID (10-digit), Egyptian National ID (14-digit), phone, email, and immutable audit logging. |
| **Code Executor** | `mizan/services/code_executor.py` | ✅ Working | Subprocess sandboxed Python execution for ROAS/CPA analytics. |
| **Scenario Datasets & Fixtures** | `mizan/scenario/fixtures/` | ✅ Working | `campaign_brief.yaml`, `products.yaml`, `customers.yaml`, `channels.yaml`, `session_history.yaml`, `pii_texts.yaml`, `ground_truth.yaml`. |
| **Scoring & Rubrics** | `mizan/scoring/rubrics.py`, `evaluator.py` | ✅ Working | 7-dimension weighted evaluation against ground truth. |
| **CLI & Matrix Runner** | `mizan/cli.py`, `mizan/runner/` | ✅ Working | Typer CLI (`run`, `matrix`, `list-frameworks`) generating Rich tables and Markdown leaderboard. |

### 2.2 Critical Gaps Identified vs. Master Benchmark Architecture

To achieve a publication-grade, scientifically defensible benchmark with task reduction and statistical validation, the following architectural modules must be established in subsequent phases:

1. **Enterprise Module Structure & Configuration Hierarchy**:
   - Establishment of `configs/` (`benchmark.yaml`, `frameworks.yaml`, `models.yaml`, `execution.yaml`, `reduction.yaml`, `observability.yaml`).
   - Reorganization into dedicated packages: `mizan/core/`, `mizan/frameworks/`, `mizan/models/`, `mizan/benchmark/`, `mizan/scenarios/`, `mizan/environment/`, `mizan/tools/`, `mizan/execution/`, `mizan/evaluation/`, `mizan/reduction/`, `mizan/validation/`, `mizan/statistics/`, `mizan/monitoring/`, `mizan/observability/`, `mizan/reporting/`.

2. **Atomic Task Taxonomy & Task Contracts**:
   - Decomposing the monolithic probe flows into granular, versioned **Atomic Tasks** with immutable IDs (e.g., `ORCH-SEQ-001`, `ORCH-PAR-001`, `TOOL-RAG-001`, `SAFE-PII-001`, `HITL-GATE-001`, `MEM-RECALL-001`, `VIS-AD-001`).
   - Every task must enforce an explicit `TaskContract` with formal preconditions, expected state transitions, safety constraints, and rubrics.

3. **Empirical Task Reduction & Difficulty Engine (`mizan/reduction/`)**:
   - Historical pass-rate calculation ($p_j = \text{mean}(X_{:,j})$).
   - Midrange task filtering ($0.30 \le p_j \le 0.70$) vs. baselines (Random selection, Stratified selection).
   - Cost reduction model measuring token & latency savings.

4. **Nested Cross-Validation & Statistical Rigor (`mizan/validation/`, `mizan/statistics/`)**:
   - **Leave-One-Scaffold-Out (LOSO)** and **Leave-One-Agent-Out (LOAO)** validation to prevent data leakage (never use test-agent data to select tasks).
   - Spearman $\rho$ and Kendall $\tau_b$ rank correlation with Bootstrap Confidence Intervals (95% CI).

5. **20-Framework Scaling Plan (`mizan/frameworks/`)**:
   - Phased expansion from initial 4 frameworks (`native`, `crewai`, `langgraph`, `autogen`) to target 20 frameworks (including `camel`, `openhands`, `aider`, `dify`, `agno`, `llamaindex`, `haystack`, `semantic-kernel`, `pydantic-ai`, etc.) with explicit `CapabilityMatrix` (native, adapter, or unsupported).

6. **Experiment Logging & Problem Reporting**:
   - `reports/experiment_log.md`
   - `reports/problems/` (standardized issue post-mortems with root cause analysis).

---

## 3. Audit Verification

- **Repository Integrity Check**: `pytest tests/` executed successfully (7/7 tests passing).
- **Environment**: Python 3.13 / Windows, SQLite3, PyYAML, Rich, Typer, OpenAI SDK.
- **Fixtures Checked**: All YAML fixtures verified for syntax and data consistency.

---

## 4. Phase 0 Recommendation & Next Phase Transition

**Phase 0 Status**: **PASS**  
**Ready for Phase 1**: **Benchmark Contracts, Schemas & Task Definitions** (`reports/phase_01_contract.md`).
