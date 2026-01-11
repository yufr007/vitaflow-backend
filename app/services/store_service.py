"""
VitaFlow API - Store Service.

Provides localization logic for grocery stores based on user location.
"""

from typing import List, Dict, Any

class StoreService:
    """
    Service for determining local grocery stores based on user location.
    """
    
    # Store mapping by Country -> State
    STORES_BY_LOCATION = {
        'Australia': {
            'currency': 'AUD',
            'states': {
                'Victoria': ['Coles', 'Woolworths', 'Aldi', 'IGA', 'Costco', 'Harris Farm'],
                'New South Wales': ['Coles', 'Woolworths', 'Aldi', 'IGA', 'Costco'],
                'Queensland': ['Coles', 'Woolworths', 'Aldi', 'IGA', 'Costco'],
                'Western Australia': ['Coles', 'Woolworths', 'Aldi', 'IGA', 'Costco'],
                'DEFAULT': ['Coles', 'Woolworths', 'Aldi', 'IGA']
            }
        },
        'USA': {
            'currency': 'USD',
            'states': {
                'California': ['Walmart', 'Whole Foods', "Trader Joe's", 'Sprouts', 'Costco'],
                'New York': ['Walmart', 'Whole Foods', "Trader Joe's", 'Target', 'Costco'],
                'Texas': ['Walmart', 'HEB', 'Kroger', 'Whole Foods', 'Costco'],
                'Florida': ['Walmart', 'Publix', 'Whole Foods', 'Target', 'Costco'],
                'DEFAULT': ['Walmart', 'Target', 'Costco', 'Kroger', 'Whole Foods']
            }
        },
        'Canada': {
            'currency': 'CAD',
            'states': {
                'British Columbia': ['Costco', 'Walmart', 'Save-on-Foods', 'Safeway', 'IGA'],
                'Ontario': ['Costco', 'Walmart', 'Loblaws', 'Metro', 'Sobeys'],
                'Quebec': ['Costco', 'Walmart', 'Loblaws', 'Metro', 'IGA'],
                'DEFAULT': ['Costco', 'Walmart', 'Loblaws', 'Metro']
            }
        },
        'UK': {
            'currency': 'GBP',
            'states': {
                'DEFAULT': ['Tesco', "Sainsbury's", 'Asda', 'Morrisons', 'Waitrose', 'Aldi', 'Lidl', 'Marks & Spencer']
            }
        },
        'Germany': {
            'currency': 'EUR',
            'states': {
                'DEFAULT': ['Rewe', 'Edeka', 'Aldi', 'Lidl', 'Kaufland', 'Penny', 'Netto']
            }
        },
        'France': {
            'currency': 'EUR',
            'states': {
                'DEFAULT': ['Carrefour', 'E.Leclerc', 'Intermarché', 'Auchan', 'Lidl', 'Monoprix']
            }
        },
        'Italy': {
            'currency': 'EUR',
            'states': {
                'DEFAULT': ['Conad', 'Coop', 'Esselunga', 'Eurospin', 'Lidl', 'Carrefour']
            }
        },
        'Spain': {
            'currency': 'EUR',
            'states': {
                'DEFAULT': ['Mercadona', 'Carrefour', 'Lidl', 'Dia', 'Eroski', 'Alcampo']
            }
        },
        'Netherlands': {
            'currency': 'EUR',
            'states': {
                'DEFAULT': ['Albert Heijn', 'Jumbo', 'Lidl', 'Aldi', 'Plus']
            }
        },
        'New Zealand': {
            'currency': 'NZD',
            'states': {
                'DEFAULT': ['Countdown', 'New World', "PAK'nSAVE", 'FreshChoice', 'Four Square']
            }
        },
        'Japan': {
            'currency': 'JPY',
            'states': {
                'DEFAULT': ['Aeon', 'Ito-Yokado', 'Costco', 'Seiyu', 'Life', 'MaxValu', 'Don Quijote']
            }
        },
        'Singapore': {
            'currency': 'SGD',
            'states': {
                'DEFAULT': ['FairPrice', 'Cold Storage', 'Giant', 'Sheng Siong', 'RedMart']
            }
        },
        'South Korea': {
            'currency': 'KRW',
            'states': {
                'DEFAULT': ['E-Mart', 'Lotte Mart', 'Homeplus', 'Costco']
            }
        },
        'India': {
            'currency': 'INR',
            'states': {
                'DEFAULT': ['BigBasket', 'Reliance Fresh', 'DMart', 'Spencer\'s', 'Nature\'s Basket']
            }
        }
    }

    def get_local_stores(self, country: str, state: str = None) -> List[str]:
        """
        Get list of popular grocery stores for a specific location.
        
        Args:
            country: User's country (e.g., "Australia", "USA").
            state: User's state/region (optional).
            
        Returns:
            List[str]: List of store names.
        """
        if not country:
            return ['Local Market', 'Supermarket']
            
        country_data = self.STORES_BY_LOCATION.get(country)
        if not country_data:
            # Default fallback for unknown countries
            return ['Local Supermarket', 'Market']
            
        states = country_data.get('states', {})
        
        # Try specific state match
        if state and state in states:
            return states[state]
            
        # Fallback to country default
        return states.get('DEFAULT', ['Local Supermarket'])

    def get_currency(self, country: str) -> str:
        """
        Get currency code for a country.
        
        Args:
            country: User's country.
            
        Returns:
            str: ISO currency code (e.g., "AUD", "USD").
        """
        if not country:
            return 'USD'
            
        country_data = self.STORES_BY_LOCATION.get(country)
        return country_data.get('currency', 'USD') if country_data else 'USD'

# Global instance
store_service = StoreService()
