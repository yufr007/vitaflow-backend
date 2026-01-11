# app/workflows/shopping_optimizer.py
"""
VitaFlow Shopping Optimizer - Gemini-Based Multi-Step Workflow.

Production-grade shopping optimization using Gemini orchestration:
1. Extract ingredients from meal plan
2. Standardize ingredient names
3. Estimate prices for multiple stores (parallel)
4. Optimize shopping route

This replaces Azure Foundry (not available on student accounts).
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.services.gemini_orchestrator import (
    GeminiOrchestrator,
    WorkflowStep,
    WorkflowResult,
    gemini_orchestrator
)

logger = logging.getLogger(__name__)


class ShoppingOptimizerWorkflow:
    """
    Production shopping optimizer using Gemini orchestration.
    
    Multi-step workflow with proper error handling, retry logic,
    and state management. Uses AI-estimated pricing (can be enhanced
    with real store APIs later).
    """
    
    def __init__(self, orchestrator: GeminiOrchestrator = None):
        self.orchestrator = orchestrator or gemini_orchestrator
    
    async def optimize(
        self,
        meal_plan_data: Dict[str, Any],
        user_location: Dict[str, Any],
        budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute complete shopping optimization workflow.
        
        Args:
            meal_plan_data: Meal plan with days and meals
            user_location: User's location (city, state, country)
            budget: Optional weekly budget constraint
        
        Returns:
            Optimized shopping plan with stores, prices, and route
        """
        workflow_id = f"shopping_{int(time.time())}"
        
        # Define workflow steps
        steps = [
            WorkflowStep(
                name="extract_ingredients",
                function=self._extract_ingredients,
                dependencies=[],
                max_retries=3,
                timeout=30
            ),
            WorkflowStep(
                name="standardize_ingredients",
                function=self._standardize_ingredients,
                dependencies=["extract_ingredients"],
                max_retries=3,
                timeout=25
            ),
            WorkflowStep(
                name="estimate_prices",
                function=self._estimate_prices,
                dependencies=["standardize_ingredients"],
                max_retries=3,
                timeout=40
            ),
            WorkflowStep(
                name="optimize_route",
                function=self._optimize_route,
                dependencies=["estimate_prices"],
                max_retries=3,
                timeout=30
            )
        ]
        
        # Build context
        context = {
            "meal_plan": meal_plan_data,
            "location": user_location,
            "budget": budget
        }
        
        # Execute workflow
        result = await self.orchestrator.execute_workflow(
            workflow_id, steps, context
        )
        
        if result.success:
            return self._format_success_response(result)
        else:
            return self._format_fallback_response(result, meal_plan_data)
    
    # =========================================================================
    # Workflow Steps
    # =========================================================================
    
    async def _extract_ingredients(
        self,
        orchestrator: GeminiOrchestrator,
        context: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> List[Dict]:
        """Step 1: Extract ingredients from meal plan."""
        meal_plan = context.get("meal_plan", {})
        
        prompt = f"""You are a meal plan ingredient extractor.

Extract ALL ingredients from this meal plan with quantities.

Meal Plan:
{meal_plan}

Return ONLY a valid JSON array:
[
  {{"name": "chicken breast", "quantity": "500g", "category": "protein"}},
  {{"name": "brown rice", "quantity": "2 cups", "category": "grain"}},
  ...
]

Categories: protein, dairy, produce, grain, pantry, frozen, other

Be thorough - extract every single ingredient mentioned."""

        result = await orchestrator.generate_json(prompt)
        
        # Validate response
        if isinstance(result, dict) and "ingredients" in result:
            return result["ingredients"]
        elif isinstance(result, list):
            return result
        else:
            raise ValueError("Invalid ingredients format from AI")
    
    async def _standardize_ingredients(
        self,
        orchestrator: GeminiOrchestrator,
        context: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> List[Dict]:
        """Step 2: Standardize ingredient names for store search."""
        ingredients = previous.get("extract_ingredients", [])
        
        prompt = f"""You are a grocery search optimizer.

Standardize these ingredient names for grocery store searches.

Rules:
- Convert "2 chicken breasts" → "chicken breast, 500g"
- Use common grocery product names
- Combine duplicate ingredients and sum quantities
- Remove cooking instructions (diced, chopped, etc.)
- Keep category information

Ingredients:
{ingredients}

Return ONLY a valid JSON array with same format:
[
  {{"name": "chicken breast", "quantity": "1kg", "category": "protein", "searchTerm": "chicken breast boneless"}},
  ...
]"""

        result = await orchestrator.generate_json(prompt)
        
        if isinstance(result, dict) and "ingredients" in result:
            return result["ingredients"]
        return result if isinstance(result, list) else []
    
    async def _estimate_prices(
        self,
        orchestrator: GeminiOrchestrator,
        context: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        """Step 3: Estimate prices for multiple stores."""
        ingredients = previous.get("standardize_ingredients", [])
        location = context.get("location", {})
        
        city = location.get("city", "Sydney")
        country = location.get("country", "Australia")
        
        # Adjust store list based on country
        if country == "Australia":
            stores = ["Woolworths", "Coles", "Aldi", "IGA"]
        else:
            stores = ["Walmart", "Kroger", "Costco", "Aldi"]
        
        prompt = f"""You are a grocery pricing expert familiar with {country} retail prices.

For a shopper in {city}, {country}, estimate realistic 2024 prices at these retailers:
{', '.join(stores)}

Ingredients to price:
{ingredients}

Return ONLY valid JSON:
{{
  "{stores[0]}": [
    {{"ingredient": "chicken breast", "price": 12.99, "unit": "per kg", "inStock": true}}
  ],
  "{stores[1]}": [...],
  ...
}}

Use realistic current prices. Aldi should generally be cheapest.
Mark items as inStock: false if typically hard to find at that store."""

        return await orchestrator.generate_json(prompt)
    
    async def _optimize_route(
        self,
        orchestrator: GeminiOrchestrator,
        context: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 4: Optimize shopping route and store selection."""
        ingredients = previous.get("standardize_ingredients", [])
        store_prices = previous.get("estimate_prices", {})
        location = context.get("location", {})
        budget = context.get("budget")
        
        prompt = f"""You are a shopping optimization expert.

Given these store prices and a shopper in {location.get('city', 'Unknown')}, 
optimize the shopping strategy.

Ingredients needed:
{ingredients}

Store prices:
{store_prices}

Budget: {"$" + str(budget) if budget else "No limit"}

Consider:
1. Total cost at each store
2. Whether to split between stores (only if savings > $10)
3. Organize shopping list by typical store layout

Return ONLY valid JSON:
{{
  "recommendation": "single_store" or "split_stores",
  "primaryStore": {{
    "name": "Store Name",
    "items": [{{"name": "item", "price": 1.99, "quantity": "1kg"}}],
    "total": 45.50,
    "address": "Optional address"
  }},
  "secondaryStore": null or {{...}},
  "totalCost": 45.50,
  "estimatedSavings": 12.00,
  "shoppingRoute": ["Produce", "Dairy", "Meat", "Pantry", "Frozen"],
  "tips": ["Buy rice in bulk", "Check weekly specials"],
  "budgetStatus": "under_budget" or "over_budget"
}}"""

        return await orchestrator.generate_json(prompt)
    
    # =========================================================================
    # Response Formatting
    # =========================================================================
    
    def _format_success_response(self, result: WorkflowResult) -> Dict[str, Any]:
        """Format successful workflow result."""
        route_result = result.results.get("optimize_route", {})
        
        return {
            "success": True,
            "recommendation": route_result.get("recommendation", "single_store"),
            "primaryStore": route_result.get("primaryStore", {}),
            "secondaryStore": route_result.get("secondaryStore"),
            "totalCost": route_result.get("totalCost", 0),
            "estimatedSavings": route_result.get("estimatedSavings", 0),
            "shoppingRoute": route_result.get("shoppingRoute", []),
            "tips": route_result.get("tips", []),
            "ingredients": result.results.get("standardize_ingredients", []),
            "storePrices": result.results.get("estimate_prices", {}),
            "workflowDurationMs": result.total_duration_ms,
            "aiProvider": "gemini_orchestration"
        }
    
    def _format_fallback_response(
        self,
        result: WorkflowResult,
        meal_plan: Dict
    ) -> Dict[str, Any]:
        """Format fallback response when workflow fails."""
        return {
            "success": False,
            "recommendation": "fallback",
            "primaryStore": {"name": "Your Local Store", "items": [], "total": 0},
            "totalCost": 0,
            "estimatedSavings": 0,
            "shoppingRoute": ["Produce", "Dairy", "Meat", "Pantry", "Frozen"],
            "tips": ["Workflow encountered an issue - basic list provided"],
            "error": result.error,
            "completedSteps": result.completed_steps,
            "failedSteps": result.failed_steps,
            "workflowDurationMs": result.total_duration_ms,
            "aiProvider": "fallback"
        }


# Factory function
def create_shopping_optimizer() -> ShoppingOptimizerWorkflow:
    """Create a shopping optimizer workflow instance."""
    return ShoppingOptimizerWorkflow()


# Default instance
shopping_optimizer = ShoppingOptimizerWorkflow()
