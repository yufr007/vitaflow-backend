# app/routes/subscription.py
"""VitaFlow API - Subscription Routes (MongoDB)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import uuid
import os
import logging
import stripe

from app.models.mongodb import SubscriptionDocument, UserDocument
from app.dependencies import get_current_user_id

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Stripe Price IDs (created Jan 1, 2026)
STRIPE_PRICES = {
    "pro_monthly": "price_1SkmCjQkZVARBPrXZjg7xEk4",  # $19.99/month
    "pro_annual": "price_1SkmEVQkZVARBPrXy5Ddp146",   # $179/year
    "elite_monthly": "price_1SkmJ7QkZVARBPrXBPBd05z5", # $29.99/month
    "elite_annual": "price_1SkmQzQkZVARBPrXy8nUljFB",  # $269/year
}

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class CheckoutSessionRequest(BaseModel):
    tier: str  # "pro" or "elite"
    interval: str  # "monthly" or "annual"


@router.get("/status")
async def get_subscription_status(user_id: str = Depends(get_current_user_id)):
    """Get current subscription status."""
    sub = await SubscriptionDocument.find_one(
        SubscriptionDocument.user_id == uuid.UUID(user_id)
    )
    if not sub:
        return {"tier": "free", "status": "active"}
    
    return {
        "tier": sub.tier,
        "status": sub.status,
        "stripe_customer_id": sub.stripe_customer_id,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
    }


@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutSessionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create Stripe checkout session."""
    try:
        # Get user email
        user = await UserDocument.find_one(UserDocument.id == uuid.UUID(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Select price ID based on tier + interval
        price_key = f"{request.tier}_{request.interval}"
        price_id = STRIPE_PRICES.get(price_key)
        
        if not price_id:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid tier/interval combination. Use tier='pro' or 'elite', interval='monthly' or 'annual'"
            )
        
        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            customer_email=user.email,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{FRONTEND_URL}/dashboard?upgrade=success&tier={request.tier}",
            cancel_url=f"{FRONTEND_URL}/dashboard?upgrade=cancelled",
            metadata={
                "user_id": str(user_id),
                "tier": request.tier,
                "interval": request.interval,
            }
        )
        
        logger.info(f"Created Stripe checkout session {session.id} for user {user_id}")
        
        return {
            "session_id": session.id,
            "url": session.url
        }
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel")
async def cancel_subscription(user_id: str = Depends(get_current_user_id)):
    """Cancel subscription."""
    try:
        # Find user's subscription
        sub = await SubscriptionDocument.find_one(
            SubscriptionDocument.user_id == uuid.UUID(user_id)
        )
        
        if not sub or not sub.stripe_subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        # Cancel at period end (don't revoke access immediately)
        subscription = stripe.Subscription.modify(
            sub.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Update local record
        sub.status = "canceling"
        await sub.save()
        
        logger.info(f"Cancelled subscription {sub.stripe_subscription_id} for user {user_id}")
        
        return {
            "message": "Subscription will be cancelled at the end of the billing period",
            "cancel_at": subscription.cancel_at
        }
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))