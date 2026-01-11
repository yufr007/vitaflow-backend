"""
VitaFlow API - Stripe Service.

Handles all Stripe payment operations including Checkout Sessions,
subscription management, and webhook processing.
"""

import logging
import os
from typing import Optional, Dict, Any

import stripe
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://vitaflow-frontend-nyacgd6nxa-km.a.run.app")
BACKEND_URL = os.getenv("BACKEND_URL", "https://vitaflow-backend.azurewebsites.net")

# Stripe Product IDs (create these in Stripe Dashboard or via API)
STRIPE_PRODUCTS = {
    "pro_monthly": os.getenv("STRIPE_PRODUCT_PRO_MONTHLY"),
    "pro_annual": os.getenv("STRIPE_PRODUCT_PRO_ANNUAL"),
}


class StripeService:
    """Service for handling Stripe payment operations."""
    
    @staticmethod
    def create_or_get_customer(db: Session, user: User) -> str:
        """
        Create or retrieve Stripe customer ID for a user.
        
        Args:
            db: Database session.
            user: User model instance.
            
        Returns:
            Stripe customer ID.
        """
        try:
            # Check if user already has a subscription with customer ID
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user.id
            ).first()
            
            if subscription and subscription.stripe_customer_id:
                return subscription.stripe_customer_id
            
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={"user_id": str(user.id)}
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer: {str(e)}")
            raise
    
    @staticmethod
    def create_checkout_session(
        db: Session,
        user: User,
        plan_type: str,  # "monthly" or "annual"
    ) -> Dict[str, str]:
        """
        Create a Stripe Checkout Session for subscription upgrade.
        
        Args:
            db: Database session.
            user: User model instance.
            plan_type: "monthly" ($19.99) or "annual" ($179.99).
            
        Returns:
            Dict with session_id and client_secret.
            
        Raises:
            ValueError: If plan_type is invalid or Stripe product ID not configured.
            stripe.error.StripeError: If Stripe API call fails.
        """
        # Validate plan type
        if plan_type not in ["monthly", "annual"]:
            raise ValueError(f"Invalid plan type: {plan_type}")
        
        # Get or create Stripe customer
        customer_id = StripeService.create_or_get_customer(db, user)
        
        # Get product ID from environment
        product_key = f"pro_{plan_type}"
        price_id = STRIPE_PRODUCTS.get(product_key)
        
        if not price_id:
            raise ValueError(f"Stripe price ID not configured for {product_key}")
        
        try:
            # Create Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                customer=customer_id,
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=f"{FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{FRONTEND_URL}/subscription/canceled",
                metadata={
                    "user_id": str(user.id),
                    "plan_type": plan_type,
                },
            )
            
            logger.info(f"Created Checkout Session {checkout_session.id} for user {user.id}")
            
            return {
                "session_id": checkout_session.id,
                "client_secret": checkout_session.client_secret or "",
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Checkout Session: {str(e)}")
            raise
    
    @staticmethod
    def cancel_subscription_at_period_end(stripe_subscription_id: str) -> Dict[str, Any]:
        """
        Cancel a Stripe subscription at the end of the billing period.
        
        User loses access at period_end date, not immediately.
        
        Args:
            stripe_subscription_id: Stripe subscription ID.
            
        Returns:
            Updated subscription data.
            
        Raises:
            stripe.error.StripeError: If Stripe API call fails.
        """
        try:
            subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            logger.info(f"Marked subscription {stripe_subscription_id} for cancellation at period end")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            raise
    
    @staticmethod
    def handle_checkout_completed(
        db: Session,
        session_data: Dict[str, Any]
    ) -> Optional[Subscription]:
        """
        Handle checkout.session.completed webhook event.
        
        Updates subscription status in database when payment is successful.
        
        Args:
            db: Database session.
            session_data: Checkout session data from webhook.
            
        Returns:
            Updated Subscription model or None if not found.
        """
        try:
            customer_id = session_data.get("customer")
            session_id = session_data.get("id")
            subscription_id = session_data.get("subscription")
            metadata = session_data.get("metadata", {})
            
            user_id = metadata.get("user_id")
            plan_type = metadata.get("plan_type")
            
            if not user_id or not subscription_id:
                logger.warning(f"Missing user_id or subscription_id in webhook data")
                return None
            
            # Update or create subscription record
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).first()
            
            if not subscription:
                subscription = Subscription(
                    user_id=user_id,
                    stripe_customer_id=customer_id,
                )
                db.add(subscription)
            
            subscription.stripe_subscription_id = subscription_id
            subscription.stripe_session_id = session_id
            subscription.plan_type = "pro"
            subscription.billing_cycle = plan_type
            subscription.status = "active"
            
            # Fetch subscription details from Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            subscription.current_period_start = stripe_subscription.current_period_start
            subscription.current_period_end = stripe_subscription.current_period_end
            
            db.commit()
            logger.info(f"Updated subscription for user {user_id} from webhook")
            
            return subscription
            
        except Exception as e:
            logger.error(f"Error handling checkout completed: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def handle_invoice_paid(
        db: Session,
        invoice_data: Dict[str, Any]
    ) -> Optional[Subscription]:
        """
        Handle invoice.payment_succeeded webhook event.
        
        Updates subscription periods for recurring payments.
        
        Args:
            db: Database session.
            invoice_data: Invoice data from webhook.
            
        Returns:
            Updated Subscription model or None if not found.
        """
        try:
            subscription_id = invoice_data.get("subscription")
            
            if not subscription_id:
                return None
            
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_id
            ).first()
            
            if subscription:
                # Fetch latest subscription data from Stripe
                stripe_subscription = stripe.Subscription.retrieve(subscription_id)
                subscription.status = stripe_subscription.status
                subscription.current_period_start = stripe_subscription.current_period_start
                subscription.current_period_end = stripe_subscription.current_period_end
                
                db.commit()
                logger.info(f"Updated subscription {subscription_id} from invoice.paid webhook")
                
                return subscription
            
        except Exception as e:
            logger.error(f"Error handling invoice paid: {str(e)}")
            db.rollback()
            raise
        
        return None
    
    @staticmethod
    def handle_customer_subscription_deleted(
        db: Session,
        subscription_data: Dict[str, Any]
    ) -> Optional[Subscription]:
        """
        Handle customer.subscription.deleted webhook event.
        
        Updates subscription status when user cancels.
        
        Args:
            db: Database session.
            subscription_data: Subscription data from webhook.
            
        Returns:
            Updated Subscription model or None if not found.
        """
        try:
            stripe_subscription_id = subscription_data.get("id")
            
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == stripe_subscription_id
            ).first()
            
            if subscription:
                subscription.status = "canceled"
                subscription.plan_type = "free"
                subscription.canceled_at = subscription_data.get("canceled_at")
                
                db.commit()
                logger.info(f"Marked subscription {stripe_subscription_id} as canceled")
                
                return subscription
            
        except Exception as e:
            logger.error(f"Error handling subscription deleted: {str(e)}")
            db.rollback()
            raise
        
        return None
    
    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        sig_header: str,
        endpoint_secret: str
    ) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature.
        
        Args:
            payload: Raw request body.
            sig_header: Stripe signature header.
            endpoint_secret: Webhook endpoint secret.
            
        Returns:
            Parsed event data.
            
        Raises:
            ValueError: If signature verification fails.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                endpoint_secret
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid Stripe webhook payload: {str(e)}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {str(e)}")
            raise ValueError(f"Invalid signature: {str(e)}")
