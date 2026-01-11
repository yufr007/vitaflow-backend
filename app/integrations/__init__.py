# app/integrations/__init__.py
"""
VitaFlow Integrations Package.

External API integrations for grocery stores, maps, etc.
"""

from app.integrations.store_apis import (
    StoreAPI,
    KrogerAPI,
    WalmartAPI,
    GoogleShoppingAPI,
    AustralianGroceryAPI,
    StoreAPIManager,
    store_api_manager,
    ProductMatch
)

__all__ = [
    "StoreAPI",
    "KrogerAPI", 
    "WalmartAPI",
    "GoogleShoppingAPI",
    "AustralianGroceryAPI",
    "StoreAPIManager",
    "store_api_manager",
    "ProductMatch"
]
