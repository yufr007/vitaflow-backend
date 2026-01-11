"""VitaFlow API - Routes Package."""

from app.routes import (
    auth,
    user,
    form_check,
    workout,
    meal_plan,
    shopping,
    coaching,
    subscription,
)

__all__ = [
    "auth",
    "user",
    "form_check",
    "workout",
    "meal_plan",
    "shopping",
    "coaching",
    "subscription",
]
