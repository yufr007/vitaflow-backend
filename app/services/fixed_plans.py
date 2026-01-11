"""
VitaFlow API - Fixed Plans Service.

Provides structured, non-AI generated plans for free tier users.
"""

from typing import Dict, Any, Optional

def get_fixed_workout_plan(goal: str, equipment: str) -> Optional[Dict[str, Any]]:
    """
    Get a structured generic workout plan based on goal and equipment.
    
    Args:
        goal: User's fitness goal.
        equipment: Comma-separated list of equipment.
        
    Returns:
        Optional[Dict[str, Any]]: 7-day workout plan or None if no match.
    """
    goal = goal.lower()
    equipment = equipment.lower()
    
    # Simple mapping logic for "Plan 4" style generic offerings
    # Logic: Weight Loss + Dumbbells + Resistance Bands = Plan 4
    
    if "weight" in goal and "loss" in goal:
        if "dumbbell" in equipment and "band" in equipment:
            return {
                "days": [
                    {
                        "day": 1,
                        "focus": "Full Body Fat Burn",
                        "exercises": [
                            {"name": "DB Goblet Squats", "sets": 3, "reps": "15", "duration_minutes": 5, "notes": "Hold one DB at chest height."},
                            {"name": "Band Row", "sets": 3, "reps": "15", "duration_minutes": 5, "notes": "Focus on squeezing shoulder blades."},
                            {"name": "DB Overhead Press", "sets": 3, "reps": "12", "duration_minutes": 5, "notes": "Keep core tight."},
                            {"name": "Mountain Climbers", "sets": 3, "reps": "30 sec", "duration_minutes": 5, "notes": "High intensity."}
                        ],
                        "rest_between_sets": "45 seconds",
                        "warmup": "5 min jumping jacks",
                        "cooldown": "5 min light stretching"
                    },
                    # ... other days would be populated here for a full 7-day structure ...
                ],
                "weekly_summary": "Standard Weight Loss Plan (Plan 4). Focus on high reps and minimal rest.",
                "tier": "free"
            }
        
    # Default generic plan if no specific match
    return {
        "days": [
            {
                "day": 1,
                "focus": "General Fitness",
                "exercises": [
                    {"name": "Bodyweight Squats", "sets": 3, "reps": "12", "duration_minutes": 5, "notes": "Standard form."},
                    {"name": "Push-ups", "sets": 3, "reps": "10", "duration_minutes": 5, "notes": "On knees if needed."},
                    {"name": "Plank", "sets": 3, "reps": "30 sec", "duration_minutes": 5, "notes": "Keep body straight."}
                ],
                "rest_between_sets": "60 seconds",
                "warmup": "5 min walk",
                "cooldown": "5 min stretching"
            }
        ],
        "weekly_summary": "Generic Daily Routine. Focused on overall health.",
        "tier": "free"
    }

def get_fixed_meal_plan(restrictions: str) -> Dict[str, Any]:
    """
    Get a generic meal plan for free users.
    """
    return {
        "days": [
            {
                "day": 1,
                "meals": [
                    {
                        "type": "Breakfast",
                        "name": "Oatmeal with Fruit",
                        "calories": 350,
                        "macros": {"protein": 10, "carbs": 50, "fat": 5},
                        "prep_time_minutes": 5,
                        "ingredients": ["Oats", "Banana", "Milk"]
                    }
                ]
            }
        ],
        "total_estimated_cost": 80.00,
        "tier": "free"
    }
