"""Specialized Agents - Domain-specific implementations."""

from typing import Any, Dict, List, Optional
from abc import abstractmethod
import time
import re
import json

from core.domain.agents.base import Agent
from core.domain.agents.agent_context import AgentContext
from core.domain.entities.agent_helper import Task


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, stripping markdown code blocks if present."""
    cleaned = text.strip()
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


class AnalysisAgent(Agent):
    """Analyzes data and extracts insights."""
    
    def __init__(self, llm_port: Any):
        """
        Initialize analysis agent.
        
        Args:
            llm_port: LLM port for analysis
        """
        self.llm_port = llm_port
    
    async def execute(self, task: Task, context: Optional[AgentContext] = None) -> Dict[str, Any]:
        """
        Analyze task data.
        
        Args:
            task: Task to analyze
            context: Agent context with shared data
            
        Returns:
            Analysis results
        """
        # Get any previous data from context
        input_data = None
        if context:
            input_data = context.get_data("current_input")
        
        # Build analysis prompt
        analysis_prompt = self._build_analysis_prompt(task, input_data)
        
        # Get LLM analysis
        analysis_result = await self.llm_port.generate(analysis_prompt)
        
        # Parse and structure results
        insights = self._parse_analysis(analysis_result)
        
        # Update context if available
        if context:
            context.set_data("analysis_results", insights)
            context.add_message(self.__class__.__name__, "analysis", {
                "insights_count": len(insights.get("insights", [])),
                "data_quality": insights.get("data_quality", 0)
            })
        
        return {
            "type": "analysis",
            "insights": insights.get("insights", []),
            "data_quality_score": insights.get("data_quality", 0),
            "recommendations": insights.get("recommendations", [])
        }
    
    def _build_analysis_prompt(self, task: Task, input_data: Optional[Dict]) -> str:
        """Build analysis prompt."""
        context_str = task.context
        if isinstance(task.context, dict):
            import json
            context_str = json.dumps(task.context, indent=2, ensure_ascii=False)
        
        constraints_str = ", ".join(task.constraints) if task.constraints else "No constraints"
        
        prompt = (
            f"Analyze the following data and provide insights:\n\n"
            f"Task Goal: {task.goal}\n"
            f"Task Context: {context_str}\n"
            f"Constraints: {constraints_str}\n"
        )
        
        if input_data:
            prompt += f"\nInput Data: {input_data}\n"
        
        prompt += (
            f"\nProvide your analysis in JSON format with keys: "
            f"'insights' (list), 'data_quality' (0-100), 'recommendations' (list)"
        )
        
        return prompt
    
    def _parse_analysis(self, result: str) -> Dict[str, Any]:
        """Parse LLM analysis result."""
        try:
            return _extract_json(result)
        except Exception:
            return {
                "insights": [result],
                "data_quality": 50,
                "recommendations": []
            }


class OptimizationAgent(Agent):
    """Optimizes campaigns and strategies."""
    
    def __init__(self, llm_port: Any):
        """Initialize optimization agent."""
        self.llm_port = llm_port
    
    async def execute(self, task: Task, context: Optional[AgentContext] = None) -> Dict[str, Any]:
        """
        Optimize campaign or strategy.
        
        Args:
            task: Task to optimize
            context: Agent context with shared data
            
        Returns:
            Optimization recommendations
        """
        # Get analysis results from context
        analysis_results = None
        if context:
            analysis_results = context.get_data("analysis_results")
        
        # Build optimization prompt
        optimization_prompt = self._build_optimization_prompt(task, analysis_results)
        
        # Get LLM recommendations
        recommendations = await self.llm_port.generate(optimization_prompt)
        
        # Parse recommendations
        optimization_plan = self._parse_recommendations(recommendations)
        
        # Update context
        if context:
            context.set_data("optimization_plan", optimization_plan)
            context.add_message(self.__class__.__name__, "optimization", {
                "actions_count": len(optimization_plan.get("actions", [])),
                "estimated_improvement": optimization_plan.get("estimated_improvement", 0)
            })
        
        return {
            "type": "optimization",
            "actions": optimization_plan.get("actions", []),
            "estimated_improvement": optimization_plan.get("estimated_improvement", 0),
            "priority": optimization_plan.get("priority", "medium"),
            "implementation_steps": optimization_plan.get("implementation_steps", [])
        }
    
    def _build_optimization_prompt(self, task: Task, analysis_results: Optional[Dict]) -> str:
        """Build optimization prompt."""
        context_str = task.context
        if isinstance(task.context, dict):
            import json
            context_str = json.dumps(task.context, indent=2, ensure_ascii=False)
        
        constraints_str = ", ".join(task.constraints) if task.constraints else "No constraints"
        
        prompt = (
            f"Based on the following, provide optimization recommendations:\n\n"
            f"Task: {task.goal}\n"
            f"Context: {context_str}\n"
            f"Constraints: {constraints_str}\n"
        )
        
        if analysis_results:
            prompt += f"\nAnalysis Results: {analysis_results}\n"
        
        prompt += (
            f"\nProvide JSON with: 'actions' (list), 'estimated_improvement' (0-100), "
            f"'priority' (low/medium/high), 'implementation_steps' (list)"
        )
        
        return prompt
    
    def _parse_recommendations(self, result: str) -> Dict[str, Any]:
        """Parse optimization recommendations."""
        try:
            return _extract_json(result)
        except Exception:
            return {
                "actions": [result],
                "estimated_improvement": 25,
                "priority": "medium",
                "implementation_steps": []
            }


class ValidatorAgent(Agent):
    """Validates data, rules, and constraints."""
    
    def __init__(self, validation_rules: Optional[Dict[str, Any]] = None):
        """
        Initialize validator agent.
        
        Args:
            validation_rules: Dictionary of validation rules
        """
        self.validation_rules = validation_rules or {}
    
    async def execute(self, task: Task, context: Optional[AgentContext] = None) -> Dict[str, Any]:
        """
        Validate task data against rules.
        
        Args:
            task: Task to validate
            context: Agent context with shared data
            
        Returns:
            Validation results
        """
        # Get optimization plan from context
        optimization_plan = None
        if context:
            optimization_plan = context.get_data("optimization_plan")
        
        # Run validations
        validation_results = self._run_validations(task, optimization_plan)
        
        # Check if valid
        is_valid = validation_results["is_valid"]
        
        # Update context
        if context:
            context.set_data("validation_results", validation_results)
            context.add_message(self.__class__.__name__, "validation", {
                "is_valid": is_valid,
                "errors_count": len(validation_results.get("errors", [])),
                "warnings_count": len(validation_results.get("warnings", []))
            })
        
        return {
            "type": "validation",
            "is_valid": is_valid,
            "errors": validation_results.get("errors", []),
            "warnings": validation_results.get("warnings", []),
            "passed_checks": validation_results.get("passed_checks", [])
        }
    
    def _run_validations(self, task: Task, optimization_plan: Optional[Dict]) -> Dict[str, Any]:
        """Run validation checks."""
        errors = []
        warnings = []
        passed_checks = []
        
        # Validate task
        if not task.goal:
            errors.append("Task goal is required")
        else:
            passed_checks.append("Task goal validated")
        
        # Validate optimization plan if present
        if optimization_plan:
            if optimization_plan.get("actions"):
                passed_checks.append("Optimization actions present")
            else:
                warnings.append("No optimization actions provided")
            
            # Validate estimated improvement
            improvement = optimization_plan.get("estimated_improvement", 0)
            if improvement > 100:
                errors.append("Estimated improvement cannot exceed 100%")
            elif improvement < 0:
                errors.append("Estimated improvement cannot be negative")
            else:
                passed_checks.append("Estimated improvement validated")
        
        # Validate against rules
        for rule_name, rule_check in self.validation_rules.items():
            try:
                if rule_check(task, optimization_plan):
                    passed_checks.append(f"Rule '{rule_name}' passed")
                else:
                    errors.append(f"Rule '{rule_name}' failed")
            except Exception as e:
                warnings.append(f"Error checking rule '{rule_name}': {str(e)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "passed_checks": passed_checks
        }


class ExecutorAgent(Agent):
    """Executes validated plans and returns results."""
    
    def __init__(self, executor_port: Any):
        """
        Initialize executor agent.
        
        Args:
            executor_port: Port for executing actions
        """
        self.executor_port = executor_port
    
    async def execute(self, task: Task, context: Optional[AgentContext] = None) -> Dict[str, Any]:
        """
        Execute the validated plan.
        
        Args:
            task: Task to execute
            context: Agent context with shared data
            
        Returns:
            Execution results
        """
        # Get validation results
        validation_results = None
        if context:
            validation_results = context.get_data("validation_results")
        
        # Check if valid before executing
        if validation_results and not validation_results.get("is_valid"):
            if context:
                context.stop_execution("Validation failed, cannot execute")
            return {
                "type": "execution",
                "status": "failed",
                "reason": "Validation failed",
                "executed_actions": []
            }
        
        # Get optimization plan
        optimization_plan = None
        if context:
            optimization_plan = context.get_data("optimization_plan")
        
        # Execute actions
        executed_actions = []
        execution_errors = []
        
        if optimization_plan and optimization_plan.get("actions"):
            for action in optimization_plan["actions"]:
                try:
                    result = await self.executor_port.execute(action)
                    executed_actions.append({
                        "action": action,
                        "result": result,
                        "status": "success"
                    })
                except Exception as e:
                    execution_errors.append({
                        "action": action,
                        "error": str(e)
                    })
        
        # Update context
        if context:
            context.set_data("execution_results", {
                "executed_actions": executed_actions,
                "errors": execution_errors
            })
            context.add_message(self.__class__.__name__, "execution", {
                "actions_executed": len(executed_actions),
                "errors_count": len(execution_errors)
            })
        
        return {
            "type": "execution",
            "status": "success" if not execution_errors else "partial",
            "executed_actions": executed_actions,
            "errors": execution_errors
        }
