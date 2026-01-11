"""VitaFlow API - Pydantic Schemas Package."""

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
)
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfile,
)
from app.schemas.form_check import (
    FormCheckRequest,
    FormCheckResponse,
)
from app.schemas.workout import (
    WorkoutRequest,
    WorkoutResponse,
    WorkoutFeedbackRequest,
)
from app.schemas.meal_plan import (
    MealPlanRequest,
    MealPlanResponse,
    MealLogRequest,
)
from app.schemas.shopping import (
    ShoppingListRequest,
    ShoppingListResponse,
    PriceCheckRequest,
    CheckoutRequest,
)
from app.schemas.coaching import (
    CoachingMessageResponse,
    CoachingFeedbackRequest,
)
from app.schemas.recovery import (
    RecoveryMetricsInput,
    RecoveryProtocol,
    RecoveryAssessmentResponse,
    RecoveryHistoryResponse,
    RecoveryQuickCheck,
)

__all__ = [
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserProfile",
    # Form Check
    "FormCheckRequest",
    "FormCheckResponse",
    # Workout
    "WorkoutRequest",
    "WorkoutResponse",
    "WorkoutFeedbackRequest",
    # Meal Plan
    "MealPlanRequest",
    "MealPlanResponse",
    "MealLogRequest",
    # Shopping
    "ShoppingListRequest",
    "ShoppingListResponse",
    "PriceCheckRequest",
    "CheckoutRequest",
    # Coaching
    "CoachingMessageResponse",
    "CoachingFeedbackRequest",
    # Recovery
    "RecoveryMetricsInput",
    "RecoveryProtocol",
    "RecoveryAssessmentResponse",
    "RecoveryHistoryResponse",
    "RecoveryQuickCheck",
]
