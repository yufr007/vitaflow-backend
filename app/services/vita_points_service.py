# app/services/vita_points_service.py
"""
VitaFlow API - Vita Points Calculation Service.

Calculates "Vita Points" - a gamified health scoring system based on
WHO HEAT (Health Economic Assessment Tool) methodology, adapted for nutrition.

Vita Points reward users for:
1. Adherence to WHO dietary guidelines
2. Balanced macronutrient distribution
3. Nutrient density (vitamins, minerals, fiber)
4. Meal timing and consistency

Source methodology: WHO HEAT Tool (https://www.who.int/tools/heat)
Adapted for VitaFlow nutrition application.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class VitaPointsBreakdown:
    """Detailed breakdown of Vita Points calculation."""
    total_points: int
    protein_points: int
    fiber_points: int
    low_sugar_points: int
    vegetable_points: int
    balanced_macro_points: int
    who_compliance_points: int
    bonus_points: int
    explanation: str


class VitaPointsService:
    """
    Service for calculating Vita Points based on nutritional quality.
    
    Scoring System (per meal):
    - Protein Quality: 0-15 points
    - Fiber Content: 0-10 points
    - Low Sugar: 0-10 points
    - Vegetables/Fruits: 0-10 points
    - Balanced Macros: 0-10 points
    - WHO Compliance: 0-15 points
    - Bonus (variety, timing): 0-5 points
    
    Max per meal: 75 points
    Max per day (3 meals): 225 points
    Max per week: 1,575 points
    """
    
    # Scoring thresholds
    PROTEIN_PER_POINT = 5  # 1 point per 5g protein (max 15 points = 75g)
    FIBER_PER_POINT = 2.5  # 1 point per 2.5g fiber (max 10 points = 25g/day)
    SUGAR_LOW_THRESHOLD = 10  # grams - under this gets full points
    VEGETABLE_SERVING_POINTS = 2  # 2 points per vegetable serving (max 5 servings)
    
    def calculate_meal_points(
        self,
        meal: Dict[str, Any]
    ) -> VitaPointsBreakdown:
        """
        Calculate Vita Points for a single meal.
        
        Args:
            meal: Meal data with macros, ingredients, etc.
        
        Returns:
            VitaPointsBreakdown with detailed scoring.
        """
        macros = meal.get("macros", {})
        ingredients = meal.get("ingredients", [])
        
        # Protein points (max 15)
        protein = macros.get("protein", 0)
        protein_points = min(15, int(protein / self.PROTEIN_PER_POINT))
        
        # Fiber points (max 10)
        fiber = macros.get("fiber", 0)
        fiber_points = min(10, int(fiber / self.FIBER_PER_POINT))
        
        # Low sugar points (max 10)
        sugar = macros.get("sugar", 0)
        if sugar <= 5:
            low_sugar_points = 10
        elif sugar <= 10:
            low_sugar_points = 7
        elif sugar <= 15:
            low_sugar_points = 4
        elif sugar <= 25:
            low_sugar_points = 2
        else:
            low_sugar_points = 0
        
        # Vegetable points (max 10)
        vegetable_keywords = [
            "spinach", "broccoli", "kale", "lettuce", "tomato", "pepper",
            "carrot", "celery", "cucumber", "zucchini", "asparagus",
            "cauliflower", "cabbage", "onion", "garlic", "mushroom",
            "eggplant", "squash", "beans", "peas", "corn", "salad"
        ]
        vegetable_count = sum(
            1 for ing in ingredients
            if any(veg in ing.lower() for veg in vegetable_keywords)
        )
        vegetable_points = min(10, vegetable_count * self.VEGETABLE_SERVING_POINTS)
        
        # Balanced macro points (max 10)
        # Ideal: 30% protein, 40% carbs, 30% fat
        carbs = macros.get("carbs", 0)
        fat = macros.get("fat", 0)
        total_macros = protein + carbs + fat
        
        if total_macros > 0:
            protein_ratio = protein / total_macros
            carb_ratio = carbs / total_macros
            fat_ratio = fat / total_macros
            
            # Score based on how close to ideal ratios
            protein_diff = abs(0.30 - protein_ratio)
            carb_diff = abs(0.40 - carb_ratio)
            fat_diff = abs(0.30 - fat_ratio)
            
            avg_diff = (protein_diff + carb_diff + fat_diff) / 3
            balanced_macro_points = max(0, int(10 - (avg_diff * 50)))
        else:
            balanced_macro_points = 0
        
        # WHO compliance points (max 15)
        who_compliance_points = 0
        if macros.get("sodium", 0) <= 0.67:  # ~2g/day / 3 meals
            who_compliance_points += 5
        if sugar <= 25:  # Reasonable per-meal sugar
            who_compliance_points += 5
        if fiber >= 8:  # ~25g/day / 3 meals
            who_compliance_points += 5
        
        # Bonus points (max 5)
        bonus_points = 0
        # Bonus for variety (3+ ingredients)
        if len(ingredients) >= 3:
            bonus_points += 2
        # Bonus for whole foods (no processed keywords)
        processed_keywords = ["fried", "processed", "instant", "candy", "soda"]
        if not any(kw in str(ingredients).lower() for kw in processed_keywords):
            bonus_points += 3
        
        # Calculate total
        total = (
            protein_points + fiber_points + low_sugar_points +
            vegetable_points + balanced_macro_points + 
            who_compliance_points + bonus_points
        )
        
        # Build explanation
        explanation = f"Protein: {protein}g (+{protein_points}pts), "
        explanation += f"Fiber: {fiber}g (+{fiber_points}pts), "
        explanation += f"Low Sugar (+{low_sugar_points}pts), "
        explanation += f"Vegetables (+{vegetable_points}pts)"
        
        return VitaPointsBreakdown(
            total_points=total,
            protein_points=protein_points,
            fiber_points=fiber_points,
            low_sugar_points=low_sugar_points,
            vegetable_points=vegetable_points,
            balanced_macro_points=balanced_macro_points,
            who_compliance_points=who_compliance_points,
            bonus_points=bonus_points,
            explanation=explanation
        )
    
    def calculate_day_points(
        self,
        meals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate Vita Points for all meals in a day.
        
        Args:
            meals: List of meal dictionaries.
        
        Returns:
            Daily summary with total and per-meal breakdown.
        """
        meal_breakdowns = []
        total_points = 0
        
        for meal in meals:
            breakdown = self.calculate_meal_points(meal)
            meal_breakdowns.append({
                "meal_name": meal.get("name", "Unknown"),
                "points": breakdown.total_points,
                "breakdown": {
                    "protein": breakdown.protein_points,
                    "fiber": breakdown.fiber_points,
                    "low_sugar": breakdown.low_sugar_points,
                    "vegetables": breakdown.vegetable_points,
                    "balanced_macros": breakdown.balanced_macro_points,
                    "who_compliance": breakdown.who_compliance_points,
                    "bonus": breakdown.bonus_points
                },
                "explanation": breakdown.explanation
            })
            total_points += breakdown.total_points
        
        # Calculate percentage of max possible
        max_possible = len(meals) * 75
        percentage = (total_points / max_possible * 100) if max_possible > 0 else 0
        
        # Determine tier
        if percentage >= 80:
            tier = "Excellent"
            tier_message = "Outstanding nutrition! You're maximizing your health potential."
        elif percentage >= 60:
            tier = "Good"
            tier_message = "Great choices! Small improvements can push you to excellence."
        elif percentage >= 40:
            tier = "Moderate"
            tier_message = "Room for improvement. Focus on protein and vegetables."
        else:
            tier = "Needs Improvement"
            tier_message = "Consider more whole foods and balanced macros."
        
        return {
            "total_points": total_points,
            "max_possible": max_possible,
            "percentage": round(percentage, 1),
            "tier": tier,
            "tier_message": tier_message,
            "meals": meal_breakdowns
        }
    
    def calculate_plan_points(
        self,
        plan_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate Vita Points for an entire meal plan (7 days).
        
        Args:
            plan_data: Full meal plan with days and meals.
        
        Returns:
            Weekly summary with daily breakdowns.
        """
        days_data = plan_data.get("days", [])
        daily_summaries = []
        weekly_total = 0
        
        for day in days_data:
            meals = day.get("meals", [])
            day_result = self.calculate_day_points(meals)
            daily_summaries.append({
                "day": day.get("day", len(daily_summaries) + 1),
                **day_result
            })
            weekly_total += day_result["total_points"]
        
        # Weekly max = 7 days * 3 meals * 75 points = 1,575
        max_weekly = len(days_data) * 3 * 75
        weekly_percentage = (weekly_total / max_weekly * 100) if max_weekly > 0 else 0
        
        return {
            "weekly_vita_points": weekly_total,
            "weekly_max": max_weekly,
            "weekly_percentage": round(weekly_percentage, 1),
            "daily_breakdowns": daily_summaries,
            "methodology": "Based on WHO HEAT methodology, adapted for nutrition",
            "source": "https://www.who.int/tools/heat"
        }


# Singleton instance
vita_points_service = VitaPointsService()
