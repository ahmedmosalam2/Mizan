# Problem Report 001: Fabricated / Hardcoded Prototype Adapters

**Date**: 2026-08-31  
**Severity**: CRITICAL  
**Status**: IDENTIFIED / PLANNED FOR REWRITE IN PHASE 4  

## Problem
The 4 initial framework adapters in `mizan/adapters/` (`native`, `crewai`, `langgraph`, `autogen`) were found to be returning hardcoded dataclass instances rather than invoking real framework orchestrator loops.

## Symptoms
- All frameworks produced identical scores (~9.87/10).
- No actual API or framework graph execution occurred during probe runs.
- `crewai` and `langgraph` were installed in the Python environment but never imported inside their respective adapter files.

## Root Cause
The initial skeleton code prioritized schema validation and pipeline scaffolding over full framework integration, resulting in mock outputs embedded directly in adapter methods.

## Investigation
Inspected `mizan/adapters/native/adapter.py`, `crewai/adapter.py`, `langgraph/adapter.py`, and `autogen/adapter.py`. Found that `OrchestrationOutput`, `HITLOutput`, and `MultimodalOutput` were instantiated with static literal dictionaries and strings.

## Final Fix (Action Plan)
1. Invalidate and deprecate all historical JSON results in `results/`.
2. In Phase 1: Establish the formal `FrameworkAdapterContract` and `CapabilityMatrix`.
3. In Phase 4: Implement true framework runners that construct actual agents and state graphs, execute real tools, and record genuine trajectories.

## Verification
Phase 0 audit report `reports/phase_00_audit.md` published and approved.
