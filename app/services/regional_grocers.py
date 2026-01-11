"""
VitaFlow Shopping Agent - Regional Grocer Integration

Supports price comparison across major grocers in:
- United States (Walmart, Kroger, Safeway, Whole Foods)
- Australia (Woolworths, Coles, Aldi, IGA)
- Europe (Tesco, Carrefour, Lidl, Aldi)
- Asia (FairPrice, ColdStorage, Don Quijote, Lotte Mart)

For PRO tier: Price comparison only
For ELITE tier: Auto-checkout integration (future)
"""

from typing import Dict, List, Optional
from enum import Enum


class Region(str, Enum):
    """Supported regions for grocery price comparison"""
    US = "us"
    AUSTRALIA = "au"
    UK = "uk"
    EUROPE = "eu"
    SINGAPORE = "sg"
    JAPAN = "jp"
    KOREA = "kr"


class GrocerChain(str, Enum):
    """Supported grocery chains"""
    # United States
    WALMART = "walmart"
    KROGER = "kroger"
    SAFEWAY = "safeway"
    WHOLE_FOODS = "whole_foods"
    TRADER_JOES = "trader_joes"
    
    # Australia
    WOOLWORTHS = "woolworths"
    COLES = "coles"
    ALDI_AU = "aldi_au"
    IGA = "iga"
    
    # United Kingdom
    TESCO = "tesco"
    SAINSBURYS = "sainsburys"
    ASDA = "asda"
    MORRISONS = "morrisons"
    
    # Europe
    CARREFOUR = "carrefour"
    LIDL = "lidl"
    ALDI_EU = "aldi_eu"
    EDEKA = "edeka"
    
    # Singapore
    FAIRPRICE = "fairprice"
    COLD_STORAGE = "cold_storage"
    GIANT = "giant"
    
    # Japan
    DON_QUIJOTE = "don_quijote"
    AEON = "aeon"
    LIFE = "life"
    
    # South Korea
    LOTTE_MART = "lotte_mart"
    EMART = "emart"
    HOMEPLUS = "homeplus"


# Regional grocer mappings
REGIONAL_GROCERS: Dict[Region, List[GrocerChain]] = {
    Region.US: [
        GrocerChain.WALMART,
        GrocerChain.KROGER,
        GrocerChain.SAFEWAY,
        GrocerChain.WHOLE_FOODS,
        GrocerChain.TRADER_JOES,
    ],
    Region.AUSTRALIA: [
        GrocerChain.WOOLWORTHS,
        GrocerChain.COLES,
        GrocerChain.ALDI_AU,
        GrocerChain.IGA,
    ],
    Region.UK: [
        GrocerChain.TESCO,
        GrocerChain.SAINSBURYS,
        GrocerChain.ASDA,
        GrocerChain.MORRISONS,
        GrocerChain.ALDI_EU,
    ],
    Region.EUROPE: [
        GrocerChain.CARREFOUR,
        GrocerChain.LIDL,
        GrocerChain.ALDI_EU,
        GrocerChain.EDEKA,
    ],
    Region.SINGAPORE: [
        GrocerChain.FAIRPRICE,
        GrocerChain.COLD_STORAGE,
        GrocerChain.GIANT,
    ],
    Region.JAPAN: [
        GrocerChain.DON_QUIJOTE,
        GrocerChain.AEON,
        GrocerChain.LIFE,
    ],
    Region.KOREA: [
        GrocerChain.LOTTE_MART,
        GrocerChain.EMART,
        GrocerChain.HOMEPLUS,
    ],
}


# Currency by region
REGIONAL_CURRENCY: Dict[Region, str] = {
    Region.US: "USD",
    Region.AUSTRALIA: "AUD",
    Region.UK: "GBP",
    Region.EUROPE: "EUR",
    Region.SINGAPORE: "SGD",
    Region.JAPAN: "JPY",
    Region.KOREA: "KRW",
}


def detect_region_from_country(country_code: str) -> Optional[Region]:
    """
    Detect region from ISO country code.
    
    Args:
        country_code: ISO 3166-1 alpha-2 code (e.g., 'US', 'AU', 'GB')
        
    Returns:
        Region enum or None if unsupported
    """
    country_to_region = {
        "US": Region.US,
        "AU": Region.AUSTRALIA,
        "GB": Region.UK,
        "UK": Region.UK,
        "FR": Region.EUROPE,
        "DE": Region.EUROPE,
        "ES": Region.EUROPE,
        "IT": Region.EUROPE,
        "NL": Region.EUROPE,
        "BE": Region.EUROPE,
        "SG": Region.SINGAPORE,
        "JP": Region.JAPAN,
        "KR": Region.KOREA,
    }
    
    return country_to_region.get(country_code.upper())


def get_grocers_for_region(region: Region) -> List[GrocerChain]:
    """
    Get available grocery chains for a region.
    
    Args:
        region: Region enum
        
    Returns:
        List of GrocerChain enums
    """
    return REGIONAL_GROCERS.get(region, [])


def get_currency_for_region(region: Region) -> str:
    """
    Get currency code for a region.
    
    Args:
        region: Region enum
        
    Returns:
        ISO 4217 currency code (e.g., 'USD', 'AUD')
    """
    return REGIONAL_CURRENCY.get(region, "USD")


# Grocer display names
GROCER_DISPLAY_NAMES: Dict[GrocerChain, str] = {
    # US
    GrocerChain.WALMART: "Walmart",
    GrocerChain.KROGER: "Kroger",
    GrocerChain.SAFEWAY: "Safeway",
    GrocerChain.WHOLE_FOODS: "Whole Foods",
    GrocerChain.TRADER_JOES: "Trader Joe's",
    # Australia
    GrocerChain.WOOLWORTHS: "Woolworths",
    GrocerChain.COLES: "Coles",
    GrocerChain.ALDI_AU: "Aldi",
    GrocerChain.IGA: "IGA",
    # UK
    GrocerChain.TESCO: "Tesco",
    GrocerChain.SAINSBURYS: "Sainsbury's",
    GrocerChain.ASDA: "Asda",
    GrocerChain.MORRISONS: "Morrisons",
    # Europe
    GrocerChain.CARREFOUR: "Carrefour",
    GrocerChain.LIDL: "Lidl",
    GrocerChain.ALDI_EU: "Aldi",
    GrocerChain.EDEKA: "Edeka",
    # Singapore
    GrocerChain.FAIRPRICE: "FairPrice",
    GrocerChain.COLD_STORAGE: "Cold Storage",
    GrocerChain.GIANT: "Giant",
    # Japan
    GrocerChain.DON_QUIJOTE: "Don Quijote",
    GrocerChain.AEON: "Aeon",
    GrocerChain.LIFE: "Life",
    # Korea
    GrocerChain.LOTTE_MART: "Lotte Mart",
    GrocerChain.EMART: "E-Mart",
    GrocerChain.HOMEPLUS: "Homeplus",
}


# Future: Auto-checkout support (Elite tier only)
ELITE_AUTO_CHECKOUT_SUPPORTED: Dict[GrocerChain, bool] = {
    # Phase 1: These grocers support API checkout
    GrocerChain.WOOLWORTHS: True,  # AU - Has API
    GrocerChain.COLES: True,       # AU - Has API
    GrocerChain.WALMART: False,    # US - No public API yet
    GrocerChain.KROGER: False,     # US - Beta API only
    # Add more as APIs become available
}
