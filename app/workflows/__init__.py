# app/workflows/__init__.py
"""
VitaFlow Workflows Package.

Azure Foundry multi-agent workflows for complex AI operations.
"""

from app.workflows.shopping_optimizer import (
    ShoppingOptimizerWorkflow,
    create_shopping_optimizer
)
from app.workflows.coaching_agents import (
    CoachingAgentsWorkflow,
    create_coaching_workflow
)

__all__ = [
    "ShoppingOptimizerWorkflow",
    "create_shopping_optimizer",
    "CoachingAgentsWorkflow",
    "create_coaching_workflow",
]
