"""
VitaFlow API - Stripe Payment Service.

Stripe integration for Pro tier subscriptions and payment processing.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import stripe

from settings import settings


logger = logging.getLogger(__name__)


class StripeService:
    """
    Stripe payment service for subscription management.
    
    Handles customer creation, subscription management, and status checks.
    """
    
    # Pro tier price IDs (configured in Stripe Dashboard)
    # These should match the prices created for "VitaFlow Pro"
    PRO_PRICE_MONTHLY = "price_pro_monthly_1999" 
    PRO_PRICE_YEARLY = "price_pro_yearly_17999"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Stripe client.
        
        Args:
            api_key: Stripe secret key. Falls back to settings if not provided.
        """
        self.api_key = api_key or settings.STRIPE_SECRET_KEY
        if self.api_key:
            stripe.api_key = self.api_key
        self.logger = logging.getLogger(__name__)
    
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Create a Stripe customer.
        """
        if not self.api_key:
            self.logger.error("Stripe API key not configured")
            return None
        
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            self.logger.info(f"Created Stripe customer: {customer.id}")
            return customer.id
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe customer creation error: {str(e)}")
            return None
    
    def create_subscription(
        self,
        customer_id: str,
        interval: str = "month" # "month" or "year"
    ) -> Optional[Dict[str, Any]]:
        """
        Create a subscription for a customer.
        
        Args:
            customer_id: Stripe customer ID.
            interval: Billing interval ("month" or "year").
        
        Returns:
            Optional[Dict[str, Any]]: Subscription details.
        """
        if not self.api_key:
            self.logger.error("Stripe API key not configured")
            return None
        
        price_id = self.PRO_PRICE_YEARLY if interval == "year" else self.PRO_PRICE_MONTHLY
        
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                payment_settings={
                    "save_default_payment_method": "on_subscription"
                },
                expand=["latest_invoice.payment_intent"]
            )
            
            self.logger.info(f"Created subscription: {subscription.id} ({interval})")
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret
                if subscription.latest_invoice.payment_intent else None
            }
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe subscription creation error: {str(e)}")
            return None
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> bool:
        """
        Cancel a subscription.
        """
        if not self.api_key:
            self.logger.error("Stripe API key not configured")
            return False
        
        try:
            if immediately:
                stripe.Subscription.delete(subscription_id)
            else:
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            self.logger.info(f"Canceled subscription: {subscription_id}")
            return True
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe cancellation error: {str(e)}")
            return False
    
    def get_subscription_status(
        self,
        subscription_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get subscription status from Stripe.
        """
        if not self.api_key:
            self.logger.error("Stripe API key not configured")
            return None
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            return {
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end
            }
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe status check error: {str(e)}")
            return None
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify Stripe webhook signature.
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            self.logger.error("Stripe webhook secret not configured")
            return None
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except Exception as e:
            self.logger.error(f"Webhook error: {str(e)}")
            return None


# Global Stripe service instance
stripe_service = StripeService()