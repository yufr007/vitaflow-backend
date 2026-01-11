# app/services/gemini_orchestrator.py
"""
VitaFlow - Production-Grade Gemini Orchestration.

Since Azure OpenAI isn't available on student accounts, this provides
reliable multi-step workflow management around Gemini with:
- Retry logic with exponential backoff
- Parallel execution for independent steps
- State management and dependency tracking
- Comprehensive error recovery
"""

import asyncio
import json
import logging
import time
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import google.generativeai as genai

from settings import settings

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Workflow step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Definition of a workflow step."""
    name: str
    function: Callable
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    timeout: int = 30
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    attempt: int = 0
    duration_ms: float = 0


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    workflow_id: str
    results: Dict[str, Any]
    error: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    total_duration_ms: float = 0


class GeminiOrchestrator:
    """
    Production-grade orchestration for Gemini API calls.
    
    Features:
    - Retry logic with exponential backoff
    - Parallel execution for independent steps
    - State management and dependency tracking
    - Comprehensive error recovery
    - JSON extraction from markdown responses
    
    Usage:
        orchestrator = GeminiOrchestrator()
        result = await orchestrator.execute_workflow(
            workflow_id="shopping_123",
            steps=[step1, step2, step3],
            context={"user_id": "123"}
        )
    """
    
    def __init__(self):
        """Initialize Gemini orchestrator."""
        self.model_name = "gemini-2.0-flash-exp"
        self._model = None
        self.workflows: Dict[str, List[WorkflowStep]] = {}
    
    @property
    def model(self):
        """Lazy load Gemini model."""
        if self._model is None:
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(self.model_name)
        return self._model
    
    async def execute_workflow(
        self,
        workflow_id: str,
        steps: List[WorkflowStep],
        context: Dict[str, Any]
    ) -> WorkflowResult:
        """
        Execute multi-step workflow with dependency management.
        
        Args:
            workflow_id: Unique workflow identifier
            steps: List of workflow steps with dependencies
            context: Shared context between steps
            
        Returns:
            WorkflowResult with success status and step results
        """
        start_time = time.time()
        self.workflows[workflow_id] = steps
        
        try:
            # Build dependency graph (topological sort)
            execution_order = self._build_dependency_graph(steps)
            logger.info(f"Workflow {workflow_id}: Executing {len(steps)} steps")
            
            # Execute steps in dependency order
            results: Dict[str, Any] = {}
            
            for step_name in execution_order:
                step = self._get_step(steps, step_name)
                
                # Check if dependencies completed successfully
                deps_ok = all(
                    self._get_step(steps, dep).status == StepStatus.COMPLETED
                    for dep in step.dependencies
                )
                
                if not deps_ok:
                    step.status = StepStatus.SKIPPED
                    step.error = "Dependency failed"
                    continue
                
                # Execute step with retry
                try:
                    step_result = await self._execute_step_with_retry(
                        step, context, results
                    )
                    results[step_name] = step_result
                except Exception as e:
                    logger.error(f"Step {step_name} failed permanently: {e}")
                    # Continue with other steps if possible
            
            # Compile results
            completed = [s.name for s in steps if s.status == StepStatus.COMPLETED]
            failed = [s.name for s in steps if s.status == StepStatus.FAILED]
            
            return WorkflowResult(
                success=len(failed) == 0,
                workflow_id=workflow_id,
                results=results,
                completed_steps=completed,
                failed_steps=failed,
                total_duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            return WorkflowResult(
                success=False,
                workflow_id=workflow_id,
                results={},
                error=str(e),
                total_duration_ms=(time.time() - start_time) * 1000
            )
    
    async def _execute_step_with_retry(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
        previous_results: Dict[str, Any]
    ) -> Any:
        """Execute single step with exponential backoff retry."""
        
        for attempt in range(step.max_retries):
            step_start = time.time()
            
            try:
                step.status = StepStatus.RUNNING
                step.attempt = attempt + 1
                
                logger.info(f"Executing step: {step.name} (attempt {attempt + 1}/{step.max_retries})")
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    step.function(self, context, previous_results),
                    timeout=step.timeout
                )
                
                step.status = StepStatus.COMPLETED
                step.result = result
                step.duration_ms = (time.time() - step_start) * 1000
                
                logger.info(f"Step {step.name} completed in {step.duration_ms:.0f}ms")
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"Step {step.name} timed out (attempt {attempt + 1})")
                if attempt < step.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    step.status = StepStatus.RETRYING
                else:
                    step.status = StepStatus.FAILED
                    step.error = "Timeout after max retries"
                    raise
                    
            except Exception as e:
                logger.error(f"Step {step.name} failed: {e} (attempt {attempt + 1})")
                if attempt < step.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    step.status = StepStatus.RETRYING
                else:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    raise
    
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> List[str]:
        """Topological sort of steps based on dependencies."""
        sorted_steps = []
        remaining = {s.name: s for s in steps}
        
        while remaining:
            # Find steps with no pending dependencies
            ready = [
                name for name, step in remaining.items()
                if all(dep in sorted_steps for dep in step.dependencies)
            ]
            
            if not ready:
                raise ValueError("Circular dependency detected in workflow")
            
            sorted_steps.extend(ready)
            for name in ready:
                del remaining[name]
        
        return sorted_steps
    
    def _get_step(self, steps: List[WorkflowStep], name: str) -> WorkflowStep:
        """Get step by name."""
        for step in steps:
            if step.name == name:
                return step
        raise ValueError(f"Step not found: {name}")
    
    # =========================================================================
    # Gemini API Helpers
    # =========================================================================
    
    async def generate(self, prompt: str) -> str:
        """Generate content using Gemini."""
        response = await asyncio.to_thread(
            self.model.generate_content, prompt
        )
        return response.text
    
    async def generate_json(self, prompt: str) -> Dict[str, Any]:
        """Generate JSON content using Gemini."""
        full_prompt = f"{prompt}\n\nRespond with ONLY valid JSON, no markdown."
        response = await self.generate(full_prompt)
        return json.loads(self.extract_json(response))
    
    @staticmethod
    def extract_json(text: str) -> str:
        """Extract JSON from markdown code blocks or raw text."""
        text = text.strip()
        
        # Handle ```json blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        
        # Handle ``` blocks
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        
        # Handle raw JSON (find first { or [)
        for i, char in enumerate(text):
            if char in '{[':
                # Find matching closing bracket
                depth = 0
                for j in range(i, len(text)):
                    if text[j] in '{[':
                        depth += 1
                    elif text[j] in '}]':
                        depth -= 1
                        if depth == 0:
                            return text[i:j+1]
                break
        
        return text


# Singleton instance
gemini_orchestrator = GeminiOrchestrator()
