"""
VitaFlow API - MongoDB Models Package.

Export all Beanie ODM models for MongoDB operations.
"""

from app.models.mongodb import (
    UserDocument,
    SubscriptionDocument,
    FormCheckDocument,
    WorkoutDocument,
    MealPlanDocument,
    ShoppingListDocument,
    CoachingMessageDocument,
    RecoveryAssessmentDocument,
)

__all__ = [
    "UserDocument",
    "SubscriptionDocument",
    "FormCheckDocument",
    "WorkoutDocument",
    "MealPlanDocument",
    "ShoppingListDocument",
    "CoachingMessageDocument",
    "RecoveryAssessmentDocument",
]
